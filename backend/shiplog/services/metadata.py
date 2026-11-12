"""Coleta de metadados do repositório antes da chamada ao Claude (spec 002 FR-06, FR-07)."""

from __future__ import annotations

import fnmatch
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import repo as git

IGNORAR_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "dist", "build", "out", "target", "__pycache__",
    ".next", ".nuxt", ".svelte-kit", ".turbo", ".cache", "coverage", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".tox", ".idea", ".vscode", "vendor", "bower_components", ".gradle", ".terraform",
    "Pods", ".dart_tool", ".parcel-cache", "site-packages", ".eggs", "htmlcov", "tmp", ".DS_Store",
}
DEP_PATTERNS = [
    "package.json", "pyproject.toml", "requirements*.txt", "Pipfile", "setup.py", "setup.cfg", "go.mod",
    "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts", "Gemfile", "composer.json", "mix.exs",
    "pubspec.yaml", "*.csproj", "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yaml",
    "Makefile", "deno.json", "environment.yml",
]
README_NAMES = ("readme.md", "readme.rst", "readme.txt", "readme")
LINGUAGENS = {
    ".py": "Python", ".ipynb": "Jupyter Notebook", ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript", ".go": "Go", ".rs": "Rust", ".java": "Java",
    ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala", ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".fs": "F#",
    ".c": "C", ".h": "C", ".cpp": "C++", ".cc": "C++", ".hpp": "C++", ".swift": "Swift", ".m": "Objective-C",
    ".dart": "Dart", ".ex": "Elixir", ".exs": "Elixir", ".erl": "Erlang", ".clj": "Clojure", ".hs": "Haskell",
    ".lua": "Lua", ".r": "R", ".jl": "Julia", ".sh": "Shell", ".bash": "Shell", ".ps1": "PowerShell",
    ".sql": "SQL", ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".vue": "Vue", ".svelte": "Svelte",
    ".tf": "HCL", ".sol": "Solidity", ".zig": "Zig", ".nim": "Nim", ".ml": "OCaml",
}


@dataclass
class Limites:
    max_arquivos: int = 20_000
    max_arvore: int = 400
    max_profundidade: int = 5
    max_readme: int = 12_000
    max_dep: int = 4_000
    max_commits: int = 15


@dataclass
class Metadados:
    readme: str | None = None
    readme_arquivo: str | None = None
    arvore: list[str] = field(default_factory=list)
    dependencias: dict[str, str] = field(default_factory=dict)
    linguagens: list[tuple[str, float]] = field(default_factory=list)
    commits: list[dict[str, str]] = field(default_factory=list)
    total_arquivos: int = 0
    parcial: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _ler(p: Path, limite: int) -> str:
    try:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            txt = f.read(limite + 1)
    except OSError:
        return ""
    return txt[:limite] + "\n…[truncado]" if len(txt) > limite else txt


def coletar(raiz: Path, limites: Limites | None = None) -> Metadados:
    lim = limites or Limites()
    md = Metadados()
    bytes_por_ling: dict[str, int] = {}

    for nome in sorted(os.listdir(raiz)):
        if nome.lower() in README_NAMES and (raiz / nome).is_file():
            md.readme_arquivo = nome
            md.readme = _ler(raiz / nome, lim.max_readme)
            break

    for dirpath, dirnames, filenames in os.walk(raiz):
        rel_dir = Path(dirpath).relative_to(raiz)
        depth = 0 if str(rel_dir) == "." else len(rel_dir.parts)
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORAR_DIRS and not d.endswith(".egg-info"))
        if depth < lim.max_profundidade:
            for d in dirnames:
                if len(md.arvore) < lim.max_arvore:
                    md.arvore.append((rel_dir / d).as_posix() + "/" if depth else d + "/")
                else:
                    md.parcial = True
        else:
            dirnames[:] = []
        for fn in sorted(filenames):
            md.total_arquivos += 1
            if md.total_arquivos > lim.max_arquivos:
                md.parcial = True
                break
            rel = (rel_dir / fn).as_posix() if depth else fn
            if depth < lim.max_profundidade:
                if len(md.arvore) < lim.max_arvore:
                    md.arvore.append(rel)
                else:
                    md.parcial = True
            full = Path(dirpath) / fn
            ext = full.suffix.lower()
            if ext in LINGUAGENS:
                try:
                    bytes_por_ling[LINGUAGENS[ext]] = bytes_por_ling.get(LINGUAGENS[ext], 0) + full.stat().st_size
                except OSError:
                    pass
            if depth <= 2 and any(fnmatch.fnmatch(fn, pat) for pat in DEP_PATTERNS):
                md.dependencias[rel] = _ler(full, lim.max_dep)
        if md.total_arquivos > lim.max_arquivos:
            break

    total = sum(bytes_por_ling.values()) or 1
    md.linguagens = sorted(
        ((lang, round(100 * b / total, 1)) for lang, b in bytes_por_ling.items()), key=lambda x: -x[1]
    )[:8]
    md.arvore.sort()
    if git.is_clone(raiz):
        md.commits = git.commits(raiz, lim.max_commits)
    return md
