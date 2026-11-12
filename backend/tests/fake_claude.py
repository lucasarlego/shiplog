#!/usr/bin/env python3
"""CLI do Claude simulado (RNF-08).

Controlado por variáveis de ambiente:
- FAKE_CLAUDE_LOG: arquivo JSONL onde cada chamada registra argv, cwd, env relevante e stdin.
- FAKE_CLAUDE_SCRIPT: arquivo JSON com a lista de ações, consumida uma por chamada `-p`
  (estado em FAKE_CLAUDE_SCRIPT + ".idx"). Ações:
    {"structured": {...}}           resposta de sucesso com structured_output
    {"result": "texto"}             sucesso só com texto em result
    {"error": "mensagem", "code": 1}  is_error=true
    {"sleep": 30}                   dorme (para timeout/cancelamento)
    {"write": "arquivo.txt", ...}   escreve um arquivo no cwd antes de responder
    {"stderr": "msg", "exit": 1}    sai sem JSON
"""

import json
import os
import sys
import time


def main() -> int:
    argv = sys.argv[1:]
    if argv[:1] == ["--version"]:
        print("9.9.9 (Claude Code)")
        return 0
    if argv[:2] == ["auth", "status"]:
        logged = os.environ.get("FAKE_CLAUDE_LOGGED", "1") == "1"
        print(json.dumps({"loggedIn": logged, "authMethod": "claude.ai" if logged else "none"}))
        return 0 if logged else 1

    stdin = sys.stdin.read()
    log = os.environ.get("FAKE_CLAUDE_LOG")
    if log:
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "argv": argv, "cwd": os.getcwd(), "stdin": stdin,
                "has_api_key": "ANTHROPIC_API_KEY" in os.environ,
            }) + "\n")

    script = os.environ.get("FAKE_CLAUDE_SCRIPT")
    acoes = json.load(open(script, encoding="utf-8")) if script else [{"result": "{}"}]
    idx_file = (script or "") + ".idx"
    idx = int(open(idx_file).read()) if script and os.path.exists(idx_file) else 0
    if script:
        open(idx_file, "w").write(str(idx + 1))
    acao = acoes[min(idx, len(acoes) - 1)]

    if "sleep" in acao:
        time.sleep(acao["sleep"])
    if "write" in acao:
        with open(acao["write"], "w") as f:
            f.write("alterado")
    if "stderr" in acao:
        sys.stderr.write(acao["stderr"])
        return acao.get("exit", 1)

    env = {"type": "result", "subtype": "success", "is_error": False, "num_turns": 3, "duration_ms": 10}
    if "error" in acao:
        env.update(is_error=True, subtype="error", result=acao["error"])
        print(json.dumps(env, ensure_ascii=False))
        return acao.get("code", 1)
    if "structured" in acao:
        env.update(result=json.dumps(acao["structured"]), structured_output=acao["structured"])
    else:
        env.update(result=acao.get("result", ""))
    print(json.dumps(env, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
