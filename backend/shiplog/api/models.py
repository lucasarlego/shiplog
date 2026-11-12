"""Modelos de entrada da API (spec 004)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class UrlIn(BaseModel):
    url: str


class ProjetoCriar(BaseModel):
    url: str | None = None
    descricao: str | None = Field(default=None, max_length=8000)
    nome: str | None = None
    branch: str | None = None
    notas: str = ""
    gerar: bool = True
    parametros: dict[str, Any] | None = None


class ProjetoEditar(BaseModel):
    nome: str | None = None
    branch: str | None = None
    notas: str | None = None
    descricao: str | None = Field(default=None, max_length=8000)


class CheckUpdates(BaseModel):
    ids: list[int] | None = None


class GeracaoCriar(BaseModel):
    tipo: Literal["post", "artigo"] = "post"
    parametros: dict[str, Any] | None = None
    instrucoes_extras: str = Field(default="", max_length=4000)
    base_versao_id: int | None = None
    atualizar_repo: bool | None = None
    atualizacao: bool = False


class PostVersao(BaseModel):
    texto: str = Field(min_length=1)
    hashtags: list[str] | None = None
    hooks_alternativos: list[str] | None = None


class ArtigoVersao(BaseModel):
    titulo: str = Field(min_length=1)
    subtitulo: str = ""
    corpo_markdown: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list, max_length=5)


class StatusIn(BaseModel):
    status: Literal["rascunho", "pronto", "publicado"]
    link: HttpUrl | None = None


class CurriculoIn(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    conteudo_base64: str = Field(min_length=1, max_length=7_200_000)


class PerfilGerar(BaseModel):
    sobre: str | None = Field(default=None, max_length=8000)


class ImagemIn(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    conteudo_base64: str = Field(min_length=1, max_length=7_200_000)


class ComentarioCriar(BaseModel):
    autor: str = Field(default="", max_length=200)
    link: str = Field(default="", max_length=500)
    texto_post: str = Field(default="", max_length=10_000)
    imagens: list[ImagemIn] = Field(default_factory=list, max_length=6)


class ComentarioGerar(BaseModel):
    parametros: dict[str, Any] | None = None
    instrucoes: str = Field(default="", max_length=2000)


class ConfigIn(BaseModel):
    prompt_base: str | None = None
    perfil_voz: str | None = None
    perfil_profissional: str | None = Field(default=None, max_length=6000)
    perfil_sobre: str | None = Field(default=None, max_length=8000)
    pasta_dados: str | None = None
    caminho_cli: str | None = None
    timeout_post_s: int | None = Field(default=None, ge=30, le=3600)
    timeout_artigo_s: int | None = Field(default=None, ge=30, le=3600)
    modelo: str | None = None
    parametros_padrao_post: dict[str, Any] | None = None
    parametros_padrao_artigo: dict[str, Any] | None = None
