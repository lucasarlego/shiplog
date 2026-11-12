import threading
import time

from conftest import POST_OK
from shiplog.services.llm.base import LLMRequest
from shiplog.services.llm.claude_cli import ClaudeCliProvider, build_command, extrair_json
from shiplog.services import schemas


def _req(tmp_path, **kw):
    base = dict(prompt="oi", cwd=tmp_path, tools=["Read", "Grep", "Glob"], json_schema=schemas.json_schema("post"),
                timeout_s=20)
    base.update(kw)
    return LLMRequest(**base)


def test_comando_post_e_artigo(tmp_path):
    post = build_command("claude", _req(tmp_path))
    assert post[:4] == ["claude", "-p", "--output-format", "json"]
    assert post[post.index("--tools") + 1] == "Read,Grep,Glob"
    dis = post[post.index("--disallowedTools") + 1:]
    assert {"Bash", "Edit", "Write"} <= set(dis)
    assert "dontAsk" in post and "--strict-mcp-config" in post and "--json-schema" in post
    assert "Skill" not in post[post.index("--tools") + 1] and "--disable-slash-commands" in post
    art = build_command("claude", _req(tmp_path, allow_skills=True))
    assert art[art.index("--tools") + 1] == "Read,Grep,Glob,Skill"
    assert "--disable-slash-commands" not in art


def test_env_sem_api_key_e_cwd(tmp_path, fake_cli, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-teste")
    r = ClaudeCliProvider(lambda: fake_cli.path).run(_req(tmp_path, prompt="PROMPT VIA STDIN"))
    assert r.ok and r.data == POST_OK
    call = fake_cli.calls()[0]
    assert call["has_api_key"] is False
    assert call["stdin"] == "PROMPT VIA STDIN"
    assert call["cwd"] == str(tmp_path)


def test_timeout_mata_processo(tmp_path, fake_cli):
    fake_cli.set([{"sleep": 30}])
    t = time.time()
    r = ClaudeCliProvider(lambda: fake_cli.path).run(_req(tmp_path, timeout_s=1))
    assert r.error_code == "timeout" and time.time() - t < 10


def test_cancelamento(tmp_path, fake_cli):
    fake_cli.set([{"sleep": 30}])
    ev = threading.Event()
    threading.Timer(0.5, ev.set).start()
    r = ClaudeCliProvider(lambda: fake_cli.path).run(_req(tmp_path), ev)
    assert r.error_code == "cancelado"


def test_limite_de_uso(tmp_path, fake_cli):
    fake_cli.set([{"error": "Claude AI usage limit reached|1760000000"}])
    r = ClaudeCliProvider(lambda: fake_cli.path).run(_req(tmp_path))
    assert not r.ok and r.error_code == "limite_uso" and "usage limit" in r.error_message


def test_nao_autenticado(tmp_path, fake_cli):
    fake_cli.set([{"stderr": "Invalid API key · Please run /login", "exit": 1}])
    r = ClaudeCliProvider(lambda: fake_cli.path).run(_req(tmp_path))
    assert r.error_code == "cli_nao_autenticado"


def test_cli_inexistente(tmp_path):
    r = ClaudeCliProvider(lambda: str(tmp_path / "nao-existe")).run(_req(tmp_path))
    assert r.error_code == "cli_nao_encontrado"


def test_extrair_json():
    assert extrair_json('texto antes ```json\n{"a": 1}\n``` depois') == {"a": 1}
    assert extrair_json('blá {"a": {"b": "}"}} fim') == {"a": {"b": "}"}}
    assert extrair_json("nada") is None
