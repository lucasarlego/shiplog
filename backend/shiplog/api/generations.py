"""Rotas de gerações e jobs (RF-11..RF-16, RF-24, RI-06)."""

from fastapi import APIRouter, Depends

from ..context import AppContext
from .deps import get_ctx
from .models import GeracaoCriar

router = APIRouter(tags=["gerações"])


@router.post("/projects/{pid}/generations", status_code=202)
def criar(pid: int, body: GeracaoCriar, ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.generation.criar(pid, body.tipo, body.parametros, body.instrucoes_extras, body.base_versao_id,
                                body.atualizar_repo, body.atualizacao)


@router.get("/projects/{pid}/generations")
def listar(pid: int, ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    ctx.projects.obter(pid)
    return [ctx.generation.apresentar(g) for g in ctx.dao.listar_geracoes(pid)]


@router.get("/jobs")
def jobs(ativos: bool = True, ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    return [ctx.generation.apresentar(g) for g in ctx.dao.geracoes_ativas()]


@router.get("/jobs/{gid}")
def job(gid: int, ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.generation.job(gid)


@router.post("/jobs/{gid}/cancel")
def cancelar(gid: int, ctx: AppContext = Depends(get_ctx)) -> dict:
    ctx.jobs.cancelar(gid)
    return ctx.generation.job(gid)


@router.post("/jobs/{gid}/retry", status_code=202)
def retry(gid: int, ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.generation.retry(gid)


@router.get("/generations/{gid}/debug")
def debug(gid: int, ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.generation.debug(gid)
