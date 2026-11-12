# Instalação e uso no dia a dia

## Pré-requisitos

| Ferramenta | Versão | Para quê |
| --- | --- | --- |
| Python | 3.11+ | backend (FastAPI) |
| [uv](https://docs.astral.sh/uv/) | recente | ambiente e dependências Python |
| Node.js + npm | 20+ | compilar a interface (só na instalação) |
| git | 2.30+ | clonar os repositórios (com acesso SSH/credential helper já configurado para repos privados) |
| [Claude Code](https://docs.claude.com/claude-code) | 2.x | geração; precisa estar logado (`claude` → `/login`) |
| Skill `medium-article-writer` | incluída | só para artigos; `make install-skill` copia de `skills/` para `~/.claude/skills/` (não sobrescreve uma existente) |

## Instalação e primeira execução

```bash
make install   # uv sync + npm install + skill de artigos
make run       # builda a interface se preciso, sobe em http://127.0.0.1:8765 e abre o navegador
```

Sem `make`: `./run` (Linux/macOS/WSL) ou `run.cmd` (Windows nativo).

## Uso no dia a dia (sem terminal nem VS Code)

```bash
make launcher
```

Cria um atalho **Shiplog** com ícone próprio:

- **WSL (Windows):** na Área de Trabalho e no Menu Iniciar (tecla Windows → "Shiplog"; dá para fixar na barra de tarefas). Também cria **Parar Shiplog** no Menu Iniciar.
- **Linux:** entrada no menu de aplicativos (com a ação "Parar Shiplog").
- **macOS:** `~/Applications/Shiplog.command`.

Ao clicar, o atalho sobe o servidor em segundo plano (sem janela de console; no WSL via `conhost --headless wsl.exe`) e abre o Shiplog numa **janela própria** do Edge/Chrome em modo app. Se já estiver rodando, só abre a janela. Para remover: `make launcher-remove`.

## Comandos (`make help`)

| Comando | O que faz |
| --- | --- |
| `make install` | Instala dependências do backend (uv), do frontend (npm) e a skill de artigos |
| `make install-skill` | Só copia a skill `medium-article-writer` para `~/.claude/skills/` (não sobrescreve) |
| `make backend` | Só a API, com reload, em `127.0.0.1:8765` |
| `make frontend` | Só a interface em modo dev (Vite em `127.0.0.1:5173`, proxy para a API) |
| `make dev` | Backend + frontend em modo desenvolvimento, juntos |
| `make build` | Compila a interface para `frontend/dist` |
| `make run` | **Aplicação completa com um comando** (primeiro plano) |
| `make start` / `make stop` | Sobe/encerra a aplicação em segundo plano |
| `make logs` | Acompanha o log do servidor |
| `make test` | Testes do backend (pytest, Claude CLI simulado) + checagem de tipos do frontend |
| `make check` | Testes + build de produção |
| `make launcher` / `make launcher-remove` | Instala/remove o atalho de desktop |

Variáveis úteis: `PORT=8766 make run`, `SHIPLOG_DATA_DIR=/outro/lugar make run`.

---

[← Voltar ao README](../../README.md)
