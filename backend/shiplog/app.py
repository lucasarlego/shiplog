"""Criação da aplicação FastAPI (spec 000 FR-01, spec 004)."""

from __future__ import annotations

import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from . import __version__
from .api import comments, generations, health, projects, settings, versions
from .config import Paths, resolve_data_dir, setup_logging
from .context import AppContext, build_context
from .errors import AppError

log = logging.getLogger("shiplog.app")


def frontend_dist() -> Path:
    env = os.environ.get("SHIPLOG_FRONTEND_DIST")
    return Path(env) if env else Path(__file__).resolve().parents[2] / "frontend" / "dist"


AJUDA_BUILD = """<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Shiplog</title>
<body style="font-family:system-ui;max-width:640px;margin:10vh auto;padding:0 16px;line-height:1.6">
<h1>Shiplog</h1><p>A API está no ar, mas a interface ainda não foi compilada.</p>
<p>Rode <code>make build</code> (ou <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code>) e recarregue.</p>
<p>Documentação da API: <a href="/api/docs">/api/docs</a></p></body></html>"""


def create_app(ctx: AppContext | None = None, start_worker: bool = True) -> FastAPI:
    if ctx is None:
        paths = Paths(resolve_data_dir()).ensure()
        setup_logging(paths)
        ctx = build_context(paths)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if start_worker:
            ctx.jobs.start()
        # Health em segundo plano para não atrasar o boot (RNF-02).
        threading.Thread(target=lambda: ctx.health.get(force=True), daemon=True).start()
        log.info("Shiplog %s iniciado. Dados em %s", __version__, ctx.paths.data_dir)
        yield
        ctx.jobs.stop()

    app = FastAPI(title="Shiplog API", version=__version__, lifespan=lifespan,
                  docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.state.ctx = ctx
    # Só aceita requisições endereçadas ao próprio computador. Sem isso, um site malicioso aberto no navegador
    # poderia usar DNS rebinding para falar com a API local (ler dados, gastar a cota do Claude).
    extras = [h.strip() for h in os.environ.get("SHIPLOG_ALLOWED_HOSTS", "").split(",") if h.strip()]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]", *extras])

    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(exc.to_dict(), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        erros = [f"{'.'.join(str(x) for x in e['loc'][1:])}: {e['msg']}" for e in exc.errors()]
        err = AppError("validacao", "Dados inválidos: " + "; ".join(erros), "Corrija os campos e tente novamente.",
                       422, {"erros": erros})
        return JSONResponse(err.to_dict(), status_code=422)

    @app.exception_handler(Exception)
    async def _interno(_: Request, exc: Exception) -> JSONResponse:
        log.exception("Erro interno: %s", exc)
        err = AppError("erro_interno", "Erro interno inesperado.", "Veja os logs na pasta de dados.", 500)
        return JSONResponse(err.to_dict(), status_code=500)

    @app.get("/api/ping", include_in_schema=False)
    def ping() -> dict:
        return {"app": "shiplog", "versao": __version__}

    for r in (health.router, projects.router, generations.router, versions.router, settings.router, comments.router):
        app.include_router(r, prefix="/api")

    dist = frontend_dist()

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(AppError("nao_encontrado", "Rota não encontrada.", None, 404).to_dict(), 404)
        if not (dist / "index.html").is_file():
            return HTMLResponse(AJUDA_BUILD)
        if full_path:
            alvo = (dist / full_path).resolve()
            if dist.resolve() in alvo.parents and alvo.is_file():
                return FileResponse(alvo)
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})

    return app
