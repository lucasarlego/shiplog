"""Operações git sobre o clone local (spec 002)."""

from __future__ import annotations

import logging
import os
import re
import shutil
import stat
import sys
import threading
from pathlib import Path

from ..errors import AppError
from . import proc

log = logging.getLogger("shiplog.repo")

TIMEOUT_LS_REMOTE = 30
TIMEOUT_CLONE = 300
HIST_DEPTH = 15

_AUTH = re.compile(
    r"authentication failed|permission denied|could not read username|terminal prompts disabled|"
    r"host key verification failed|returned error: 403|invalid username or password",
    re.I,
)
_NOT_FOUND = re.compile(
    r"not found|does not appear to be a git repository|could not resolve host|repository .* does not exist|"
    r"returned error: 404|unable to access|no such file or directory|failed to connect",
    re.I,
)


class GitError(AppError):
    pass


def git_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        GIT_TERMINAL_PROMPT="0",
        GCM_INTERACTIVE="never",
        LC_ALL="C",
        LANG="C",
        GIT_ASKPASS=env.get("GIT_ASKPASS", ""),
    )
    if "GIT_SSH_COMMAND" not in env:
        env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o ConnectTimeout=15"
    return env


def classificar_erro(stderr: str, contexto: str = "acessar") -> GitError:
    s = stderr.strip()
    if _AUTH.search(s):
        return GitError(
            "repo_auth",
            "Sem acesso ao repositório: o git local precisa de acesso a ele (ou o repositório não existe).",
            "Confira a URL. Se for privado, configure sua chave SSH ou credential helper e teste com `git ls-remote <url>` no terminal.",
            422,
            {"stderr": s[-800:]},
        )
    if _NOT_FOUND.search(s):
        return GitError(
            "repo_inacessivel",
            "Repositório não encontrado ou inacessível.",
            "Confira a URL e sua conexão de rede.",
            422,
            {"stderr": s[-800:]},
        )
    return GitError("git_falha", f"Falha do git ao {contexto} o repositório.", "Veja os detalhes e tente novamente.",
                    422, {"stderr": s[-800:]})


def _git(args: list[str], cwd: Path | None = None, timeout: float = 60,
         cancel: threading.Event | None = None) -> proc.ProcResult:
    return proc.run(["git", *args], cwd=cwd, timeout=timeout, cancel=cancel, env=git_env())


class Cancelado(Exception):
    pass


def _check(r: proc.ProcResult, contexto: str) -> proc.ProcResult:
    if r.cancelled:
        raise Cancelado()
    if r.not_found:
        raise GitError("git_falha", "git não encontrado no PATH.", "Instale o git.", 500)
    if r.timed_out:
        raise GitError("git_falha", f"Tempo esgotado ao {contexto} o repositório.", "Tente novamente.", 422)
    if r.returncode != 0:
        raise classificar_erro(r.stderr, contexto)
    return r


def ls_remote(url: str, branch: str | None = None, timeout: float = TIMEOUT_LS_REMOTE) -> str | None:
    """Retorna o hash do HEAD (ou da branch). Lança GitError se inacessível."""
    ref = f"refs/heads/{branch}" if branch else "HEAD"
    r = _check(_git(["ls-remote", url, ref], timeout=timeout), "acessar")
    line = r.stdout.strip().splitlines()
    if not line:
        if branch:
            raise GitError("branch_inexistente", f"A branch '{branch}' não existe no remoto.",
                           "Confira o nome da branch ou deixe em branco para usar a padrão.", 422)
        return None
    return line[0].split()[0]


def is_clone(path: Path) -> bool:
    return (path / ".git").exists()


def garantir_clone(url: str, path: Path, branch: str | None, atualizar: bool,
                   cancel: threading.Event | None = None) -> str:
    """Clona (1ª vez, --depth 1) ou atualiza (fetch + reset). Retorna o HEAD (RF-07, RF-09)."""
    if not is_clone(path):
        if path.exists():
            remover(path, path.parent)
        path.parent.mkdir(parents=True, exist_ok=True)
        args = ["clone", "--depth", "1", "--no-tags"]
        if branch:
            args += ["--branch", branch]
        args += [url, str(path)]
        try:
            _check(_git(args, timeout=TIMEOUT_CLONE, cancel=cancel), "clonar")
        except BaseException:
            if path.exists():
                remover(path, path.parent)
            raise
        # Q-05: aprofunda o histórico para coletar commits recentes (best-effort).
        _git(["fetch", "--depth", str(HIST_DEPTH), "--no-tags", "origin"], cwd=path, timeout=120, cancel=cancel)
    elif atualizar:
        ref = branch or "HEAD"
        _check(_git(["fetch", "--depth", str(HIST_DEPTH), "--no-tags", "origin", ref], cwd=path,
                    timeout=TIMEOUT_CLONE, cancel=cancel), "atualizar")
        _check(_git(["reset", "--hard", "FETCH_HEAD"], cwd=path, cancel=cancel), "atualizar")
        _git(["clean", "-fdx"], cwd=path, cancel=cancel)
    return head(path)


def head(path: Path) -> str:
    return _check(_git(["rev-parse", "HEAD"], cwd=path), "ler").stdout.strip()


def branch_atual(path: Path) -> str | None:
    r = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=path)
    b = r.stdout.strip()
    return b if r.returncode == 0 and b and b != "HEAD" else None


def alteracoes(path: Path) -> list[str]:
    """Arquivos alterados/criados no clone (R-05)."""
    r = _git(["status", "--porcelain", "--untracked-files=all"], cwd=path)
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def restaurar(path: Path) -> None:
    _git(["reset", "--hard", "HEAD"], cwd=path)
    _git(["clean", "-fdx"], cwd=path)


def commits(path: Path, n: int = HIST_DEPTH) -> list[dict[str, str]]:
    r = _git(["log", f"-n{n}", "--date=short", "--pretty=format:%h%x1f%ad%x1f%s"], cwd=path)
    out = []
    for ln in r.stdout.splitlines():
        parts = ln.split("\x1f")
        if len(parts) == 3:
            out.append({"hash": parts[0], "data": parts[1], "mensagem": parts[2]})
    return out


def _onerror(func, p, _exc):  # pragma: no cover - Windows read-only files
    os.chmod(p, stat.S_IWRITE)
    func(p)


def remover(path: Path, raiz_permitida: Path) -> None:
    """Remove o clone só se estiver dentro de `raiz_permitida` (NFR-04)."""
    path = path.resolve()
    raiz = raiz_permitida.resolve()
    if path == raiz or raiz not in path.parents:
        raise AppError("erro_interno", "Caminho de clone fora da pasta de dados; remoção recusada.", None, 500)
    if path.exists():
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=_onerror)
        else:  # pragma: no cover
            shutil.rmtree(path, onerror=_onerror)
