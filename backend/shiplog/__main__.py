"""Entrypoint `shiplog`: sobe o servidor em 127.0.0.1 e abre o navegador (spec 000 FR-02, NFR-01)."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

from .config import HOST, resolve_port


def is_wsl() -> bool:
    return "microsoft" in platform.release().lower() or bool(os.environ.get("WSL_DISTRO_NAME"))


def abrir_navegador(url: str) -> None:
    """Abre o navegador; no WSL usa o navegador do Windows."""
    if is_wsl():
        for cmd in (["wslview", url], ["cmd.exe", "/c", "start", "", url], ["explorer.exe", url]):
            if shutil.which(cmd[0]):
                try:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd="/")
                    return
                except OSError:
                    continue
    webbrowser.open(url)


def ja_rodando(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/api/ping", timeout=1) as r:
            return json.loads(r.read()).get("app") == "shiplog"
    except Exception:
        return False


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="shiplog", description="Shiplog — posts do LinkedIn a partir de repositórios.")
    ap.add_argument("--port", type=int, default=resolve_port())
    ap.add_argument("--no-browser", action="store_true", help="não abrir o navegador")
    ap.add_argument("--reload", action="store_true", help="modo desenvolvimento (recarrega ao editar o código)")
    args = ap.parse_args(argv)

    url = f"http://{HOST}:{args.port}"
    if ja_rodando(url):
        print(f"Shiplog já está rodando em {url}")
        if not args.no_browser:
            abrir_navegador(url)
        return

    if not args.no_browser:
        def esperar_e_abrir() -> None:
            for _ in range(100):
                if ja_rodando(url):
                    abrir_navegador(url)
                    return
                time.sleep(0.1)

        threading.Thread(target=esperar_e_abrir, daemon=True).start()

    import uvicorn

    from .config import Paths, resolve_data_dir

    pid_file = Paths(resolve_data_dir()).ensure().data_dir / "shiplog.pid"
    pid_file.write_text(str(os.getpid()))
    print(f"Shiplog em {url}  (Ctrl+C para encerrar)")
    try:
        if args.reload:
            uvicorn.run("shiplog.app:create_app", factory=True, host=HOST, port=args.port, reload=True,
                        reload_dirs=[os.path.dirname(__file__)], log_level="warning")
        else:
            from .app import create_app

            uvicorn.run(create_app(), host=HOST, port=args.port, log_level="warning")
    except OSError as e:  # pragma: no cover
        print(f"Não foi possível usar a porta {args.port}: {e}. Tente SHIPLOG_PORT=8766.", file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            if pid_file.read_text().strip() == str(os.getpid()):
                pid_file.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    main()
