"""Schemas de resposta do LLM e validação (spec 003 FR-04..FR-06, RI-03, RI-05)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator


class PostResposta(BaseModel):
    post: str = Field(min_length=50, description="texto completo do post")
    hooks_alternativos: list[str] = Field(min_length=2, max_length=2, description="2 ganchos alternativos de abertura")
    hashtags: list[str] = Field(min_length=3, max_length=5, description="3 a 5 hashtags, com #")
    resumo_tecnico: str = Field(min_length=10, description="2-3 frases sobre o que o projeto faz e a stack")
    destaques: list[str] = Field(default_factory=list, description="pontos técnicos relevantes encontrados no código")

    @field_validator("hashtags")
    @classmethod
    def _hashtags(cls, v: list[str]) -> list[str]:
        out = []
        for h in v:
            h = h.strip().replace(" ", "")
            if not h:
                continue
            out.append(h if h.startswith("#") else f"#{h}")
        if len(out) < 3:
            raise ValueError("são necessárias de 3 a 5 hashtags não vazias")
        return out

    @field_validator("hooks_alternativos")
    @classmethod
    def _hooks(cls, v: list[str]) -> list[str]:
        if any(not h.strip() for h in v):
            raise ValueError("ganchos não podem ser vazios")
        return [h.strip() for h in v]


class Trecho(BaseModel):
    arquivo: str = Field(description="caminho relativo do arquivo de origem no repositório")
    linhas: str = Field(description="intervalo de linhas, ex.: 10-42")


class ArtigoResposta(BaseModel):
    titulo: str = Field(min_length=5)
    subtitulo: str = Field(min_length=5)
    corpo_markdown: str = Field(min_length=200, description="artigo completo em Markdown")
    tags: list[str] = Field(max_length=5, description="até 5 tags do Medium")
    trechos_de_codigo: list[Trecho] = Field(min_length=1, description="trechos de código reais citados")
    sugestoes_de_imagens: list[str] = Field(default_factory=list, description="descrições de imagens/diagramas")


class PostExterno(BaseModel):
    """Post escrito pelo modelo do harness (spec 009 FR-09): mesmas regras visíveis ao usuário, ganchos opcionais."""
    texto: str = Field(min_length=50, max_length=3000)
    hashtags: list[str] = Field(min_length=3, max_length=5)
    hooks_alternativos: list[str] = Field(default_factory=list, max_length=3)
    resumo_tecnico: str = ""
    destaques: list[str] = Field(default_factory=list, max_length=8)

    _hashtags = field_validator("hashtags")(PostResposta._hashtags.__func__)  # type: ignore[attr-defined]

    @field_validator("hooks_alternativos")
    @classmethod
    def _hooks(cls, v: list[str]) -> list[str]:
        return [h.strip() for h in v if h.strip()]


MODELOS: dict[str, type[BaseModel]] = {"post": PostResposta, "artigo": ArtigoResposta, "post_externo": PostExterno}

_LINHAS = re.compile(r"^\s*(\d+)\s*(?:[-–]\s*(\d+))?\s*$")


def json_schema(tipo: str) -> dict[str, Any]:
    return MODELOS[tipo].model_json_schema()


def _validar_trechos(trechos: list[Trecho], raiz: Path) -> list[str]:
    """RF-27: todo trecho deve existir no repositório (proibido inventar código)."""
    erros = []
    raiz_r = raiz.resolve()
    for i, t in enumerate(trechos):
        rel = t.arquivo.strip()
        while rel.startswith("./"):
            rel = rel[2:]
        p = (raiz_r / rel.lstrip("/")).resolve()
        if raiz_r not in p.parents or not p.is_file():
            erros.append(f"trechos_de_codigo[{i}].arquivo: '{t.arquivo}' não existe no repositório")
            continue
        m = _LINHAS.match(t.linhas)
        if not m:
            erros.append(f"trechos_de_codigo[{i}].linhas: '{t.linhas}' deve ter o formato inicio-fim")
            continue
        a, b = int(m[1]), int(m[2] or m[1])
        try:
            total = sum(1 for _ in p.open("rb"))
        except OSError:
            total = 0
        if not (1 <= a <= b <= max(total, 1)):
            erros.append(f"trechos_de_codigo[{i}].linhas: {t.linhas} fora do arquivo '{t.arquivo}' ({total} linhas)")
    return erros


def validar(tipo: str, data: Any, raiz: Path | None = None) -> tuple[dict[str, Any] | None, list[str]]:
    """Retorna (dados normalizados, erros)."""
    if not isinstance(data, dict):
        return None, ["a resposta deve ser um objeto JSON"]
    try:
        obj = MODELOS[tipo].model_validate(data)
    except ValidationError as e:
        return None, [f"{'.'.join(str(x) for x in err['loc']) or '(raiz)'}: {err['msg']}" for err in e.errors()]
    if tipo == "artigo" and raiz is not None:
        erros = _validar_trechos(obj.trechos_de_codigo, raiz)  # type: ignore[attr-defined]
        if erros:
            return None, erros
    return obj.model_dump(), []
