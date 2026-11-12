"""Spec 006 — post sem repositório."""

import shutil
import sqlite3

import pytest
from fastapi.testclient import TestClient

from conftest import POST_OK, wait_job
from shiplog.app import create_app
from shiplog.config import Paths
from shiplog.context import build_context
from shiplog.services import prompts
from shiplog.storage import db as dbmod

DESC = "Nesta semana migrei o deploy do time de VMs manuais para um pipeline com revisão obrigatória."


@pytest.fixture
def client(ctx):
    with TestClient(create_app(ctx)) as c:
        yield c


def _criar(client, ctx, **extra):
    r = client.post("/api/projects", json={"descricao": DESC, "gerar": True, **extra})
    assert r.status_code == 201, r.text
    body = r.json()
    return body["projeto"], wait_job(ctx, body["job"]["id"])


def test_criar_e_gerar_livre(client, ctx, fake_cli):
    projeto, g = _criar(client, ctx)
    assert projeto["origem"] == "livre" and projeto["url_repo"] is None and projeto["descricao"] == DESC
    assert projeto["nome"].startswith("Nesta semana")
    assert g["status"] == "concluido", g
    assert g["commit_hash"] is None
    call = fake_cli.calls()[0]
    argv = call["argv"]
    assert argv[argv.index("--tools") + 1] == ""
    assert DESC in call["stdin"] and "Como investigar" not in call["stdin"]
    assert call["cwd"].endswith("workspace-livre")
    assert not any(ctx.paths.repos.iterdir()) if ctx.paths.repos.exists() else True
    posts = client.get(f"/api/projects/{projeto['id']}/posts").json()
    assert len(posts) == 1 and posts[0]["texto"] == POST_OK["post"]


def test_validacao_sem_url_nem_descricao(client):
    r = client.post("/api/projects", json={"gerar": False})
    assert r.status_code == 422 and r.json()["erro"]["codigo"] == "validacao"
    r = client.post("/api/projects", json={"descricao": "curta", "gerar": False})
    assert r.status_code == 422 and "20 caracteres" in r.json()["erro"]["mensagem"]


def test_artigo_recusado(client, ctx):
    projeto, _ = _criar(client, ctx)
    r = client.post(f"/api/projects/{projeto['id']}/generations", json={"tipo": "artigo"})
    assert r.status_code == 409 and r.json()["erro"]["codigo"] == "artigo_requer_repositorio"


def test_sem_duplicidade(client):
    a = client.post("/api/projects", json={"descricao": DESC, "gerar": False})
    b = client.post("/api/projects", json={"descricao": DESC, "gerar": False})
    assert a.status_code == b.status_code == 201
    assert a.json()["projeto"]["id"] != b.json()["projeto"]["id"]


def test_edicao_descricao_e_branch(client):
    pid = client.post("/api/projects", json={"descricao": DESC, "gerar": False}).json()["projeto"]["id"]
    nova = DESC + " Também documentei o processo."
    assert client.patch(f"/api/projects/{pid}", json={"descricao": nova}).json()["descricao"] == nova
    assert client.patch(f"/api/projects/{pid}", json={"branch": "dev"}).status_code == 422


def test_regeneracao_livre(client, ctx, fake_cli):
    projeto, g = _criar(client, ctx)
    v1 = g["resultado_id"]
    r = client.post(f"/api/projects/{projeto['id']}/generations",
                    json={"tipo": "post", "instrucoes_extras": "Deixe mais curto e sem emojis", "base_versao_id": v1})
    assert r.status_code == 202, r.text
    g2 = wait_job(ctx, r.json()["id"])
    assert g2["status"] == "concluido", g2
    stdin = fake_cli.calls()[-1]["stdin"]
    assert "Deixe mais curto e sem emojis" in stdin and POST_OK["post"].strip()[:40] in stdin
    versoes = client.get(f"/api/projects/{projeto['id']}/posts").json()
    assert sorted(v["versao"] for v in versoes) == [1, 2]


def test_check_updates_ignora_livre(client, ctx, remote_repo):
    client.post("/api/projects", json={"descricao": DESC, "gerar": False})
    client.post("/api/projects", json={"url": remote_repo.as_uri(), "gerar": False})
    r = client.post("/api/projects/check-updates", json={})
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_exportacao_inclui_livre(client):
    client.post("/api/projects", json={"descricao": DESC, "gerar": False})
    md = client.get("/api/export?formato=md")
    assert md.status_code == 200 and DESC in md.text


def test_prompt_livre_sem_metadados():
    ctx = prompts.ContextoPrompt(nome="Deploy", url=None, branch=None, commit=None, notas="", metadados=None,
                                 prompt_base="", perfil_voz="", parametros={"tom": "tecnico", "tamanho": "curto",
                                                                             "idioma": "pt"},
                                 instrucoes_extras="", versao_anterior=None, descricao=DESC)
    p = prompts.montar_prompt_post(ctx, {"type": "object"})
    assert DESC in p and "não invente" in p and "Como investigar" not in p


def test_migracao_preserva_dados(tmp_path, monkeypatch):
    """AC-06: banco na versão 1 com dados migra para a versão 2 sem perder linhas."""
    so_v1 = tmp_path / "mig_v1"
    so_v1.mkdir()
    shutil.copy(dbmod.MIGRATIONS_DIR / "0001_inicial.sql", so_v1)
    path = tmp_path / "data" / "shiplog.db"
    path.parent.mkdir()
    conn = dbmod.connect(path)
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", so_v1)
    assert dbmod.migrate(conn) == [1]
    t = "2026-01-01T00:00:00Z"
    conn.execute("INSERT INTO projetos (id, nome, url_repo, url_normalizada, caminho_local, criado_em) "
                 "VALUES (1, 'app', 'https://github.com/a/b', 'github.com/a/b', '/x', ?)", (t,))
    conn.execute("INSERT INTO geracoes (id, projeto_id, tipo, status, criado_em) VALUES (1, 1, 'post', 'concluido', ?)", (t,))
    conn.execute("INSERT INTO posts (projeto_id, geracao_id, versao, texto, criado_em) VALUES (1, 1, 1, 'olá', ?)", (t,))
    conn.close()

    monkeypatch.undo()
    c = build_context(Paths(tmp_path / "data"), skill_check=lambda: True)
    assert c.dao.projeto(1)["origem"] == "repo" and c.dao.projeto(1)["url_repo"] == "https://github.com/a/b"
    raw = sqlite3.connect(path)
    assert raw.execute("SELECT COUNT(*) FROM geracoes").fetchone()[0] == 1
    assert raw.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 1
    assert raw.execute("SELECT MAX(versao) FROM schema_migrations").fetchone()[0] >= 2
    assert raw.execute("PRAGMA foreign_key_check").fetchall() == []


def test_prompt_base_antigo_e_atualizado(tmp_path):
    c = build_context(Paths(tmp_path / "d"), skill_check=lambda: True)
    c.dao.salvar_config(prompt_base=prompts.PROMPT_BASE_ANTIGO)
    c2 = build_context(Paths(tmp_path / "d"), skill_check=lambda: True)
    assert c2.dao.config()["prompt_base"] == prompts.PROMPT_BASE_PADRAO
    c2.dao.salvar_config(prompt_base="meu prompt")
    c3 = build_context(Paths(tmp_path / "d"), skill_check=lambda: True)
    assert c3.dao.config()["prompt_base"] == "meu prompt"
