"""Rotas de posts e artigos (RF-17..RF-20, RF-24..RF-30)."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Response

from ..context import AppContext
from ..services.export import artigo_markdown
from ..services.projects import slug
from .deps import get_ctx
from .models import ArtigoVersao, PostVersao, StatusIn

router = APIRouter(tags=["posts e artigos"])


# -- posts -------------------------------------------------------------------
@router.get("/projects/{pid}/posts")
def posts(pid: int, ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    ctx.projects.obter(pid)
    return ctx.versions.listar("post", pid)


@router.get("/posts/{vid}")
def post(vid: int, ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.versions.apresentar("post", ctx.versions.obter("post", vid))  # type: ignore[return-value]


@router.post("/posts/{vid}/versions", status_code=201)
def post_editar(vid: int, body: PostVersao, ctx: AppContext = Depends(get_ctx)) -> dict:
    mud = body.model_dump()
    if mud.get("hashtags") is not None:
        mud["hashtags"] = [h if h.startswith("#") else f"#{h}" for h in (x.strip() for x in mud["hashtags"]) if h]
    nid = ctx.versions.editar("post", vid, mud)
    return ctx.versions.apresentar("post", ctx.versions.obter("post", nid))  # type: ignore[return-value]


@router.patch("/posts/{vid}/status")
def post_status(vid: int, body: StatusIn, ctx: AppContext = Depends(get_ctx)) -> dict:
    ctx.versions.alterar_status("post", vid, body.status, str(body.link) if body.link else None)
    return ctx.versions.apresentar("post", ctx.versions.obter("post", vid))  # type: ignore[return-value]


# -- artigos -----------------------------------------------------------------
@router.get("/projects/{pid}/articles")
def artigos(pid: int, ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    ctx.projects.obter(pid)
    return ctx.versions.listar("artigo", pid)


@router.get("/articles/{vid}")
def artigo(vid: int, ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.versions.apresentar("artigo", ctx.versions.obter("artigo", vid))  # type: ignore[return-value]


@router.post("/articles/{vid}/versions", status_code=201)
def artigo_editar(vid: int, body: ArtigoVersao, ctx: AppContext = Depends(get_ctx)) -> dict:
    mud = body.model_dump()
    mud["tags"] = [t.strip().lstrip("#") for t in mud["tags"] if t.strip()]
    nid = ctx.versions.editar("artigo", vid, mud)
    return ctx.versions.apresentar("artigo", ctx.versions.obter("artigo", nid))  # type: ignore[return-value]


@router.patch("/articles/{vid}/status")
def artigo_status(vid: int, body: StatusIn, ctx: AppContext = Depends(get_ctx)) -> dict:
    ctx.versions.alterar_status("artigo", vid, body.status, str(body.link) if body.link else None)
    return ctx.versions.apresentar("artigo", ctx.versions.obter("artigo", vid))  # type: ignore[return-value]


@router.get("/articles/{vid}/export.md")
def artigo_export(vid: int, ctx: AppContext = Depends(get_ctx)) -> Response:
    a = ctx.versions.obter("artigo", vid)
    nome = f"{slug(a['titulo'])}-v{a['versao']}.md"
    return Response(
        artigo_markdown(a),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=\"{nome}\"; filename*=UTF-8''{quote(nome)}"},
    )
