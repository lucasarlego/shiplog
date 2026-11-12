"""Rotas de comentários (spec 008)."""

from fastapi import APIRouter, Depends, Response
from fastapi.responses import FileResponse

from ..context import AppContext
from .deps import get_ctx
from .models import ComentarioCriar, ComentarioGerar

router = APIRouter(tags=["comentários"])


@router.get("/comments")
def listar(ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    return ctx.comments.listar()


@router.post("/comments", status_code=201)
def criar(body: ComentarioCriar, ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.comments.criar(body.texto_post, [i.model_dump() for i in body.imagens], body.autor, body.link)


@router.get("/comments/{cid}")
def obter(cid: int, ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.comments.obter(cid)


@router.post("/comments/{cid}/generate")
def gerar(cid: int, body: ComentarioGerar, ctx: AppContext = Depends(get_ctx)) -> dict:
    """Síncrono (~15-40 s), como o perfil (spec 007)."""
    return ctx.comments.gerar(cid, body.parametros, body.instrucoes)


@router.get("/comments/{cid}/images/{nome}")
def imagem(cid: int, nome: str, ctx: AppContext = Depends(get_ctx)) -> FileResponse:
    return FileResponse(ctx.comments.imagem(cid, nome))


@router.delete("/comments/{cid}", status_code=204)
def excluir(cid: int, ctx: AppContext = Depends(get_ctx)) -> Response:
    ctx.comments.excluir(cid)
    return Response(status_code=204)
