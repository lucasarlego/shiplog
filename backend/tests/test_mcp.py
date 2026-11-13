"""Spec 009 — servidor MCP: cliente MCP em memória → httpx ASGITransport → API real (sem porta, sem CLI)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from mcp import Client

from shiplog.app import create_app
from shiplog.mcp.client import ShiplogClient
from shiplog.mcp.server import criar_servidor

from conftest import git

pytestmark = pytest.mark.anyio

TEXTO = ("Hoje fechei a integração do Shiplog com o Claude Code: o post nasce durante o desenvolvimento, "
         "a partir dos commits do dia, e vai direto para o painel como rascunho.")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mcp_srv(ctx):
    api = ShiplogClient(base="http://testserver", transport=httpx.ASGITransport(app=create_app(ctx)))
    return criar_servidor(api)


def _dados(r):
    assert not r.is_error, r.content[0].text
    return r.structured_content if r.structured_content is not None else json.loads(r.content[0].text)


def _pasta(tmp_path: Path, origin: str | None = None) -> Path:
    r = tmp_path / "meu-projeto"
    r.mkdir()
    git("init", "-q", "-b", "main", cwd=r)
    (r / "README.md").write_text("# Meu projeto\n")
    (r / "app.py").write_text("\n".join(f"valor_{i} = {i}" for i in range(1, 21)) + "\n")
    git("add", "-A", cwd=r)
    git("commit", "-qm", "primeiro", cwd=r)
    if origin:
        git("remote", "add", "origin", origin, cwd=r)
    return r


async def test_tools_e_anotacoes(mcp_srv):
    async with Client(mcp_srv) as c:
        tools = {t.name: t for t in (await c.list_tools()).tools}
    assert {"projeto_atual", "contexto_post", "salvar_post", "salvar_artigo", "salvar_comentario",
            "marcar_status", "marcar_comentario_usado", "listar", "obter", "shiplog_status"} <= set(tools)
    for nome in ("contexto_post", "contexto_artigo", "contexto_comentario", "listar", "obter"):
        assert tools[nome].annotations.read_only_hint
    assert not any("exclu" in n or "delete" in n or "publicar" in n for n in tools)
    assert all(t.annotations.destructive_hint is False for t in tools.values())


async def test_fluxo_post_local(mcp_srv, ctx, tmp_path, fake_cli):
    pasta = _pasta(tmp_path)
    async with Client(mcp_srv) as c:
        p = _dados(await c.call_tool("projeto_atual", {"caminho": str(pasta)}))
        assert p["origem"] == "local" and p["criado"] and p["caminho_local"] == str(pasta.resolve())
        head = p["pasta"]["head"]

        cx = _dados(await c.call_tool("contexto_post", {"caminho": str(pasta), "tom": "aprendizado"}))
        assert cx["parametros"]["tom"] == "aprendizado" and cx["material"]["head"] == head
        assert [x["mensagem"] for x in cx["material"]["commits"]] == ["primeiro"]
        assert cx["regras"] and "texto" in cx["formato_salvar_post"]["properties"]

        s = _dados(await c.call_tool("salvar_post", {
            "projeto_id": p["id"], "texto": TEXTO, "hashtags": ["Python", "#MCP", "#ClaudeCode"],
            "commit_referencia": head}))
        v = s["versao"]
        assert v["status"] == "rascunho" and v["fonte"] == "claude_code" and v["commit_referencia"] == head
        assert v["hashtags"][0] == "#Python" and s["link_shiplog"].endswith(f"/projetos/{p['id']}")

        # Novo commit: o próximo contexto parte do HEAD salvo.
        (pasta / "novo.py").write_text("z = 1\n")
        git("add", "-A", cwd=pasta)
        git("commit", "-qm", "feat: novo", cwd=pasta)
        cx2 = _dados(await c.call_tool("contexto_post", {"caminho": str(pasta)}))
        assert [x["mensagem"] for x in cx2["material"]["commits"]] == ["feat: novo"]
        assert cx2["ultimo_post"]["id"] == v["id"]

        st = _dados(await c.call_tool("marcar_status", {"tipo": "post", "versao_id": v["id"], "status": "publicado",
                                                        "link": "https://www.linkedin.com/posts/x"}))
        assert st["status"] == "publicado"
        lst = _dados(await c.call_tool("listar", {"tipo": "posts", "projeto_id": p["id"]}))
        assert len(lst["itens"]) == 1

        # O mesmo caminho não duplica o projeto.
        p2 = _dados(await c.call_tool("projeto_atual", {"caminho": str(pasta)}))
        assert p2["id"] == p["id"] and not p2["criado"]
    assert fake_cli.calls() == []  # nenhum modelo chamado pelo Shiplog
    assert git("status", "--porcelain", cwd=pasta) == ""  # pasta intocada


async def test_validacao_de_post_vira_erro_de_ferramenta(mcp_srv, tmp_path):
    pasta = _pasta(tmp_path)
    async with Client(mcp_srv) as c:
        r = await c.call_tool("salvar_post", {"caminho": str(pasta), "texto": "x" * 3001,
                                              "hashtags": ["#a", "#b", "#c"]})
        assert r.is_error and "3000" in r.content[0].text
        r = await c.call_tool("salvar_post", {"caminho": str(pasta), "texto": TEXTO, "hashtags": ["#a"]})
        assert r.is_error


async def test_post_sem_projeto_por_descricao(mcp_srv, fake_cli):
    desc = "Esta semana conduzi um workshop interno sobre revisão de código com o time."
    async with Client(mcp_srv) as c:
        cx = _dados(await c.call_tool("contexto_post", {"descricao": desc}))
        assert cx["material"]["tipo"] == "descricao" and cx["projeto"] is None
        s = _dados(await c.call_tool("salvar_post", {"descricao": desc, "texto": TEXTO,
                                                     "hashtags": ["#a", "#b", "#c"]}))
        proj = _dados(await c.call_tool("obter", {"tipo": "projeto", "id": s["projeto_id"]}))
        assert proj["origem"] == "livre"
        r = await c.call_tool("contexto_artigo", {"projeto_id": s["projeto_id"]})
        assert r.is_error
    assert fake_cli.calls() == []


async def test_artigo_confere_trechos(mcp_srv, tmp_path):
    pasta = _pasta(tmp_path)
    base = {"caminho": str(pasta), "titulo": "Como fiz", "subtitulo": "Um relato",
            "corpo_markdown": "## Intro\n\n```python\nvalor_1 = 1\n```\n" + "Texto. " * 80, "tags": ["python"]}
    async with Client(mcp_srv) as c:
        cx = _dados(await c.call_tool("contexto_artigo", {"caminho": str(pasta)}))
        assert "trechos_de_codigo" in cx["formato_salvar_artigo"]["properties"]
        r = await c.call_tool("salvar_artigo", {**base, "trechos_de_codigo": [{"arquivo": "nao_existe.py",
                                                                               "linhas": "1-3"}]})
        assert r.is_error
        s = _dados(await c.call_tool("salvar_artigo", {**base, "trechos_de_codigo": [{"arquivo": "app.py",
                                                                                      "linhas": "1-5"}]}))
        assert s["versao"]["fonte"] == "claude_code" and s["versao"]["status"] == "rascunho"


async def test_comentario_medium_e_usado(mcp_srv, tmp_path, fake_cli):
    png = tmp_path / "print.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    async with Client(mcp_srv) as c:
        cx = _dados(await c.call_tool("contexto_comentario", {"plataforma": "medium", "objetivo": "perguntar"}))
        assert cx["plataforma"] == "medium" and cx["regras"]
        s = _dados(await c.call_tool("salvar_comentario", {
            "plataforma": "medium", "texto_original": "Um artigo sobre filas.", "resumo": "Sobre filas.",
            "sugestoes": [{"abordagem": "Pergunta", "texto": "Como vocês lidaram com reprocessamento?"},
                          {"abordagem": "Complemento", "texto": "Idempotência ajuda muito aqui."}],
            "caminhos_imagens": [str(png)]}))
        assert s["plataforma"] == "medium" and s["status"] == "sugerido" and s["fonte"] == "claude_code"
        assert s["imagens"] and s["link_shiplog"].endswith(f"/comentarios/{s['id']}")
        u = _dados(await c.call_tool("marcar_comentario_usado", {"comentario_id": s["id"], "indice": 1,
                                                                 "link": "https://medium.com/x"}))
        assert u["status"] == "usado" and u["escolhido"] == 1
        r = await c.call_tool("salvar_comentario", {"sugestoes": [{"texto": "oi"}],
                                                    "caminhos_imagens": ["/nao/existe.png"]})
        assert r.is_error
    assert fake_cli.calls() == []


async def test_resources_e_prompts(mcp_srv, ctx):
    ctx.dao.salvar_config(perfil_profissional="Engenheiro de dados sênior.")
    async with Client(mcp_srv) as c:
        perfil = (await c.read_resource("shiplog://perfil")).contents[0].text
        assert "Engenheiro de dados" in perfil
        cfg = json.loads((await c.read_resource("shiplog://config/escrita")).contents[0].text)
        assert "parametros_padrao_post" in cfg
        msg = (await c.get_prompt("post_do_projeto", {"foco": "testes"})).messages[0].content.text
        assert "contexto_post" in msg and "testes" in msg


async def test_servidor_fora_do_ar_da_erro_claro():
    api = ShiplogClient(base="http://127.0.0.1:9", iniciar_servidor=False)
    async with Client(criar_servidor(api)) as c:
        r = await c.call_tool("listar", {"tipo": "projetos"})
    assert r.is_error and "Shiplog" in r.content[0].text


def test_migracao_0005_preserva_dados(tmp_path, monkeypatch):
    import shutil
    import sqlite3

    from shiplog.config import Paths
    from shiplog.context import build_context
    from shiplog.storage import db as dbmod

    ate4 = tmp_path / "mig"
    ate4.mkdir()
    for f in sorted(dbmod.MIGRATIONS_DIR.glob("000[1-4]_*.sql")):
        shutil.copy(f, ate4)
    path = tmp_path / "data" / "shiplog.db"
    path.parent.mkdir()
    conn = dbmod.connect(path)
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", ate4)
    assert dbmod.migrate(conn) == [1, 2, 3, 4]
    t = "2026-01-01T00:00:00Z"
    conn.execute("INSERT INTO projetos (id, origem, nome, url_repo, url_normalizada, caminho_local, criado_em) "
                 "VALUES (1, 'repo', 'app', 'https://github.com/a/b', 'github.com/a/b', '/x', ?)", (t,))
    conn.execute("INSERT INTO geracoes (id, projeto_id, tipo, status, commit_hash, criado_em) "
                 "VALUES (1, 1, 'post', 'concluido', 'abc', ?)", (t,))
    conn.execute("INSERT INTO posts (projeto_id, geracao_id, versao, texto, criado_em) VALUES (1, 1, 1, 'olá', ?)", (t,))
    conn.execute("INSERT INTO comentarios (id, texto_post, criado_em) VALUES (1, 'post', ?)", (t,))
    conn.commit()
    conn.close()
    monkeypatch.undo()

    c = build_context(Paths(tmp_path / "data"), skill_check=lambda: True)
    raw = sqlite3.connect(path)
    assert raw.execute("SELECT fonte, commit_referencia FROM posts").fetchone() == ("shiplog", None)
    assert raw.execute("SELECT plataforma, status, fonte FROM comentarios").fetchone() == ("linkedin", "sugerido",
                                                                                           "shiplog")
    assert raw.execute("PRAGMA foreign_key_check").fetchall() == []
    assert c.dao.ultimo_commit_gerado(1) == "abc"


def test_geracao_recusada_para_projeto_local(ctx, tmp_path):
    from fastapi.testclient import TestClient

    pasta = _pasta(tmp_path)
    p = ctx.projects.projeto_atual(str(pasta))
    with TestClient(create_app(ctx)) as cl:
        r = cl.post(f"/api/projects/{p['id']}/generations", json={"tipo": "post"})
    assert r.status_code == 409 and r.json()["erro"]["codigo"] == "projeto_local_sem_geracao"
