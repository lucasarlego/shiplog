from pathlib import Path

import pytest

from conftest import git
from shiplog.errors import AppError
from shiplog.services import metadata
from shiplog.services import repo as r


def test_classifica_erro_git():
    assert r.classificar_erro("fatal: Authentication failed for 'https://x'").codigo == "repo_auth"
    assert r.classificar_erro("git@github.com: Permission denied (publickey).").codigo == "repo_auth"
    assert r.classificar_erro("fatal: repository 'https://x/y' not found").codigo == "repo_inacessivel"
    assert r.classificar_erro("algo estranho").codigo == "git_falha"


def test_ls_remote_inexistente(tmp_path):
    with pytest.raises(AppError) as e:
        r.ls_remote((tmp_path / "nada").as_uri())
    assert e.value.codigo in ("repo_inacessivel", "git_falha")


def test_branch_inexistente(remote_repo):
    with pytest.raises(AppError) as e:
        r.ls_remote(remote_repo.as_uri(), "nao-existe")
    assert e.value.codigo == "branch_inexistente"


def test_clone_e_atualizacao(remote_repo, tmp_path):
    dest = tmp_path / "data" / "repos" / "1-app"
    h1 = r.garantir_clone(remote_repo.as_uri(), dest, None, atualizar=True)
    assert h1 == git("rev-parse", "HEAD", cwd=remote_repo)
    (remote_repo / "novo.txt").write_text("x")
    git("add", "-A", cwd=remote_repo)
    git("commit", "-qm", "novo", cwd=remote_repo)
    h2 = r.garantir_clone(remote_repo.as_uri(), dest, None, atualizar=True)
    assert h2 == git("rev-parse", "HEAD", cwd=remote_repo) != h1
    assert r.alteracoes(dest) == []


def test_metadados(remote_repo, tmp_path):
    dest = tmp_path / "c"
    r.garantir_clone(remote_repo.as_uri(), dest, None, atualizar=False)
    md = metadata.coletar(dest)
    assert md.readme and "Meu App" in md.readme
    assert "pyproject.toml" in md.dependencias
    assert not any("node_modules" in p for p in md.arvore)
    assert md.linguagens[0][0] == "Python"
    assert [c["mensagem"] for c in md.commits][:2] == ["feat: util de soma", "feat: primeira versão"]
    assert not md.parcial


def test_metadados_parcial(remote_repo):
    md = metadata.coletar(remote_repo, metadata.Limites(max_arquivos=2))
    assert md.parcial


def test_remover_fora_da_raiz(tmp_path):
    with pytest.raises(AppError):
        r.remover(tmp_path / "x", tmp_path / "data")


def test_alteracao_detectada_e_restaurada(remote_repo, tmp_path):
    dest = tmp_path / "c"
    r.garantir_clone(remote_repo.as_uri(), dest, None, atualizar=False)
    (dest / "README.md").write_text("mudou")
    (dest / "novo.txt").write_text("x")
    assert len(r.alteracoes(dest)) == 2
    r.restaurar(dest)
    assert r.alteracoes(dest) == []
