#!/usr/bin/env bash
# Instala o atalho "Shiplog" para abrir o app sem terminal/VS Code.
#   WSL    → atalhos no Menu Iniciar e na Área de Trabalho do Windows (+ "Parar Shiplog")
#   Linux  → ~/.local/share/applications/shiplog.desktop
#   macOS  → ~/Applications/Shiplog.command
# Uso: scripts/install-launcher.sh [--uninstall]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/scripts/shiplog-app.sh"
STOP="$ROOT/scripts/shiplog-stop.sh"
UNINSTALL="${1:-}"
chmod +x "$APP" "$STOP"

if grep -qi microsoft /proc/version 2>/dev/null; then
  DISTRO="${WSL_DISTRO_NAME:?execute dentro do WSL}"
  ps() { powershell.exe -NoProfile -NonInteractive -Command "$1" | tr -d '\r'; }
  LOCALAPPDATA_WIN="$(ps '$env:LOCALAPPDATA')"
  DESKTOP_WIN="$(ps '[Environment]::GetFolderPath("Desktop")')"
  PROGRAMS_WIN="$(ps '[Environment]::GetFolderPath("Programs")')"
  ICON_DIR="$(wslpath "$LOCALAPPDATA_WIN")/Shiplog"
  if [ "$UNINSTALL" = "--uninstall" ]; then
    rm -f "$(wslpath "$DESKTOP_WIN")/Shiplog.lnk" "$(wslpath "$PROGRAMS_WIN")/Shiplog.lnk" "$(wslpath "$PROGRAMS_WIN")/Parar Shiplog.lnk"
    rm -rf "$ICON_DIR"
    echo "Atalhos removidos."; exit 0
  fi
  mkdir -p "$ICON_DIR"
  cp "$ROOT/assets/shiplog.ico" "$ICON_DIR/shiplog.ico"
  ICON_WIN="$LOCALAPPDATA_WIN\\Shiplog\\shiplog.ico"
  # conhost --headless executa o wsl.exe sem abrir janela de console.
  mk() { # nome pasta script
    ps "\$s=(New-Object -ComObject WScript.Shell).CreateShortcut('$2\\$1.lnk');
        \$s.TargetPath='C:\\Windows\\System32\\conhost.exe';
        \$s.Arguments='--headless wsl.exe -d $DISTRO -- bash -lc \"$3\"';
        \$s.IconLocation='$ICON_WIN';
        \$s.Description='$1';
        \$s.WorkingDirectory='%USERPROFILE%';
        \$s.Save()"
  }
  mk "Shiplog" "$PROGRAMS_WIN" "$APP"
  mk "Shiplog" "$DESKTOP_WIN" "$APP"
  mk "Parar Shiplog" "$PROGRAMS_WIN" "$STOP"
  echo "Atalhos criados:"
  echo "  • Área de Trabalho: Shiplog"
  echo "  • Menu Iniciar: Shiplog e Parar Shiplog (tecla Windows → digite 'Shiplog')"
  echo "Dica: clique com o botão direito no atalho do Menu Iniciar → 'Fixar na barra de tarefas'."
elif [ "$(uname)" = "Darwin" ]; then
  DEST="$HOME/Applications/Shiplog.command"
  if [ "$UNINSTALL" = "--uninstall" ]; then rm -f "$DEST"; echo "Removido."; exit 0; fi
  mkdir -p "$HOME/Applications"
  printf '#!/bin/bash\nnohup "%s" >/dev/null 2>&1 &\nexit 0\n' "$APP" > "$DEST"
  chmod +x "$DEST"
  echo "Criado $DEST (abra pelo Finder ou Spotlight)."
else
  DEST="$HOME/.local/share/applications/shiplog.desktop"
  if [ "$UNINSTALL" = "--uninstall" ]; then rm -f "$DEST"; echo "Removido."; exit 0; fi
  mkdir -p "$(dirname "$DEST")" "$HOME/.local/share/icons"
  cp "$ROOT/frontend/public/favicon.svg" "$HOME/.local/share/icons/shiplog.svg"
  cat > "$DEST" <<DESK
[Desktop Entry]
Type=Application
Name=Shiplog
Comment=Posts do LinkedIn e artigos do Medium a partir dos seus repositórios
Exec=$APP
Icon=$HOME/.local/share/icons/shiplog.svg
Terminal=false
Categories=Development;
Actions=stop;

[Desktop Action stop]
Name=Parar Shiplog
Exec=$STOP
DESK
  echo "Criado $DEST (procure 'Shiplog' no menu de aplicativos)."
fi
