"""Spec 007 — perfil profissional a partir do currículo."""

import base64
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from shiplog.app import create_app
from shiplog.services import prompts

PERFIL = ("## Quem é\nO autor é engenheiro de software sênior com foco em backend Python e dados. "
          "Contato: fulano@exemplo.com, (11) 98765-4321.\n## Experiência e domínio\n" + "Plataformas de dados. " * 15)


@pytest.fixture
def client(ctx):
    with TestClient(create_app(ctx)) as c:
        yield c


def b64(dados: bytes) -> str:
    return base64.b64encode(dados).decode()


def docx(texto: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml",
                   '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
                   f"<w:p><w:r><w:t>{texto}</w:t></w:r></w:p></w:body></w:document>")
    return buf.getvalue()


def test_gerar_com_pdf_usa_read_no_diretorio_do_perfil(client, ctx, fake_cli):
    fake_cli.set([{"structured": {"perfil": PERFIL}}])
    r = client.put("/api/profile/curriculo", json={"nome": "CV Fulano.pdf", "conteudo_base64": b64(b"%PDF-1.4 teste")})
    assert r.status_code == 200 and r.json()["curriculo_nome"] == "CV Fulano.pdf"
    r = client.post("/api/profile/generate", json={"sobre": "Hoje lidero um time de plataforma de dados."})
    assert r.status_code == 200, r.text
    cfg = r.json()
    assert cfg["perfil_gerado_em"] and "engenheiro de software sênior" in cfg["perfil_profissional"]
    assert "fulano@exemplo.com" not in cfg["perfil_profissional"] and "98765" not in cfg["perfil_profissional"]
    assert cfg["perfil_sobre"] == "Hoje lidero um time de plataforma de dados."
    call = fake_cli.calls()[0]
    argv = call["argv"]
    assert argv[argv.index("--tools") + 1] == "Read"
    assert call["cwd"].endswith("perfil") and "curriculo.pdf" in call["stdin"]
    assert "lidero um time" in call["stdin"]


def test_docx_vai_como_texto_sem_ferramentas(client, fake_cli):
    fake_cli.set([{"structured": {"perfil": PERFIL}}])
    client.put("/api/profile/curriculo", json={"nome": "cv.docx", "conteudo_base64": b64(docx("Experiência em Kubernetes"))})
    assert client.post("/api/profile/generate", json={}).status_code == 200
    call = fake_cli.calls()[0]
    assert call["argv"][call["argv"].index("--tools") + 1] == ""
    assert "Experiência em Kubernetes" in call["stdin"]


def test_validacoes(client):
    assert client.post("/api/profile/generate", json={"sobre": "curto"}).status_code == 422
    r = client.put("/api/profile/curriculo", json={"nome": "cv.exe", "conteudo_base64": b64(b"x")})
    assert r.status_code == 422 and r.json()["erro"]["codigo"] == "validacao"
    r = client.put("/api/profile/curriculo", json={"nome": "cv.pdf", "conteudo_base64": b64(b"nao e pdf")})
    assert r.status_code == 422


def test_troca_e_remocao_do_curriculo(client, ctx):
    client.put("/api/profile/curriculo", json={"nome": "a.txt", "conteudo_base64": b64(b"texto")})
    client.put("/api/profile/curriculo", json={"nome": "b.md", "conteudo_base64": b64(b"# cv")})
    assert [f.name for f in (ctx.paths.data_dir / "perfil").iterdir()] == ["curriculo.md"]
    r = client.delete("/api/profile/curriculo")
    assert r.json()["curriculo_nome"] == "" and not list((ctx.paths.data_dir / "perfil").iterdir())


def test_perfil_curto_falha(client, fake_cli):
    fake_cli.set([{"structured": {"perfil": "curto"}}])
    r = client.post("/api/profile/generate", json={"sobre": "Sou desenvolvedor há dez anos em fintechs."})
    assert r.status_code == 422 and r.json()["erro"]["codigo"] == "schema_invalido"


def test_perfil_editavel_e_usado_nos_prompts(client):
    r = client.put("/api/settings", json={"perfil_profissional": "O autor é especialista em dados."})
    assert r.json()["perfil_profissional"] == "O autor é especialista em dados."
    ctx = prompts.ContextoPrompt(nome="x", url=None, branch=None, commit=None, notas="", metadados=None,
                                 prompt_base="", perfil_voz="direto", parametros={}, descricao="a" * 30,
                                 perfil_profissional="O autor é especialista em dados.")
    p = prompts.montar_prompt_post(ctx, {"type": "object"})
    assert "Quem é o autor" in p and "especialista em dados" in p and "Perfil de voz" in p
