"""Acesso a dados por entidade (spec 001). Todo o SQL da aplicação vive aqui."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .db import Database, now_iso

JSON_FIELDS = {
    "parametros", "avisos", "hooks_alternativos", "hashtags", "destaques", "tags",
    "trechos_de_codigo", "sugestoes_de_imagens", "imagens", "sugestoes", "parametros_padrao_post", "parametros_padrao_artigo",
}
BOOL_FIELDS = {"arquivado", "editado_manualmente", "atualizar_repo", "atualizacao"}
ATIVOS = ("na_fila", "clonando", "analisando", "gerando")


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if k in JSON_FIELDS and isinstance(v, str):
            try:
                d[k] = json.loads(v)
            except ValueError:
                pass
        elif k in BOOL_FIELDS and v is not None:
            d[k] = bool(v)
    return d


def _enc(v: Any) -> Any:
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool):
        return int(v)
    return v


class Dao:
    def __init__(self, db: Database) -> None:
        self.db = db

    # -- utilitários -------------------------------------------------------
    def _one(self, sql: str, args: tuple = ()) -> dict[str, Any] | None:
        return row_to_dict(self.db.conn.execute(sql, args).fetchone())

    def _all(self, sql: str, args: tuple = ()) -> list[dict[str, Any]]:
        return [row_to_dict(r) for r in self.db.conn.execute(sql, args).fetchall()]  # type: ignore[misc]

    def _update(self, table: str, id_: int, fields: dict[str, Any]) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        with self.db.tx() as c:
            c.execute(f"UPDATE {table} SET {cols} WHERE id = ?", (*[_enc(v) for v in fields.values()], id_))

    def _insert(self, c: sqlite3.Connection, table: str, fields: dict[str, Any]) -> int:
        cols = ", ".join(fields)
        qs = ", ".join("?" for _ in fields)
        cur = c.execute(f"INSERT INTO {table} ({cols}) VALUES ({qs})", tuple(_enc(v) for v in fields.values()))
        return int(cur.lastrowid)  # type: ignore[arg-type]

    # -- comentários (spec 008) --------------------------------------------
    def criar_comentario(self, **f: Any) -> int:
        f.setdefault("criado_em", now_iso())
        with self.db.tx() as c:
            return self._insert(c, "comentarios", f)

    def comentario(self, id_: int) -> dict[str, Any] | None:
        return self._one("SELECT * FROM comentarios WHERE id = ?", (id_,))

    def listar_comentarios(self) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM comentarios ORDER BY criado_em DESC, id DESC")

    def atualizar_comentario(self, id_: int, **f: Any) -> None:
        self._update("comentarios", id_, f)

    def excluir_comentario(self, id_: int) -> None:
        with self.db.tx() as c:
            c.execute("DELETE FROM comentarios WHERE id = ?", (id_,))

    # -- projetos ----------------------------------------------------------
    def criar_projeto(self, **f: Any) -> int:
        f.setdefault("criado_em", now_iso())
        with self.db.tx() as c:
            return self._insert(c, "projetos", f)

    def projeto(self, id_: int) -> dict[str, Any] | None:
        return self._one("SELECT * FROM projetos WHERE id = ?", (id_,))

    def projeto_por_url(self, url_normalizada: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM projetos WHERE url_normalizada = ?", (url_normalizada,))

    def listar_projetos(self, incluir_arquivados: bool = False) -> list[dict[str, Any]]:
        where = "" if incluir_arquivados else "WHERE arquivado = 0"
        return self._all(f"SELECT * FROM projetos {where} ORDER BY COALESCE(ultima_analise_em, criado_em) DESC, id DESC")

    def atualizar_projeto(self, id_: int, **f: Any) -> None:
        self._update("projetos", id_, f)

    def excluir_projeto(self, id_: int) -> None:
        with self.db.tx() as c:
            c.execute("DELETE FROM projetos WHERE id = ?", (id_,))

    # -- gerações ----------------------------------------------------------
    def criar_geracao(self, **f: Any) -> int:
        f.setdefault("criado_em", now_iso())
        f.setdefault("status", "na_fila")
        with self.db.tx() as c:
            return self._insert(c, "geracoes", f)

    def geracao(self, id_: int) -> dict[str, Any] | None:
        return self._one("SELECT * FROM geracoes WHERE id = ?", (id_,))

    def atualizar_geracao(self, id_: int, **f: Any) -> None:
        self._update("geracoes", id_, f)

    def listar_geracoes(self, projeto_id: int) -> list[dict[str, Any]]:
        return self._all(
            "SELECT id, projeto_id, tipo, status, commit_hash, parametros, instrucoes_extras, erro, erro_codigo, "
            "acao_sugerida, avisos, resultado_id, tentativas, duracao_ms, criado_em, iniciado_em, finalizado_em "
            "FROM geracoes WHERE projeto_id = ? ORDER BY id DESC",
            (projeto_id,),
        )

    def geracoes_ativas(self) -> list[dict[str, Any]]:
        qs = ",".join("?" for _ in ATIVOS)
        return self._all(f"SELECT * FROM geracoes WHERE status IN ({qs}) ORDER BY id", ATIVOS)

    def geracao_ativa_do_projeto(self, projeto_id: int) -> dict[str, Any] | None:
        qs = ",".join("?" for _ in ATIVOS)
        return self._one(
            f"SELECT id, tipo, status FROM geracoes WHERE projeto_id = ? AND status IN ({qs}) ORDER BY id DESC LIMIT 1",
            (projeto_id, *ATIVOS),
        )

    def ultimo_commit_gerado(self, projeto_id: int) -> str | None:
        r = self.db.conn.execute(
            "SELECT commit_hash FROM geracoes WHERE projeto_id = ? AND status = 'concluido' AND commit_hash IS NOT NULL "
            "ORDER BY id DESC LIMIT 1",
            (projeto_id,),
        ).fetchone()
        return r[0] if r else None

    def marcar_interrompidas(self) -> int:
        qs = ",".join("?" for _ in ATIVOS)
        with self.db.tx() as c:
            cur = c.execute(
                f"UPDATE geracoes SET status = 'erro', erro_codigo = 'interrompido', "
                f"erro = 'Interrompida: a aplicação foi encerrada durante a geração.', "
                f"acao_sugerida = 'Tente novamente.', finalizado_em = ? WHERE status IN ({qs})",
                (now_iso(), *ATIVOS),
            )
            return cur.rowcount

    # -- versões (posts/artigos) -------------------------------------------
    def versao(self, tabela: str, id_: int) -> dict[str, Any] | None:
        return self._one(f"SELECT * FROM {tabela} WHERE id = ?", (id_,))

    def listar_versoes(self, tabela: str, projeto_id: int) -> list[dict[str, Any]]:
        return self._all(f"SELECT * FROM {tabela} WHERE projeto_id = ? ORDER BY versao DESC", (projeto_id,))

    def ultima_versao(self, tabela: str, projeto_id: int) -> dict[str, Any] | None:
        return self._one(f"SELECT * FROM {tabela} WHERE projeto_id = ? ORDER BY versao DESC LIMIT 1", (projeto_id,))

    def publicada(self, tabela: str, projeto_id: int) -> dict[str, Any] | None:
        return self._one(
            f"SELECT * FROM {tabela} WHERE projeto_id = ? AND status = 'publicado' ORDER BY rodada DESC LIMIT 1",
            (projeto_id,),
        )

    def rodada_atual(self, tabela: str, projeto_id: int) -> int:
        r = self.db.conn.execute(f"SELECT COALESCE(MAX(rodada), 1) FROM {tabela} WHERE projeto_id = ?", (projeto_id,)).fetchone()
        return int(r[0])

    def inserir_versao(self, tabela: str, fields: dict[str, Any]) -> int:
        """Insere com número de versão sequencial na mesma transação (FR-04)."""
        fields.setdefault("criado_em", now_iso())
        with self.db.tx() as c:
            r = c.execute(f"SELECT COALESCE(MAX(versao), 0) + 1 FROM {tabela} WHERE projeto_id = ?", (fields["projeto_id"],)).fetchone()
            fields["versao"] = int(r[0])
            return self._insert(c, tabela, fields)

    def atualizar_versao(self, tabela: str, id_: int, **f: Any) -> None:
        self._update(tabela, id_, f)

    # -- configuração -------------------------------------------------------
    def seed_config(self, defaults: dict[str, Any]) -> None:
        f = {"id": 1, "atualizado_em": now_iso(), **defaults}
        cols = ", ".join(f)
        qs = ", ".join("?" for _ in f)
        with self.db.tx() as c:
            c.execute(f"INSERT OR IGNORE INTO configuracoes ({cols}) VALUES ({qs})", tuple(_enc(v) for v in f.values()))

    def config(self) -> dict[str, Any]:
        d = self._one("SELECT * FROM configuracoes WHERE id = 1")
        assert d is not None, "configuração não semeada"
        return d

    def salvar_config(self, **f: Any) -> None:
        f["atualizado_em"] = now_iso()
        self._update("configuracoes", 1, f)
