# Shiplog

Aplicação web **local** que ajuda pessoas desenvolvedoras a escrever para o LinkedIn e o Medium usando o **Claude Code CLI** que já está logado na sua máquina (modo headless). Ela para na entrega do texto: publicar é sempre manual.

- **Post a partir de um repositório Git:** o Claude lê o código (somente leitura) e escreve o rascunho.
- **Post a partir de uma descrição:** para o que não tem código (uma palestra, uma migração, um aprendizado da semana).
- **Artigo para o Medium:** com trechos reais do código, usando a skill `medium-article-writer` (incluída em [`skills/`](skills/)).
- **Comentários:** cole o texto e os prints do post de outra pessoa e receba 3 opções de comentário.
- **Perfil profissional:** envie seu currículo; o Claude monta um perfil que entra em todos os textos.

- Roda 100% em `127.0.0.1`, sem deploy, sem login, sem API paga (usa a sua assinatura do Claude Code).
- O Claude só pode **ler** o repositório (`Read`, `Grep`, `Glob`; Bash/Edit/Write bloqueados). Depois de cada geração o clone é conferido com `git status`.
- Histórico de versões (regenerar e editar nunca sobrescrevem), status rascunho → pronto → publicado com link.

## Começo rápido

Você precisa de uma assinatura do Claude (Pro ou superior) com o [Claude Code](https://docs.claude.com/claude-code) instalado e logado. Cada pessoa usa o **próprio login e a própria cota**; o Shiplog nunca usa chave de API.

```bash
git clone <este repositório> shiplog && cd shiplog
claude            # se ainda não fez login: digite /login e siga as instruções; depois saia
make install      # dependências do backend e do frontend + skill de artigos
make run          # abre http://127.0.0.1:8765
make launcher     # opcional: atalho para abrir sem terminal
```

Testado em Linux e no WSL (Windows). macOS e Windows sem WSL têm suporte no código (`./run`, `run.cmd`), mas ainda não foram testados.

## Documentação

- [Instalação e uso no dia a dia](docs/guia/instalacao.md): pré-requisitos, atalho de desktop e todos os comandos `make`.
- [Como usar](docs/guia/uso.md): posts com e sem repositório, artigos, comentários, perfil profissional e onde ficam os dados.
- [Segurança e privacidade](docs/guia/seguranca.md)
- [Arquitetura](docs/guia/arquitetura.md)
- [Solução de problemas](docs/guia/solucao-de-problemas.md)

## Licença

[MIT](LICENSE), incluindo a skill em `skills/medium-article-writer/`.
