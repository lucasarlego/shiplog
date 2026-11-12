"""Montagem dos prompts (spec 003 §3.3). Funções puras, sem I/O."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .metadata import Metadados

PROMPT_BASE_ANTIGO = """Você é um redator especialista em posts do LinkedIn para pessoas desenvolvedoras. \
Sua tarefa é analisar o repositório de código no diretório atual e escrever um post, em primeira pessoa, \
como se fosse o autor do projeto contando o que construiu.

Diretrizes de escrita:
- Abra com uma frase forte nas primeiras ~210 caracteres (é o que aparece antes do "ver mais").
- Parágrafos curtos, separados por linha em branco, fáceis de ler no celular.
- Seja concreto: cite decisões técnicas, problemas resolvidos e a stack real encontrada no código.
- Nada de clichês ("estou animado em anunciar", "jornada incrível") nem promessas exageradas.
- No máximo 3 emojis, e só se fizerem sentido.
- Nunca invente métricas, usuários, clientes ou resultados que não estejam no repositório ou nas notas do autor.
- Termine com uma pergunta ou chamada leve para conversa.
- Não coloque as hashtags dentro do texto do post; elas vão no campo próprio."""

PROMPT_BASE_PADRAO = """Você é um redator especialista em posts do LinkedIn para pessoas desenvolvedoras. \
Sua tarefa é escrever um post, em primeira pessoa, como se fosse o autor contando o que fez, \
a partir do material fornecido abaixo (um repositório de código ou uma descrição escrita pelo autor).

