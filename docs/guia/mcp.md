# MCP: escrever pelo Claude Code

O Shiplog tem um servidor MCP local. Com ele, a sua sessão do Claude Code (ou de outro harness compatível com MCP) escreve posts, artigos e comentários **durante o desenvolvimento**, e tudo cai no Shiplog como rascunho para você acompanhar o status pela interface.

Quem escreve é o modelo da sua sessão, que já sabe o que vocês fizeram na conversa. O Shiplog entrega o que só ele sabe (perfil profissional, voz, parâmetros padrão, histórico de posts, commits desde o último post), confere o formato e guarda. Nada é publicado no LinkedIn ou no Medium: publicar continua manual.

## Instalar

```bash
cd shiplog
make mcp-install      # registra "shiplog" no Claude Code, escopo do usuário (vale em todos os projetos)
claude mcp list       # deve mostrar: shiplog ... ✔ Connected
```

Se o Shiplog não estiver aberto, o MCP o inicia em segundo plano (sem abrir o navegador) na primeira chamada.

Para remover: `make mcp-remove`. Para testar as ferramentas sem o Claude Code: `make mcp-inspect` (MCP Inspector).

Outros harnesses: registre um servidor stdio com o comando `uv run --quiet --directory <pasta do shiplog> shiplog-mcp`.

## Pedidos que funcionam

Dentro da pasta de um projeto, no Claude Code:

- "faz um post do LinkedIn sobre o que fizemos hoje"
- "escreve um artigo do Medium sobre este projeto, formato tutorial"
- "sugere um comentário para este post do LinkedIn: <cole o texto>"
- "sugere um comentário para este artigo do Medium: <cole o texto>"
- "publiquei o post, o link é https://…" (marca a versão como publicada)
- "usei a segunda opção de comentário"

Também há prompts prontos no menu `/` do Claude Code: `post_do_projeto`, `artigo_do_projeto` e `comentar`.

## Como funciona

1. `projeto_atual` localiza o projeto pela URL do `origin` da pasta. Se a pasta não tem remoto, cria um projeto **local** ligado ao caminho (ícone de pasta no painel). Se mais tarde a pasta ganhar um `origin`, o agente pergunta se você quer vincular.
2. `contexto_post` junta perfil, voz, parâmetros, regras, o último post (para não repetir assunto) e o estado da pasta: commits desde o último post, `diff --stat` e arquivos não commitados. Tudo com comandos git de leitura; a pasta nunca é alterada.
3. O agente lê o código que precisar, escreve, mostra para você e ajusta.
4. `salvar_post` valida (até 3.000 caracteres, 3 a 5 hashtags) e cria uma nova versão `rascunho` marcada **via Claude Code**, guardando o commit de referência. O próximo post parte desse commit.
5. No Shiplog você revisa, edita, copia e marca como publicado (ou pede ao agente).

Artigos seguem o mesmo caminho com `contexto_artigo` e `salvar_artigo`. Cada trecho de código citado é conferido nos arquivos do projeto e trechos inexistentes são recusados. Comentários (`contexto_comentario`, `salvar_comentario`, `marcar_comentario_usado`) ficam na página **Comentários**, com plataforma (LinkedIn ou Medium) e status (sugerido ou usado).

## Ferramentas

| Ferramenta | O que faz | Grava? |
| --- | --- | --- |
| `shiplog_status` | Saúde do Shiplog, perfil e voz configurados | não |
| `projeto_atual` | Projeto da pasta (cria se não existir) | cadastro |
| `contexto_post`, `contexto_artigo`, `contexto_comentario` | Contexto para escrever | não |
| `salvar_post`, `salvar_artigo`, `salvar_comentario` | Guarda como rascunho/sugestão | nova versão |
| `marcar_status` | rascunho → pronto → publicado (com link) | status |
| `marcar_comentario_usado` | Qual sugestão você usou | status |
| `listar`, `obter` | Consulta projetos, versões e comentários | não |

Recursos: `shiplog://perfil` (perfil e voz) e `shiplog://config/escrita` (prompt base e parâmetros padrão).

Nenhuma ferramenta exclui dados, publica em rede social ou escreve na pasta do projeto.

## Limites

- Projetos **locais** não têm o botão "Gerar" no Shiplog: os textos vêm do Claude Code.
- Imagens de comentário só entram se o agente tiver o caminho do arquivo. Imagem colada direto no chat é vista pelo modelo, mas o item é salvo só com o texto e o resumo.
- Em harnesses com modelos mais fracos o texto pode sair pior; o formato continua garantido pela validação.
- Os logs do MCP ficam em `~/.shiplog/logs/mcp.log`.
