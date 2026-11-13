"""Leitura do estado de uma pasta de projeto do usuário (spec 009 FR-04, FR-07).

Só comandos git de leitura; nunca escreve, restaura ou altera a pasta (NFR-03).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..errors import AppError
from . import metadata, proc
from .repo import git_env

MAX_COMMITS = 50
MAX_ARQUIVOS = 200
MAX_TEXTO = 30_000
PADRAO_COMMITS = 15
_CREDENCIAL = re.compile(r"^(https?://)[^/@\s]+@")


@dataclass
class Pasta:
    caminho: str              # raiz do projeto (raiz git, ou a própria pasta quando não é git)
    git: bool
    origin: str | None        # URL do remoto, sem credenciais
    branch: str | None
    head: str | None
    nome: str


@dataclass
class Material:
    tipo: str = "projeto"
    caminho: str = ""
    branch: str | None = None
    head: str | None = None
    desde_commit: str | None = None
    desde_encontrado: bool = True
    commits: list[dict[str, str]] = field(default_factory=list)
    diffstat: str = ""
    nao_commitados: list[str] = field(default_factory=list)
    metadados: dict[str, Any] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)
    truncado: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _git(args: list[str], cwd: Path, timeout: float = 20) -> proc.ProcResult:
    return proc.run(["git", *args], cwd=cwd, timeout=timeout, env=git_env())


def sem_credenciais(url: str) -> str:
    """`https://usuario:token@host/...` → `https://host/...` (nunca guardamos segredos)."""
    return _CREDENCIAL.sub(r"\1", url.strip())


def resolver(caminho: str) -> Pasta:
    p = Path(caminho or "").expanduser()
    if not caminho or not p.is_absolute():
        raise AppError("validacao", "Informe o caminho absoluto da pasta do projeto.",
                       "Passe o diretório de trabalho atual (ex.: /home/voce/projetos/app).", 422)
    if not p.is_dir():
        raise AppError("validacao", f"A pasta '{caminho}' não existe.", None, 422)
    p = p.resolve()
    r = _git(["rev-parse", "--show-toplevel"], p)
    if r.returncode != 0:
        return Pasta(str(p), False, None, None, None, p.name)
    raiz = Path(r.stdout.strip()).resolve()
    o = _git(["remote", "get-url", "origin"], raiz)
    origin = sem_credenciais(o.stdout) if o.returncode == 0 and o.stdout.strip() else None
    b = _git(["rev-parse", "--abbrev-ref", "HEAD"], raiz)
    branch = b.stdout.strip() if b.returncode == 0 and b.stdout.strip() != "HEAD" else None
    h = _git(["rev-parse", "HEAD"], raiz)
    head = h.stdout.strip() if h.returncode == 0 else None  # repositório sem commits
    return Pasta(str(raiz), True, origin, branch, head, raiz.name)


def material(pasta: Pasta, desde: str | None, limites: metadata.Limites | None = None) -> Material:
    raiz = Path(pasta.caminho)
    m = Material(caminho=pasta.caminho, branch=pasta.branch, head=pasta.head, desde_commit=desde)
    md = metadata.coletar(raiz, limites or metadata.Limites())
    m.metadados = {k: v for k, v in md.to_dict().items() if k != "commits"}
    if not pasta.git:
        m.avisos.append("A pasta não é um repositório git: só há metadados (README, estrutura, dependências).")
        return m
    if not pasta.head:
        m.avisos.append("O repositório ainda não tem commits.")
    else:
        intervalo: list[str]
        if desde and _git(["cat-file", "-e", f"{desde}^{{commit}}"], raiz).returncode == 0:
            intervalo = [f"{desde}..HEAD"]
        else:
            if desde:
                m.desde_encontrado = False
                m.avisos.append(f"O commit do último post ({desde[:7]}) não existe mais neste repositório "
                                f"(rebase?); usando os últimos {PADRAO_COMMITS} commits.")
            intervalo = ["-n", str(PADRAO_COMMITS), "HEAD"]
        log = _git(["log", f"--max-count={MAX_COMMITS + 1}", "--date=short",
                    "--pretty=format:%h%x1f%ad%x1f%an%x1f%s", *intervalo], raiz)
        linhas = [ln for ln in log.stdout.splitlines() if ln.strip()]
        if len(linhas) > MAX_COMMITS:
            m.truncado = True
            linhas = linhas[:MAX_COMMITS]
        for ln in linhas:
            h, d, a, s = (ln.split("\x1f") + ["", "", "", ""])[:4]
            m.commits.append({"hash": h, "data": d, "autor": a, "mensagem": s})
        if desde and m.desde_encontrado:
            m.diffstat = _git(["diff", "--stat", f"{desde}..HEAD"], raiz).stdout.strip()
        elif m.commits:
            base = _git(["rev-parse", f"HEAD~{len(m.commits)}"], raiz)
            if base.returncode == 0:
                m.diffstat = _git(["diff", "--stat", f"{base.stdout.strip()}..HEAD"], raiz).stdout.strip()
    st = _git(["status", "--porcelain", "--untracked-files=normal"], raiz)
    arquivos = [ln[3:] for ln in st.stdout.splitlines() if len(ln) > 3]
    if len(arquivos) > MAX_ARQUIVOS:
        m.truncado = True
        arquivos = arquivos[:MAX_ARQUIVOS]
    m.nao_commitados = arquivos
    if len(m.diffstat) > MAX_TEXTO // 3:
        m.diffstat = m.diffstat[: MAX_TEXTO // 3] + "\n… (cortado)"
        m.truncado = True
    if not m.commits and not m.nao_commitados and pasta.head:
        m.avisos.append("Nada mudou desde o último post: sem commits novos nem alterações pendentes.")
    return m
