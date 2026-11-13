"""Cliente HTTP da API local, usado pelo servidor MCP (spec 009 FR-02, NFR-05)."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from typing import Any

import httpx

from ..config import HOST, resolve_port

log = logging.getLogger("shiplog.mcp")

ESPERA_SERVIDOR = 20.0


class ErroShiplog(Exception):
    """Erro já formatado para o modelo: mensagem + o que fazer."""

    def __init__(self, codigo: str, mensagem: str, acao: str | None = None, detalhes: dict[str, Any] | None = None):
        texto = mensagem + (f" O que fazer: {acao}" if acao else "")
        erros = (detalhes or {}).get("erros")
        if erros:
            texto += " Detalhes: " + "; ".join(str(e) for e in erros)
        super().__init__(texto)
        self.codigo = codigo


def url_base() -> str:
    return f"http://{HOST}:{resolve_port()}"


class ShiplogClient:
    def __init__(self, base: str | None = None, transport: httpx.AsyncBaseTransport | None = None,
                 iniciar_servidor: bool = True) -> None:
        self.base = (base or url_base()).rstrip("/")
        self._transport = transport
        self._iniciar = iniciar_servidor and transport is None
        self._pronto = False

    def _cliente(self, timeout: float = 30) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base, transport=self._transport, timeout=timeout)

    async def _ping(self) -> bool:
        try:
            async with self._cliente(timeout=1.5) as c:
                r = await c.get("/api/ping")
                return r.status_code == 200 and r.json().get("app") == "shiplog"
        except (httpx.HTTPError, ValueError):
            return False

    async def garantir_servidor(self) -> None:
        """Sobe o Shiplog em segundo plano se ele não estiver rodando (sem abrir o navegador)."""
        if self._pronto or await self._ping():
            self._pronto = True
            return
        if not self._iniciar:
            raise ErroShiplog("servidor_indisponivel", f"O Shiplog não respondeu em {self.base}.",
                              "Abra o Shiplog (atalho ou `make run`) e tente de novo.")
        log.info("Shiplog fora do ar; iniciando em segundo plano")
        try:
            subprocess.Popen([sys.executable, "-m", "shiplog", "--no-browser"], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
                             env={**os.environ}, cwd=os.path.expanduser("~"))
        except OSError as e:
            raise ErroShiplog("servidor_indisponivel", f"Não consegui iniciar o Shiplog: {e}.",
                              "Rode `make run` na pasta do Shiplog.") from e
        passos = int(ESPERA_SERVIDOR / 0.25)
        for _ in range(passos):
            await asyncio.sleep(0.25)
            if await self._ping():
                self._pronto = True
                return
        raise ErroShiplog("servidor_indisponivel", f"O Shiplog não subiu em {int(ESPERA_SERVIDOR)} s.",
                          "Veja os logs em ~/.shiplog/logs/shiplog.log ou rode `make run`.")

    async def req(self, metodo: str, caminho: str, json: Any = None, params: dict[str, Any] | None = None) -> Any:
        await self.garantir_servidor()
        try:
            async with self._cliente() as c:
                r = await c.request(metodo, "/api" + caminho, json=json,
                                    params={k: v for k, v in (params or {}).items() if v is not None})
        except httpx.HTTPError as e:
            self._pronto = False
            raise ErroShiplog("servidor_indisponivel", f"Falha ao falar com o Shiplog: {e}.",
                              "Confira se o Shiplog está aberto.") from e
        if r.status_code == 204:
            return None
        try:
            dados = r.json()
        except ValueError:
            dados = None
        if r.status_code >= 400:
            erro = (dados or {}).get("erro") if isinstance(dados, dict) else None
            if erro:
                raise ErroShiplog(erro.get("codigo", "erro"), erro.get("mensagem", "Erro."),
                                  erro.get("acao_sugerida"), erro.get("detalhes"))
            raise ErroShiplog("erro_http", f"O Shiplog respondeu {r.status_code}.")
        return dados

    async def get(self, caminho: str, **params: Any) -> Any:
        return await self.req("GET", caminho, params=params)

    async def post(self, caminho: str, json: Any = None) -> Any:
        return await self.req("POST", caminho, json=json)

    async def patch(self, caminho: str, json: Any = None) -> Any:
        return await self.req("PATCH", caminho, json=json)
