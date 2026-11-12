"""Rotas de saúde (RI-07, RI-09)."""

from fastapi import APIRouter, Depends

from ..context import AppContext
from .deps import get_ctx

router = APIRouter(tags=["saúde"])


@router.get("/health")
def health(ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.health.get()


@router.post("/health/refresh")
def health_refresh(ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.health.get(force=True)
