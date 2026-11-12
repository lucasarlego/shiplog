from shiplog.services import prompts, schemas
from shiplog.services.metadata import Metadados


def _ctx(**kw):
    md = Metadados(readme="# App", readme_arquivo="README.md", arvore=["src/", "src/app.py"],
                   dependencias={"pyproject.toml": "[project]"}, linguagens=[("Python", 100.0)],
                   commits=[{"hash": "abc", "data": "2026-01-01", "mensagem": "feat: x"}])
    base = dict(nome="app", url="https://github.com/me/app", branch="main", commit="abc123", notas="fiz para um cliente",
                metadados=md, prompt_base="BASE PERSONALIZADA", perfil_voz="escrevo direto",
                parametros={"tom": "storytelling", "tamanho": "curto", "idioma": "en"})
    base.update(kw)
    return prompts.ContextoPrompt(**base)


def test_prompt_post_contem_contexto():
    p = prompts.montar_prompt_post(_ctx(), schemas.json_schema("post"))
    for trecho in ("BASE PERSONALIZADA", "escrevo direto", "fiz para um cliente", "Storytelling", "Curto",
                   "Inglês", "src/app.py", "pyproject.toml", "feat: x", "Read, Grep e Glob", "hooks_alternativos"):
        assert trecho in p, trecho
    assert "Regeneração" not in p


def test_prompt_regeneracao():
    p = prompts.montar_prompt_post(_ctx(instrucoes_extras="menos formal",
                                        versao_anterior={"texto": "TEXTO ANTIGO", "hashtags": ["#a"]}),
                                   schemas.json_schema("post"))
    assert "TEXTO ANTIGO" in p and "menos formal" in p


def test_prompt_link_artigo():
    p = prompts.montar_prompt_post(_ctx(link_artigo="https://medium.com/@me/x", titulo_artigo="Meu artigo"),
                                   schemas.json_schema("post"))
    assert "https://medium.com/@me/x" in p


def test_prompt_artigo_usa_skill():
    p = prompts.montar_prompt_artigo(_ctx(parametros={"idioma": "pt", "publico": "avancado", "formato": "tutorial"}),
                                     schemas.json_schema("artigo"))
    assert "medium-article-writer" in p and "PROIBIDO inventar" in p and "trechos_de_codigo" in p
    assert "Avançado" in p and "Tutorial" in p


def test_prompt_correcao():
    p = prompts.montar_prompt_correcao(schemas.json_schema("post"), '{"post": 1}', ["post: erro"])
    assert "post: erro" in p and '{"post": 1}' in p
