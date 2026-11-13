"""Servidor MCP do Shiplog (spec 009).

O modelo da sessão (Claude Code ou outro harness) escreve; este servidor só entrega contexto e salva no
Shiplog. Nada é publicado no LinkedIn/Medium e nenhuma ferramenta exclui dados ou escreve na pasta do projeto.
"""


import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import (AcceptedElicitation, Context, Elicit, ElicitationResult, MCPServer,
                                  Resolve)
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field, create_model

from ..config import Paths, RedactingFilter, resolve_data_dir
from ..services.prompts import FORMATOS, IDIOMAS, PUBLICOS, TAMANHOS, TONS
from .client import ErroShiplog, ShiplogClient

log = logging.getLogger("shiplog.mcp")

INSTRUCOES = """Shiplog is the user's local tool for LinkedIn posts, Medium articles and comment suggestions.
You (the session model) write the text; Shiplog gives you the author's profile, voice, defaults and project
history, validates what you wrote and stores it as a draft so the user can track its status in the Shiplog UI.

Typical flows:
- "write a post about what we did today": current_project(caminho=<cwd>) -> post_context(caminho=<cwd>) ->
  confirm the parameters (see below) -> read the relevant code yourself -> write -> show the user -> save_post ->
  give the user the Shiplog link.
- "write a Medium article about this project": article_context(caminho=<cwd>) -> confirm the parameters ->
  write with real code snippets -> show -> save_article.
- "suggest a comment for this post/article": comment_context(plataforma) -> write 3 options -> show ->
  save_comment; later mark_comment_used.
Parameters (post: tom, tamanho, idioma; article: idioma, publico, formato): pass the ones the user already stated.
If the user did not choose them, post_context/article_context opens a form for the user when the client supports
it; otherwise the response has `parametros_confirmados: false` and `confirmar_parametros`: ask the user BEFORE
writing and call the context tool again with the choices. Never write with unconfirmed defaults silently.
Always show the text to the user before saving. Shiplog never publishes anything: the user posts manually and
then you may call set_status(..., "publicado", link)."""

RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
GRAVA = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
GRAVA_IDEMPOTENTE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True,
                                    openWorldHint=False)

Caminho = Annotated[str | None, Field(description="Absolute path of the project folder (usually the session's "
                                                  "current working directory).")]
ProjetoId = Annotated[int | None, Field(description="Shiplog project id (from current_project or list_items).")]


