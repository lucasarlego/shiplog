import pytest

from shiplog.errors import AppError
from shiplog.services.versions import VersionService
from shiplog.storage.dao import Dao
from shiplog.storage.db import Database

CONT = {"texto": "v", "hooks_alternativos": ["a", "b"], "hashtags": ["#a", "#b", "#c"],
        "resumo_tecnico": "r", "destaques": []}


@pytest.fixture
def env(tmp_path):
    db = Database(tmp_path / "t.db")
    db.migrate()
    dao = Dao(db)
    pid = dao.criar_projeto(nome="a", url_repo="u", url_normalizada="n", caminho_local="x")
    gid = dao.criar_geracao(projeto_id=pid, tipo="post")
    return dao, VersionService(dao), pid, gid


def test_regeneracao_preserva_anterior(env):
    dao, vs, pid, gid = env
    v1 = vs.criar_gerada("post", pid, gid, 1, {**CONT, "texto": "um"})
    v2 = vs.criar_gerada("post", pid, gid, 1, {**CONT, "texto": "dois"}, origem_id=v1)
    assert dao.versao("posts", v1)["texto"] == "um"
    assert [v["versao"] for v in vs.listar("post", pid)] == [2, 1]
    assert dao.versao("posts", v2)["origem_id"] == v1


def test_edicao_cria_versao(env):
    dao, vs, pid, gid = env
    v1 = vs.criar_gerada("post", pid, gid, 1, CONT)
    v2 = vs.editar("post", v1, {"texto": "editado"})
    d = dao.versao("posts", v2)
    assert d["versao"] == 2 and d["editado_manualmente"] and d["origem_id"] == v1 and d["texto"] == "editado"
    assert d["hashtags"] == CONT["hashtags"]


def test_publicar_registra_data_link(env):
    dao, vs, pid, gid = env
    v1 = vs.criar_gerada("post", pid, gid, 1, CONT)
    vs.alterar_status("post", v1, "publicado", "https://linkedin.com/x")
    d = vs.apresentar("post", dao.versao("posts", v1))
    assert d["publicado_em"] and d["link"] == "https://linkedin.com/x"
    vs.alterar_status("post", v1, "pronto")
    assert dao.versao("posts", v1)["publicado_em"] is None


def test_conflito_publicado_mesma_rodada(env):
    dao, vs, pid, gid = env
    v1 = vs.criar_gerada("post", pid, gid, 1, CONT)
    v2 = vs.criar_gerada("post", pid, gid, 1, CONT)
    vs.alterar_status("post", v2, "publicado")
    with pytest.raises(AppError) as e:
        vs.alterar_status("post", v1, "publicado")
    assert e.value.codigo == "conflito_publicado"


def test_rodada_de_atualizacao(env):
    dao, vs, pid, gid = env
    v1 = vs.criar_gerada("post", pid, gid, 1, CONT)
    vs.alterar_status("post", v1, "publicado")
    rodada = vs.rodada_para_geracao("post", pid, atualizacao=True)
    assert rodada == 2
    v2 = vs.criar_gerada("post", pid, gid, rodada, CONT)
    vs.alterar_status("post", v2, "publicado")
    assert dao.versao("posts", v2)["status"] == "publicado"
