from shiplog.services.health import HealthService, skill_instalada


def test_cli_ausente(tmp_path):
    h = HealthService(lambda: str(tmp_path / "nao"), lambda: True).get()
    assert not h["cli"]["ok"] and h["cli"]["comando_sugerido"] and not h["pode_gerar_post"]


def test_cli_ok_sem_skill(fake_cli):
    h = HealthService(lambda: fake_cli.path, lambda: False).get()
    assert h["cli"]["ok"] and h["auth"]["ok"] and h["pode_gerar_post"] and not h["pode_gerar_artigo"]


def test_nao_logado(fake_cli, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_LOGGED", "0")
    h = HealthService(lambda: fake_cli.path, lambda: True).get()
    assert not h["auth"]["ok"] and "login" in h["auth"]["comando_sugerido"]


def test_skill_instalada(tmp_path):
    assert not skill_instalada(tmp_path)
    (tmp_path / "skills" / "medium-article-writer").mkdir(parents=True)
    (tmp_path / "skills" / "medium-article-writer" / "SKILL.md").write_text("x")
    assert skill_instalada(tmp_path)
