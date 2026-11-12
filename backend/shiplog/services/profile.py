"""Perfil profissional gerado a partir do currículo e de um texto livre (spec 007)."""

from __future__ import annotations

import base64
import binascii
import logging
import re
import threading
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree

from ..errors import AppError
from ..storage.dao import Dao
from ..storage.db import now_iso
from .llm.base import LLMProvider, LLMRequest

log = logging.getLogger("shiplog.profile")

EXTENSOES = {".pdf", ".docx", ".txt", ".md"}
MAX_BYTES = 5 * 1024 * 1024
MAX_TEXTO = 40_000
MIN_SOBRE = 20
MIN_PERFIL, MAX_PERFIL = 200, 6000

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "perfil": {"type": "string", "description": "Perfil profissional pronto para ser usado como contexto de escrita."},
    },
    "required": ["perfil"],
    "additionalProperties": False,
}

INSTRUCOES = f"""Você vai preparar o PERFIL PROFISSIONAL de uma pessoa desenvolvedora. Esse perfil será colado no \
início de todo pedido de escrita de posts do LinkedIn e artigos do Medium dela, para que o redator saiba quem é o autor.

Escreva em português, em segunda pessoa dirigida ao redator ("O autor é…"), com estas seções em Markdown:
## Quem é
Área, senioridade, cargo atual/recente e tempo de experiência (só se estiverem no material).
## Experiência e domínio
Stack, domínios de negócio, tipos de sistema e conquistas concretas (com números só se estiverem no material).
## Temas em que fala com autoridade
3 a 6 temas.
## Como escrever por ele
Nível técnico do público, perspectiva (ex.: quem lidera, quem constrói), o que valorizar e o que evitar.

Regras:
- Use somente fatos do currículo e do texto do autor; não invente empresas, cargos, datas, números ou tecnologias.
- NÃO inclua dados de contato nem dados pessoais sensíveis (e-mail, telefone, endereço, documentos, data de \
nascimento, links pessoais).
- Seja denso: entre {MIN_PERFIL} e {MAX_PERFIL} caracteres no total.
- O texto livre do autor tem prioridade sobre o currículo quando houver conflito (pode estar mais atualizado).
- Responda apenas com o JSON pedido: {{"perfil": "<markdown>"}}."""


def extrair_docx(dados: bytes) -> str:
    """Texto de um .docx usando só a biblioteca padrão (parágrafos de word/document.xml)."""
    try:
        with zipfile.ZipFile(BytesIO(dados)) as z:
            xml = z.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as e:
        raise AppError("validacao", "Não consegui ler esse .docx.", "Exporte o currículo como PDF e tente de novo.", 422) from e
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    raiz = ElementTree.fromstring(xml)
    paragrafos = ["".join(t.text or "" for t in p.iter(f"{ns}t")) for p in raiz.iter(f"{ns}p")]
    return "\n".join(p for p in paragrafos if p.strip())


