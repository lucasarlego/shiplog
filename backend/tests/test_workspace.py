"""Spec 009 — leitura do estado da pasta local (só git de leitura)."""

from pathlib import Path

import pytest

from shiplog.errors import AppError
from shiplog.services import workspace

from conftest import git


def _repo(tmp_path: Path, nome: str = "proj", origin: str | None = None) -> Path:
    r = tmp_path / nome
    r.mkdir()
    git("init", "-q", "-b", "main", cwd=r)
    (r / "README.md").write_text("# Proj\n")
    git("add", "-A", cwd=r)
    git("commit", "-qm", "primeiro", cwd=r)
    if origin:
        git("remote", "add", "origin", origin, cwd=r)
    return r


def test_resolver_com_origin_tira_credenciais(tmp_path):
    r = _repo(tmp_path, origin="https://usuario:segredo@github.com/a/b.git")
    (r / "sub").mkdir()
    p = workspace.resolver(str(r / "sub"))
    assert p.git and p.caminho == str(r.resolve()) and p.branch == "main"
    assert p.origin == "https://github.com/a/b.git" and len(p.head) == 40


def test_resolver_sem_git_e_caminhos_invalidos(tmp_path):
    d = tmp_path / "solta"
    d.mkdir()
    p = workspace.resolver(str(d))
    assert not p.git and p.origin is None and p.nome == "solta"
    m = workspace.material(p, None)
    assert m.commits == [] and any("não é um repositório git" in a for a in m.avisos)
    for ruim in ("", "relativo/pasta", str(tmp_path / "nao-existe")):
        with pytest.raises(AppError):
            workspace.resolver(ruim)


def test_material_desde_referencia_e_nao_commitados(tmp_path):
    r = _repo(tmp_path)
    base = git("rev-parse", "HEAD", cwd=r)
    for i in range(3):
        (r / f"f{i}.py").write_text(f"x = {i}\n")
        git("add", "-A", cwd=r)
        git("commit", "-qm", f"feat {i}", cwd=r)
    (r / "pendente.py").write_text("y = 1\n")
    m = workspace.material(workspace.resolver(str(r)), base)
    assert [c["mensagem"] for c in m.commits] == ["feat 2", "feat 1", "feat 0"]
    assert "f0.py" in m.diffstat and m.nao_commitados == ["pendente.py"] and m.desde_encontrado


def test_referencia_inexistente_usa_ultimos(tmp_path):
    r = _repo(tmp_path)
    m = workspace.material(workspace.resolver(str(r)), "0" * 40)
    assert not m.desde_encontrado and len(m.commits) == 1 and m.avisos


def test_nada_mudou_e_truncamento(tmp_path, monkeypatch):
    r = _repo(tmp_path)
    head = git("rev-parse", "HEAD", cwd=r)
    m = workspace.material(workspace.resolver(str(r)), head)
    assert m.commits == [] and any("Nada mudou" in a for a in m.avisos)
    monkeypatch.setattr(workspace, "MAX_COMMITS", 2)
    for i in range(4):
        git("commit", "-q", "--allow-empty", "-m", f"c{i}", cwd=r)
    m = workspace.material(workspace.resolver(str(r)), head)
    assert len(m.commits) == 2 and m.truncado


def test_leitura_nao_altera_a_pasta(tmp_path):
    r = _repo(tmp_path)
    (r / "sujo.txt").write_text("a")
    antes = git("status", "--porcelain", cwd=r), git("rev-parse", "HEAD", cwd=r)
    workspace.material(workspace.resolver(str(r)), None)
    assert (git("status", "--porcelain", cwd=r), git("rev-parse", "HEAD", cwd=r)) == antes
