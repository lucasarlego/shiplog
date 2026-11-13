import threading
import time

from conftest import POST_OK, wait_job


def _projeto(ctx, remote_repo):
    return ctx.projects.cadastrar(remote_repo.as_uri())["id"]


def _run(ctx, gid):
    ctx.generation.executar(gid, threading.Event())
    return ctx.dao.geracao(gid)


def test_sucesso(ctx, remote_repo, fake_cli):
    pid = _projeto(ctx, remote_repo)
    job = ctx.generation.criar(pid, "post", {"tom": "aprendizado"})
    g = _run(ctx, job["id"])
    assert g["status"] == "concluido", g
    assert g["commit_hash"] and g["prompt"] and g["resposta_bruta"] and g["tentativas"] == 1 and g["codigo_saida"] == 0
    post = ctx.dao.versao("posts", g["resultado_id"])
    assert post["versao"] == 1 and post["hashtags"][1] == "#FastAPI" and post["status"] == "rascunho"
    assert ctx.projects.detalhe(pid)["ultima_analise_em"]
    call = fake_cli.calls()[0]
    assert "Aprendizado" in call["stdin"] and call["cwd"].endswith(f"{pid}-meu-app")


def test_correcao(ctx, remote_repo, fake_cli):
    fake_cli.set([{"structured": {"post": "curto"}}, {"structured": POST_OK}])
    pid = _projeto(ctx, remote_repo)
    g = _run(ctx, ctx.generation.criar(pid, "post")["id"])
    assert g["status"] == "concluido" and g["tentativas"] == 2 and "correcao_aplicada" in g["avisos"]
    segunda = fake_cli.calls()[1]
    assert segunda["argv"][segunda["argv"].index("--tools") + 1] == ""
    assert "não seguiu o formato" in segunda["stdin"]


def test_correcao_falha(ctx, remote_repo, fake_cli):
    fake_cli.set([{"result": "não sei"}, {"result": "ainda não"}])
    pid = _projeto(ctx, remote_repo)
    g = _run(ctx, ctx.generation.criar(pid, "post")["id"])
    assert g["status"] == "erro" and g["erro_codigo"] == "schema_invalido"
    assert "não sei" in g["resposta_bruta"] and "ainda não" in g["resposta_bruta"]


def test_regeneracao_mantem_versoes(ctx, remote_repo, fake_cli):
    pid = _projeto(ctx, remote_repo)
    g1 = _run(ctx, ctx.generation.criar(pid, "post")["id"])
    g2 = _run(ctx, ctx.generation.criar(pid, "post", None, "menos formal", g1["resultado_id"])["id"])
    assert [v["versao"] for v in ctx.versions.listar("post", pid)] == [2, 1]
    assert "menos formal" in fake_cli.calls()[-1]["stdin"]
    assert ctx.dao.versao("posts", g2["resultado_id"])["origem_id"] == g1["resultado_id"]


def test_repo_alterado(ctx, remote_repo, fake_cli):
    fake_cli.set([{"write": "hack.txt", "structured": POST_OK}])
    pid = _projeto(ctx, remote_repo)
    g = _run(ctx, ctx.generation.criar(pid, "post")["id"])
    assert "repo_alterado" in g["avisos"]
    from shiplog.services import repo
    assert repo.alteracoes(__import__("pathlib").Path(ctx.projects.obter(pid)["caminho_local"])) == []


def test_cancelamento_na_fila_e_em_execucao(ctx, remote_repo, fake_cli):
    fake_cli.set([{"sleep": 30}])
    pid = _projeto(ctx, remote_repo)
    ctx.jobs.start()
    try:
        j1 = ctx.generation.criar(pid, "post")
        j2 = ctx.generation.criar(pid, "post")
        assert ctx.generation.job(j2["id"])["posicao_fila"] == 1
        ctx.jobs.cancelar(j2["id"])
        fim = time.time() + 10
        while ctx.dao.geracao(j1["id"])["status"] != "gerando" and time.time() < fim:
            time.sleep(0.05)
        ctx.jobs.cancelar(j1["id"])
        assert wait_job(ctx, j1["id"])["status"] == "cancelado"
        assert ctx.dao.geracao(j2["id"])["status"] == "cancelado"
        assert len(fake_cli.calls()) <= 1
    finally:
        ctx.jobs.stop()


def test_artigo(ctx, remote_repo, fake_cli):
    art = {"titulo": "Como fiz", "subtitulo": "Um caso real", "corpo_markdown": "## Intro\n" + "texto " * 60,
           "tags": ["Python"], "trechos_de_codigo": [{"arquivo": "src/app.py", "linhas": "1-5"}],
           "sugestoes_de_imagens": ["diagrama"]}
    fake_cli.set([{"structured": art}])
    pid = _projeto(ctx, remote_repo)
    g = _run(ctx, ctx.generation.criar(pid, "artigo", {"formato": "tutorial"})["id"])
    assert g["status"] == "concluido", g
    call = fake_cli.calls()[0]
    assert "Skill" in call["argv"][call["argv"].index("--tools") + 1] and "medium-article-writer" in call["stdin"]
    v = ctx.dao.versao("artigos", g["resultado_id"])
    assert v["titulo"] == "Como fiz" and v["parametros"]["formato"] == "tutorial"  # a versão guarda os parâmetros


def test_limite_de_uso_e_retry(ctx, remote_repo, fake_cli):
    fake_cli.set([{"error": "usage limit reached"}, {"structured": POST_OK}])
    pid = _projeto(ctx, remote_repo)
    j = ctx.generation.criar(pid, "post", {"tom": "conquista", "idioma": "en"})
    g = _run(ctx, j["id"])
    assert g["erro_codigo"] == "limite_uso" and g["acao_sugerida"]
    j2 = ctx.generation.retry(j["id"])
    assert j2["parametros"]["tom"] == "conquista" and j2["parametros"]["idioma"] == "en"
    assert _run(ctx, j2["id"])["status"] == "concluido"
