"""Provedor Claude Code CLI em modo headless (spec 003 §3.1; RI-01..RI-04, RI-08; R-02, R-03, R-05)."""

from __future__ import annotations

import json
import os
import re
import shutil
import threading
from typing import Any, Callable

from .. import proc
from .base import LLMRequest, LLMResult

READ_ONLY_TOOLS = ["Read", "Grep", "Glob"]
BLOCKED_TOOLS = ["Bash", "Edit", "Write", "MultiEdit", "NotebookEdit", "WebFetch", "WebSearch", "Task", "Agent"]
# R-02/R-03: força a assinatura logada; nunca a API paga.
ENV_REMOVIDAS = (
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY", "ANTHROPIC_BASE_URL",
)

_LIMITE = re.compile(r"usage limit|rate limit|limit reached|limit will reset|quota|too many requests|\b429\b|hit your limit", re.I)
_AUTH = re.compile(r"not logged in|please run /login|invalid api key|authentication|unauthorized|\b401\b|oauth token", re.I)

INSTALAR = "Instale o Claude Code (`npm install -g @anthropic-ai/claude-code`) ou informe o caminho em Configurações."
LOGIN = "Abra um terminal, rode `claude` e faça login com `/login` (ou `claude auth login`)."


def resolver_cli(caminho: str | None) -> str | None:
    if caminho:
        if os.path.isfile(caminho):
            return caminho
        return shutil.which(caminho)
    return shutil.which("claude")


def subprocess_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in ENV_REMOVIDAS}
    env.setdefault("NO_COLOR", "1")
    return env


def build_command(cli: str, req: LLMRequest, schema: bool = True) -> list[str]:
    tools = list(req.tools)
    if req.allow_skills and "Skill" not in tools:
        tools.append("Skill")
    cmd = [cli, "-p", "--output-format", "json"]
    if schema:
        cmd += ["--json-schema", json.dumps(req.json_schema, ensure_ascii=False)]
    cmd += ["--tools", ",".join(tools)]
    if tools:
        cmd += ["--allowedTools", *tools]
    cmd += ["--disallowedTools", *BLOCKED_TOOLS]
    cmd += ["--permission-mode", "dontAsk", "--strict-mcp-config", "--no-session-persistence"]
    if not req.allow_skills:
        cmd.append("--disable-slash-commands")
    if req.model:
        cmd += ["--model", req.model]
    return cmd


def extrair_json(texto: str) -> Any:
    """Extrai o primeiro objeto JSON de um texto (tolera cercas ```json)."""
    if not texto:
        return None
    t = texto.strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", t, re.S)
    if m:
        t = m.group(1)
    try:
        return json.loads(t)
    except ValueError:
        pass
    ini = t.find("{")
    while ini != -1:
        prof = 0
        em_str = esc = False
        for i in range(ini, len(t)):
            ch = t[i]
            if em_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    em_str = False
            elif ch == '"':
                em_str = True
            elif ch == "{":
                prof += 1
            elif ch == "}":
                prof -= 1
                if prof == 0:
                    try:
                        return json.loads(t[ini : i + 1])
                    except ValueError:
                        break
        ini = t.find("{", ini + 1)
    return None


def classificar(msg: str) -> tuple[str, str]:
    if _LIMITE.search(msg):
        return "limite_uso", "Tente novamente mais tarde; seus parâmetros foram mantidos."
    if _AUTH.search(msg):
        return "cli_nao_autenticado", LOGIN
    return "cli_falha", "Veja os detalhes da geração e tente novamente."


class ClaudeCliProvider:
    def __init__(self, cli_path: Callable[[], str | None]) -> None:
        self._cli_path = cli_path

    def run(self, req: LLMRequest, cancel: threading.Event | None = None) -> LLMResult:
        cli = resolver_cli(self._cli_path())
        if not cli:
            return LLMResult(False, None, "", None, 0, "cli_nao_encontrado", "Claude Code CLI não encontrado.",
                             {"acao": INSTALAR})
        cmd = build_command(cli, req)
        r = proc.run(cmd, cwd=req.cwd, timeout=req.timeout_s, cancel=cancel, env=subprocess_env(),
                     input_text=req.prompt)
        raw = r.stdout if r.stdout.strip() else r.stderr
        base = dict(raw=raw, exit_code=r.returncode, duration_ms=r.duration_ms)
        if r.not_found:
            return LLMResult(False, None, r.stderr, None, 0, "cli_nao_encontrado",
                             "Claude Code CLI não encontrado.", {"acao": INSTALAR})
        if r.cancelled:
            return LLMResult(False, None, **base, error_code="cancelado", error_message="Geração cancelada.")
        if r.timed_out:
            return LLMResult(False, None, **base, error_code="timeout",
                             error_message=f"A geração passou de {req.timeout_s} s e foi encerrada.",
                             meta={"acao": "Tente novamente ou aumente o timeout em Configurações."})

        envelope = extrair_json(r.stdout) if r.stdout.strip() else None
        if not isinstance(envelope, dict) or "type" not in envelope:
            msg = (r.stderr or r.stdout or "Sem saída do CLI.").strip()
            codigo, acao = classificar(msg)
            return LLMResult(False, None, **base, error_code=codigo, error_message=msg[-1500:], meta={"acao": acao})

        resultado = envelope.get("result") or ""
        if envelope.get("is_error") or r.returncode not in (0, None):
            msg = str(resultado or envelope.get("subtype") or r.stderr or "Erro do Claude Code.").strip()
            codigo, acao = classificar(msg + " " + (r.stderr or "") + " " + str(envelope.get("api_error_status") or ""))
            return LLMResult(False, None, **base, error_code=codigo, error_message=msg[-1500:],
                             meta={"acao": acao, "subtype": envelope.get("subtype")})

        data = envelope.get("structured_output")
        if not isinstance(data, dict):
            data = extrair_json(resultado) if isinstance(resultado, str) else None
        return LLMResult(True, data if isinstance(data, dict) else None, **base,
                         meta={"result_text": resultado, "num_turns": envelope.get("num_turns")})
