import time

import pytest
from fastapi.testclient import TestClient

from conftest import wait_job
from shiplog.app import create_app

ARTIGO = {"titulo": "Como fiz", "subtitulo": "Um caso real", "corpo_markdown": "## Intro\n" + "texto " * 60,
          "tags": ["Python"], "trechos_de_codigo": [{"arquivo": "src/app.py", "linhas": "1-5"}],
          "sugestoes_de_imagens": []}


@pytest.fixture
def client(ctx):
    with TestClient(create_app(ctx)) as c:
        yield c


def _criar_e_gerar(client, ctx, remote_repo):
    r = client.post("/api/projects", json={"url": remote_repo.as_uri(), "gerar": True})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["job"]["status"] in ("na_fila", "clonando", "analisando", "gerando", "concluido")
    g = wait_job(ctx, body["job"]["id"])
    assert g["status"] == "concluido", g
    return body["projeto"]["id"], g


def test_criar_projeto_e_gerar(client, ctx, remote_repo):
    pid, g = _criar_e_gerar(client, ctx, remote_repo)
    job = client.get(f"/api/jobs/{g['id']}").json()
    assert job["status"] == "concluido" and job["resultado_id"]
    posts = client.get(f"/api/projects/{pid}/posts").json()
    assert len(posts) == 1 and posts[0]["versao"] == 1 and posts[0]["parametros"]["tom"] == "tecnico"
    lista = client.get("/api/projects").json()
    assert lista[0]["ultimo_post"]["status"] == "rascunho" and lista[0]["ultima_analise_em"]
    assert client.get(f"/api/generations/{g['id']}/debug").json()["prompt"]
    assert client.get("/api/jobs?ativos=true").json() == []


def test_duplicado_e_url_invalida(client, remote_repo):
    assert client.post("/api/projects", json={"url": remote_repo.as_uri(), "gerar": False}).status_code == 201
    r = client.post("/api/projects", json={"url": remote_repo.as_uri(), "gerar": False})
    assert r.status_code == 409 and r.json()["erro"]["codigo"] == "projeto_duplicado"
    r = client.post("/api/projects", json={"url": "ftp://x"})
    assert r.status_code == 422 and r.json()["erro"]["codigo"] == "url_invalida" and r.json()["erro"]["acao_sugerida"]
    assert client.post("/api/projects/validate", json={"url": "https://github.com/a/b"}).json()["nome_sugerido"] == "b"


def test_repo_inexistente(client, tmp_path):
    r = client.post("/api/projects", json={"url": (tmp_path / "nada" / "x").as_uri()})
    assert r.status_code == 422 and r.json()["erro"]["codigo"] in ("repo_inacessivel", "git_falha")


def test_fluxo_versoes_status(client, ctx, remote_repo):
    pid, g = _criar_e_gerar(client, ctx, remote_repo)
    v1 = g["resultado_id"]
    r = client.post(f"/api/projects/{pid}/generations",
                    json={"tipo": "post", "instrucoes_extras": "menos formal", "base_versao_id": v1})
    assert r.status_code == 202
    assert wait_job(ctx, r.json()["id"])["status"] == "concluido"
    v2 = client.get(f"/api/projects/{pid}/posts").json()[0]
    assert v2["versao"] == 2 and v2["instrucoes_extras"] == "menos formal"
    v3 = client.post(f"/api/posts/{v2['id']}/versions", json={"texto": "Editado à mão", "hashtags": ["a", "#b", "#c"]}).json()
    assert v3["versao"] == 3 and v3["editado_manualmente"] and v3["hashtags"] == ["#a", "#b", "#c"]
    pub = client.patch(f"/api/posts/{v3['id']}/status", json={"status": "publicado", "link": "https://www.linkedin.com/posts/x"}).json()
    assert pub["publicado_em"] and pub["link"].startswith("https://www.linkedin.com")
    r = client.patch(f"/api/posts/{v1}/status", json={"status": "publicado"})
    assert r.status_code == 409 and r.json()["erro"]["codigo"] == "conflito_publicado"
    assert len(client.get(f"/api/projects/{pid}/posts").json()) == 3
    assert client.get("/api/projects?status=publicado").json()[0]["id"] == pid
    assert client.get("/api/projects?status=sem_post").json() == []


