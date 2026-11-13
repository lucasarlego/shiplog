"""Regras de versão e status de posts e artigos (spec 001 FR-05..FR-07)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Literal

from ..errors import AppError, nao_encontrado
from ..storage.dao import Dao
from ..storage.db import now_iso
from . import schemas

Tipo = Literal["post", "artigo"]
TABELA = {"post": "posts", "artigo": "artigos"}
LINK = {"post": "link_linkedin", "artigo": "link_medium"}
EDITAVEIS = {
    "post": ("texto", "hooks_alternativos", "hashtags", "resumo_tecnico", "destaques"),
    "artigo": ("titulo", "subtitulo", "corpo_markdown", "tags", "trechos_de_codigo", "sugestoes_de_imagens"),
}
STATUS = ("rascunho", "pronto", "publicado")
PARAMETROS = {
    "post": {"tom": ("tecnico", "storytelling", "conquista", "aprendizado"), "tamanho": ("curto", "medio", "longo"),
             "idioma": ("pt", "en")},
    "artigo": {"idioma": ("pt", "en"), "publico": ("iniciante", "intermediario", "avancado"),
               "formato": ("tutorial", "deep_dive", "case_arquitetura")},
}


def _parametros(tipo: Tipo, p: dict[str, Any] | None) -> dict[str, Any]:
    """Guarda só os parâmetros informados (nunca preenche padrões que o autor não escolheu) e recusa valores inválidos."""
    out: dict[str, Any] = {}
    for k, validos in PARAMETROS[tipo].items():
        v = (p or {}).get(k)
        if v is None:
            continue
        if v not in validos:
            raise AppError("validacao", f"Parâmetro '{k}' inválido: {v!r}.", f"Valores aceitos: {', '.join(validos)}.", 422)
        out[k] = v
    if tipo == "post" and (p or {}).get("incluir_link_artigo") is not None:
        out["incluir_link_artigo"] = bool(p["incluir_link_artigo"])  # type: ignore[index]
    return out


class VersionService:
    def __init__(self, dao: Dao) -> None:
        self.dao = dao

    def apresentar(self, tipo: Tipo, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """Formato público: `link` unificado + parâmetros/instruções da geração de origem."""
        if v is None:
            return None
        out = dict(v)
        out["link"] = out.pop(LINK[tipo], None)
        g = self.dao.geracao(v["geracao_id"]) if v.get("geracao_id") else None
        # A versão guarda os próprios parâmetros (0006); a geração de origem é só o fallback.
        out["parametros"] = v.get("parametros") or (g["parametros"] if g else {})
        out["instrucoes_extras"] = v.get("instrucoes_extras") or (g["instrucoes_extras"] if g else "")
        out["commit_hash"] = g["commit_hash"] if g else None
        return out

    def obter(self, tipo: Tipo, id_: int) -> dict[str, Any]:
        v = self.dao.versao(TABELA[tipo], id_)
        if not v:
            raise nao_encontrado("Post" if tipo == "post" else "Artigo")
        return v

    def listar(self, tipo: Tipo, projeto_id: int) -> list[dict[str, Any]]:
        return [self.apresentar(tipo, v) for v in self.dao.listar_versoes(TABELA[tipo], projeto_id)]  # type: ignore[misc]

    def rodada_para_geracao(self, tipo: Tipo, projeto_id: int, atualizacao: bool) -> int:
        atual = self.dao.rodada_atual(TABELA[tipo], projeto_id)
        tem_versoes = self.dao.ultima_versao(TABELA[tipo], projeto_id) is not None
        return atual + 1 if (atualizacao and tem_versoes) else atual

    def criar_gerada(self, tipo: Tipo, projeto_id: int, geracao_id: int, rodada: int,
                     conteudo: dict[str, Any], origem_id: int | None = None) -> int:
        """Regeneração sempre insere uma nova versão (AC-02)."""
        if tipo == "post" and "post" in conteudo and "texto" not in conteudo:
            conteudo = {**conteudo, "texto": conteudo["post"]}
        fields = {k: conteudo[k] for k in EDITAVEIS[tipo] if k in conteudo}
        g = self.dao.geracao(geracao_id)
        fields.update(projeto_id=projeto_id, geracao_id=geracao_id, rodada=rodada,
                      origem_id=origem_id, status="rascunho", editado_manualmente=False,
                      parametros=(g or {}).get("parametros") or {}, instrucoes_extras=(g or {}).get("instrucoes_extras") or "")
        return self.dao.inserir_versao(TABELA[tipo], fields)

    def criar_externa(self, tipo: Tipo, projeto_id: int, dados: dict[str, Any], raiz: Path | None,
                      fonte: str = "claude_code", commit_referencia: str | None = None,
                      base_versao_id: int | None = None, parametros: dict[str, Any] | None = None,
                      instrucoes_extras: str = "") -> int:
        """Versão escrita fora do Shiplog, pelo modelo do harness via MCP (spec 009 FR-09, FR-11)."""
        if tipo == "artigo" and raiz is None:
            raise AppError("validacao", "Para conferir os trechos de código, informe `caminho` com a pasta do projeto.",
                           None, 422)
        validos, erros = schemas.validar("post_externo" if tipo == "post" else "artigo", dados, raiz)
        if validos is None:
            raise AppError("validacao", "O conteúdo não passou na validação: " + "; ".join(erros[:8]),
                           "Corrija os itens e chame de novo.", 422, {"erros": erros})
        if base_versao_id is not None:
            base = self.dao.versao(TABELA[tipo], base_versao_id)
            if not base or base["projeto_id"] != projeto_id:
                raise nao_encontrado("Versão base")
        fields = {k: validos[k] for k in EDITAVEIS[tipo] if k in validos}
        fields.update(projeto_id=projeto_id, geracao_id=None, rodada=self.dao.rodada_atual(TABELA[tipo], projeto_id),
                      origem_id=base_versao_id, status="rascunho", editado_manualmente=False, fonte=fonte,
                      commit_referencia=commit_referencia, parametros=_parametros(tipo, parametros),
                      instrucoes_extras=(instrucoes_extras or "").strip())
        return self.dao.inserir_versao(TABELA[tipo], fields)

    def editar(self, tipo: Tipo, origem_id: int, mudancas: dict[str, Any]) -> int:
        """Edição manual cria nova versão a partir da origem (AC-03)."""
        origem = self.obter(tipo, origem_id)
        fields = {k: origem[k] for k in EDITAVEIS[tipo]}
        fields.update({k: v for k, v in mudancas.items() if k in EDITAVEIS[tipo] and v is not None})
        fields.update(projeto_id=origem["projeto_id"], geracao_id=origem["geracao_id"], rodada=origem["rodada"],
                      origem_id=origem["id"], status="rascunho", editado_manualmente=True,
                      parametros=origem.get("parametros") or {},
                      instrucoes_extras=origem.get("instrucoes_extras") or "")
        return self.dao.inserir_versao(TABELA[tipo], fields)

    def alterar_status(self, tipo: Tipo, id_: int, status: str, link: str | None = None) -> None:
        if status not in STATUS:
            raise AppError("validacao", "Status inválido.", "Use rascunho, pronto ou publicado.", 422)
        v = self.obter(tipo, id_)
        campos: dict[str, Any] = {"status": status}
        if status == "publicado":
            campos["publicado_em"] = v.get("publicado_em") or now_iso()
            if link is not None:
                campos[LINK[tipo]] = link.strip() or None
        else:
            campos["publicado_em"] = None
        try:
            self.dao.atualizar_versao(TABELA[tipo], id_, **campos)
        except sqlite3.IntegrityError as e:
            raise AppError(
                "conflito_publicado",
                "Já existe outra versão publicada nesta rodada.",
                "Volte a outra versão para 'pronto' antes, ou gere um post de atualização.",
                409,
            ) from e
