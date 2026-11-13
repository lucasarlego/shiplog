"""Sugestões de comentário para posts de outras pessoas (spec 008)."""

from __future__ import annotations

import base64
import binascii
import logging
import shutil
import threading
from pathlib import Path
from typing import Any, Callable

from ..errors import AppError, nao_encontrado
from ..storage.dao import Dao
from ..storage.db import now_iso
from .llm.base import LLMProvider, LLMRequest

log = logging.getLogger("shiplog.comments")

MAX_TEXTO = 10_000
MAX_IMAGENS = 6
MAX_BYTES = 5 * 1024 * 1024
ASSINATURAS = {
    ".png": (b"\x89PNG",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF8",),
    ".webp": (b"RIFF",),
}
PARAMS = {
    "objetivo": ("acrescentar", "apoiar", "perguntar", "discordar"),
    "tamanho": ("curto", "medio"),
    "idioma": ("auto", "pt", "en"),
}
PADRAO = {"objetivo": "acrescentar", "tamanho": "curto", "idioma": "auto"}

OBJETIVOS = {
    "acrescentar": "acrescentar valor à conversa com um ponto de vista, experiência ou complemento concreto",
    "apoiar": "reconhecer o trabalho/conquista de forma específica e genuína (nada de elogio genérico)",
    "perguntar": "fazer uma pergunta interessante que aprofunde o tema e convide o autor a responder",
    "discordar": "discordar ou trazer um contraponto com respeito, argumentando de forma construtiva",
}
TAMANHOS = {"curto": "1 a 3 frases (até ~300 caracteres)", "medio": "3 a 5 frases (até ~700 caracteres)"}
TAMANHOS_MEDIUM = {"curto": "2 a 4 frases (até ~400 caracteres)", "medio": "1 a 2 parágrafos (até ~1.200 caracteres)"}
PLATAFORMAS = {"linkedin": "LinkedIn", "medium": "Medium"}
STATUS = ("sugerido", "usado")


def tamanho(plataforma: str, t: str) -> str:
    return (TAMANHOS_MEDIUM if plataforma == "medium" else TAMANHOS)[t]


def regras(plataforma: str, tem_perfil: bool) -> list[str]:
    alvo = "artigo" if plataforma == "medium" else "post"
    r = [
        "Cada opção usa uma abordagem diferente, todas servindo ao objetivo pedido.",
        f"Seja específico: cite um ponto concreto do {alvo}. Nada de \"Ótimo {alvo}!\", \"Parabéns pelo conteúdo\" "
        "ou frases que serviriam para qualquer conteúdo.",
        "Natural e humano, como alguém que realmente leu. Sem hashtags, sem links, sem autopromoção, "
        "no máximo 1 emoji e só se combinar.",
        f"Não invente fatos sobre o autor do {alvo}, sobre quem comenta ou sobre o assunto.",
        f"Pode mencionar o autor do {alvo} pelo primeiro nome, se informado.",
    ]
    if plataforma == "medium":
        r.append("No Medium o comentário (\"response\") pode citar uma frase curta do artigo entre aspas e "
                 "aprofundar um ponto; evite resumir o artigo de volta para o autor.")
    if not tem_perfil:
        r.append("Não há perfil profissional configurado: não afirme experiências pessoais específicas "
                 "(\"já passei por isso\", \"no meu time fazemos…\"); comente a partir do conteúdo.")
    return r
IDIOMAS = {"auto": "o mesmo idioma do post", "pt": "português do Brasil", "en": "inglês"}

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "resumo_post": {"type": "string", "description": "1-2 frases sobre o que o post diz (incluindo as imagens)."},
        "sugestoes": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "abordagem": {"type": "string", "description": "Rótulo curto da abordagem (2-5 palavras)."},
                    "texto": {"type": "string", "description": "O comentário pronto para colar."},
                },
                "required": ["abordagem", "texto"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["resumo_post", "sugestoes"],
    "additionalProperties": False,
}


