"""Pacotes de contexto para o modelo do harness escrever (spec 009 FR-06..FR-13).

O Shiplog não chama nenhum modelo aqui: devolve o que só ele sabe (perfil, voz, parâmetros, histórico,
estado do projeto) e as regras/formato que `salvar_*` vai validar.
"""

from __future__ import annotations

from typing import Any

from ..errors import AppError
from ..storage.dao import Dao
from . import comments as com
from . import workspace
from .projects import MIN_DESCRICAO, ProjectService
from .prompts import FORMATOS, IDIOMAS, PUBLICOS, PROMPT_BASE_PADRAO, TAMANHOS, TONS

LIMITE_POST = 3000

REGRAS_POST = [
    "Primeira pessoa, como o autor contando o que fez; o texto final pronto para colar no LinkedIn.",
    "Abra com uma frase forte nos primeiros ~210 caracteres (o que aparece antes do \"ver mais\").",
    f"Máximo de {LIMITE_POST} caracteres no total; parágrafos curtos separados por linha em branco.",
    "Nada de hashtags no corpo: elas vão em `hashtags` (3 a 5, com #).",
    "`hooks_alternativos`: 2 aberturas alternativas (1-2 frases) que possam substituir o primeiro parágrafo.",
    "`resumo_tecnico`: 2-3 frases objetivas; `destaques`: 2 a 5 pontos concretos.",
    "Nunca invente métricas, usuários, clientes ou resultados que não estejam no material ou na conversa.",
    "Se houver um post publicado anteriormente, não repita o assunto: foque no que mudou desde então.",
    "Mostre o texto ao usuário e só chame `salvar_post` depois que ele aprovar (ou pedir para salvar).",
]
REGRAS_ARTIGO = [
    "Use a skill `medium-article-writer` se ela estiver disponível nesta sessão; siga as regras dela.",
    "Todo trecho de código no artigo deve ser copiado de um arquivo real do projeto, com o caminho indicado no texto.",
    "Liste cada trecho em `trechos_de_codigo` com o caminho relativo à raiz do projeto e o intervalo de linhas "
    "real (ex.: \"10-42\"): `salvar_artigo` confere cada um nos arquivos e recusa trechos inexistentes.",
    "Onde faltar informação que só o autor tem (números, resultados, anedotas), pergunte ao usuário ou marque `TK: ...`.",
    "`tags`: até 5; `subtitulo` obrigatório.",
    "Mostre o artigo (ou um resumo e o título) ao usuário antes de chamar `salvar_artigo`.",
]
SCHEMA_POST = {
    "type": "object",
    "required": ["texto", "hashtags"],
    "properties": {
        "texto": {"type": "string", "maxLength": LIMITE_POST},
        "hashtags": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 5},
        "hooks_alternativos": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        "resumo_tecnico": {"type": "string"},
        "destaques": {"type": "array", "items": {"type": "string"}},
    },
}
SCHEMA_ARTIGO = {
    "type": "object",
    "required": ["titulo", "subtitulo", "corpo_markdown", "trechos_de_codigo"],
    "properties": {
        "titulo": {"type": "string"},
        "subtitulo": {"type": "string"},
        "corpo_markdown": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "trechos_de_codigo": {"type": "array", "minItems": 1, "items": {
            "type": "object", "required": ["arquivo", "linhas"],
            "properties": {"arquivo": {"type": "string"}, "linhas": {"type": "string"}}}},
        "sugestoes_de_imagens": {"type": "array", "items": {"type": "string"}},
    },
}


def _mini_post(v: dict[str, Any] | None) -> dict[str, Any] | None:
    if not v:
        return None
    return {"id": v["id"], "versao": v["versao"], "status": v["status"], "criado_em": v["criado_em"],
            "publicado_em": v.get("publicado_em"), "texto": v.get("texto"), "link": v.get("link_linkedin")}