class ProfileService:
    def __init__(self, dao: Dao, pasta: Path, provider: LLMProvider, health: Callable[[], dict[str, Any]]) -> None:
        self.dao = dao
        self.pasta = pasta
        self.provider = provider
        self.health = health
        self._lock = threading.Lock()

    # -- currículo -------------------------------------------------------------
    def arquivo(self) -> Path | None:
        achados = sorted(self.pasta.glob("curriculo.*")) if self.pasta.exists() else []
        return achados[0] if achados else None

    def salvar_curriculo(self, nome: str, conteudo_base64: str) -> None:
        ext = Path(nome or "").suffix.lower()
        if ext not in EXTENSOES:
            raise AppError("validacao", "Formato de currículo não suportado.", "Envie PDF, DOCX, TXT ou MD.", 422)
        try:
            dados = base64.b64decode(conteudo_base64, validate=True)
        except (binascii.Error, ValueError) as e:
            raise AppError("validacao", "Arquivo corrompido no envio.", "Tente enviar de novo.", 422) from e
        if not dados:
            raise AppError("validacao", "O arquivo está vazio.", None, 422)
        if len(dados) > MAX_BYTES:
            raise AppError("validacao", "O currículo passou de 5 MB.", "Envie uma versão menor (PDF de texto).", 422)
        if ext == ".pdf" and not dados.startswith(b"%PDF"):
            raise AppError("validacao", "Esse arquivo não parece ser um PDF.", None, 422)
        if ext == ".docx":
            extrair_docx(dados)  # valida já no envio
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.remover_arquivo()
        (self.pasta / f"curriculo{ext}").write_bytes(dados)
        self.dao.salvar_config(curriculo_nome=Path(nome).name[:200])
        log.info("Currículo salvo (%s, %d bytes)", ext, len(dados))

    def remover_arquivo(self) -> None:
        for f in self.pasta.glob("curriculo.*") if self.pasta.exists() else []:
            f.unlink()

    def remover_curriculo(self) -> None:
        self.remover_arquivo()
        self.dao.salvar_config(curriculo_nome="")

    def _texto(self, arq: Path) -> str:
        if arq.suffix == ".docx":
            texto = extrair_docx(arq.read_bytes())
        else:
            texto = arq.read_text(encoding="utf-8", errors="replace")
        return texto[:MAX_TEXTO]

    # -- geração ---------------------------------------------------------------
    def montar_prompt(self, sobre: str, arq: Path | None) -> tuple[str, list[str]]:
        partes = [INSTRUCOES]
        tools: list[str] = []
        if arq is not None and arq.suffix == ".pdf":
            partes.append(f"## Currículo\nLeia o arquivo `{arq.name}` (no diretório atual) com a ferramenta Read. "
                          "Não leia nenhum outro arquivo.")
            tools = ["Read"]
        elif arq is not None:
            partes += ["## Currículo", "```", self._texto(arq), "```"]
        else:
            partes.append("## Currículo\n(nenhum enviado; use só o texto do autor)")
        partes += ["## Texto livre do autor", sobre.strip() or "(vazio)"]
        return "\n\n".join(partes), tools

    def gerar(self, sobre: str | None = None) -> dict[str, Any]:
        cfg = self.dao.config()
        sobre = (cfg["perfil_sobre"] if sobre is None else sobre).strip()
        arq = self.arquivo()
        if arq is None and len(sobre) < MIN_SOBRE:
            raise AppError("validacao", "Envie o currículo ou escreva pelo menos 20 caracteres sobre você.",
                           "O Claude precisa de algum material para montar o perfil.", 422)
        h = self.health()
        if not h["pode_gerar_post"]:
            raise AppError("cli_indisponivel", h["cli"]["mensagem"] or h["auth"]["mensagem"] or "Claude Code indisponível.",
                           h["cli"]["comando_sugerido"] or h["auth"]["comando_sugerido"], 409)
        if not self._lock.acquire(blocking=False):
            raise AppError("conflito", "O perfil já está sendo gerado.", "Aguarde terminar.", 409)
        try:
            self.dao.salvar_config(perfil_sobre=sobre)
            prompt, tools = self.montar_prompt(sobre, arq)
            self.pasta.mkdir(parents=True, exist_ok=True)
            req = LLMRequest(prompt=prompt, cwd=self.pasta, tools=tools, json_schema=SCHEMA,
                             timeout_s=int(cfg["timeout_post_s"]), model=cfg["modelo"] or None)
            r = self.provider.run(req, threading.Event())
        finally:
            self._lock.release()
        if not r.ok:
            raise AppError(r.error_code or "cli_falha", r.error_message or "Falha do Claude Code.", r.meta.get("acao"), 422)
        perfil = str((r.data or {}).get("perfil") or "").strip()
        if len(perfil) < MIN_PERFIL:
            raise AppError("schema_invalido", "O Claude devolveu um perfil vazio ou curto demais.", "Tente novamente.", 422)
        perfil = _sem_contato(perfil)[:MAX_PERFIL]
        self.dao.salvar_config(perfil_profissional=perfil, perfil_gerado_em=now_iso())
        return {"perfil_profissional": perfil, "perfil_gerado_em": self.dao.config()["perfil_gerado_em"]}


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_FONE = re.compile(r"(?<![\w-])(?:\+\d{1,3}\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}(?![\w-])")


def _sem_contato(texto: str) -> str:
    """Rede de segurança: o perfil vai para todo prompt, então e-mail e telefone nunca ficam nele."""
    return _FONE.sub("[removido]", _EMAIL.sub("[removido]", texto))
