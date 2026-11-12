"""Acesso ao contexto da aplicação a partir das rotas."""

from __future__ import annotations

from fastapi import Request

from ..context import AppContext


def get_ctx(request: Request) -> AppContext:
    return request.app.state.ctx
