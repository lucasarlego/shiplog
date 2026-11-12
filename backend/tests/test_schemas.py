from conftest import POST_OK
from shiplog.services import schemas


def test_post_valido_normaliza_hashtags():
    d, erros = schemas.validar("post", POST_OK)
    assert not erros and d["hashtags"] == ["#Python", "#FastAPI", "#OpenSource"]


def test_post_invalido():
    _, erros = schemas.validar("post", {**POST_OK, "hooks_alternativos": ["só um"], "hashtags": ["#a"]})
    assert any("hooks_alternativos" in e for e in erros) and any("hashtags" in e for e in erros)
    assert schemas.validar("post", "texto")[1]


def _artigo(trechos):
    return {"titulo": "Título bom", "subtitulo": "Sub bom aqui", "corpo_markdown": "x" * 300, "tags": ["Python"],
            "trechos_de_codigo": trechos, "sugestoes_de_imagens": []}


def test_artigo_trechos_reais(remote_repo):
    d, erros = schemas.validar("artigo", _artigo([{"arquivo": "./src/app.py", "linhas": "10-20"}]), remote_repo)
    assert not erros and d


def test_artigo_arquivo_inventado(remote_repo):
    _, erros = schemas.validar("artigo", _artigo([{"arquivo": "src/inventado.py", "linhas": "1-2"}]), remote_repo)
    assert erros and "não existe" in erros[0]
    _, erros = schemas.validar("artigo", _artigo([{"arquivo": "src/app.py", "linhas": "40-90"}]), remote_repo)
    assert erros and "fora do arquivo" in erros[0]
    _, erros = schemas.validar("artigo", _artigo([{"arquivo": "../../etc/passwd", "linhas": "1"}]), remote_repo)
    assert erros


def test_artigo_max_tags():
    _, erros = schemas.validar("artigo", {**_artigo([{"arquivo": "a", "linhas": "1"}]), "tags": list("abcdef")})
    assert any("tags" in e for e in erros)
