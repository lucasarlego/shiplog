"""Rotas de configurações e exportação (RF-21..RF-23)."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Response

from ..config import write_pointer
from ..context import AppContext
from ..errors import AppError
from ..services import export
from .deps import get_ctx
from .models import ConfigIn, CurriculoIn, PerfilGerar

router = APIRouter(tags=["configurações"])


def _config(ctx: AppContext) -> dict:
    c = dict(ctx.dao.config())
    c.pop("id", None)
    c["pasta_dados"] = str(ctx.paths.data_dir)
    c["reinicio_necessario"] = ctx.reinicio_necessario
    return c


@router.get("/settings")
def obter(ctx: AppContext = Depends(get_ctx)) -> dict:
    return _config(ctx)


@router.put("/settings")
def salvar(body: ConfigIn, ctx: AppContext = Depends(get_ctx)) -> dict:
    dados = body.model_dump(exclude_unset=True)
    pasta = dados.pop("pasta_dados", None)
    for chave, tipo in (("parametros_padrao_post", "post"), ("parametros_padrao_artigo", "artigo")):
        if dados.get(chave) is not None:
            dados[chave] = ctx.generation.normalizar_parametros(tipo, dados[chave])
    dados = {k: v for k, v in dados.items() if v is not None}
    if dados:
        ctx.dao.salvar_config(**dados)
    if pasta and pasta.strip() and pasta.strip() != str(ctx.paths.data_dir):
        try:
            write_pointer(pasta.strip())
        except OSError as e:
            raise AppError("validacao", f"Não foi possível gravar a pasta de dados: {e}", None, 422) from e
        ctx.reinicio_necessario = True
    if "caminho_cli" in dados:
        ctx.health.invalidate()
    return _config(ctx)


@router.put("/profile/curriculo")
def enviar_curriculo(body: CurriculoIn, ctx: AppContext = Depends(get_ctx)) -> dict:
    ctx.profile.salvar_curriculo(body.nome, body.conteudo_base64)
    return _config(ctx)


@router.delete("/profile/curriculo")
def remover_curriculo(ctx: AppContext = Depends(get_ctx)) -> dict:
    ctx.profile.remover_curriculo()
    return _config(ctx)


@router.post("/profile/generate")
def gerar_perfil(body: PerfilGerar, ctx: AppContext = Depends(get_ctx)) -> dict:
    """Síncrono (~20-60 s): o perfil é pequeno e a tela espera pelo resultado (spec 007)."""
    ctx.profile.gerar(body.sobre)
    return _config(ctx)


@router.get("/export")
def exportar(formato: Literal["md", "json"] = "md", ctx: AppContext = Depends(get_ctx)) -> Response:
    hoje = date.today().isoformat()
    if formato == "json":
        return Response(export.historico_json(ctx.dao, ctx.versions), media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="shiplog-{hoje}.json"'})
    return Response(export.historico_md(ctx.dao, ctx.versions), media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="shiplog-{hoje}.md"'})
