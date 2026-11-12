"""Verificação do Claude Code, login, skill e git (spec 003 FR-14; RI-07, RI-09)."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable

from ..storage.db import now_iso
from . import proc
from .llm.claude_cli import INSTALAR, LOGIN, resolver_cli, subprocess_env

SKILL = "medium-article-writer"
TTL_S = 60


def claude_config_dir() -> Path:
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(env).expanduser() if env else Path.home() / ".claude"


def skill_instalada(base: Path | None = None) -> bool:
    base = base or claude_config_dir()
    if (base / "skills" / SKILL / "SKILL.md").is_file():
        return True
    plugins = base / "plugins"
    if plugins.is_dir():
        for _ in plugins.rglob(f"skills/{SKILL}/SKILL.md"):
            return True
    return False


class HealthService:
    def __init__(self, cli_path: Callable[[], str | None], skill_check: Callable[[], bool] = skill_instalada) -> None:
        self._cli_path = cli_path
        self._skill_check = skill_check
        self._cache: dict[str, Any] | None = None
        self._ts = 0.0
        self._lock = threading.Lock()

    def invalidate(self) -> None:
        with self._lock:
            self._cache = None

    def get(self, force: bool = False) -> dict[str, Any]:
        with self._lock:
            if not force and self._cache and time.monotonic() - self._ts < TTL_S:
                return self._cache
        h = self._check()
        with self._lock:
            self._cache, self._ts = h, time.monotonic()
        return h

    def cached(self) -> dict[str, Any] | None:
        return self._cache

    def _check(self) -> dict[str, Any]:
        env = subprocess_env()
        cli: dict[str, Any] = {"ok": False, "caminho": None, "versao": None, "mensagem": None, "comando_sugerido": None}
        auth: dict[str, Any] = {"ok": False, "mensagem": None, "comando_sugerido": None}
        caminho = resolver_cli(self._cli_path())
        if not caminho:
            cli.update(mensagem="Claude Code CLI não encontrado.", comando_sugerido=INSTALAR)
            auth.update(mensagem="Instale o Claude Code primeiro.")
        else:
            cli["caminho"] = caminho
            r = proc.run([caminho, "--version"], timeout=15, env=env)
            if r.returncode == 0:
                cli.update(ok=True, versao=r.stdout.strip().split(" ")[0])
            else:
                cli.update(mensagem=f"Falha ao executar o CLI: {(r.stderr or r.stdout).strip()[:300]}",
                           comando_sugerido=INSTALAR)
            if cli["ok"]:
                r = proc.run([caminho, "auth", "status", "--json"], timeout=20, env=env)
                try:
                    data = json.loads(r.stdout)
                    logged = bool(data.get("loggedIn"))
                except ValueError:
                    logged = r.returncode == 0 and "logged in" in r.stdout.lower() and "not" not in r.stdout.lower()
                    data = {}
                if logged:
                    metodo = data.get("authMethod")
                    auth.update(ok=True, metodo=metodo, plano=data.get("subscriptionType"))
                    if metodo and metodo not in ("claude.ai", "oauth", "oauth_token"):
                        auth["mensagem"] = (
                            f"Autenticado via '{metodo}'. Para custo zero, use o login da assinatura (claude.ai)."
                        )
                else:
                    auth.update(mensagem="Claude Code não está autenticado.", comando_sugerido=LOGIN)

        skill_ok = self._skill_check()
        skill = {
            "ok": skill_ok,
            "mensagem": None if skill_ok else f"Skill '{SKILL}' não encontrada; a geração de artigos fica desabilitada.",
            "comando_sugerido": None if skill_ok else "Na pasta do Shiplog, rode: make install-skill",
        }
        rg = proc.run(["git", "--version"], timeout=10)
        git = {"ok": rg.returncode == 0, "versao": rg.stdout.strip().replace("git version ", "") or None,
               "mensagem": None if rg.returncode == 0 else "git não encontrado no PATH."}
        pode_post = cli["ok"] and auth["ok"] and git["ok"]
        return {
            "cli": cli, "auth": auth, "skill": skill, "git": git,
            "pode_gerar_post": pode_post,
            "pode_gerar_artigo": pode_post and skill_ok,
            "verificado_em": now_iso(),
        }
