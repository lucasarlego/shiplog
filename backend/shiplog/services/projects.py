"""Regras de projetos: cadastro, edição, exclusão e commits novos (spec 002)."""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from ..errors import AppError, nao_encontrado
from ..storage.dao import Dao
from ..storage.db import now_iso
from . import repo as git
from . import workspace
from .urls import UrlInfo, validar_url
from .versions import VersionService

log = logging.getLogger("shiplog.projects")

FILTROS = ("rascunho", "pronto", "publicado", "sem_post", "commits_novos")
MIN_DESCRICAO = 20
MAX_DESCRICAO = 8000


def titulo_de(descricao: str, max_palavras: int = 7) -> str:
    primeira = descricao.strip().splitlines()[0]
    palavras = primeira.split()
    titulo = " ".join(palavras[:max_palavras]).rstrip(".,;:!?")
    return (titulo + ("…" if len(palavras) > max_palavras else ""))[:80] or "Post sem repositório"


def slug(nome: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", nome).strip("-").lower()
    return s[:40] or "repo"


class ProjectService:
    def __init__(self, dao: Dao, repos_dir: Path, versions: VersionService, permitir_file: bool = False) -> None:
        self.dao = dao
        self.repos_dir = repos_dir
        self.versions = versions
        self.permitir_file = permitir_file

    # -- validação ----------------------------------------------------------
    def validar(self, url: str) -> UrlInfo:
        info = validar_url(url, permitir_file=self.permitir_file)
        existente = self.dao.projeto_por_url(info.normalizada)
        if existente:
            raise AppError(
                "projeto_duplicado",
                "Este repositório já está cadastrado.",
                "Abra o projeto existente para gerar uma nova versão.",
                409,
                {"projeto_id": existente["id"], "arquivado": bool(existente["arquivado"])},
            )
        return info

    # -- CRUD ---------------------------------------------------------------
    def cadastrar(self, url: str, nome: str | None = None, branch: str | None = None, notas: str = "") -> dict[str, Any]:
        info = self.validar(url)
        branch = (branch or "").strip() or None
        remoto = git.ls_remote(info.url, branch)
        pid = self.dao.criar_projeto(
            nome=(nome or "").strip() or info.nome,
            url_repo=info.url,
            url_normalizada=info.normalizada,
            branch=branch,
            caminho_local="",
            notas=notas or "",
            commit_remoto=remoto,
            verificado_em=now_iso(),
        )
        caminho = self.repos_dir / f"{pid}-{slug(info.nome)}"
        self.dao.atualizar_projeto(pid, caminho_local=str(caminho))
        log.info("Projeto %s cadastrado (%s)", pid, info.normalizada)
        return self.detalhe(pid)

    def cadastrar_livre(self, descricao: str, nome: str | None = None, notas: str = "") -> dict[str, Any]:
        """Projeto sem repositório: o post nasce de uma descrição (spec 006)."""
        descricao = (descricao or "").strip()
        if len(descricao) < MIN_DESCRICAO:
            raise AppError("validacao", f"Descreva com pelo menos {MIN_DESCRICAO} caracteres o que você quer contar.",
                           "Conte o que fez, por que importa e o que aprendeu.", 422)
        if len(descricao) > MAX_DESCRICAO:
            raise AppError("validacao", f"A descrição passou de {MAX_DESCRICAO} caracteres.", "Resuma o essencial.", 422)
        pid = self.dao.criar_projeto(origem="livre", nome=(nome or "").strip() or titulo_de(descricao),
                                     descricao=descricao, notas=notas or "")
        log.info("Post livre %s cadastrado", pid)
        return self.detalhe(pid)

    def projeto_atual(self, caminho: str, vincular: bool = False) -> dict[str, Any]:
        """Projeto da pasta aberta no harness (spec 009 FR-04): pelo `origin`, ou `local` pelo caminho."""
        pasta = workspace.resolver(caminho)
        info: UrlInfo | None = None
        if pasta.origin:
            try:
                info = validar_url(pasta.origin, permitir_file=self.permitir_file)
            except AppError:
                info = None  # remoto que o Shiplog não clona (ex.: caminho local): trata como projeto local
        local = self.dao.projeto_local(pasta.caminho)
        criado = vinculado = False
        if info:
            p = self.dao.projeto_por_url(info.normalizada)
            if p is None and local is not None and vincular:
                caminho_clone = self.repos_dir / f"{local['id']}-{slug(info.nome)}"
                self.dao.atualizar_projeto(local["id"], origem="repo", url_repo=info.url, url_normalizada=info.normalizada,
                                           caminho_local=str(caminho_clone))
                p, vinculado = self.dao.projeto(local["id"]), True
            elif p is None and local is None:
                pid = self.dao.criar_projeto(nome=info.nome, url_repo=info.url, url_normalizada=info.normalizada,
                                             caminho_local="", notas="")
                self.dao.atualizar_projeto(pid, caminho_local=str(self.repos_dir / f"{pid}-{slug(info.nome)}"))
                p, criado = self.dao.projeto(pid), True
            elif p is None:
                p = local  # já existe como local; o usuário decide se vincula
        else:
            p = local
            if p is None:
                pid = self.dao.criar_projeto(origem="local", nome=pasta.nome, caminho_local=pasta.caminho, notas="")
                p, criado = self.dao.projeto(pid), True
        assert p is not None
        if p["arquivado"]:
            self.dao.atualizar_projeto(p["id"], arquivado=False)
        d = self.detalhe(p["id"])
        d.update(
            criado=criado,
            vinculado=vinculado,
            pode_vincular=bool(info and p["origem"] == "local"),
            pasta={"caminho": pasta.caminho, "git": pasta.git, "origin": pasta.origin, "branch": pasta.branch,
                   "head": pasta.head},
        )
        return d

    def obter(self, pid: int) -> dict[str, Any]:
        p = self.dao.projeto(pid)
        if not p:
            raise nao_encontrado("Projeto")
        return p

    def resumo(self, p: dict[str, Any]) -> dict[str, Any]:
        ult_post = self.dao.ultima_versao("posts", p["id"])
        ult_art = self.dao.ultima_versao("artigos", p["id"])
        pub_art = self.dao.publicada("artigos", p["id"])
        ultimo_commit = self.dao.ultimo_commit_gerado(p["id"])
        livre = p["origem"] == "livre"
        return {
            "id": p["id"],
            "origem": p["origem"],
            "descricao": p["descricao"],
            "nome": p["nome"],
            "url_repo": p["url_repo"],
            "branch": p["branch"],
            "notas": p["notas"],
            "arquivado": p["arquivado"],
            "criado_em": p["criado_em"],
            "ultima_analise_em": p["ultima_analise_em"],
            "commit_analisado": ultimo_commit,
            "commit_remoto": p["commit_remoto"],
            "verificado_em": p["verificado_em"],
            "commits_novos": (not livre) and bool(p["commit_remoto"] and ultimo_commit and p["commit_remoto"] != ultimo_commit),
            "ultimo_post": _mini(ult_post),
            "ultimo_artigo": _mini(ult_art),
            "artigo_publicado": (
                {"id": pub_art["id"], "titulo": pub_art["titulo"], "link": pub_art["link_medium"]} if pub_art else None
            ),
            "job_ativo": self.dao.geracao_ativa_do_projeto(p["id"]),
        }

    def detalhe(self, pid: int) -> dict[str, Any]:
        p = self.obter(pid)
        d = self.resumo(p)
        caminho = Path(p["caminho_local"]) if p["caminho_local"] else None
        d.update(
            caminho_local=str(caminho) if caminho else None,
            clone_existe=bool(caminho and git.is_clone(caminho)),
            rodada_atual=self.dao.rodada_atual("posts", pid),
        )
        return d

    def listar(self, status: str | None = None) -> list[dict[str, Any]]:
        if status and status not in FILTROS:
            raise AppError("validacao", "Filtro inválido.", f"Use um de: {', '.join(FILTROS)}.", 422)
        itens = [self.resumo(p) for p in self.dao.listar_projetos()]
        if status == "sem_post":
            return [i for i in itens if not i["ultimo_post"]]
        if status == "commits_novos":
            return [i for i in itens if i["commits_novos"]]
        if status:
            return [i for i in itens if i["ultimo_post"] and i["ultimo_post"]["status"] == status]
        return itens

    def editar(self, pid: int, nome: str | None = None, branch: str | None = None, notas: str | None = None,
               descricao: str | None = None) -> dict[str, Any]:
        p = self.obter(pid)
        livre = p["origem"] == "livre"
        campos: dict[str, Any] = {}
        if descricao is not None:
            if not livre:
                raise AppError("validacao", "Só posts sem repositório têm descrição.", "Use as notas do projeto.", 422)
            if len(descricao.strip()) < MIN_DESCRICAO:
                raise AppError("validacao", f"A descrição precisa de pelo menos {MIN_DESCRICAO} caracteres.", None, 422)
            campos["descricao"] = descricao.strip()[:MAX_DESCRICAO]
        if branch is not None and p["origem"] == "local":
            raise AppError("validacao", "Projetos locais usam a branch atual da pasta.", None, 422)
        if branch is not None and livre:
            raise AppError("validacao", "Posts sem repositório não têm branch.", None, 422)
        if nome is not None:
            if not nome.strip():
                raise AppError("validacao", "O nome não pode ficar vazio.", None, 422)
            campos["nome"] = nome.strip()
        if notas is not None:
            campos["notas"] = notas
        if branch is not None:
            nova = branch.strip() or None
            if nova != p["branch"]:
                if nova:
                    git.ls_remote(p["url_repo"], nova)
                campos["branch"] = nova
                # FR-10: troca de branch invalida o clone.
                git.remover(Path(p["caminho_local"]), self.repos_dir)
        self.dao.atualizar_projeto(pid, **campos)
        return self.detalhe(pid)

    def excluir(self, pid: int, manter_historico: bool = False) -> None:
        p = self.obter(pid)
        if self.dao.geracao_ativa_do_projeto(pid):
            raise AppError("validacao", "Há uma geração em andamento neste projeto.", "Cancele-a antes de excluir.", 409)
        # Projeto `local` aponta para a pasta de trabalho do usuário: nunca é apagada (spec 009 FR-05).
        if p["caminho_local"] and p["origem"] != "local":
            git.remover(Path(p["caminho_local"]), self.repos_dir)
        if manter_historico:
            # Libera a URL para recadastro mantendo o histórico (Q-07).
            nova = f"arquivado:{pid}:{p['url_normalizada']}" if p["url_normalizada"] else None
            self.dao.atualizar_projeto(pid, arquivado=True, url_normalizada=nova)
        else:
            self.dao.excluir_projeto(pid)

    # -- commits novos (RF-10) -------------------------------------------------
    def check_updates(self, ids: list[int] | None = None) -> list[dict[str, Any]]:
        projetos = [p for p in self.dao.listar_projetos()
                    if p["origem"] == "repo" and (not ids or p["id"] in ids)]

        def verificar(p: dict[str, Any]) -> dict[str, Any]:
            try:
                remoto = git.ls_remote(p["url_repo"], p["branch"], timeout=15)
                self.dao.atualizar_projeto(p["id"], commit_remoto=remoto, verificado_em=now_iso())
            except AppError as e:
                log.info("check-updates falhou para %s: %s", p["id"], e.codigo)
                remoto = p["commit_remoto"]
            ultimo = self.dao.ultimo_commit_gerado(p["id"])
            return {"id": p["id"], "commit_remoto": remoto,
                    "commits_novos": bool(remoto and ultimo and remoto != ultimo)}

        with ThreadPoolExecutor(max_workers=4) as ex:
            return list(ex.map(verificar, projetos))

    def marcar_analise(self, pid: int, branch_detectada: str | None, commit: str, atualizado: bool) -> None:
        p = self.obter(pid)
        campos: dict[str, Any] = {"ultima_analise_em": now_iso()}
        if atualizado or not p["commit_remoto"]:
            campos.update(commit_remoto=commit, verificado_em=now_iso())
        if not p["branch"] and branch_detectada:
            campos["branch"] = branch_detectada
        self.dao.atualizar_projeto(pid, **campos)


def _mini(v: dict[str, Any] | None) -> dict[str, Any] | None:
    if not v:
        return None
    return {"id": v["id"], "versao": v["versao"], "status": v["status"], "criado_em": v["criado_em"]}
