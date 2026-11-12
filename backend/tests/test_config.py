import json
import logging

from shiplog import config
from shiplog.config import Paths, redact, setup_logging


def test_data_dir_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SHIPLOG_DATA_DIR", str(tmp_path / "x"))
    d = config.resolve_data_dir()
    assert d == (tmp_path / "x").resolve()
    p = Paths(d).ensure()
    assert p.repos.is_dir() and p.logs.is_dir() and p.db.parent == d


def test_data_dir_pointer(monkeypatch, tmp_path):
    monkeypatch.delenv("SHIPLOG_DATA_DIR", raising=False)
    monkeypatch.setattr(config.Path, "home", lambda: tmp_path)
    assert config.resolve_data_dir() == tmp_path / ".shiplog"
    config.write_pointer(str(tmp_path / "outra"))
    assert json.loads((tmp_path / ".shiplog" / "location.json").read_text())["data_dir"]
    assert config.resolve_data_dir() == (tmp_path / "outra").resolve()


def test_log_redaction(tmp_path):
    assert "sk-ant-abc" not in redact("chave sk-ant-abc123XYZ")
    assert "senha" not in redact("clone https://user:senha@github.com/a/b")
    paths = Paths(tmp_path).ensure()
    setup_logging(paths)
    logging.getLogger("shiplog.t").info("token=%s url=%s", "ghp_abcdefghij1234", "https://u:p@host/x")
    for h in logging.getLogger("shiplog").handlers:
        h.flush()
    txt = (paths.logs / "shiplog.log").read_text()
    assert "ghp_abcdefghij1234" not in txt and "u:p@" not in txt


def test_host_fixo():
    assert config.HOST == "127.0.0.1"