def test_artigo_export_md_e_link_no_post(client, ctx, remote_repo, fake_cli):
    pid, _ = _criar_e_gerar(client, ctx, remote_repo)
    fake_cli.set([{"structured": ARTIGO}])
    r = client.post(f"/api/projects/{pid}/generations", json={"tipo": "artigo", "parametros": {"publico": "avancado"}})
    g = wait_job(ctx, r.json()["id"])
    assert g["status"] == "concluido", g
    art = client.get(f"/api/projects/{pid}/articles").json()[0]
    md = client.get(f"/api/articles/{art['id']}/export.md")
    assert md.headers["content-type"].startswith("text/markdown") and "attachment" in md.headers["content-disposition"]
    assert md.text.startswith("# Como fiz") and "Um caso real" in md.text
    client.patch(f"/api/articles/{art['id']}/status", json={"status": "publicado", "link": "https://medium.com/@me/como-fiz"})
    assert client.get(f"/api/projects/{pid}").json()["artigo_publicado"]["link"] == "https://medium.com/@me/como-fiz"
    fake_cli.set([{"structured": __import__("conftest").POST_OK}])
    r = client.post(f"/api/projects/{pid}/generations", json={"tipo": "post", "parametros": {"incluir_link_artigo": True}})
    wait_job(ctx, r.json()["id"])
    assert "https://medium.com/@me/como-fiz" in fake_cli.calls()[0]["stdin"]


def test_artigo_sem_skill(client, ctx, remote_repo):
    pid = client.post("/api/projects", json={"url": remote_repo.as_uri(), "gerar": False}).json()["projeto"]["id"]
    time.sleep(0.3)  # deixa terminar a verificação de saúde disparada no boot
    ctx.health._skill_check = lambda: False
    assert ctx.health.get(force=True)["pode_gerar_artigo"] is False
    r = client.post(f"/api/projects/{pid}/generations", json={"tipo": "artigo"})
    assert r.status_code == 409 and r.json()["erro"]["codigo"] == "skill_ausente"


def test_export_json_md(client, ctx, remote_repo):
    _criar_e_gerar(client, ctx, remote_repo)
    j = client.get("/api/export?formato=json").json()
    assert j["projetos"][0]["posts"][0]["versao"] == 1
    md = client.get("/api/export?formato=md")
    assert "# Histórico do Shiplog" in md.text and "Post v1" in md.text


def test_settings(client):
    s = client.get("/api/settings").json()
    assert s["timeout_post_s"] == 300 and s["prompt_base"] and s["pasta_dados"]
    s = client.put("/api/settings", json={"perfil_voz": "direto", "parametros_padrao_post": {"tom": "storytelling"}}).json()
    assert s["perfil_voz"] == "direto" and s["parametros_padrao_post"]["tom"] == "storytelling"
    r = client.put("/api/settings", json={"timeout_post_s": 5})
    assert r.status_code == 422 and r.json()["erro"]["codigo"] == "validacao"


def test_editar_excluir(client, remote_repo, ctx):
    pid, _ = _criar_e_gerar(client, ctx, remote_repo)
    assert client.patch(f"/api/projects/{pid}", json={"notas": "para um cliente", "nome": "App"}).json()["notas"] == "para um cliente"
    assert client.get(f"/api/projects/{pid}").json()["clone_existe"]
    assert client.delete(f"/api/projects/{pid}?manter_historico=true").status_code == 204
    assert client.get("/api/projects").json() == []
    assert client.get("/api/export?formato=json").json()["projetos"][0]["arquivado"] is True
    # URL liberada para recadastro
    assert client.post("/api/projects", json={"url": remote_repo.as_uri(), "gerar": False}).status_code == 201


def test_check_updates(client, ctx, remote_repo):
    from conftest import git
    pid, _ = _criar_e_gerar(client, ctx, remote_repo)
    assert client.post("/api/projects/check-updates", json={}).json()[0]["commits_novos"] is False
    (remote_repo / "x.txt").write_text("x")
    git("add", "-A", cwd=remote_repo)
    git("commit", "-qm", "mais", cwd=remote_repo)
    assert client.post("/api/projects/check-updates", json={}).json()[0]["commits_novos"] is True
    assert client.get("/api/projects?status=commits_novos").json()[0]["id"] == pid


def test_tempo_resposta(client, ctx):
    for i in range(100):
        ctx.dao.criar_projeto(nome=f"p{i}", url_repo="u", url_normalizada=f"h/x/{i}", caminho_local="x")
    t = time.perf_counter()
    assert len(client.get("/api/projects").json()) == 100
    assert time.perf_counter() - t < 0.3


def test_spa_fallback(client, tmp_path, monkeypatch):
    assert "Shiplog" in client.get("/qualquer/rota").text
    assert client.get("/api/nao-existe").status_code == 404
    assert client.get("/api/ping").json()["app"] == "shiplog"


def test_host_estranho_e_recusado(ctx, monkeypatch):
    """DNS rebinding: só 127.0.0.1/localhost são aceitos."""
    monkeypatch.delenv("SHIPLOG_ALLOWED_HOSTS", raising=False)
    with TestClient(create_app(ctx), base_url="http://127.0.0.1:8765") as c:
        assert c.get("/api/ping").status_code == 200
        assert c.get("/api/ping", headers={"host": "localhost:8765"}).status_code == 200
        assert c.get("/api/ping", headers={"host": "evil.example.com"}).status_code == 400
        assert c.get("/api/settings", headers={"host": "evil.example.com:8765"}).status_code == 400
