from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from shiplog.config import Paths
from shiplog.context import AppContext, build_context

FAKE = Path(__file__).parent / "fake_claude.py"

POST_OK = {
    "post": "Construí um gerador de posts que lê o repositório e escreve por mim. " * 3,
    "hooks_alternativos": ["E se o seu código escrevesse o post?", "Três commits, um post."],
    "hashtags": ["#Python", "FastAPI", "#OpenSource"],
    "resumo_tecnico": "Aplicação FastAPI que analisa repositórios e gera textos.",
    "destaques": ["Fila de jobs com cancelamento"],
}


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}).stdout.strip()


@pytest.fixture
def remote_repo(tmp_path: Path) -> Path:
    """Repositório 'remoto' local com README, pyproject, código e node_modules."""
    r = tmp_path / "remote" / "meu-app"
    r.mkdir(parents=True)
    git("init", "-q", "-b", "main", cwd=r)
    (r / "README.md").write_text("# Meu App\n\nUm app de exemplo.\n")
    (r / "pyproject.toml").write_text('[project]\nname = "meu-app"\ndependencies = ["fastapi"]\n')
    (r / "src").mkdir()
    (r / "src" / "app.py").write_text("\n".join(f"linha_{i} = {i}" for i in range(1, 51)) + "\n")
    (r / "node_modules" / "lib").mkdir(parents=True)
    (r / "node_modules" / "lib" / "index.js").write_text("module.exports = 1\n")
    (r / ".gitignore").write_text("")
    git("add", "-A", cwd=r)
    git("commit", "-qm", "feat: primeira versão", cwd=r)
    (r / "src" / "util.py").write_text("def soma(a, b):\n    return a + b\n")
    git("add", "-A", cwd=r)
    git("commit", "-qm", "feat: util de soma", cwd=r)
    return r


def file_url(p: Path) -> str:
    return p.as_uri()


class FakeCli:
    def __init__(self, tmp: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.tmp = tmp
        self.log = tmp / "fake_log.jsonl"
        self.script = tmp / "fake_script.json"
        wrapper = tmp / "claude"
        wrapper.write_text(f"#!/bin/sh\nexec {sys.executable} {FAKE} \"$@\"\n")
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)
        self.path = str(wrapper)
        monkeypatch.setenv("FAKE_CLAUDE_LOG", str(self.log))
        monkeypatch.setenv("FAKE_CLAUDE_SCRIPT", str(self.script))
        self.set([{"structured": POST_OK}])

    def set(self, acoes: list[dict[str, Any]]) -> None:
        self.script.write_text(json.dumps(acoes))
        idx = Path(str(self.script) + ".idx")
        if idx.exists():
            idx.unlink()
        if self.log.exists():
            self.log.unlink()

    def calls(self) -> list[dict[str, Any]]:
        if not self.log.exists():
            return []
        return [json.loads(l) for l in self.log.read_text().splitlines()]


@pytest.fixture(autouse=True)
def _host_de_teste(monkeypatch: pytest.MonkeyPatch) -> None:
    # O TestClient usa o host "testserver"; em produção só 127.0.0.1/localhost são aceitos.
    monkeypatch.setenv("SHIPLOG_ALLOWED_HOSTS", "testserver")


@pytest.fixture
def fake_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeCli:
    return FakeCli(tmp_path, monkeypatch)


@pytest.fixture
def ctx(tmp_path: Path, fake_cli: FakeCli) -> AppContext:
    c = build_context(Paths(tmp_path / "data"), skill_check=lambda: True, permitir_file=True)
    c.dao.salvar_config(caminho_cli=fake_cli.path)
    return c


def wait_job(ctx: AppContext, gid: int, timeout: float = 30) -> dict[str, Any]:
    fim = time.time() + timeout
    while time.time() < fim:
        g = ctx.dao.geracao(gid)
        if g and g["status"] in ("concluido", "erro", "cancelado"):
            return g
        time.sleep(0.05)
    raise AssertionError(f"job {gid} não terminou: {ctx.dao.geracao(gid)}")
