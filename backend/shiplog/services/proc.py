"""Subprocesso com timeout, cancelamento e kill da árvore (spec 002 NFR-02)."""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProcResult:
    returncode: int | None
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False
    cancelled: bool = False
    not_found: bool = False


def _kill_tree(p: subprocess.Popen) -> None:
    if p.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True, check=False)
        else:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            p.kill()
        except OSError:
            pass


def run(
    cmd: list[str],
    *,
    cwd: Path | str | None = None,
    timeout: float = 60,
    cancel: threading.Event | None = None,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> ProcResult:
    start = time.monotonic()
    kwargs: dict = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    else:
        kwargs["start_new_session"] = True
    try:
        p = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            **kwargs,
        )
    except (FileNotFoundError, PermissionError, NotADirectoryError) as e:
        return ProcResult(None, "", str(e), 0, not_found=True)

    out: list[str] = []
    err: list[str] = []

    def comm() -> None:
        o, e = p.communicate(input_text)
        out.append(o or "")
        err.append(e or "")

    t = threading.Thread(target=comm, daemon=True)
    t.start()
    deadline = start + timeout
    timed_out = cancelled = False
    while t.is_alive():
        t.join(0.1)
        if not t.is_alive():
            break
        if cancel is not None and cancel.is_set():
            cancelled = True
            _kill_tree(p)
            break
        if time.monotonic() > deadline:
            timed_out = True
            _kill_tree(p)
            break
    t.join(5)
    return ProcResult(
        returncode=p.returncode,
        stdout="".join(out),
        stderr="".join(err),
        duration_ms=int((time.monotonic() - start) * 1000),
        timed_out=timed_out,
        cancelled=cancelled,
    )
