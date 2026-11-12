"""Configuração de ambiente: pasta de dados, porta e logging (spec 000)."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

HOST = "127.0.0.1"  # RNF-01: fixo, sem opção de alterar.
DEFAULT_PORT = 8765


def default_root() -> Path:
    return Path.home() / ".shiplog"


def pointer_file() -> Path:
    return default_root() / "location.json"


def resolve_data_dir() -> Path:
    """SHIPLOG_DATA_DIR > ponteiro ~/.shiplog/location.json > ~/.shiplog (FR-04)."""
    env = os.environ.get("SHIPLOG_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    ptr = pointer_file()
    if ptr.is_file():
        try:
            data = json.loads(ptr.read_text(encoding="utf-8"))
            if data.get("data_dir"):
                return Path(data["data_dir"]).expanduser().resolve()
        except (OSError, ValueError):
            pass
    return default_root()


def write_pointer(data_dir: str) -> None:
    ptr = pointer_file()
    ptr.parent.mkdir(parents=True, exist_ok=True)
    ptr.write_text(json.dumps({"data_dir": data_dir}, ensure_ascii=False), encoding="utf-8")


def resolve_port() -> int:
    try:
        return int(os.environ.get("SHIPLOG_PORT", DEFAULT_PORT))
    except ValueError:
        return DEFAULT_PORT


@dataclass(frozen=True)
class Paths:
    data_dir: Path

    @property
    def db(self) -> Path:
        return self.data_dir / "shiplog.db"

    @property
    def repos(self) -> Path:
        return self.data_dir / "repos"

    @property
    def logs(self) -> Path:
        return self.data_dir / "logs"

    def ensure(self) -> "Paths":
        for p in (self.data_dir, self.repos, self.logs):
            p.mkdir(parents=True, exist_ok=True)
        return self


# --- Logging (RNF-06) -------------------------------------------------------

_SECRET_PATTERNS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]+"), "sk-ant-***"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{8,})"), "gh*_***"),
    (re.compile(r"\b(github_pat_[A-Za-z0-9_]{8,})"), "github_pat_***"),
    (re.compile(r"(https?://)[^/\s:@]+:[^/\s@]+@"), r"\1***:***@"),
    (re.compile(r"(?i)(authorization\s*[:=]\s*)(\S+(\s+\S+)?)"), r"\1***"),
    (re.compile(r"(?i)((?:api[_-]?key|token|password|secret)\s*[=:]\s*)\S+"), r"\1***"),
]


def redact(text: str) -> str:
    for pat, repl in _SECRET_PATTERNS:
        text = pat.sub(repl, text)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        record.msg = redact(msg)
        record.args = None
        return True


def setup_logging(paths: Paths, level: int = logging.INFO) -> None:
    root = logging.getLogger("shiplog")
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh = RotatingFileHandler(paths.logs / "shiplog.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.addFilter(RedactingFilter())
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    sh.addFilter(RedactingFilter())
    root.addHandler(fh)
    root.addHandler(sh)
    root.propagate = False
