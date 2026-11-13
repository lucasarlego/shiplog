"""Pacotes de contexto para o modelo do harness escrever (spec 009 FR-06..FR-13).

O Shiplog não chama nenhum modelo aqui: devolve o que só ele sabe (perfil, voz, parâmetros, histórico,
estado do projeto) e o formato que `save_*` vai validar. O texto de instruções é montado pelas mesmas funções da
geração pela interface (`prompts.montar_prompt_post`/`montar_prompt_artigo`, modo "sessao"), para que as
Configurações (prompt base, perfil, voz) e as regras valham igual nos dois caminhos.
"""

from __future__ import annotations

from typing import Any

from ..errors import AppError
from ..storage.dao import Dao
from . import comments as com
from . import workspace
from .projects import MIN_DESCRICAO, ProjectService
from . import prompts
from .prompts import FORMATOS, IDIOMAS, PUBLICOS, TAMANHOS, TONS

LIMITE_POST = 3000

# Só o que é próprio do fluxo pelo MCP. As regras de escrita vêm de `prompts.montar_prompt_*` (as mesmas da
# geração pela interface), no campo `instrucoes`.
REGRA_INSTRUCOES = ("Escreva seguindo `instrucoes`: é o mesmo prompt que o Shiplog usa ao gerar pela interface "
                    "(prompt base, perfil, voz, parâmetros, notas do autor e regras do resultado).")
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

CHAVES_POST = ("tom", "tamanho", "idioma")
CHAVES_ARTIGO = ("idioma", "publico", "formato")
CONFIRMACOES = ("formulario", "recusada")


