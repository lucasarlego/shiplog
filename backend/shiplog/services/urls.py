"""Validação e normalização de URLs Git (spec 002 FR-01, FR-02, FR-04)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from ..errors import AppError

_SCP = re.compile(r"^(?P<user>[A-Za-z0-9_.\-]+)@(?P<host>[A-Za-z0-9_.\-]+):(?P<path>[^\s:]+)$")
_PATH_OK = re.compile(r"^[A-Za-z0-9_.\-~/]+$")


@dataclass(frozen=True)
class UrlInfo:
    url: str
    normalizada: str
    nome: str
    tipo: str  # https | ssh | file


def _clean_path(path: str) -> str:
    path = path.strip().strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return path.rstrip("/")


def _invalida(msg: str) -> AppError:
    return AppError(
        "url_invalida",
        msg,
        "Use uma URL HTTPS (https://github.com/usuario/repo) ou SSH (git@github.com:usuario/repo.git).",
        422,
    )


def validar_url(url: str, permitir_file: bool = False) -> UrlInfo:
    url = (url or "").strip()
    if not url:
        raise _invalida("Informe a URL do repositório.")
    if any(c.isspace() for c in url):
        raise _invalida("A URL não pode conter espaços.")

    m = _SCP.match(url)
    if m and "://" not in url:
        host, path, tipo = m["host"], _clean_path(m["path"]), "ssh"
    else:
        p = urlparse(url)
        if p.scheme == "file" and permitir_file:
            path = _clean_path(p.path)
            return UrlInfo(url, f"file/{path.lower()}", path.rsplit("/", 1)[-1] or "repo", "file")
        if p.scheme not in ("https", "http", "ssh", "git+ssh"):
            raise _invalida("Formato de URL não suportado.")
        if not p.hostname or "." not in p.hostname and p.hostname != "localhost":
            raise _invalida("A URL precisa ter um host válido.")
        if p.scheme in ("https", "http") and (p.password or p.username):
            raise _invalida("Não inclua usuário ou senha na URL; o git local cuida da autenticação.")
        host, path = p.hostname, _clean_path(p.path)
        tipo = "https" if p.scheme in ("https", "http") else "ssh"

    if not path or "/" not in path or not _PATH_OK.match(path) or ".." in path.split("/"):
        raise _invalida("A URL deve apontar para um repositório (ex.: dono/repositorio).")
    nome = path.rsplit("/", 1)[-1]
    return UrlInfo(url=url, normalizada=f"{host.lower()}/{path.lower()}", nome=nome, tipo=tipo)
