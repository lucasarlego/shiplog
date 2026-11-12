"""Conexão SQLite e migrador (spec 001)."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=15, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def migrate(conn: sqlite3.Connection) -> list[int]:
    """Aplica migrações pendentes, cada uma numa transação. Idempotente (AC-01)."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (versao INTEGER PRIMARY KEY, aplicada_em TEXT NOT NULL)"
    )
    aplicadas = {r[0] for r in conn.execute("SELECT versao FROM schema_migrations")}
    novas: list[int] = []
    # Recriar tabelas (ex.: 0002) exige FKs desligadas, senão o DROP dispara ON DELETE CASCADE.
    # O PRAGMA só tem efeito fora de transação.
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        _aplicar(conn, aplicadas, novas)
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
    return novas


def _aplicar(conn: sqlite3.Connection, aplicadas: set[int], novas: list[int]) -> None:
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        versao = int(f.name.split("_", 1)[0])
        if versao in aplicadas:
            continue
        sql = f.read_text(encoding="utf-8")
        try:
            conn.execute("BEGIN")
            for stmt in _split(sql):
                conn.execute(stmt)
            violacoes = conn.execute("PRAGMA foreign_key_check").fetchall()
            if violacoes:
                raise sqlite3.IntegrityError(f"migração {f.name} violou chaves estrangeiras: {violacoes[:5]}")
            conn.execute("INSERT INTO schema_migrations VALUES (?, ?)", (versao, now_iso()))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        novas.append(versao)


def _split(sql: str) -> list[str]:
    lines = [ln.split("--", 1)[0] for ln in sql.splitlines()]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


class Database:
    """Uma conexão por thread (NFR-01)."""

    def __init__(self, path: Path | str) -> None:
        self.path = path
        self._local = threading.local()
        self._write_lock = threading.RLock()

    @property
    def conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            c = connect(self.path)
            self._local.conn = c
        return c

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        """Transação de escrita serializada (BEGIN IMMEDIATE)."""
        with self._write_lock:
            c = self.conn
            c.execute("BEGIN IMMEDIATE")
            try:
                yield c
            except BaseException:
                c.execute("ROLLBACK")
                raise
            else:
                c.execute("COMMIT")

    def migrate(self) -> list[int]:
        with self._write_lock:
            return migrate(self.conn)