def confirmacao_parametros(ferramenta: str, mapas: dict[str, dict[str, str]], informados: dict[str, Any] | None,
                           params: dict[str, Any], confirmacao: str | None) -> dict[str, Any]:
    """Diz ao modelo se os parâmetros foram escolhidos pelo usuário ou são só os padrões (spec 009 FR-23).

    `confirmacao`: "formulario" (o usuário escolheu no formulário do MCP), "recusada" (fechou o formulário:
    seguir com os padrões) ou None (sem formulário: o que não veio em `informados` precisa ser perguntado).
    """
    if confirmacao == "formulario":
        return {"parametros_confirmados": True}
    if confirmacao == "recusada":
        return {"parametros_confirmados": False,
                "aviso_parametros": "O usuário fechou o formulário de parâmetros sem escolher: siga com os valores "
                                    "de `parametros` (padrões do Shiplog) e diga a ele quais usou."}
    pendentes = [k for k in mapas if not (informados or {}).get(k)]
    if not pendentes:
        return {"parametros_confirmados": True}
    return {
        "parametros_confirmados": False,
        "confirmar_parametros": {
            "pendentes": pendentes,
            "opcoes": {k: mapas[k] for k in pendentes},
            "padrao": {k: params[k] for k in pendentes},
            "instrucao": (f"ANTES de escrever, pergunte ao usuário os parâmetros em `pendentes` (mostre as opções e "
                          f"o padrão de cada um, numa única pergunta) e chame `{ferramenta}` de novo com os valores "
                          "escolhidos. Se ele disser para usar os padrões, chame de novo passando os padrões."),
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
             parametros: dict[str, Any] | None = None, desde_commit: str | None = None,
             confirmacao: str | None = None, instrucoes_extras: str = "",
             base_versao_id: int | None = None) -> dict[str, Any]:
        cfg = self.dao.config()
        params = {**cfg["parametros_padrao_post"], **{k: v for k, v in (parametros or {}).items() if v is not None}}
        mapas = {"tom": TONS, "tamanho": TAMANHOS, "idioma": IDIOMAS}
        self._validar(params, mapas)
        params["incluir_link_artigo"] = bool(params.get("incluir_link_artigo", False))
        link_art = titulo_art = None
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
            art = self.dao.publicada("artigos", projeto["id"])
            if params["incluir_link_artigo"] and art and art.get("link_medium"):
                link_art, titulo_art = art["link_medium"], art["titulo"]
        base = self._versao_base("posts", projeto, base_versao_id)
        ctx = prompts.ContextoPrompt(
            nome=projeto["nome"] if projeto else "Post sem repositório",
            url=projeto["url_repo"] if projeto else None, branch=material.get("branch"),
            commit=material.get("head"), notas=(projeto or {}).get("notas") or "", metadados=None,
            prompt_base=cfg["prompt_base"], perfil_voz=cfg["perfil_voz"],
            perfil_profissional=cfg["perfil_profissional"], parametros=params, instrucoes_extras=instrucoes_extras,
            versao_anterior=base, link_artigo=link_art, titulo_artigo=titulo_art,
            descricao=material.get("descricao", "") if material.get("tipo") == "descricao" else "",
            modo="sessao", caminho=material.get("caminho"))
        conf = confirmacao_parametros("post_context", mapas, parametros, params, confirmacao)
        return {
            "tarefa": "Escreva um post do LinkedIn sobre o trabalho descrito no material (e no que vocês fizeram nesta "
                      "conversa), em primeira pessoa, como o autor.",
            "projeto": self._resumo_projeto(projeto),
            "parametros": params,
            "parametros_explicados": {"tom": TONS[params["tom"]], "tamanho": TAMANHOS[params["tamanho"]],
                                      "idioma": IDIOMAS[params["idioma"]]},
            **conf,
            "instrucoes": prompts.montar_prompt_post(ctx, SCHEMA_POST),
            "material": material,
            "versao_base": base and {"id": base["id"], "versao": base["versao"]},
            "artigo_publicado": ({"titulo": titulo_art, "link": link_art} if link_art else None),
            "ultimo_post": _mini_post(ult),
            "ultimo_post_publicado": _mini_post(pub),
            "regras": self._regras(conf),
            "formato_salvar_post": SCHEMA_POST,
            "proximo_passo": self._proximo("save_post", projeto, material, conf, base, instrucoes_extras),
        }

    # -- artigo -----------------------------------------------------------------
    def artigo(self, projeto_id: int | None = None, caminho: str | None = None,
               parametros: dict[str, Any] | None = None, confirmacao: str | None = None,
               instrucoes_extras: str = "", base_versao_id: int | None = None) -> dict[str, Any]:
        cfg = self.dao.config()
        params = {**cfg["parametros_padrao_artigo"], **{k: v for k, v in (parametros or {}).items() if v}}
        mapas = {"idioma": IDIOMAS, "publico": PUBLICOS, "formato": FORMATOS}
        self._validar(params, mapas)
        projeto, pasta = self._projeto(projeto_id, caminho)
        if projeto["origem"] == "livre":
            raise AppError("artigo_requer_repositorio", "Artigos precisam de um projeto com código.",
                           "Passe `caminho` com a pasta do projeto.", 409)
        material = workspace.material(pasta, None).to_dict() if pasta else {
            "tipo": "projeto", "avisos": ["Passe `caminho` para incluir o estado atual do projeto."]}
        ult = self.dao.ultima_versao("artigos", projeto["id"])
        base = self._versao_base("artigos", projeto, base_versao_id)
        ctx = prompts.ContextoPrompt(
            nome=projeto["nome"], url=projeto["url_repo"], branch=material.get("branch"), commit=material.get("head"),
            notas=projeto.get("notas") or "", metadados=None, prompt_base=cfg["prompt_base"],
            perfil_voz=cfg["perfil_voz"], perfil_profissional=cfg["perfil_profissional"], parametros=params,
            instrucoes_extras=instrucoes_extras, versao_anterior=base, modo="sessao", caminho=material.get("caminho"))
        conf = confirmacao_parametros("article_context", mapas, parametros, params, confirmacao)
        return {
            "tarefa": "Escreva um artigo para o Medium sobre este projeto, com trechos reais do código.",
            "projeto": self._resumo_projeto(projeto),
            "parametros": params,
            "parametros_explicados": {"idioma": IDIOMAS[params["idioma"]], "publico": PUBLICOS[params["publico"]],
                                      "formato": FORMATOS[params["formato"]]},
            **conf,
            "instrucoes": prompts.montar_prompt_artigo(ctx, SCHEMA_ARTIGO),
            "material": material,
            "versao_base": base and {"id": base["id"], "versao": base["versao"]},
            "ultimo_artigo": ({"id": ult["id"], "versao": ult["versao"], "titulo": ult["titulo"], "status": ult["status"]}
                              if ult else None),
            "regras": self._regras(conf),
            "formato_salvar_artigo": SCHEMA_ARTIGO,
            "proximo_passo": self._proximo("save_article", projeto, material, conf, base, instrucoes_extras),
        }

    @staticmethod
    def _validar(params: dict[str, Any], mapas: dict[str, dict[str, str]]) -> None:
        for k, mapa in mapas.items():
            if params.get(k) not in mapa:
                raise AppError("validacao", f"Parâmetro '{k}' inválido: {params.get(k)!r}.",
                               f"Valores aceitos: {', '.join(mapa)}.", 422)

    def _versao_base(self, tabela: str, projeto: dict[str, Any] | None, vid: int | None) -> dict[str, Any] | None:
        """Versão usada como referência num ajuste (igual a "Regenerar" na interface)."""
        if vid is None:
            return None
        v = self.dao.versao(tabela, vid)
        if not v or projeto is None or v["projeto_id"] != projeto["id"]:
            raise AppError("nao_encontrado", f"Versão {vid} não encontrada neste projeto.", None, 404)
        return v

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
            "proximo_passo": "Mostre as 3 opções ao usuário e chame `save_comment` para registrá-las no Shiplog; "
                             "quando ele disser qual usou, chame `mark_comment_used`.",
        }

    # -- utilitários -----------------------------------------------------------
    def _resumo_projeto(self, p: dict[str, Any] | None) -> dict[str, Any] | None:
        if p is None:
            return None
        return {"id": p["id"], "nome": p["nome"], "origem": p["origem"], "url_repo": p["url_repo"],
                "link_shiplog": self.link_projeto(p["id"])}

    @staticmethod
    def _regras(conf: dict[str, Any]) -> list[str]:
        if "confirmar_parametros" in conf:
            return [conf["confirmar_parametros"]["instrucao"], REGRA_INSTRUCOES]
        return [REGRA_INSTRUCOES]

    @staticmethod
    def _proximo(tool: str, projeto: dict[str, Any] | None, material: dict[str, Any],
                 conf: dict[str, Any] | None = None, base: dict[str, Any] | None = None,
                 extras: str = "") -> str:
        if conf and "confirmar_parametros" in conf:
            return conf["confirmar_parametros"]["instrucao"]
        alvo = f"projeto_id={projeto['id']}" if projeto else "descricao=<a mesma descrição>"
        ref = f", commit_referencia=\"{material['head']}\"" if material.get("head") else ""
        ref += f", base_versao_id={base['id']}" if base else ""
        ref += ", parametros=<o objeto `parametros` desta resposta>"
        ref += ", instrucoes_extras=<as mesmas instruções extras>" if extras else ""
        return (f"Escreva, mostre ao usuário, ajuste se ele pedir e então chame `{tool}` com {alvo}{ref}. "
                "Depois mostre o link do Shiplog para ele revisar.")
