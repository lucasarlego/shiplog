#!/usr/bin/env bash
# Launcher de uso diário do Shiplog (atalho de desktop / Menu Iniciar).
# - Se o servidor já estiver no ar, só abre a janela do app.
# - Senão, sobe o servidor em primeiro plano (mantém o WSL vivo enquanto roda) e abre a janela quando estiver pronto.
# A janela abre em "modo app" (Edge/Chrome sem barra de endereço) quando possível.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
PORT="${SHIPLOG_PORT:-8765}"
URL="http://127.0.0.1:${PORT}"
DATA="${SHIPLOG_DATA_DIR:-$HOME/.shiplog}"
LOG="$DATA/logs/server.out"
mkdir -p "$DATA/logs"

ping() { curl -fsS --max-time 1 "$URL/api/ping" 2>/dev/null | grep -q shiplog; }

open_app() {
  if grep -qi microsoft /proc/version 2>/dev/null; then
    # `start` do Windows desacopla o navegador do WSL e retorna na hora. Chamar o .exe em segundo plano
    # daqui não serve: quando o script termina, a sessão do WSL fecha e a chamada morre antes de abrir a janela.
    # Preferência: script do Windows que abre o modo app e maximiza a janela nova (com o navegador já
    # aberto, --start-maximized é ignorado e a janela podia vir minimizada/pequena).
    # Ele é copiado para uma pasta local do Windows: o PowerShell não executa scripts direto do \\wsl$.
    local win_local ps1
    win_local="$(cd /mnt/c && cmd.exe /c "echo %LOCALAPPDATA%" 2>/dev/null | tr -d '\r')"
    if [ -n "$win_local" ] && command -v powershell.exe >/dev/null; then
      ps1="$(wslpath "$win_local")/Shiplog/abrir-janela.ps1"
      mkdir -p "$(dirname "$ps1")" && cp -f "$ROOT/scripts/abrir-janela.ps1" "$ps1" 2>/dev/null
      if (cd /mnt/c && powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden \
            -File "$win_local\\Shiplog\\abrir-janela.ps1" -Url "$URL" >/dev/null 2>&1); then return; fi
    fi
    # Alternativa: /max e --start-maximized via `start` do Windows.
    for exe in msedge chrome; do
      if (cd /mnt/c && cmd.exe /c start "" /max "$exe" --start-maximized --app="$URL" >/dev/null 2>&1); then return; fi
    done
    (cd /mnt/c && cmd.exe /c start "" /max "$URL" >/dev/null 2>&1)
  elif [ "$(uname)" = "Darwin" ]; then
    open -na "Google Chrome" --args --app="$URL" 2>/dev/null || open "$URL"
  else
    for b in google-chrome chromium chromium-browser microsoft-edge brave-browser; do
      if command -v "$b" >/dev/null; then "$b" --app="$URL" >/dev/null 2>&1 & return; fi
    done
    xdg-open "$URL" >/dev/null 2>&1 &
  fi
}

if ping; then open_app; exit 0; fi

# Abre a janela assim que o servidor responder.
( for _ in $(seq 1 300); do if ping; then open_app; exit 0; fi; sleep 0.2; done ) &

cd "$ROOT"
{
  echo "=== $(date '+%F %T') iniciando Shiplog ==="
  [ -d .venv ] || uv sync --quiet
  [ -f frontend/dist/index.html ] || make -s build
} >>"$LOG" 2>&1
exec uv run --quiet shiplog --no-browser --port "$PORT" >>"$LOG" 2>&1
