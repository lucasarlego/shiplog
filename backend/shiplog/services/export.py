"""Exportação do histórico e do artigo (RF-23, RF-30)."""

from __future__ import annotations

import json
from typing import Any

from ..storage.dao import Dao
from ..storage.db import now_iso
from .versions import VersionService

STATUS_LABEL = {"rascunho": "Rascunho", "pronto": "Pronto", "publicado": "Publicado"}


def artigo_markdown(a: dict[str, Any]) -> str:
    partes = [f"# {a['titulo']}", ""]
    if a.get("subtitulo"):
        partes += [f"*{a['subtitulo']}*", ""]
    partes.append(a["corpo_markdown"].strip())
    if a.get("tags"):
        partes += ["", "---", "", "Tags: " + ", ".join(a["tags"])]
    return "\n".join(partes) + "\n"


def historico(dao: Dao, versions: VersionService) -> dict[str, Any]:
    projetos = []
    for p in dao.listar_projetos(incluir_arquivados=True):
        projetos.append({
            "id": p["id"], "origem": p["origem"], "descricao": p["descricao"], "nome": p["nome"],
            "url_repo": p["url_repo"], "branch": p["branch"], "notas": p["notas"],
            "arquivado": p["arquivado"], "criado_em": p["criado_em"], "ultima_analise_em": p["ultima_analise_em"],
            "posts": versions.listar("post", p["id"]),
            "artigos": versions.listar("artigo", p["id"]),
        })
    return {"exportado_em": now_iso(), "projetos": projetos}


def historico_json(dao: Dao, versions: VersionService) -> str:
    return json.dumps(historico(dao, versions), ensure_ascii=False, indent=2)


def historico_md(dao: Dao, versions: VersionService) -> str:
    h = historico(dao, versions)
    out = ["# Histórico do Shiplog", "", f"Exportado em {h['exportado_em']}", ""]
    for p in h["projetos"]:
        out += [f"## {p['nome']}" + (" (arquivado)" if p["arquivado"] else ""), ""]
        if p["origem"] == "livre":
            out += ["- Origem: sem repositório (post a partir de descrição)", f"- Descrição: {p['descricao']}"]
        else:
            out.append(f"- Repositório: {p['url_repo'] or '—'}")
        if p["notas"]:
            out.append(f"- Notas: {p['notas']}")
        out.append("")
        for v in p["posts"]:
            out += [f"### Post v{v['versao']} — {STATUS_LABEL[v['status']]}"
                    + (f" em {v['publicado_em']}" if v.get("publicado_em") else ""), ""]
            if v.get("link"):
                out += [f"Link: {v['link']}", ""]
            out += [v["texto"], "", " ".join(v["hashtags"]), ""]
        for v in p["artigos"]:
            out += [f"### Artigo v{v['versao']} — {v['titulo']} — {STATUS_LABEL[v['status']]}", ""]
            if v.get("link"):
                out += [f"Link: {v['link']}", ""]
            out += [f"*{v['subtitulo']}*", "", v["corpo_markdown"], ""]
    return "\n".join(out)