class ContextService:
    def __init__(self, dao: Dao, projects: ProjectService, comments: com.CommentService, url_base: str) -> None:
        self.dao = dao
        self.projects = projects
        self.comments = comments
        self.url_base = url_base.rstrip("/")

    def link_projeto(self, pid: int) -> str:
        return f"{self.url_base}/projetos/{pid}"

    def _autor(self) -> dict[str, str]:
        cfg = self.dao.config()
        return {"perfil_profissional": cfg["perfil_profissional"], "perfil_voz": cfg["perfil_voz"]}

    def _projeto(self, projeto_id: int | None, caminho: str | None) -> tuple[dict[str, Any], workspace.Pasta | None]:
        if caminho:
            d = self.projects.projeto_atual(caminho)
            return d, workspace.resolver(caminho)
        if projeto_id is None:
            raise AppError("validacao", "Informe `caminho` (pasta do projeto), `projeto_id` ou `descricao`.", None, 422)
        p = self.projects.detalhe(projeto_id)
        pasta = workspace.resolver(p["caminho_local"]) if p["origem"] == "local" and p["caminho_local"] else None
        return p, pasta

    # -- post -----------------------------------------------------------------
    def post(self, projeto_id: int | None = None, caminho: str | None = None, descricao: str | None = None,
             parametros: dict[str, Any] | None = None, desde_commit: str | None = None) -> dict[str, Any]:
        cfg = self.dao.config()
        params = {**cfg["parametros_padrao_post"], **{k: v for k, v in (parametros or {}).items() if v}}
        for k, mapa in (("tom", TONS), ("tamanho", TAMANHOS), ("idioma", IDIOMAS)):
            if params.get(k) not in mapa:
                raise AppError("validacao", f"Parâmetro '{k}' inválido: {params.get(k)!r}.",
                               f"Valores aceitos: {', '.join(mapa)}.", 422)
        if descricao is not None and not caminho and projeto_id is None:
            if len(descricao.strip()) < MIN_DESCRICAO:
                raise AppError("validacao", f"Descreva com pelo menos {MIN_DESCRICAO} caracteres.", None, 422)
            projeto = None
            material: dict[str, Any] = {"tipo": "descricao", "descricao": descricao.strip()}
            ult = pub = None
        else:
            projeto, pasta = self._projeto(projeto_id, caminho)
            desde = desde_commit or self.dao.ultimo_commit_gerado(projeto["id"])
            if pasta is not None:
                material = workspace.material(pasta, desde).to_dict()
            elif projeto["origem"] == "livre":
                material = {"tipo": "descricao", "descricao": projeto["descricao"]}
            else:
                material = {"tipo": "projeto", "avisos": [
                    "Sem a pasta local deste projeto: passe `caminho` para incluir commits e alterações pendentes."]}
            ult = self.dao.ultima_versao("posts", projeto["id"])
            pub = self.dao.publicada("posts", projeto["id"])
        return {
            "tarefa": "Escreva um post do LinkedIn sobre o trabalho descrito no material (e no que vocês fizeram nesta "
                      "conversa), em primeira pessoa, como o autor.",
            "projeto": self._resumo_projeto(projeto),
            "prompt_base": (cfg["prompt_base"] or "").strip() or PROMPT_BASE_PADRAO,
            **self._autor(),
            "parametros": params,
            "parametros_explicados": {"tom": TONS[params["tom"]], "tamanho": TAMANHOS[params["tamanho"]],
                                      "idioma": IDIOMAS[params["idioma"]]},
            "material": material,
            "ultimo_post": _mini_post(ult),
            "ultimo_post_publicado": _mini_post(pub),
            "regras": REGRAS_POST,
            "formato_salvar_post": SCHEMA_POST,
            "proximo_passo": self._proximo("salvar_post", projeto, material),
        }

    # -- artigo -----------------------------------------------------------------
    def artigo(self, projeto_id: int | None = None, caminho: str | None = None,
               parametros: dict[str, Any] | None = None) -> dict[str, Any]:
        cfg = self.dao.config()
        params = {**cfg["parametros_padrao_artigo"], **{k: v for k, v in (parametros or {}).items() if v}}
        for k, mapa in (("idioma", IDIOMAS), ("publico", PUBLICOS), ("formato", FORMATOS)):
            if params.get(k) not in mapa:
                raise AppError("validacao", f"Parâmetro '{k}' inválido: {params.get(k)!r}.",
                               f"Valores aceitos: {', '.join(mapa)}.", 422)
        projeto, pasta = self._projeto(projeto_id, caminho)
        if projeto["origem"] == "livre":
            raise AppError("artigo_requer_repositorio", "Artigos precisam de um projeto com código.",
                           "Passe `caminho` com a pasta do projeto.", 409)
        material = workspace.material(pasta, None).to_dict() if pasta else {
            "tipo": "projeto", "avisos": ["Passe `caminho` para incluir o estado atual do projeto."]}
        ult = self.dao.ultima_versao("artigos", projeto["id"])
        return {
            "tarefa": "Escreva um artigo para o Medium sobre este projeto, com trechos reais do código.",
            "projeto": self._resumo_projeto(projeto),
            **self._autor(),
            "parametros": params,
            "parametros_explicados": {"idioma": IDIOMAS[params["idioma"]], "publico": PUBLICOS[params["publico"]],
                                      "formato": FORMATOS[params["formato"]]},
            "material": material,
            "ultimo_artigo": ({"id": ult["id"], "versao": ult["versao"], "titulo": ult["titulo"], "status": ult["status"]}
                              if ult else None),
            "regras": REGRAS_ARTIGO,
            "formato_salvar_artigo": SCHEMA_ARTIGO,
            "proximo_passo": self._proximo("salvar_artigo", projeto, material),
        }

    # -- comentário ------------------------------------------------------------
    def comentario(self, plataforma: str = "linkedin", parametros: dict[str, Any] | None = None) -> dict[str, Any]:
        if plataforma not in com.PLATAFORMAS:
            raise AppError("validacao", "Plataforma inválida.", "Use linkedin ou medium.", 422)
        params = self.comments.normalizar(parametros)
        return {
            "tarefa": f"Escreva 3 opções de comentário para um conteúdo de OUTRA pessoa no {com.PLATAFORMAS[plataforma]}, "
                      "em primeira pessoa, como o autor comentando.",
            "plataforma": plataforma,
            **self._autor(),
            "parametros": params,
            "parametros_explicados": {"objetivo": com.OBJETIVOS[params["objetivo"]],
                                      "tamanho": com.tamanho(plataforma, params["tamanho"]),
                                      "idioma": com.IDIOMAS[params["idioma"]]},
            "regras": com.regras(plataforma, bool(self.dao.config()["perfil_profissional"].strip())),
            "formato_salvar_comentario": {
                "texto_original": "o texto do post/artigo comentado (como o usuário colou)",
                "resumo": "1-2 frases sobre o que o conteúdo diz",
                "sugestoes": [{"abordagem": "rótulo curto", "texto": "comentário pronto"}],
            },
            "proximo_passo": "Mostre as 3 opções ao usuário e chame `salvar_comentario` para registrá-las no Shiplog; "
                             "quando ele disser qual usou, chame `marcar_comentario_usado`.",
        }

    # -- utilitários -----------------------------------------------------------
    def _resumo_projeto(self, p: dict[str, Any] | None) -> dict[str, Any] | None:
        if p is None:
            return None
        return {"id": p["id"], "nome": p["nome"], "origem": p["origem"], "url_repo": p["url_repo"],
                "link_shiplog": self.link_projeto(p["id"])}

    @staticmethod
    def _proximo(tool: str, projeto: dict[str, Any] | None, material: dict[str, Any]) -> str:
        alvo = f"projeto_id={projeto['id']}" if projeto else "descricao=<a mesma descrição>"
        ref = f", commit_referencia=\"{material['head']}\"" if material.get("head") else ""
        return (f"Escreva, mostre ao usuário, ajuste se ele pedir e então chame `{tool}` com {alvo}{ref}. "
                "Depois mostre o link do Shiplog para ele revisar.")