def _decodificar(nome: str, conteudo_base64: str) -> tuple[str, bytes]:
    ext = Path(nome or "").suffix.lower()
    if ext not in ASSINATURAS:
        raise AppError("validacao", f"Imagem '{nome}' em formato não suportado.", "Use PNG, JPG, GIF ou WEBP.", 422)
    try:
        dados = base64.b64decode(conteudo_base64, validate=True)
    except (binascii.Error, ValueError) as e:
        raise AppError("validacao", f"Imagem '{nome}' corrompida no envio.", "Tente colar de novo.", 422) from e
    if not dados or len(dados) > MAX_BYTES:
        raise AppError("validacao", f"Imagem '{nome}' vazia ou maior que 5 MB.", None, 422)
    if not dados.startswith(ASSINATURAS[ext]):
        raise AppError("validacao", f"'{nome}' não parece ser uma imagem {ext[1:].upper()}.", None, 422)
    return (".jpg" if ext == ".jpeg" else ext), dados


class CommentService:
    def __init__(self, dao: Dao, pasta: Path, provider: LLMProvider, health: Callable[[], dict[str, Any]]) -> None:
        self.dao = dao
        self.pasta = pasta
        self.provider = provider
        self.health = health
        self._lock = threading.Lock()

    def _dir(self, cid: int) -> Path:
        return self.pasta / str(cid)

    # -- CRUD ------------------------------------------------------------------
    def criar(self, texto_post: str, imagens: list[dict[str, str]], autor: str = "", link: str = "",
              plataforma: str = "linkedin") -> dict[str, Any]:
        if plataforma not in PLATAFORMAS:
            raise AppError("validacao", "Plataforma inválida.", "Use linkedin ou medium.", 422)
        texto_post = (texto_post or "").strip()
        if not texto_post and not imagens:
            raise AppError("validacao", "Cole o texto do post ou adicione pelo menos uma imagem.", None, 422)
        if len(texto_post) > MAX_TEXTO:
            raise AppError("validacao", f"O texto do post passou de {MAX_TEXTO} caracteres.", None, 422)
        if len(imagens) > MAX_IMAGENS:
            raise AppError("validacao", f"No máximo {MAX_IMAGENS} imagens por post.", None, 422)
        arquivos = [_decodificar(i.get("nome", ""), i.get("conteudo_base64", "")) for i in imagens]  # valida tudo antes
        cid = self.dao.criar_comentario(autor=(autor or "").strip()[:200], link=(link or "").strip()[:500],
                                        texto_post=texto_post, plataforma=plataforma)
        nomes: list[str] = []
        if arquivos:
            d = self._dir(cid)
            d.mkdir(parents=True, exist_ok=True)
            for n, (ext, dados) in enumerate(arquivos, 1):
                nome = f"imagem-{n}{ext}"
                (d / nome).write_bytes(dados)
                nomes.append(nome)
            self.dao.atualizar_comentario(cid, imagens=nomes)
        return self.obter(cid)

    def obter(self, cid: int) -> dict[str, Any]:
        c = self.dao.comentario(cid)
        if not c:
            raise nao_encontrado("Comentário")
        return self.apresentar(c)

    @staticmethod
    def apresentar(c: dict[str, Any]) -> dict[str, Any]:
        return {k: c[k] for k in ("id", "autor", "link", "texto_post", "imagens", "parametros", "instrucoes",
                                  "resumo_post", "sugestoes", "erro", "criado_em", "gerado_em", "plataforma", "status",
                                  "escolhido", "texto_final", "link_publicado", "fonte")}

    def listar(self) -> list[dict[str, Any]]:
        return [self.apresentar(c) for c in self.dao.listar_comentarios()]

    def imagem(self, cid: int, nome: str) -> Path:
        c = self.dao.comentario(cid)
        if not c or nome not in (c["imagens"] or []):
            raise nao_encontrado("Imagem")
        return self._dir(cid) / nome

    def excluir(self, cid: int) -> None:
        self.obter(cid)
        self.dao.excluir_comentario(cid)
        shutil.rmtree(self._dir(cid), ignore_errors=True)

    def criar_externo(self, plataforma: str, texto_original: str, sugestoes: list[dict[str, Any]], resumo: str = "",
                      autor: str = "", link: str = "", imagens: list[dict[str, str]] | None = None,
                      parametros: dict[str, Any] | None = None, fonte: str = "claude_code") -> dict[str, Any]:
        """Comentário escrito fora do Shiplog (Claude Code via MCP, spec 009 FR-14)."""
        validas = _validar({"sugestoes": sugestoes})
        if not validas:
            raise AppError("validacao", "Envie pelo menos uma sugestão com `texto`.", None, 422)
        params = self.normalizar(parametros)
        c = self.criar(texto_original, imagens or [], autor, link, plataforma)
        self.dao.atualizar_comentario(c["id"], sugestoes=validas[:5], resumo_post=(resumo or "").strip(), parametros=params,
                                      fonte=fonte, gerado_em=now_iso())
        return self.obter(c["id"])

    def marcar_usado(self, cid: int, indice: int | None = None, texto_final: str | None = None,
                     link: str | None = None) -> dict[str, Any]:
        c = self.obter(cid)
        if texto_final is None:
            if indice is None or not (0 <= indice < len(c["sugestoes"])):
                raise AppError("validacao", "Informe o índice da sugestão usada (0, 1 ou 2) ou o texto final.", None, 422)
            texto_final = c["sugestoes"][indice]["texto"]
        self.dao.atualizar_comentario(cid, status="usado", escolhido=indice, texto_final=texto_final.strip(),
                                      link_publicado=(link or "").strip() or None)
        return self.obter(cid)

    def voltar_sugerido(self, cid: int) -> dict[str, Any]:
        self.obter(cid)
        self.dao.atualizar_comentario(cid, status="sugerido", escolhido=None, texto_final=None, link_publicado=None)
        return self.obter(cid)

    # -- geração -----------------------------------------------------------------
    def normalizar(self, parametros: dict[str, Any] | None) -> dict[str, str]:
        p = {**PADRAO, **{k: v for k, v in (parametros or {}).items() if v is not None}}
        for k, validos in PARAMS.items():
            if p.get(k) not in validos:
                raise AppError("validacao", f"Parâmetro '{k}' inválido: {p.get(k)!r}.",
                               f"Valores aceitos: {', '.join(validos)}.", 422)
        return {k: p[k] for k in PARAMS}

    def montar_prompt(self, c: dict[str, Any], params: dict[str, str], instrucoes: str, cfg: dict[str, Any]) -> str:
        partes = [
            "# Tarefa",
            f"Você ajuda uma pessoa desenvolvedora a comentar {'no artigo' if c['plataforma'] == 'medium' else 'no post'} "
            f"de OUTRA pessoa no {PLATAFORMAS[c['plataforma']]}. "
            "Escreva 3 opções de comentário, em primeira pessoa, como se fosse ela comentando.",
        ]
        if cfg.get("perfil_profissional", "").strip():
            partes += ["## Quem vai comentar (perfil profissional)",
                       "Use para dar perspectiva e propriedade ao comentário. Só cite experiências que estejam no perfil.",
                       cfg["perfil_profissional"].strip()]
        if cfg.get("perfil_voz", "").strip():
            partes += ["## Como essa pessoa escreve", cfg["perfil_voz"].strip()]
        partes += [
            "## Parâmetros",
            f"- Objetivo: {OBJETIVOS[params['objetivo']]}",
            f"- Tamanho de cada comentário: {tamanho(c['plataforma'], params['tamanho'])}",
            f"- Idioma: {IDIOMAS[params['idioma']]}",
            "## O post",
            f"Autor do post: {c['autor']}" if c["autor"] else "Autor do post: (não informado)",
        ]
        partes += ["Texto do post:", "```", c["texto_post"], "```"] if c["texto_post"] else ["(Sem texto: o post está nas imagens.)"]
        if c["imagens"]:
            arquivos = ", ".join(f"`{n}`" for n in c["imagens"])
            partes.append(f"Imagens publicadas no post (no diretório atual): {arquivos}. Leia TODAS com a ferramenta Read "
                          "antes de escrever; elas podem conter o texto do post, slides, prints ou gráficos. "
                          "Não leia nenhum outro arquivo.")
        if c["sugestoes"]:
            anteriores = "\n".join(f"- {s['texto']}" for s in c["sugestoes"])
            partes += ["## Sugestões anteriores (escreva opções diferentes destas)", anteriores]
        if instrucoes.strip():
            partes += ["## Instruções extras de quem vai comentar (prioridade máxima)", instrucoes.strip()]
        partes += ["## Regras", *(f"- {r}" for r in regras(c["plataforma"], bool(cfg.get("perfil_profissional", "").strip())))]
        partes += [
            "## Formato da resposta",
            "Responda apenas com o JSON: {\"resumo_post\": \"...\", \"sugestoes\": "
            "[{\"abordagem\": \"...\", \"texto\": \"...\"}, ... 3 itens]}",
        ]
        return "\n\n".join(partes)

    def gerar(self, cid: int, parametros: dict[str, Any] | None = None, instrucoes: str = "") -> dict[str, Any]:
        c = self.dao.comentario(cid)
        if not c:
            raise nao_encontrado("Comentário")
        params = self.normalizar(parametros)
        h = self.health()
        if not h["pode_gerar_post"]:
            raise AppError("cli_indisponivel", h["cli"]["mensagem"] or h["auth"]["mensagem"] or "Claude Code indisponível.",
                           h["cli"]["comando_sugerido"] or h["auth"]["comando_sugerido"], 409)
        if not self._lock.acquire(blocking=False):
            raise AppError("conflito", "Já há um comentário sendo gerado.", "Aguarde terminar.", 409)
        try:
            cfg = self.dao.config()
            prompt = self.montar_prompt(c, params, instrucoes or "", cfg)
            cwd = self._dir(cid)
            cwd.mkdir(parents=True, exist_ok=True)  # vazio quando não há imagens: o Claude não vê nada além disso
            req = LLMRequest(prompt=prompt, cwd=cwd, tools=["Read"] if c["imagens"] else [], json_schema=SCHEMA,
                             timeout_s=int(cfg["timeout_post_s"]), model=cfg["modelo"] or None)
            self.dao.atualizar_comentario(cid, parametros=params, instrucoes=(instrucoes or "").strip(), prompt=prompt)
            r = self.provider.run(req, threading.Event())
        finally:
            self._lock.release()
        self.dao.atualizar_comentario(cid, resposta_bruta=r.raw)
        if not r.ok:
            msg = r.error_message or "Falha do Claude Code."
            self.dao.atualizar_comentario(cid, erro=msg)
            raise AppError(r.error_code or "cli_falha", msg, r.meta.get("acao"), 422)
        sugestoes = _validar(r.data)
        if sugestoes is None:
            msg = "O Claude respondeu fora do formato esperado."
            self.dao.atualizar_comentario(cid, erro=msg)
            raise AppError("schema_invalido", msg, "Tente gerar de novo.", 422)
        self.dao.atualizar_comentario(cid, sugestoes=sugestoes, resumo_post=str((r.data or {}).get("resumo_post", "")).strip(),
                                      erro=None, gerado_em=now_iso())
        log.info("Comentário %s gerado (%d sugestões)", cid, len(sugestoes))
        return self.obter(cid)


def _validar(data: Any) -> list[dict[str, str]] | None:
    if not isinstance(data, dict) or not isinstance(data.get("sugestoes"), list):
        return None
    out = []
    for s in data["sugestoes"]:
        if isinstance(s, dict) and str(s.get("texto", "")).strip():
            out.append({"abordagem": str(s.get("abordagem", "")).strip()[:60] or "Sugestão",
                        "texto": str(s["texto"]).strip()})
    return out or None

