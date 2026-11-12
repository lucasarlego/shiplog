"""Interface de provedor de LLM (RNF-07). Trocar o provedor = nova implementação desta interface."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class LLMRequest:
    prompt: str
    cwd: Path
    tools: list[str]
    json_schema: dict[str, Any]
    timeout_s: int
    allow_skills: bool = False
    model: str | None = None


@dataclass
class LLMResult:
    ok: bool
    data: dict[str, Any] | None
    raw: str
    exit_code: int | None
    duration_ms: int
    error_code: str | None = None
    error_message: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    def run(self, req: LLMRequest, cancel: threading.Event | None = None) -> LLMResult: ...
