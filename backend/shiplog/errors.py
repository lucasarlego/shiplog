"""Erro de negócio com formato único (spec 000 FR-03, spec 004 FR-08)."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    def __init__(
        self,
        codigo: str,
        mensagem: str,
        acao_sugerida: str | None = None,
        status: int = 400,
        detalhes: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.acao_sugerida = acao_sugerida
        self.status = status
        self.detalhes = detalhes or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "erro": {
                "codigo": self.codigo,
                "mensagem": self.mensagem,
                "acao_sugerida": self.acao_sugerida,
                "detalhes": self.detalhes,
            }
        }


def nao_encontrado(oque: str) -> AppError:
    return AppError("nao_encontrado", f"{oque} não encontrado.", None, 404)
