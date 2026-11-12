import pytest

from shiplog.errors import AppError
from shiplog.services.urls import validar_url


def test_normalizacao_equivalente():
    a = validar_url("git@github.com:Me/App.git")
    b = validar_url("https://github.com/me/app")
    c = validar_url("ssh://git@github.com/me/app.git/")
    assert a.normalizada == b.normalizada == c.normalizada == "github.com/me/app"
    assert a.nome == "App" and a.tipo == "ssh" and b.tipo == "https"


def test_gitlab_subgrupo():
    assert validar_url("https://gitlab.com/g/sub/repo.git").normalizada == "gitlab.com/g/sub/repo"


@pytest.mark.parametrize("url", ["", "ftp://x.com/y/z", "github.com/me", "https://u:p@github.com/me/app",
                                 "https://github.com/", "https://github.com/me", "file:///tmp/x/y"])
def test_urls_invalidas(url):
    with pytest.raises(AppError) as e:
        validar_url(url)
    assert e.value.codigo == "url_invalida"
