"""Rotas de suporte ao MCP local (spec 009): contexto para o modelo do harness e salvamento do que ele escreveu."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..context import AppContext
from ..errors import AppError
from ..services import comments as com
from ..services import workspace
from ..storage.db import now_iso
from .deps import get_ctx

router = APIRouter(tags=["mcp"])


class ResolverIn(BaseModel):
    caminho: str
    vincular: bool = False


class ContextoPostIn(BaseModel):
    projeto_id: int | None = None
    caminho: str | None = None
    descricao: str | None = Field(default=None, max_length=8000)
    parametros: dict[str, Any] | None = None
    desde_commit: str | None = None
    confirmacao: Literal["formulario", "recusada"] | None = None
    instrucoes_extras: str = Field(default="", max_length=4000)
    base_versao_id: int | None = None


class ContextoArtigoIn(BaseModel):
    projeto_id: int | None = None
    caminho: str | None = None
    parametros: dict[str, Any] | None = None
    confirmacao: Literal["formulario", "recusada"] | None = None
    instrucoes_extras: str = Field(default="", max_length=4000)
    base_versao_id: int | None = None


class ContextoComentarioIn(BaseModel):
    plataforma: Literal["linkedin", "medium"] = "linkedin"
    parametros: dict[str, Any] | None = None


class PostExternoIn(BaseModel):
    projeto_id: int | None = None
    caminho: str | None = None
    descricao: str | None = Field(default=None, max_length=8000)
    nome: str | None = None
    texto: str
    hashtags: list[str]
    hooks_alternativos: list[str] = Field(default_factory=list)
    resumo_tecnico: str = ""
    destaques: list[str] = Field(default_factory=list)
    base_versao_id: int | None = None
    commit_referencia: str | None = None
    parametros: dict[str, Any] | None = None
    instrucoes_extras: str = Field(default="", max_length=4000)


class TrechoIn(BaseModel):
    arquivo: str
    linhas: str


class ArtigoExternoIn(BaseModel):
    projeto_id: int | None = None
    caminho: str | None = None
    titulo: str
    subtitulo: str
    corpo_markdown: str
    tags: list[str] = Field(default_factory=list)
    trechos_de_codigo: list[TrechoIn]
    sugestoes_de_imagens: list[str] = Field(default_factory=list)
    base_versao_id: int | None = None
    parametros: dict[str, Any] | None = None
    instrucoes_extras: str = Field(default="", max_length=4000)


class SugestaoIn(BaseModel):
    abordagem: str = ""
    texto: str


class ComentarioExternoIn(BaseModel):
    plataforma: Literal["linkedin", "medium"] = "linkedin"
    texto_original: str = Field(default="", max_length=10_000)
    sugestoes: list[SugestaoIn] = Field(min_length=1, max_length=5)
    resumo: str = ""
    autor: str = Field(default="", max_length=200)
    link: str = Field(default="", max_length=500)
    caminhos_imagens: list[str] = Field(default_factory=list, max_length=com.MAX_IMAGENS)
    parametros: dict[str, Any] | None = None


class UsadoIn(BaseModel):
    indice: int | None = None
    texto_final: str | None = Field(default=None, max_length=10_000)
    link: str | None = Field(default=None, max_length=500)


def _com_link(ctx: AppContext, pid: int, extra: dict[str, Any]) -> dict[str, Any]:
    return {**extra, "projeto_id": pid, "link_shiplog": ctx.contexto.link_projeto(pid)}


@router.post("/workspace/resolve")
def resolver(body: ResolverIn, ctx: AppContext = Depends(get_ctx)) -> dict:
    d = ctx.projects.projeto_atual(body.caminho, body.vincular)
    d["link_shiplog"] = ctx.contexto.link_projeto(d["id"])
    return d


@router.post("/context/post")
def contexto_post(body: ContextoPostIn, ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.contexto.post(body.projeto_id, body.caminho, body.descricao, body.parametros, body.desde_commit,
                             body.confirmacao, body.instrucoes_extras, body.base_versao_id)


@router.post("/context/artigo")
def contexto_artigo(body: ContextoArtigoIn, ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.contexto.artigo(body.projeto_id, body.caminho, body.parametros, body.confirmacao,
                               body.instrucoes_extras, body.base_versao_id)


@router.post("/context/comentario")
def contexto_comentario(body: ContextoComentarioIn, ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.contexto.comentario(body.plataforma, body.parametros)


def _projeto_e_raiz(ctx: AppContext, projeto_id: int | None, caminho: str | None) -> tuple[dict[str, Any], Path | None, str | None]:
    """Projeto alvo, pasta para conferir trechos e HEAD atual (para `commit_referencia`)."""
    if caminho:
        p = ctx.projects.projeto_atual(caminho)
        return p, Path(p["pasta"]["caminho"]), p["pasta"]["head"]
    if projeto_id is None:
        raise AppError("validacao", "Informe `caminho` (pasta do projeto) ou `projeto_id`.", None, 422)
    p = ctx.projects.detalhe(projeto_id)
    if p["origem"] == "local" and p["caminho_local"]:
        pasta = workspace.resolver(p["caminho_local"])
        return p, Path(pasta.caminho), pasta.head
    clone = Path(p["caminho_local"]) if p["caminho_local"] and p.get("clone_existe") else None
    return p, clone, None


@router.post("/external/posts", status_code=201)
def salvar_post(body: PostExternoIn, ctx: AppContext = Depends(get_ctx)) -> dict:
    if body.projeto_id is None and not body.caminho and body.descricao:
        p, head = ctx.projects.cadastrar_livre(body.descricao, body.nome), None
    else:
        p, _raiz, head = _projeto_e_raiz(ctx, body.projeto_id, body.caminho)
    dados = body.model_dump(include={"texto", "hashtags", "hooks_alternativos", "resumo_tecnico", "destaques"})
    vid = ctx.versions.criar_externa("post", p["id"], dados, None, commit_referencia=body.commit_referencia or head,
                                     base_versao_id=body.base_versao_id, parametros=body.parametros,
                                     instrucoes_extras=body.instrucoes_extras)
    ctx.dao.atualizar_projeto(p["id"], ultima_analise_em=now_iso())
    v = ctx.versions.apresentar("post", ctx.dao.versao("posts", vid))
    return _com_link(ctx, p["id"], {"versao": v})


@router.post("/external/articles", status_code=201)
def salvar_artigo(body: ArtigoExternoIn, ctx: AppContext = Depends(get_ctx)) -> dict:
    p, raiz, head = _projeto_e_raiz(ctx, body.projeto_id, body.caminho)
    if p["origem"] == "livre":
        raise AppError("artigo_requer_repositorio", "Artigos precisam de um projeto com código.", None, 409)
    dados = body.model_dump(exclude={"projeto_id", "caminho", "base_versao_id", "parametros", "instrucoes_extras"})
    vid = ctx.versions.criar_externa("artigo", p["id"], dados, raiz, commit_referencia=head,
                                     base_versao_id=body.base_versao_id, parametros=body.parametros,
                                     instrucoes_extras=body.instrucoes_extras)
    v = ctx.versions.apresentar("artigo", ctx.dao.versao("artigos", vid))
    return _com_link(ctx, p["id"], {"versao": v})


def _ler_imagens(caminhos: list[str]) -> list[dict[str, str]]:
    out = []
    for c in caminhos:
        f = Path(c).expanduser()
        if not f.is_absolute() or not f.is_file():
            raise AppError("validacao", f"Imagem não encontrada: '{c}'.", "Passe o caminho absoluto do arquivo.", 422)
        if f.suffix.lower() not in com.ASSINATURAS:
            raise AppError("validacao", f"'{f.name}' não é PNG, JPG, GIF ou WEBP.", None, 422)
        if f.stat().st_size > com.MAX_BYTES:
            raise AppError("validacao", f"'{f.name}' passou de 5 MB.", None, 422)
        out.append({"nome": f.name, "conteudo_base64": base64.b64encode(f.read_bytes()).decode()})
    return out


@router.post("/external/comments", status_code=201)
def salvar_comentario(body: ComentarioExternoIn, ctx: AppContext = Depends(get_ctx)) -> dict:
    c = ctx.comments.criar_externo(body.plataforma, body.texto_original, [s.model_dump() for s in body.sugestoes],
                                   body.resumo, body.autor, body.link, _ler_imagens(body.caminhos_imagens),
                                   body.parametros)
    return {**c, "link_shiplog": f"{ctx.contexto.url_base}/comentarios/{c['id']}"}


@router.post("/comments/{cid}/usado")
def marcar_usado(cid: int, body: UsadoIn, ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.comments.marcar_usado(cid, body.indice, body.texto_final, body.link)


@router.post("/comments/{cid}/sugerido")
def voltar_sugerido(cid: int, ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.comments.voltar_sugerido(cid)

