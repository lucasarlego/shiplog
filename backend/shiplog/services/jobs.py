"""Fila de gerações: 1 worker, FIFO, cancelável (spec 003 §3.5; RNF-04, RF-15, RF-16)."""

from __future__ import annotations

import logging
import queue
import threading
from typing import Callable

from ..errors import AppError, nao_encontrado
from ..storage.dao import Dao

log = logging.getLogger("shiplog.jobs")


class JobQueue:
    def __init__(self, dao: Dao, executar: Callable[[int, threading.Event], None]) -> None:
        self.dao = dao
        self._executar = executar
        self._q: "queue.Queue[int | None]" = queue.Queue()
        self._pendentes: list[int] = []
        self._cancel: dict[int, threading.Event] = {}
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self.atual: int | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, name="shiplog-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2) -> None:
        with self._lock:
            for ev in self._cancel.values():
                ev.set()
        self._q.put(None)
        if self._thread:
            self._thread.join(timeout)

    def enfileirar(self, gid: int) -> None:
        with self._lock:
            self._pendentes.append(gid)
            self._cancel[gid] = threading.Event()
        self._q.put(gid)

    def posicao(self, gid: int) -> int:
        with self._lock:
            return self._pendentes.index(gid) + 1 if gid in self._pendentes else 0

    def cancelar(self, gid: int) -> None:
        g = self.dao.geracao(gid)
        if not g:
            raise nao_encontrado("Job")
        if g["status"] in ("concluido", "erro", "cancelado"):
            raise AppError("job_nao_cancelavel", "Esta geração já terminou.", None, 409)
        with self._lock:
            ev = self._cancel.get(gid)
            if gid in self._pendentes:
                self._pendentes.remove(gid)
                self.dao.atualizar_geracao(gid, status="cancelado", erro="Geração cancelada pelo usuário.",
                                           erro_codigo="cancelado")
        if ev:
            ev.set()

    def _loop(self) -> None:
        while True:
            gid = self._q.get()
            if gid is None:
                return
            with self._lock:
                if gid not in self._pendentes:
                    self._cancel.pop(gid, None)
                    continue
                self._pendentes.remove(gid)
                ev = self._cancel.setdefault(gid, threading.Event())
                self.atual = gid
            try:
                self._executar(gid, ev)
            except Exception:  # pragma: no cover
                log.exception("Worker falhou no job %s", gid)
            finally:
                with self._lock:
                    self.atual = None
                    self._cancel.pop(gid, None)
