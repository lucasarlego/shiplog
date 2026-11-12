"""Composição das dependências da aplicação (camadas: api → services → storage)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable

from .config import Paths
from .services import metadata
from .services.generation import GenerationService
from .services.health import HealthService, skill_instalada
from .services.jobs import JobQueue
from .services.llm.base import LLMProvider
from .services.llm.claude_cli import ClaudeCliProvider
from .services.comments import CommentService
from .services.profile import ProfileService
from .services.projects import ProjectService
from .services.prompts import PROMPT_BASE_ANTIGO, PROMPT_BASE_PADRAO
from .services.versions import VersionService
from .storage.dao import Dao
from .storage.db import Database

DEFAULT_CONFIG: dict[str, Any] = {
    "prompt_base": PROMPT_BASE_PADRAO,
    "perfil_voz": "",
    "caminho_cli": "",
    "timeout_post_s": 300,
    "timeout_artigo_s": 900,
    "modelo": "",
    "parametros_padrao_post": {"tom": "tecnico", "tamanho": "medio", "idioma": "pt", "incluir_link_artigo": False},
    "parametros_padrao_artigo": {"idioma": "pt", "publico": "intermediario", "formato": "deep_dive"},
}


@dataclass
class AppContext:
    paths: Paths
    db: Database
    dao: Dao
    versions: VersionService
    projects: ProjectService
    health: HealthService
    generation: GenerationService
    jobs: JobQueue
    profile: ProfileService
    comments: CommentService
    reinicio_necessario: bool = False


def build_context(
    paths: Paths,
    provider: LLMProvider | None = None,
    skill_check: Callable[[], bool] | None = None,
    permitir_file: bool | None = None,
    limites: metadata.Limites | None = None,
) -> AppContext:
    paths.ensure()
    db = Database(paths.db)
    db.migrate()
    dao = Dao(db)
    dao.seed_config(DEFAULT_CONFIG)
    # Q-22: quem ainda usa o prompt base padrão antigo (focado em repositório) recebe o novo; personalizados ficam.
    if dao.config().get("prompt_base", "").strip() == PROMPT_BASE_ANTIGO.strip():
        dao.salvar_config(prompt_base=PROMPT_BASE_PADRAO)
    dao.marcar_interrompidas()

    def cli_path() -> str | None:
        return dao.config()["caminho_cli"] or None

    versions = VersionService(dao)
    if permitir_file is None:
        permitir_file = os.environ.get("SHIPLOG_ALLOW_FILE_URLS") == "1"
    projects = ProjectService(dao, paths.repos, versions, permitir_file=permitir_file)
    health = HealthService(cli_path, skill_check or skill_instalada)
    llm = provider or ClaudeCliProvider(cli_path)
    gen = GenerationService(dao, projects, versions, llm, health.get, limites)
    jobs = JobQueue(dao, gen.executar)
    gen.enqueue = jobs.enfileirar
    gen.posicao = jobs.posicao
    profile = ProfileService(dao, paths.data_dir / "perfil", llm, health.get)
    comments = CommentService(dao, paths.data_dir / "comentarios", llm, health.get)
    return AppContext(paths, db, dao, versions, projects, health, gen, jobs, profile, comments)
