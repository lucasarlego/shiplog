import sqlite3

import pytest

from shiplog.storage.dao import Dao
from shiplog.storage.db import Database


@pytest.fixture
def dao(tmp_path):
    db = Database(tmp_path / "t.db")
    db.migrate()
    return Dao(db)


def test_migrate_idempotente(tmp_path):
    db = Database(tmp_path / "t.db")
    assert db.migrate() == [1, 2, 3, 4]
    assert db.migrate() == []


def test_url_normalizada_unica(dao):
    dao.criar_projeto(nome="a", url_repo="u", url_normalizada="github.com/me/app", caminho_local="x")
    with pytest.raises(sqlite3.IntegrityError):
        dao.criar_projeto(nome="b", url_repo="u2", url_normalizada="github.com/me/app", caminho_local="y")


def test_cascade_delete(dao):
    pid = dao.criar_projeto(nome="a", url_repo="u", url_normalizada="n", caminho_local="x")
    gid = dao.criar_geracao(projeto_id=pid, tipo="post")
    dao.inserir_versao("posts", {"projeto_id": pid, "geracao_id": gid, "texto": "t"})
    dao.excluir_projeto(pid)
    assert dao.geracao(gid) is None
    assert dao.listar_versoes("posts", pid) == []


def test_interrompidas(dao):
    pid = dao.criar_projeto(nome="a", url_repo="u", url_normalizada="n", caminho_local="x")
    gid = dao.criar_geracao(projeto_id=pid, tipo="post", status="gerando")
    assert dao.marcar_interrompidas() == 1
    assert dao.geracao(gid)["erro_codigo"] == "interrompido"
