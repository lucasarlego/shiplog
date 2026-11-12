# Shiplog — comandos de desenvolvimento e teste local.
# Uso diário sem terminal: `make launcher` (cria o atalho "Shiplog" no Menu Iniciar/Área de Trabalho).

SHELL := /bin/bash
PORT ?= 8765
URL := http://127.0.0.1:$(PORT)
export SHIPLOG_PORT := $(PORT)

.DEFAULT_GOAL := help
.PHONY: help install install-backend install-frontend install-skill backend frontend dev build run start stop \
        test test-backend test-frontend check launcher launcher-remove logs clean

help: ## Lista os comandos
	@awk 'BEGIN {FS = ":.*##"; printf "\nShiplog — comandos disponíveis:\n\n"} /^[a-zA-Z_-]+:.*##/ { printf "  \033[36mmake %-16s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo

# --- Instalação --------------------------------------------------------------
install: install-backend install-frontend install-skill ## Instala backend (uv), frontend (npm) e a skill de artigos

install-backend: ## Instala dependências Python com uv
	uv sync

install-frontend: ## Instala dependências do frontend com npm
	cd frontend && npm install

SKILL_DIR := $(HOME)/.claude/skills/medium-article-writer
install-skill: ## Copia a skill medium-article-writer para ~/.claude/skills (não sobrescreve uma existente)
	@if [ -f "$(SKILL_DIR)/SKILL.md" ]; then \
	  echo "Skill já instalada em $(SKILL_DIR) (mantida como está)."; \
	else \
	  mkdir -p "$(dir $(SKILL_DIR))" && cp -R skills/medium-article-writer "$(SKILL_DIR)" && \
	  echo "Skill instalada em $(SKILL_DIR). Para o tom dos artigos, preencha references/voz-do-autor.md."; \
	fi

# --- Rodar partes separadas ----------------------------------------------------
backend: ## Sobe só a API (com reload) em 127.0.0.1:8765
	uv run shiplog --no-browser --reload --port $(PORT)

frontend: ## Sobe só o frontend em modo dev (Vite, http://127.0.0.1:5173, proxy para a API)
	cd frontend && npm run dev

dev: ## Backend + frontend em modo desenvolvimento, juntos (Ctrl+C encerra os dois)
	@echo "API: $(URL)  |  Interface (dev): http://127.0.0.1:5173"
	@trap 'kill 0' INT TERM EXIT; \
	  uv run shiplog --no-browser --reload --port $(PORT) & \
	  (cd frontend && npm run dev -- --open) & \
	  wait

# --- App completo --------------------------------------------------------------
build: ## Compila o frontend (frontend/dist), servido pelo FastAPI
	@[ -d frontend/node_modules ] || (cd frontend && npm install)
	cd frontend && npm run build

run: ## Aplicação completa com um comando: instala o que faltar, builda e abre o navegador
	@[ -d .venv ] || uv sync
	@[ -f frontend/dist/index.html ] || $(MAKE) -s build
	uv run shiplog --port $(PORT)

start: ## Sobe a aplicação completa em segundo plano e abre a janela do app
	@nohup scripts/shiplog-app.sh >/dev/null 2>&1 &
	@echo "Shiplog iniciando em $(URL) (logs: make logs)"

stop: ## Encerra o servidor em segundo plano
	@scripts/shiplog-stop.sh

logs: ## Mostra os logs do servidor
	@tail -n 80 -f $${SHIPLOG_DATA_DIR:-$$HOME/.shiplog}/logs/shiplog.log

# --- Testes ----------------------------------------------------------------------
test: test-backend test-frontend ## Roda todos os testes

test-backend: ## Testes do backend (pytest, Claude CLI simulado)
	uv run pytest -q

test-frontend: ## Checagem de tipos do frontend
	@[ -d frontend/node_modules ] || (cd frontend && npm install)
	cd frontend && npx tsc -b --noEmit

check: test build ## Testes + build de produção

# --- Atalho de uso diário --------------------------------------------------------
launcher: build ## Cria o atalho "Shiplog" (Windows via WSL, Linux ou macOS)
	@scripts/install-launcher.sh

launcher-remove: ## Remove o atalho
	@scripts/install-launcher.sh --uninstall

clean: ## Remove artefatos de build e caches (não toca nos seus dados em ~/.shiplog)
	rm -rf frontend/dist .pytest_cache
	find backend -name __pycache__ -type d -prune -exec rm -rf {} +
