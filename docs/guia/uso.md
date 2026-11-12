# Como usar

## Post a partir de um repositório

1. Cole a URL (HTTPS ou SSH) no painel e aperte **Enter** — o projeto é cadastrado e a geração do post entra na fila.
2. Acompanhe o progresso (Na fila → Clonando → Analisando → Escrevendo → Pronto). Dá para cancelar.
3. Revise: edite o texto, troque a abertura por um dos ganchos alternativos, ajuste hashtags, confira o contador (limite de 3.000 e corte do "ver mais").
4. **Copiar post** (`Ctrl/⌘+Shift+C`), publique no LinkedIn e marque como **publicado** com o link.
5. Na aba **Artigo do Medium**, gere um artigo com trechos reais do código (cada caminho/linha citado é verificado no repositório) e exporte em `.md`.

## Post sem repositório

no painel, troque para **Descrever** e conte o que você fez. O Claude escreve só com base no seu texto, sem acesso a arquivos (artigos exigem repositório).

## Comentários em posts de outras pessoas

no menu **Comentários**, cole o texto do post, cole prints com `Ctrl+V`, escolha o objetivo (acrescentar, apoiar, perguntar, contrapor) e copie uma das 3 sugestões.

## Perfil profissional

em **Configurações**, envie o currículo (PDF, DOCX, TXT ou MD) e escreva o que ele não diz. O perfil gerado é editável e entra em posts, artigos e comentários. Para o estilo dos artigos, preencha também `~/.claude/skills/medium-article-writer/references/voz-do-autor.md`.

## Atalhos

`Ctrl/⌘+K` paleta de comandos · `/` foca o campo de URL · `Ctrl/⌘+Enter` gera/salva · `Ctrl/⌘+Shift+C` copia o texto atual.

## Dados

Tudo fica em `~/.shiplog/` (ou `SHIPLOG_DATA_DIR`), fora do repositório: `shiplog.db` (SQLite), `repos/` (clones), `perfil/` (currículo), `comentarios/` (imagens coladas), `logs/` (rotacionados, sem segredos). Em **Configurações** você edita o prompt base, o perfil de voz, caminhos, timeouts, parâmetros padrão e exporta o histórico em Markdown/JSON.

---

[← Voltar ao README](../../README.md)
