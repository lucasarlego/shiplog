"""Orquestração de uma geração (spec 003 §3.6)."""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable

from ..errors import AppError, nao_encontrado
from ..storage.dao import Dao
from ..storage.db import now_iso
from . import metadata, prompts, schemas
from . import repo as git
from .llm.base import LLMProvider, LLMRequest
from .llm.claude_cli import READ_ONLY_TOOLS
from .projects import ProjectService
from .versions import TABELA, VersionService

log = logging.getLogger("shiplog.generation")

PARAMS_POST = {"tom": ("tecnico", "storytelling", "conquista", "aprendizado"),
               "tamanho": ("curto", "medio", "longo"), "idioma": ("pt", "en")}
PARAMS_ARTIGO = {"idioma": ("pt", "en"), "publico": ("iniciante", "intermediario", "avancado"),
                 "formato": ("tutorial", "deep_dive", "case_arquitetura")}
SEPARADOR = "\n\n===== tentativa {n} =====\n\n"
ETAPAS = ("na_fila", "clonando", "analisando", "gerando")


class Cancelled(Exception):
    pass


class GenerationService:
    def __init__(self, dao: Dao, projects: ProjectService, versions: VersionService, provider: LLMProvider,
                 health: Callable[[], dict[str, Any]], limites: metadata.Limites | None = None) -> None:
        self.dao = dao
        self.projects = projects
        self.versions = versions
        self.provider = provider
        self.health = health
        self.limites = limites or metadata.Limites()
        self.enqueue: Callable[[int], None] = lambda _id: None
        self.posicao: Callable[[int], int] = lambda _id: 0

    # -- criação -------------------------------------------------------------
    def normalizar_parametros(self, tipo: str, parametros: dict[str, Any] | None) -> dict[str, Any]:
        cfg = self.dao.config()
        base = dict(cfg["parametros_padrao_post"] if tipo == "post" else cfg["parametros_padrao_artigo"])
        base.update({k: v for k, v in (parametros or {}).items() if v is not None})
        regras = PARAMS_POST if tipo == "post" else PARAMS_ARTIGO
        for k, validos in regras.items():
            if base.get(k) not in validos:
                raise AppError("validacao", f"Parâmetro '{k}' inválido: {base.get(k)!r}.",
                               f"Valores aceitos: {', '.join(validos)}.", 422)
        if tipo == "post":
            base["incluir_link_artigo"] = bool(base.get("incluir_link_artigo", False))
        return {k: base[k] for k in (*regras, *(["incluir_link_artigo"] if tipo == "post" else []))}

    def criar(self, projeto_id: int, tipo: str, parametros: dict[str, Any] | None = None,
              instrucoes_extras: str = "", base_versao_id: int | None = None,
              atualizar_repo: bool | None = None, atualizacao: bool = False) -> dict[str, Any]:
        if tipo not in ("post", "artigo"):
            raise AppError("validacao", "Tipo inválido.", "Use 'post' ou 'artigo'.", 422)
        projeto = self.projects.obter(projeto_id)
        if projeto["origem"] == "local":
            # Spec 009 FR-05: rodar o Claude headless na pasta de trabalho do usuário não é seguro (R-05).
            raise AppError("projeto_local_sem_geracao",
                           "Este projeto vive só na sua máquina; o Shiplog não gera textos direto nele.",
                           "Gere pelo Claude Code com o MCP do Shiplog (\"faz um post sobre este projeto\").", 409)
        if tipo == "artigo" and projeto["origem"] == "livre":
            raise AppError("artigo_requer_repositorio",
                           "Artigos do Medium precisam de um repositório: eles citam trechos reais de código.",
                           "Cadastre o repositório para gerar artigos com código real.", 409)
        h = self.health()
        if not h["pode_gerar_post"]:
            msg = h["cli"]["mensagem"] or h["auth"]["mensagem"] or h["git"]["mensagem"] or "Claude Code indisponível."
            acao = h["cli"]["comando_sugerido"] or h["auth"]["comando_sugerido"]
            raise AppError("cli_indisponivel", msg, acao, 409)
        if tipo == "artigo" and not h["pode_gerar_artigo"]:
            raise AppError("skill_ausente", h["skill"]["mensagem"] or "Skill ausente.", h["skill"]["comando_sugerido"], 409)
        if base_versao_id is not None:
            v = self.dao.versao(TABELA[tipo], base_versao_id)
            if not v or v["projeto_id"] != projeto_id:
                raise nao_encontrado("Versão base")
        params = self.normalizar_parametros(tipo, parametros)
        gid = self.dao.criar_geracao(
            projeto_id=projeto_id, tipo=tipo, parametros=params, instrucoes_extras=(instrucoes_extras or "").strip(),
            base_versao_id=base_versao_id,
            atualizar_repo=(tipo == "post") if atualizar_repo is None else bool(atualizar_repo),
            atualizacao=bool(atualizacao),
        )
        self.enqueue(gid)
        return self.job(gid)

    def retry(self, gid: int) -> dict[str, Any]:
        g = self.dao.geracao(gid)
        if not g:
            raise nao_encontrado("Geração")
        return self.criar(g["projeto_id"], g["tipo"], g["parametros"], g["instrucoes_extras"], g["base_versao_id"],
                          g["atualizar_repo"], g["atualizacao"])

    # -- apresentação --------------------------------------------------------
    def job(self, gid: int) -> dict[str, Any]:
        g = self.dao.geracao(gid)
        if not g:
            raise nao_encontrado("Job")
        return self.apresentar(g)

    def apresentar(self, g: dict[str, Any]) -> dict[str, Any]:
        out = {k: g.get(k) for k in (
            "id", "projeto_id", "tipo", "status", "commit_hash", "parametros", "instrucoes_extras", "erro",
            "erro_codigo", "acao_sugerida", "avisos", "resultado_id", "tentativas", "duracao_ms", "criado_em",
            "iniciado_em", "finalizado_em", "base_versao_id", "atualizacao")}
        out["posicao_fila"] = self.posicao(g["id"]) if g["status"] == "na_fila" else 0
        return out

    def debug(self, gid: int) -> dict[str, Any]:
        g = self.dao.geracao(gid)
        if not g:
            raise nao_encontrado("Geração")
        return {k: g[k] for k in ("id", "prompt", "resposta_bruta", "duracao_ms", "codigo_saida", "tentativas", "erro",
                                  "erro_codigo", "status")}

    # -- execução (worker) -----------------------------------------------------
    def _status(self, gid: int, status: str, cancel: threading.Event) -> None:
        if cancel.is_set():
            raise Cancelled()
        self.dao.atualizar_geracao(gid, status=status)

    def executar(self, gid: int, cancel: threading.Event) -> None:
        g = self.dao.geracao(gid)
        if not g or g["status"] != "na_fila":
            return
        inicio = time.monotonic()
        self.dao.atualizar_geracao(gid, iniciado_em=now_iso())
        avisos: list[str] = []
        brutos: list[str] = []
        try:
            self._executar(g, cancel, avisos, brutos)
        except (Cancelled, git.Cancelado):
            self.dao.atualizar_geracao(gid, status="cancelado", erro="Geração cancelada pelo usuário.",
                                       erro_codigo="cancelado")
        except AppError as e:
            mapa = {"repo_auth": "git_auth", "repo_inacessivel": "git_falha", "branch_inexistente": "git_falha"}
            self.dao.atualizar_geracao(gid, status="erro", erro=e.mensagem, erro_codigo=mapa.get(e.codigo, e.codigo),
                                       acao_sugerida=e.acao_sugerida)
        except Exception as e:  # pragma: no cover - defensivo
            log.exception("Falha inesperada na geração %s", gid)
            self.dao.atualizar_geracao(gid, status="erro", erro=f"Erro interno: {e}", erro_codigo="interno",
                                       acao_sugerida="Veja os logs em <pasta de dados>/logs.")
        finally:
            self.dao.atualizar_geracao(
                gid, finalizado_em=now_iso(), duracao_ms=int((time.monotonic() - inicio) * 1000), avisos=avisos,
                resposta_bruta="".join(brutos) if brutos else None,
            )

    def _executar(self, g: dict[str, Any], cancel: threading.Event, avisos: list[str], brutos: list[str]) -> None:
        gid, tipo = g["id"], g["tipo"]
        projeto = self.projects.obter(g["projeto_id"])
        if projeto["origem"] == "livre":
            self._executar_livre(g, projeto, cancel, avisos, brutos)
            return
        caminho = Path(projeto["caminho_local"])

        # 1. Clone/atualização (RF-07, RF-09)
        self._status(gid, "clonando", cancel)
        precisa = not git.is_clone(caminho)
        commit = git.garantir_clone(projeto["url_repo"], caminho, projeto["branch"],
                                    atualizar=bool(g["atualizar_repo"]), cancel=cancel)
        self.dao.atualizar_geracao(gid, commit_hash=commit)
        self.projects.marcar_analise(projeto["id"], git.branch_atual(caminho), commit,
                                     atualizado=precisa or bool(g["atualizar_repo"]))
        projeto = self.projects.obter(projeto["id"])

        # 2. Metadados (RF-08)
        self._status(gid, "analisando", cancel)
        md = metadata.coletar(caminho, self.limites)
        if md.parcial:
            avisos.append("analise_parcial")

        # 3. Prompt + LLM (RF-11, RI-*)
        self._status(gid, "gerando", cancel)
        cfg = self.dao.config()
        base = self.dao.versao(TABELA[tipo], g["base_versao_id"]) if g["base_versao_id"] else None
        link_art = titulo_art = None
        if tipo == "post" and g["parametros"].get("incluir_link_artigo"):
            pub = self.dao.publicada("artigos", projeto["id"])
            if pub and pub["link_medium"]:
                link_art, titulo_art = pub["link_medium"], pub["titulo"]
        ctx = prompts.ContextoPrompt(
            nome=projeto["nome"], url=projeto["url_repo"], branch=projeto["branch"], commit=commit,
            notas=projeto["notas"], metadados=md, prompt_base=cfg["prompt_base"], perfil_voz=cfg["perfil_voz"], perfil_profissional=cfg["perfil_profissional"],
            parametros=g["parametros"], instrucoes_extras=g["instrucoes_extras"], versao_anterior=base,
            link_artigo=link_art, titulo_artigo=titulo_art,
        )
        schema = schemas.json_schema(tipo)
        prompt = (prompts.montar_prompt_post if tipo == "post" else prompts.montar_prompt_artigo)(ctx, schema)
        self.dao.atualizar_geracao(gid, prompt=prompt)
        timeout = cfg["timeout_post_s"] if tipo == "post" else cfg["timeout_artigo_s"]
        req = LLMRequest(prompt=prompt, cwd=caminho, tools=list(READ_ONLY_TOOLS), json_schema=schema,
                         timeout_s=int(timeout), allow_skills=(tipo == "artigo"), model=cfg["modelo"] or None)
        try:
            dados = self._chamar_com_correcao(gid, tipo, req, caminho, cancel, avisos, brutos)
        finally:
            # 4. R-05: o repositório analisado não pode ter sido alterado.
            alterados = git.alteracoes(caminho) if git.is_clone(caminho) else []
            if alterados:
                log.warning("Geração %s alterou o clone: %s", gid, alterados[:20])
                avisos.append("repo_alterado")
                git.restaurar(caminho)

        # 5. Persistência como nova versão (RF-14, RF-17)
        rodada = self.versions.rodada_para_geracao(tipo, projeto["id"], bool(g["atualizacao"]))
        vid = self.versions.criar_gerada(tipo, projeto["id"], gid, rodada, dados, origem_id=g["base_versao_id"])
        self.dao.atualizar_geracao(gid, status="concluido", resultado_id=vid)

    def _executar_livre(self, g: dict[str, Any], projeto: dict[str, Any], cancel: threading.Event,
                        avisos: list[str], brutos: list[str]) -> None:
        """Post sem repositório (spec 006): sem clone, sem metadados e sem nenhuma ferramenta (NFR-02)."""
        gid = g["id"]
        if g["tipo"] != "post":
            raise AppError("artigo_requer_repositorio", "Artigos do Medium precisam de um repositório.",
                           "Cadastre o repositório para gerar artigos com código real.", 409)
        self._status(gid, "gerando", cancel)
        cfg = self.dao.config()
        base = self.dao.versao("posts", g["base_versao_id"]) if g["base_versao_id"] else None
        ctx = prompts.ContextoPrompt(
            nome=projeto["nome"], url=None, branch=None, commit=None, notas=projeto["notas"], metadados=None,
            prompt_base=cfg["prompt_base"], perfil_voz=cfg["perfil_voz"], perfil_profissional=cfg["perfil_profissional"], parametros=g["parametros"],
            instrucoes_extras=g["instrucoes_extras"], versao_anterior=base, descricao=projeto["descricao"],
        )
        schema = schemas.json_schema("post")
        prompt = prompts.montar_prompt_post(ctx, schema)
        self.dao.atualizar_geracao(gid, prompt=prompt)
        # Diretório de trabalho vazio, fora de qualquer repositório.
        cwd = self.projects.repos_dir.parent / "workspace-livre"
        cwd.mkdir(parents=True, exist_ok=True)
        req = LLMRequest(prompt=prompt, cwd=cwd, tools=[], json_schema=schema, timeout_s=int(cfg["timeout_post_s"]),
                         allow_skills=False, model=cfg["modelo"] or None)
        dados = self._chamar_com_correcao(gid, "post", req, cwd, cancel, avisos, brutos)
        self.dao.atualizar_projeto(projeto["id"], ultima_analise_em=now_iso())
        rodada = self.versions.rodada_para_geracao("post", projeto["id"], bool(g["atualizacao"]))
        vid = self.versions.criar_gerada("post", projeto["id"], gid, rodada, dados, origem_id=g["base_versao_id"])
        self.dao.atualizar_geracao(gid, status="concluido", resultado_id=vid)

    def _chamar_com_correcao(self, gid: int, tipo: str, req: LLMRequest, raiz: Path, cancel: threading.Event,
                             avisos: list[str], brutos: list[str]) -> dict[str, Any]:
        r = self.provider.run(req, cancel)
        brutos.append(r.raw)
        self.dao.atualizar_geracao(gid, tentativas=1, codigo_saida=r.exit_code)
        self._falha(r)
        dados, erros = schemas.validar(tipo, r.data, raiz) if r.data is not None else (None, ["a resposta não contém um objeto JSON"])
        if dados is not None:
            return dados

        # RI-05: uma tentativa de correção.
        if cancel.is_set():
            raise Cancelled()
        anterior = r.meta.get("result_text") or r.raw
        if r.data is not None:
            anterior = json.dumps(r.data, ensure_ascii=False)
        corr = LLMRequest(prompt=prompts.montar_prompt_correcao(req.json_schema, anterior, erros), cwd=req.cwd,
                          tools=[], json_schema=req.json_schema, timeout_s=min(req.timeout_s, 300),
                          allow_skills=False, model=req.model)
        r2 = self.provider.run(corr, cancel)
        brutos.append(SEPARADOR.format(n=2) + r2.raw)
        self.dao.atualizar_geracao(gid, tentativas=2, codigo_saida=r2.exit_code,
                                   prompt=req.prompt + SEPARADOR.format(n=2) + corr.prompt)
        self._falha(r2)
        dados, erros2 = schemas.validar(tipo, r2.data, raiz) if r2.data is not None else (None, ["sem JSON"])
        if dados is None:
            raise AppError("schema_invalido", "A resposta do Claude ficou fora do formato mesmo após uma correção: "
                           + "; ".join(erros2[:5]), "Veja a resposta bruta nos detalhes e tente novamente.", 422)
        avisos.append("correcao_aplicada")
        return dados

    @staticmethod
    def _falha(r: Any) -> None:
        if r.ok:
            return
        if r.error_code == "cancelado":
            raise Cancelled()
        raise AppError(r.error_code or "cli_falha", r.error_message or "Falha do Claude Code.",
                       r.meta.get("acao"), 422)