def _sem_nulos(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


OPCOES_POST = {"tom": TONS, "tamanho": TAMANHOS, "idioma": IDIOMAS}
OPCOES_ARTIGO = {"idioma": IDIOMAS, "publico": PUBLICOS, "formato": FORMATOS}
TITULOS = {"tom": "Tom", "tamanho": "Tamanho", "idioma": "Idioma", "publico": "Público", "formato": "Formato"}


def formulario(mensagem: str, opcoes: dict[str, dict[str, str]], informados: dict[str, Any],
               padroes: dict[str, Any], link_artigo: bool = False) -> Elicit[BaseModel] | None:
    """Formulário (elicitation) com os mesmos campos da tela "Gerar" do Shiplog (spec 009 FR-23).

    Só abre quando faltam parâmetros. Traz os que faltam (com o padrão das Configurações marcado), "Instruções
    extras" e, no post, "Incluir link do artigo" quando há artigo publicado com link.
    """
    pendentes = [k for k in opcoes if not informados.get(k)]
    if not pendentes:
        return None
    campos: dict[str, Any] = {}
    for k in pendentes:
        valores = list(opcoes[k])
        padrao = padroes.get(k) if padroes.get(k) in valores else valores[0]
        campos[k] = (Literal[tuple(valores)], Field(padrao, title=TITULOS.get(k, k), description=" | ".join(
            f"{v} = {d}" for v, d in opcoes[k].items())))
    if link_artigo:
        campos["incluir_link_artigo"] = (bool, Field(bool(padroes.get("incluir_link_artigo")),
                                                     title="Incluir link do artigo",
                                                     description="Termina o post convidando para o artigo publicado."))
    campos["instrucoes_extras"] = (str, Field("", title="Instruções extras (opcional)",
                                              description="Ex.: foque na parte de testes; não cite o cliente."))
    return Elicit(mensagem, create_model("ParametrosShiplog", **campos))


def _pode_perguntar(ctx: Context) -> bool:
    caps = ctx.client_capabilities
    el = getattr(caps, "elicitation", None) if caps is not None else None
    return el is not None and (getattr(el, "form", None) is not None or getattr(el, "url", None) is None)


def _escolhas(r: ElicitationResult[BaseModel]) -> tuple[dict[str, Any], str | None]:
    """(valores escolhidos, confirmação para a API): formulário aceito, fechado, ou nenhum formulário."""
    if isinstance(r, AcceptedElicitation):
        if r.data is None:
            return {}, None
        return {k: v for k, v in r.data.model_dump().items() if v not in ("", None)}, "formulario"
    return {}, "recusada"


def criar_servidor(cliente: ShiplogClient | None = None) -> MCPServer:
    api = cliente or ShiplogClient()
    srv = MCPServer(name="shiplog", title="Shiplog", instructions=INSTRUCOES)

    async def chamar(metodo: str, caminho: str, corpo: Any = None, **params: Any) -> Any:
        try:
            return await api.req(metodo, caminho, json=corpo, params=params or None)
        except ErroShiplog as e:
            log.info("%s %s -> %s", metodo, caminho, e.codigo)
            raise ToolError(str(e)) from e

    async def _tem_artigo_publicado(caminho: str | None, projeto_id: int | None) -> bool:
        try:
            if caminho:
                p = await chamar("POST", "/workspace/resolve", {"caminho": caminho, "vincular": False})
            elif projeto_id is not None:
                p = await chamar("GET", f"/projects/{projeto_id}")
            else:
                return False
        except ToolError:
            return False  # o erro real aparece na chamada do contexto
        return bool((p.get("artigo_publicado") or {}).get("link"))

    async def form_post(ctx: Context, caminho: str | None = None, projeto_id: int | None = None,
                        tom: str | None = None, tamanho: str | None = None, idioma: str | None = None,
                        incluir_link_artigo: bool | None = None) -> Elicit[BaseModel] | None:
        if not _pode_perguntar(ctx) or (tom and tamanho and idioma):
            return None
        cfg = await chamar("GET", "/settings")
        link = incluir_link_artigo is None and await _tem_artigo_publicado(caminho, projeto_id)
        return formulario("Post do LinkedIn: escolha os parâmetros (o padrão das Configurações já vem marcado).",
                          OPCOES_POST, _sem_nulos({"tom": tom, "tamanho": tamanho, "idioma": idioma}),
                          cfg.get("parametros_padrao_post") or {}, link_artigo=link)

    async def form_artigo(ctx: Context, idioma: str | None = None, publico: str | None = None,
                          formato: str | None = None) -> Elicit[BaseModel] | None:
        if not _pode_perguntar(ctx) or (idioma and publico and formato):
            return None
        cfg = await chamar("GET", "/settings")
        return formulario("Artigo do Medium: escolha os parâmetros (o padrão das Configurações já vem marcado).",
                          OPCOES_ARTIGO, _sem_nulos({"idioma": idioma, "publico": publico, "formato": formato}),
                          cfg.get("parametros_padrao_artigo") or {})

    # -- status e projeto --------------------------------------------------------
    @srv.tool(title="Shiplog status", annotations=RO, description=(
        "Check that Shiplog is running (starts it in the background if needed) and whether the Claude CLI, the "
        "author's professional profile and voice are configured. Returns the Shiplog web address."))
    async def shiplog_status() -> dict[str, Any]:
        saude = await chamar("GET", "/health")
        cfg = await chamar("GET", "/settings")
        return {
            "shiplog": api.base,
            "saude": saude,
            "perfil_profissional_configurado": bool((cfg.get("perfil_profissional") or "").strip()),
            "voz_configurada": bool((cfg.get("perfil_voz") or "").strip()),
            "parametros_padrao_post": cfg.get("parametros_padrao_post"),
            "parametros_padrao_artigo": cfg.get("parametros_padrao_artigo"),
        }

    @srv.tool(title="Current project", annotations=GRAVA_IDEMPOTENTE, description=(
        "Find (or register) the Shiplog project for a local folder. Uses the git `origin` remote when there is "
        "one; otherwise registers a 'local' project tied to the folder. Never writes to the folder. Returns the "
        "project, its last posts/articles and the folder's branch/HEAD. If a 'local' project exists and the "
        "folder now has an origin, `pode_vincular` is true: ask the user, then call again with vincular=true."))
    async def current_project(
        caminho: Annotated[str, Field(description="Absolute path of the project folder (the session's cwd).")],
        vincular: Annotated[bool, Field(description="Convert an existing 'local' project into a repository "
                                                    "project using the folder's origin.")] = False,
    ) -> dict[str, Any]:
        return await chamar("POST", "/workspace/resolve", {"caminho": caminho, "vincular": vincular})

    # -- contexto ---------------------------------------------------------------
    @srv.tool(title="Context for a LinkedIn post", annotations=RO, description=(
        "Everything needed to write a LinkedIn post in the author's voice. `instrucoes` is the same prompt Shiplog "
        "uses when generating from its UI (base prompt, profile, voice, parameters, author notes, extra "
        "instructions, previous version, result rules): follow it. Also returns the format save_post expects, the "
        "last post and the project's state since the last post (commits, diffstat, uncommitted files). Pass the "
        "parameters the user stated; if some are missing a form asks the user (or the response asks you to). "
        "Pass `caminho` for a code project, or only `descricao` for a post that is not about a repository. "
        "To adjust a saved post, pass base_versao_id and the request in instrucoes_extras. Read-only."))
    async def post_context(
        escolha: Annotated[ElicitationResult[BaseModel], Resolve(form_post)],
        caminho: Caminho = None,
        projeto_id: ProjetoId = None,
        descricao: Annotated[str | None, Field(description="What the post is about, when there is no project "
                                                           "folder (at least 20 characters).")] = None,
        tom: Annotated[Literal["tecnico", "storytelling", "conquista", "aprendizado"] | None, Field(description="Tone.")] = None,
        tamanho: Annotated[Literal["curto", "medio", "longo"] | None, Field(description="Length.")] = None,
        idioma: Annotated[Literal["pt", "en"] | None, Field(description="Language.")] = None,
        incluir_link_artigo: Annotated[bool | None, Field(description="End the post inviting readers to the "
                                                                      "project's published Medium article.")] = None,
        instrucoes_extras: Annotated[str | None, Field(description="Extra instructions from the user (highest "
                                                                   "priority), e.g. 'shorter', 'new hook'.")] = None,
        base_versao_id: Annotated[int | None, Field(description="Post version to revise (the user's adjustment "
                                                                "request goes in instrucoes_extras).")] = None,
        desde_commit: Annotated[str | None, Field(description="Override: collect commits after this hash "
                                                              "instead of after the last post.")] = None,
    ) -> dict[str, Any]:
        escolhido, confirmacao = _escolhas(escolha)
        params = {**_sem_nulos({"tom": tom, "tamanho": tamanho, "idioma": idioma,
                                "incluir_link_artigo": incluir_link_artigo}), **escolhido}
        extras = params.pop("instrucoes_extras", None) or instrucoes_extras
        return await chamar("POST", "/context/post", _sem_nulos({
            "caminho": caminho, "projeto_id": projeto_id, "descricao": descricao, "desde_commit": desde_commit,
            "parametros": params, "confirmacao": confirmacao, "instrucoes_extras": extras,
            "base_versao_id": base_versao_id}))

    @srv.tool(title="Context for a Medium article", annotations=RO, description=(
        "Everything needed to write a Medium article about a code project. `instrucoes` is the same prompt Shiplog "
        "uses when generating from its UI (skill medium-article-writer, profile, voice, parameters, author notes, "
        "real-code rules): follow it. Also returns the format save_article expects and the project's state. "
        "Missing parameters are asked through a form (or the response asks you to). Requires a project with "
        "code (folder or repository). Read-only."))
    async def article_context(
        escolha: Annotated[ElicitationResult[BaseModel], Resolve(form_artigo)],
        caminho: Caminho = None,
        projeto_id: ProjetoId = None,
        idioma: Annotated[Literal["pt", "en"] | None, Field(description="Language.")] = None,
        publico: Annotated[Literal["iniciante", "intermediario", "avancado"] | None,
                           Field(description="Audience level.")] = None,
        formato: Annotated[Literal["tutorial", "deep_dive", "case_arquitetura"] | None,
                           Field(description="Article format.")] = None,
        instrucoes_extras: Annotated[str | None, Field(description="Extra instructions from the user (highest "
                                                                   "priority).")] = None,
        base_versao_id: Annotated[int | None, Field(description="Article version to revise.")] = None,
    ) -> dict[str, Any]:
        escolhido, confirmacao = _escolhas(escolha)
        params = {**_sem_nulos({"idioma": idioma, "publico": publico, "formato": formato}), **escolhido}
        extras = params.pop("instrucoes_extras", None) or instrucoes_extras
        return await chamar("POST", "/context/artigo", _sem_nulos({
            "caminho": caminho, "projeto_id": projeto_id, "parametros": params, "confirmacao": confirmacao,
            "instrucoes_extras": extras, "base_versao_id": base_versao_id}))

    @srv.tool(title="Context for a comment", annotations=RO, description=(
        "Profile, voice, parameters and rules to write 3 comment options on SOMEONE ELSE's LinkedIn post or "
        "Medium article (the user pastes the content in the chat). Read-only."))
    async def comment_context(
        plataforma: Annotated[Literal["linkedin", "medium"], Field(description="Where the content was "
                                                                               "published.")] = "linkedin",
        objetivo: Annotated[Literal["acrescentar", "apoiar", "perguntar", "discordar"] | None,
                            Field(description="Goal of the comment.")] = None,
        tamanho: Annotated[Literal["curto", "medio"] | None, Field(description="Length.")] = None,
        idioma: Annotated[Literal["auto", "pt", "en"] | None,
                          Field(description="Language; auto = same as the content.")] = None,
    ) -> dict[str, Any]:
        return await chamar("POST", "/context/comentario", {
            "plataforma": plataforma,
            "parametros": _sem_nulos({"objetivo": objetivo, "tamanho": tamanho, "idioma": idioma})})

    # -- salvar -----------------------------------------------------------------
    @srv.tool(title="Save LinkedIn post", annotations=GRAVA, description=(
        "Save a post YOU wrote as a new draft version in Shiplog (never publishes, never overwrites). Call only "
        "after showing the text to the user. Target: `caminho`/`projeto_id`, or only `descricao` for a post "
        "without a project. Pass `commit_referencia` (HEAD from the context) so the next post starts after it. "
        "Returns the version and the Shiplog link to show the user."))
    async def save_post(
        texto: Annotated[str, Field(description="Final post text, ready to paste (max 3000 chars, no hashtags).")],
        hashtags: Annotated[list[str], Field(description="3 to 5 hashtags.")],
        caminho: Caminho = None,
        projeto_id: ProjetoId = None,
        descricao: Annotated[str | None, Field(description="For a post without a project: what it is "
                                                           "about.")] = None,
        hooks_alternativos: Annotated[list[str] | None, Field(description="Up to 3 alternative openings.")] = None,
        resumo_tecnico: Annotated[str | None, Field(description="2-3 sentence technical summary.")] = None,
        destaques: Annotated[list[str] | None, Field(description="2 to 5 concrete highlights.")] = None,
        commit_referencia: Annotated[str | None, Field(description="Commit the post covers up to.")] = None,
        base_versao_id: Annotated[int | None, Field(description="Version id this one revises, if any.")] = None,
        parametros: Annotated[dict[str, Any] | None, Field(description=(
            "The `parametros` object returned by the context tool, unchanged (it is shown in the Shiplog UI on "
            "this version)."))] = None,
        instrucoes_extras: Annotated[str | None, Field(description="The extra instructions used, if any (same "
                                                                   "value passed to the context tool).")] = None,
    ) -> dict[str, Any]:
        return await chamar("POST", "/external/posts", _sem_nulos({
            "texto": texto, "hashtags": hashtags, "caminho": caminho, "projeto_id": projeto_id,
            "descricao": descricao, "hooks_alternativos": hooks_alternativos, "resumo_tecnico": resumo_tecnico,
            "destaques": destaques, "commit_referencia": commit_referencia, "base_versao_id": base_versao_id,
            "parametros": parametros, "instrucoes_extras": instrucoes_extras}))

    @srv.tool(title="Save Medium article", annotations=GRAVA, description=(
        "Save an article YOU wrote as a new draft version in Shiplog. Every entry in `trechos_de_codigo` is "
        "checked against the project files (path relative to the project root + real line range); invalid "
        "snippets are rejected with details so you can fix them. Never publishes."))
    async def save_article(
        titulo: str,
        subtitulo: str,
        corpo_markdown: Annotated[str, Field(description="Full article in Markdown.")],
        trechos_de_codigo: Annotated[list[dict[str, str]], Field(description=(
            "Code snippets used, e.g. [{\"arquivo\": \"src/app.py\", \"linhas\": \"10-42\"}].") )],
        caminho: Caminho = None,
        projeto_id: ProjetoId = None,
        tags: Annotated[list[str] | None, Field(description="Up to 5 tags.")] = None,
        sugestoes_de_imagens: Annotated[list[str] | None, Field(description="Image ideas.")] = None,
        base_versao_id: Annotated[int | None, Field(description="Version id this one revises, if any.")] = None,
        parametros: Annotated[dict[str, Any] | None, Field(description=(
            "The `parametros` object returned by the context tool, unchanged (it is shown in the Shiplog UI on "
            "this version)."))] = None,
        instrucoes_extras: Annotated[str | None, Field(description="The extra instructions used, if any (same "
                                                                   "value passed to the context tool).")] = None,
    ) -> dict[str, Any]:
        return await chamar("POST", "/external/articles", _sem_nulos({
            "titulo": titulo, "subtitulo": subtitulo, "corpo_markdown": corpo_markdown,
            "trechos_de_codigo": trechos_de_codigo, "caminho": caminho, "projeto_id": projeto_id, "tags": tags,
            "sugestoes_de_imagens": sugestoes_de_imagens, "base_versao_id": base_versao_id,
            "parametros": parametros, "instrucoes_extras": instrucoes_extras}))

    @srv.tool(title="Save comment suggestions", annotations=GRAVA, description=(
        "Register comment suggestions YOU wrote for someone else's post/article, so the user can track them in "
        "Shiplog (status 'sugerido'). Images are optional and must be absolute paths of local files."))
    async def save_comment(
        sugestoes: Annotated[list[dict[str, str]], Field(description=(
            "1-5 options: [{\"abordagem\": \"short label\", \"texto\": \"ready comment\"}].") )],
        plataforma: Annotated[Literal["linkedin", "medium"], Field(description="Platform.")] = "linkedin",
        texto_original: Annotated[str, Field(description="The commented content, as the user pasted it.")] = "",
        resumo: Annotated[str, Field(description="1-2 sentences about the content.")] = "",
        autor: Annotated[str, Field(description="Author of the original content.")] = "",
        link: Annotated[str, Field(description="Link of the original content.")] = "",
        caminhos_imagens: Annotated[list[str] | None, Field(description="Absolute paths of images.")] = None,
    ) -> dict[str, Any]:
        return await chamar("POST", "/external/comments", _sem_nulos({
            "sugestoes": sugestoes, "plataforma": plataforma, "texto_original": texto_original, "resumo": resumo,
            "autor": autor, "link": link, "caminhos_imagens": caminhos_imagens}))

    # -- status -----------------------------------------------------------------
    @srv.tool(title="Set post/article status", annotations=GRAVA_IDEMPOTENTE, description=(
        "Move a post or article version to rascunho, pronto or publicado. Use 'publicado' only after the user "
        "says they published it, ideally with the link. Shiplog never publishes by itself."))
    async def set_status(
        tipo: Literal["post", "artigo"],
        versao_id: int,
        status: Literal["rascunho", "pronto", "publicado"],
        link: Annotated[str | None, Field(description="Public link (LinkedIn/Medium) when publicado.")] = None,
    ) -> dict[str, Any]:
        rota = "posts" if tipo == "post" else "articles"
        return await chamar("PATCH", f"/{rota}/{versao_id}/status", _sem_nulos({"status": status, "link": link}))

    @srv.tool(title="Mark comment as used", annotations=GRAVA_IDEMPOTENTE, description=(
        "Record which suggestion the user actually posted (by index, starting at 0) or the final text they "
        "used, plus the link. Status becomes 'usado'."))
    async def mark_comment_used(
        comentario_id: int,
        indice: Annotated[int | None, Field(description="Index of the suggestion used (0-based).")] = None,
        texto_final: Annotated[str | None, Field(description="Final text, if the user edited it.")] = None,
        link: Annotated[str | None, Field(description="Link to the posted comment.")] = None,
    ) -> dict[str, Any]:
        return await chamar("POST", f"/comments/{comentario_id}/usado",
                            _sem_nulos({"indice": indice, "texto_final": texto_final, "link": link}))

    # -- leitura ----------------------------------------------------------------
    @srv.tool(title="List", annotations=RO, description=(
        "List projects, the post/article versions of a project, or comment suggestions. Read-only."))
    async def list_items(
        tipo: Literal["projetos", "posts", "artigos", "comentarios"],
        projeto_id: Annotated[int | None, Field(description="Required for posts and artigos.")] = None,
    ) -> dict[str, Any]:
        if tipo in ("posts", "artigos"):
            if projeto_id is None:
                raise ToolError("Informe projeto_id para listar posts ou artigos.")
            itens = await chamar("GET", f"/projects/{projeto_id}/{'posts' if tipo == 'posts' else 'articles'}")
        else:
            itens = await chamar("GET", "/projects" if tipo == "projetos" else "/comments")
        return {"tipo": tipo, "itens": itens}

    @srv.tool(title="Get one item", annotations=RO, description="Get a project, post/article version or comment by id.")
    async def get_item(tipo: Literal["projeto", "post", "artigo", "comentario"], id: int) -> dict[str, Any]:
        rota = {"projeto": "projects", "post": "posts", "artigo": "articles", "comentario": "comments"}[tipo]
        return await chamar("GET", f"/{rota}/{id}")

    # -- resources --------------------------------------------------------------
    @srv.resource("shiplog://perfil", name="perfil", title="Author profile", mime_type="text/markdown",
                  description="The author's professional profile and writing voice configured in Shiplog.")
    async def perfil() -> str:
        cfg = await chamar("GET", "/settings")
        return ("# Perfil profissional\n\n" + ((cfg.get("perfil_profissional") or "").strip() or "(não configurado)")
                + "\n\n# Voz\n\n" + ((cfg.get("perfil_voz") or "").strip() or "(não configurada)") + "\n")

    @srv.resource("shiplog://config/escrita", name="config_escrita", title="Writing defaults",
                  mime_type="application/json", description="Base prompt and default parameters for posts/articles.")
    async def config_escrita() -> dict[str, Any]:
        cfg = await chamar("GET", "/settings")
        return {k: cfg.get(k) for k in ("prompt_base", "parametros_padrao_post", "parametros_padrao_artigo")}

    # -- prompts ----------------------------------------------------------------
    @srv.prompt(title="Post about this project", description="Write a LinkedIn post about the current project state.")
    def post_about_project(foco: str = "") -> str:
        extra = f" Foco pedido pelo usuário: {foco}." if foco else ""
        return ("Escreva um post do LinkedIn sobre o estado atual deste projeto usando o Shiplog." + extra +
                " Roteiro: 1) current_project(caminho=<diretório atual>); 2) post_context(caminho=<diretório atual>), "
                "passando só os parâmetros (tom, tamanho, idioma) que eu já disse; 3) se a resposta vier com "
                "parametros_confirmados=false e confirmar_parametros, me pergunte os parâmetros antes de escrever e "
                "chame post_context de novo; 4) leia os arquivos relevantes das mudanças; 5) escreva seguindo "
                "prompt_base, perfil, voz e regras; 6) mostre o texto e ajuste se eu pedir; 7) save_post com "
                "commit_referencia; 8) mostre o link do Shiplog.")

    @srv.prompt(title="Medium article about this project", description="Write a Medium article about this project.")
    def article_about_project(formato: str = "") -> str:
        extra = f" Formato: {formato} (passe formato=\"{formato}\")." if formato else ""
        return ("Escreva um artigo para o Medium sobre este projeto usando o Shiplog." + extra +
                " Roteiro: article_context(caminho=<diretório atual>), passando só os parâmetros (idioma, publico, "
                "formato) que eu já disse → se vier parametros_confirmados=false e confirmar_parametros, me pergunte "
                "antes de escrever e chame article_context de novo → leia o código → escreva com trechos reais "
                "(caminho e linhas) → mostre → save_article → mostre o link do Shiplog.")

    @srv.prompt(title="Comment on a post", description="Suggest comments for someone else's post or article.")
    def suggest_comment(plataforma: str = "linkedin") -> str:
        return (f"Vou colar um conteúdo de outra pessoa no {plataforma}. Chame comment_context(plataforma="
                f"\"{plataforma}\"), escreva 3 opções de comentário seguindo perfil, voz e regras, mostre, e "
                "registre com save_comment. Quando eu disser qual usei, chame mark_comment_used.")

    return srv


def _logging() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    log.setLevel(logging.INFO)
    log.propagate = False
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]  # stdout é do protocolo
    try:
        paths = Paths(resolve_data_dir()).ensure()
        handlers.append(RotatingFileHandler(paths.logs / "mcp.log", maxBytes=500_000, backupCount=3,
                                            encoding="utf-8"))
    except OSError:
        pass
    for h in handlers:
        h.setFormatter(fmt)
        h.addFilter(RedactingFilter())
        log.addHandler(h)


def main() -> None:
    _logging()
    log.info("Servidor MCP do Shiplog iniciado (stdio)")
    criar_servidor().run("stdio")


if __name__ == "__main__":
    main()
