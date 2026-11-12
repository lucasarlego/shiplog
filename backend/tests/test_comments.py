"""Spec 008 — sugestões de comentário."""

import base64

import pytest
from fastapi.testclient import TestClient

from shiplog.app import create_app

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
RESPOSTA = {
    "resumo_post": "A autora conta como reduziu o custo do data warehouse.",
    "sugestoes": [
        {"abordagem": "Experiência parecida", "texto": "Passei por algo parecido com particionamento por data."},
        {"abordagem": "Pergunta", "texto": "Como vocês mediram o impacto antes de mudar?"},
        {"abordagem": "Complemento", "texto": "Clustering junto do particionamento costuma ajudar ainda mais."},
    ],
}


@pytest.fixture
def client(ctx):
    with TestClient(create_app(ctx)) as c:
        yield c


def img(nome="print.png", dados=PNG):
    return {"nome": nome, "conteudo_base64": base64.b64encode(dados).decode()}


def test_criar_com_imagem_e_gerar(client, ctx, fake_cli):
    fake_cli.set([{"structured": RESPOSTA}])
    r = client.post("/api/comments", json={"autor": "Ana", "texto_post": "Reduzimos 40% do custo.", "imagens": [img()]})
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["imagens"] == ["imagem-1.png"] and c["sugestoes"] == []
    assert client.get(f"/api/comments/{c['id']}/images/imagem-1.png").content == PNG

    r = client.post(f"/api/comments/{c['id']}/generate", json={"parametros": {"objetivo": "perguntar"}})
    assert r.status_code == 200, r.text
    g = r.json()
    assert len(g["sugestoes"]) == 3 and g["resumo_post"] and g["gerado_em"] and g["parametros"]["objetivo"] == "perguntar"
    call = fake_cli.calls()[0]
    argv = call["argv"]
    assert argv[argv.index("--tools") + 1] == "Read"
    assert call["cwd"].endswith(f"comentarios/{c['id']}")
    assert "imagem-1.png" in call["stdin"] and "Reduzimos 40%" in call["stdin"] and "Ana" in call["stdin"]
    assert "pergunta interessante" in call["stdin"]


def test_sem_imagem_nao_tem_ferramentas_e_usa_perfil(client, ctx, fake_cli):
    fake_cli.set([{"structured": RESPOSTA}])
    ctx.dao.salvar_config(perfil_profissional="O autor é engenheiro de dados sênior.")
    cid = client.post("/api/comments", json={"texto_post": "Um post sobre dbt."}).json()["id"]
    assert client.post(f"/api/comments/{cid}/generate", json={}).status_code == 200
    call = fake_cli.calls()[0]
    assert call["argv"][call["argv"].index("--tools") + 1] == ""
    assert "engenheiro de dados sênior" in call["stdin"]


def test_regerar_com_instrucoes_inclui_anteriores(client, fake_cli):
    fake_cli.set([{"structured": RESPOSTA}])
    cid = client.post("/api/comments", json={"texto_post": "Post"}).json()["id"]
    client.post(f"/api/comments/{cid}/generate", json={})
    client.post(f"/api/comments/{cid}/generate", json={"instrucoes": "mencione que uso BigQuery"})
    stdin = fake_cli.calls()[-1]["stdin"]
    assert "mencione que uso BigQuery" in stdin and "Clustering junto" in stdin


def test_validacoes(client):
    assert client.post("/api/comments", json={}).status_code == 422
    assert client.post("/api/comments", json={"imagens": [img("a.exe")]}).status_code == 422
    assert client.post("/api/comments", json={"imagens": [img("a.png", b"nao e png")]}).status_code == 422
    cid = client.post("/api/comments", json={"texto_post": "x"}).json()["id"]
    r = client.post(f"/api/comments/{cid}/generate", json={"parametros": {"objetivo": "xingar"}})
    assert r.status_code == 422
    assert client.get(f"/api/comments/{cid}/images/shiplog.db").status_code == 404
    assert client.get(f"/api/comments/{cid}/images/..%2F..%2Fshiplog.db").status_code == 404


def test_resposta_invalida_registra_erro(client, fake_cli):
    fake_cli.set([{"structured": {"resumo_post": "x", "sugestoes": []}}])
    cid = client.post("/api/comments", json={"texto_post": "Post"}).json()["id"]
    r = client.post(f"/api/comments/{cid}/generate", json={})
    assert r.status_code == 422 and r.json()["erro"]["codigo"] == "schema_invalido"
    assert client.get(f"/api/comments/{cid}").json()["erro"]


def test_listar_e_excluir(client, ctx):
    a = client.post("/api/comments", json={"texto_post": "A", "imagens": [img()]}).json()["id"]
    client.post("/api/comments", json={"texto_post": "B"})
    assert [c["texto_post"] for c in client.get("/api/comments").json()] == ["B", "A"]
    assert client.delete(f"/api/comments/{a}").status_code == 204
    assert not (ctx.paths.data_dir / "comentarios" / str(a)).exists()
    assert len(client.get("/api/comments").json()) == 1
