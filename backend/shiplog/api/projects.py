"""Rotas de projetos (RF-01..RF-06, RF-10)."""

from fastapi import APIRouter, Depends, Response

from ..context import AppContext
from ..errors import AppError
from .deps import get_ctx
from .models import CheckUpdates, ProjetoCriar, ProjetoEditar, UrlIn

router = APIRouter(tags=["projetos"])


@router.get("/projects")
def listar(status: str | None = None, ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    return ctx.projects.listar(status)


@router.post("/projects/validate")
def validar(body: UrlIn, ctx: AppContext = Depends(get_ctx)) -> dict:
    try:
        info = ctx.projects.validar(body.url)
    except AppError as e:
        return {"valida": False, "url_normalizada": None, "nome_sugerido": None, "erro": e.to_dict()["erro"]}
    return {"valida": True, "url_normalizada": info.normalizada, "nome_sugerido": info.nome, "erro": None}


@router.post("/projects", status_code=201)
def criar(body: ProjetoCriar, ctx: AppContext = Depends(get_ctx)) -> dict:
    if body.url and body.url.strip():
        projeto = ctx.projects.cadastrar(body.url, body.nome, body.branch, body.notas)
    elif body.descricao is not None:
        projeto = ctx.projects.cadastrar_livre(body.descricao, body.nome, body.notas)  # spec 006
    else:
        raise AppError("validacao", "Informe a URL de um repositório ou descreva o que você quer contar.",
                       "Use o modo Repositório ou o modo Descrever.", 422)
    job = None
    if body.gerar:
        try:
            job = ctx.generation.criar(projeto["id"], "post", body.parametros)
        except AppError as e:
            # Projeto fica cadastrado; a interface mostra o motivo de não ter gerado.
            return {"projeto": ctx.projects.detalhe(projeto["id"]), "job": None, "aviso": e.to_dict()["erro"]}
    return {"projeto": ctx.projects.detalhe(projeto["id"]), "job": job, "aviso": None}


@router.post("/projects/check-updates")
def check_updates(body: CheckUpdates | None = None, ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    return ctx.projects.check_updates(body.ids if body else None)


@router.get("/projects/{pid}")
def detalhe(pid: int, ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.projects.detalhe(pid)


@router.patch("/projects/{pid}")
def editar(pid: int, body: ProjetoEditar, ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.projects.editar(pid, body.nome, body.branch, body.notas, body.descricao)


@router.delete("/projects/{pid}", status_code=204)
def excluir(pid: int, manter_historico: bool = False, ctx: AppContext = Depends(get_ctx)) -> Response:
    ctx.projects.excluir(pid, manter_historico)
    return Response(status_code=204)