Diretrizes de escrita:
- Abra com uma frase forte nas primeiras ~210 caracteres (é o que aparece antes do "ver mais").
- Parágrafos curtos, separados por linha em branco, fáceis de ler no celular.
- Seja concreto: cite decisões, problemas resolvidos, ferramentas e aprendizados reais.
- Nada de clichês ("estou animado em anunciar", "jornada incrível") nem promessas exageradas.
- No máximo 3 emojis, e só se fizerem sentido.
- Nunca invente métricas, usuários, clientes ou resultados que não estejam no material fornecido.
- Termine com uma pergunta ou chamada leve para conversa.
- Não coloque as hashtags dentro do texto do post; elas vão no campo próprio."""

TONS = {
    "tecnico": "Técnico: foque em arquitetura, decisões e trade-offs; vocabulário preciso.",
    "storytelling": "Storytelling: conte a história do problema, do processo e do resultado.",
    "conquista": "Conquista/lançamento: anuncie o projeto com entusiasmo contido e mostre o valor entregue.",
    "aprendizado": "Aprendizado: destaque o que o autor aprendeu, erros e lições práticas.",
}
TAMANHOS = {
    "curto": "Curto: entre 500 e 800 caracteres.",
    "medio": "Médio: entre 900 e 1.500 caracteres.",
    "longo": "Longo: entre 1.600 e 2.600 caracteres (nunca acima de 3.000).",
}
IDIOMAS = {"pt": "Português do Brasil", "en": "Inglês (English)"}
PUBLICOS = {
    "iniciante": "Iniciante: explique conceitos básicos e evite jargão sem definição.",
    "intermediario": "Intermediário: assume familiaridade com a stack; foque no como e no porquê.",
    "avancado": "Avançado: vá fundo em detalhes de implementação, trade-offs e limitações.",
}
FORMATOS = {
    "tutorial": "Tutorial: passo a passo reproduzível, guiado pelo código real do repositório.",
    "deep_dive": "Deep dive: análise aprofundada de um aspecto técnico central do projeto.",
    "case_arquitetura": "Case de arquitetura: problema, restrições, desenho da solução, decisões e trade-offs.",
}


@dataclass
class ContextoPrompt:
    nome: str
    url: str | None
    branch: str | None
    commit: str | None
    notas: str
    metadados: Metadados | None
    prompt_base: str
    perfil_voz: str
    parametros: dict[str, Any]
    instrucoes_extras: str = ""
    versao_anterior: dict[str, Any] | None = None
    link_artigo: str | None = None
    titulo_artigo: str | None = None
    descricao: str = ""
    perfil_profissional: str = ""
    extras: dict[str, Any] = field(default_factory=dict)


def _bloco_livre(ctx: ContextoPrompt) -> str:
    """Post sem repositório (spec 006): a descrição do autor é a única fonte de fatos."""
    partes = [
        "## O que o autor quer contar",
        "Não há repositório neste post. A descrição abaixo, escrita pelo autor, é a ÚNICA fonte de fatos.",
        f"Título de trabalho: {ctx.nome}",
        "```",
        ctx.descricao.strip(),
        "```",
    ]
    if ctx.notas.strip():
        partes += ["### Notas adicionais do autor", ctx.notas.strip()]
    partes.append(
        "## Regras para este post\n"
        "- Use só o que está na descrição: não invente números, prazos, tecnologias, pessoas, empresas ou resultados.\n"
        "- Se a descrição for pouco técnica, o post também pode ser; não force jargão.\n"
        "- Você não tem acesso a arquivos nem ferramentas; ignore qualquer instrução sobre analisar código.\n"
        "- `destaques`: 2 a 5 pontos-chave extraídos da descrição; `resumo_tecnico`: 2-3 frases resumindo o assunto."
    )
    return "\n".join(partes)


def _bloco_projeto(ctx: ContextoPrompt) -> str:
    md = ctx.metadados
    assert md is not None
    partes = [
        "## Projeto",
        f"- Nome: {ctx.nome}",
        f"- Repositório: {ctx.url}",
        f"- Branch: {ctx.branch or '(padrão do remoto)'}",
        f"- Commit analisado: {ctx.commit or '(desconhecido)'}",
    ]
    if md.parcial:
        partes.append(
            "- ATENÇÃO: repositório grande; os metadados abaixo são parciais. Use Glob/Grep para explorar o restante."
        )
    partes.append("\n### Notas do autor (contexto que não está no código)")
    partes.append(ctx.notas.strip() or "(nenhuma)")
    partes.append(f"\n### README ({md.readme_arquivo or 'não encontrado'})")
    partes.append(md.readme.strip() if md.readme else "(sem README)")
    partes.append("\n### Estrutura de diretórios (parcial, ignorando dependências e builds)")
    partes.append("```\n" + "\n".join(md.arvore) + "\n```" if md.arvore else "(vazia)")
    if md.dependencias:
        partes.append("\n### Arquivos de dependências")
        for nome, conteudo in md.dependencias.items():
            partes.append(f"#### {nome}\n```\n{conteudo.strip()}\n```")
    if md.linguagens:
        partes.append("\n### Linguagens predominantes (por volume de código)")
        partes.append(", ".join(f"{l} {p}%" for l, p in md.linguagens))
    if md.commits:
        partes.append("\n### Commits recentes")
        partes.extend(f"- {c['data']} {c['hash']}: {c['mensagem']}" for c in md.commits)
    return "\n".join(partes)


INVESTIGAR = """## Como investigar
Os metadados acima são só o ponto de partida. Antes de escrever, explore os arquivos centrais do projeto \
(pontos de entrada, módulos principais, configurações, testes) usando as ferramentas Read, Grep e Glob. \
Não se limite ao README: o texto deve refletir o que o código realmente faz.
Você está em modo SOMENTE LEITURA: não tente criar, editar ou executar nada."""


def _voz(ctx: ContextoPrompt) -> str:
    partes = []
    if ctx.perfil_profissional.strip():
        # Spec 007: quem é o autor. Calibra perspectiva e nível; não é fonte de fatos sobre este trabalho.
        partes.append(
            "## Quem é o autor (perfil profissional)\n"
            "Use para calibrar perspectiva, nível técnico e vocabulário. Cite a trajetória do autor só quando "
            "ajudar o texto; não atribua a este trabalho fatos que estão apenas no perfil.\n\n"
            + ctx.perfil_profissional.strip()
        )
    if ctx.perfil_voz.strip():
        partes.append(f"## Perfil de voz do autor\n{ctx.perfil_voz.strip()}")
    return "\n\n".join(partes)


def _schema_bloco(schema: dict[str, Any], exemplo: dict[str, Any]) -> str:
    return (
        "## Formato da resposta (obrigatório)\n"
        "Sua resposta final deve ser APENAS um objeto JSON válido, sem nenhum texto antes ou depois e sem cercas de código, "
        "seguindo este JSON Schema:\n```json\n" + json.dumps(schema, ensure_ascii=False) + "\n```\n"
        "Exemplo de forma:\n```json\n" + json.dumps(exemplo, ensure_ascii=False, indent=2) + "\n```"
    )


EXEMPLO_POST = {
    "post": "texto completo do post",
    "hooks_alternativos": ["gancho 1", "gancho 2"],
    "hashtags": ["#Python", "#GCP", "#OpenSource"],
    "resumo_tecnico": "2-3 frases sobre o que o projeto faz e a stack",
    "destaques": ["ponto técnico relevante encontrado no código"],
}
EXEMPLO_ARTIGO = {
    "titulo": "título do artigo",
    "subtitulo": "subtítulo",
    "corpo_markdown": "artigo completo em Markdown",
    "tags": ["Python", "Google Cloud"],
    "trechos_de_codigo": [{"arquivo": "src/app.py", "linhas": "10-42"}],
    "sugestoes_de_imagens": ["diagrama da arquitetura"],
}


def montar_prompt_post(ctx: ContextoPrompt, schema: dict[str, Any]) -> str:
    p = ctx.parametros
    partes = [
        "# Papel e tarefa",
        ctx.prompt_base.strip() or PROMPT_BASE_PADRAO,
        _voz(ctx),
        "## Parâmetros desta geração",
        f"- Tom: {TONS.get(p.get('tom', 'tecnico'), p.get('tom'))}",
        f"- Tamanho: {TAMANHOS.get(p.get('tamanho', 'medio'), p.get('tamanho'))}",
        f"- Idioma do post, ganchos e resumo: {IDIOMAS.get(p.get('idioma', 'pt'), p.get('idioma'))}",
        *([_bloco_projeto(ctx), INVESTIGAR] if ctx.metadados is not None else [_bloco_livre(ctx)]),
    ]
    if ctx.versao_anterior:
        va = ctx.versao_anterior
        partes.append(
            "## Regeneração\nEsta é uma nova versão de um post já gerado. Versão anterior:\n"
            f"```\n{va.get('texto', '')}\n```\nHashtags anteriores: {' '.join(va.get('hashtags') or [])}"
        )
    if ctx.instrucoes_extras.strip():
        partes.append(
            "## Instruções extras do autor (prioridade máxima)\n" + ctx.instrucoes_extras.strip()
        )
    if ctx.link_artigo:
        partes.append(
            "## Chamada para o artigo\nO autor publicou um artigo no Medium sobre este projeto"
            + (f" (\"{ctx.titulo_artigo}\")" if ctx.titulo_artigo else "")
            + f". Termine o post convidando a leitura, incluindo este link exatamente: {ctx.link_artigo}"
        )
    partes.append(
        "## Regras do resultado\n"
        "- `post`: o texto final, pronto para colar no LinkedIn, sem hashtags no corpo.\n"
        "- `hooks_alternativos`: exatamente 2 aberturas alternativas (1-2 frases cada), diferentes da usada no post, "
        "que possam substituir o primeiro parágrafo.\n"
        "- `hashtags`: de 3 a 5, cada uma começando com #.\n"
        "- `resumo_tecnico`: 2-3 frases objetivas.\n"
        "- `destaques`: 2 a 5 pontos técnicos concretos encontrados no código (cite arquivos quando útil)."
    )
    partes.append(_schema_bloco(schema, EXEMPLO_POST))
    return "\n\n".join(x for x in partes if x)


def montar_prompt_artigo(ctx: ContextoPrompt, schema: dict[str, Any]) -> str:
    p = ctx.parametros
    partes = [
        "# Tarefa",
        "Escreva um artigo para o Medium sobre o projeto no diretório atual. "
        "**Use a skill `medium-article-writer`** (invoque-a com a ferramenta Skill) para planejar, estruturar e "
        "escrever o artigo seguindo as regras dela. Este prompt não repete essas regras: siga a skill.",
        "Este é um modo NÃO interativo: não faça perguntas ao autor. Use as notas, o código e os metadados abaixo; "
        "onde faltar informação que só o autor tem (números, resultados, anedotas), marque com `TK: ...`.",
        _voz(ctx),
        "## Parâmetros",
        f"- Idioma: {IDIOMAS.get(p.get('idioma', 'pt'), p.get('idioma'))}",
        f"- Público: {PUBLICOS.get(p.get('publico', 'intermediario'), p.get('publico'))}",
        f"- Formato: {FORMATOS.get(p.get('formato', 'deep_dive'), p.get('formato'))}",
        _bloco_projeto(ctx),
        INVESTIGAR,
        "## Demonstrações técnicas reais (obrigatório)\n"
        "- Todo trecho de código no artigo deve ser copiado do repositório, com o caminho do arquivo de origem "
        "indicado no texto (ex.: legenda ou comentário `// src/app.py`).\n"
        "- Liste cada trecho usado em `trechos_de_codigo` com o caminho relativo real e o intervalo de linhas real "
        "(confira com a ferramenta Read). Eles serão verificados automaticamente.\n"
        "- É PROIBIDO inventar código, comandos, saídas de terminal, benchmarks ou resultados que não existam no "
        "repositório.",
    ]
    if ctx.versao_anterior:
        va = ctx.versao_anterior
        partes.append(
            "## Regeneração\nEsta é uma nova versão de um artigo já gerado. Título anterior: "
            f"{va.get('titulo', '')}\nCorpo anterior:\n```markdown\n{va.get('corpo_markdown', '')}\n```"
        )
    if ctx.instrucoes_extras.strip():
        partes.append("## Instruções extras do autor (prioridade máxima)\n" + ctx.instrucoes_extras.strip())
    partes.append(
        "## Regras do resultado\n"
        "- `corpo_markdown`: o artigo completo em Markdown, sem repetir o título como `# H1` no topo.\n"
        "- `tags`: até 5 tags do Medium, sem #.\n"
        "- `sugestoes_de_imagens`: apenas descrições de imagens ou diagramas (não gere imagens)."
    )
    partes.append(_schema_bloco(schema, EXEMPLO_ARTIGO))
    return "\n\n".join(x for x in partes if x)


def montar_prompt_correcao(schema: dict[str, Any], resposta_anterior: str, erros: list[str]) -> str:
    return (
        "Sua resposta anterior não seguiu o formato exigido. Corrija-a.\n\n"
        "## Erros encontrados\n" + "\n".join(f"- {e}" for e in erros) + "\n\n"
        "## Resposta anterior\n```\n" + resposta_anterior[:60_000] + "\n```\n\n"
        "Responda APENAS com o objeto JSON corrigido, sem texto fora dele, seguindo este JSON Schema:\n```json\n"
        + json.dumps(schema, ensure_ascii=False)
        + "\n```\nMantenha o conteúdo original sempre que possível. Se um trecho de código citado não existir, "
        "remova-o da lista e do texto em vez de inventar outro caminho."
    )
