#!/usr/bin/env python3
"""Verificação cruzada entre o artigo e o projeto demonstrativo.

Uso:
    python verify_article.py <repo>                 # verificação completa
    python verify_article.py <repo> --secrets-only  # só busca segredos em evidence/
    python verify_article.py <repo> --article caminho/para/article.md --evidence outra_pasta

Checagens:
  1. Todo bloco de código (exceto text/output/console/bash/shell/sh) do artigo
     existe, linha a linha e em sequência, em algum arquivo do repositório.
  2. Todo bloco `text`/`output`/`console` existe em algum arquivo de evidence/
     (linhas "..." são tratadas como cortes permitidos).
  3. Blocos bash/shell: avisa se o comando não aparece no README.
  4. Nenhum segredo aparente em evidence/ ou no artigo.
  5. Lista os TK pendentes.

Sai com código 1 se houver erro.
"""
import argparse
import re
import sys
from pathlib import Path

OUTPUT_LANGS = {"text", "output", "console", "log", "plaintext"}
COMMAND_LANGS = {"bash", "shell", "sh", "zsh"}
SKIP_DIRS = {".git", ".specify", "specs", ".venv", "venv", "node_modules", "__pycache__", "article", ".mypy_cache", ".pytest_cache"}
SECRET_PATTERNS = [
    (r"AIza[0-9A-Za-z\-_]{35}", "Google API key"),
    (r"sk-[A-Za-z0-9_\-]{20,}", "API key estilo sk-"),
    (r"ghp_[A-Za-z0-9]{36}", "GitHub token"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "chave privada"),
    (r"ya29\.[0-9A-Za-z\-_]+", "OAuth access token Google"),
    (r"xox[baprs]-[0-9A-Za-z\-]+", "Slack token"),
    (r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}", "atribuição de segredo"),
]
FENCE = re.compile(r"^```([^\n`]*)\n(.*?)^```", re.S | re.M)


def norm_lines(text):
    return [l.rstrip() for l in text.strip("\n").splitlines() if l.strip()]


def read_files(root, only_dir=None):
    base = root / only_dir if only_dir else root
    files = {}
    if not base.exists():
        return files
    for p in base.rglob("*"):
        if not p.is_file() or any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        try:
            files[p] = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
    return files


def contains_sequence(haystack_lines, needle_lines):
    """Verifica se needle aparece em ordem em haystack, permitindo cortes '...'."""
    chunks, cur = [], []
    for l in needle_lines:
        if l.strip() in {"...", "…", "# ...", "// ..."}:
            if cur:
                chunks.append(cur)
            cur = []
        else:
            cur.append(l.strip())
    if cur:
        chunks.append(cur)
    hay = [l.strip() for l in haystack_lines]
    pos = 0
    for chunk in chunks:
        found = False
        for i in range(pos, len(hay) - len(chunk) + 1):
            if hay[i:i + len(chunk)] == chunk:
                pos = i + len(chunk)
                found = True
                break
        if not found:
            return False
    return True


def scan_secrets(files):
    hits = []
    for path, text in files.items():
        for pat, label in SECRET_PATTERNS:
            for m in re.finditer(pat, text):
                hits.append((path, label, m.group(0)[:12] + "…"))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--article", default=None)
    ap.add_argument("--evidence", default="evidence", help="pasta de evidências relativa ao repo")
    ap.add_argument("--secrets-only", action="store_true")
    args = ap.parse_args()

    root = Path(args.repo).resolve()
    evidence = read_files(root, args.evidence)
    errors, warnings = [], []

    article_path = Path(args.article) if args.article else root / "article" / "article.md"
    article = article_path.read_text(encoding="utf-8") if article_path.exists() else ""

    secret_targets = dict(evidence)
    if article:
        secret_targets[article_path] = article
    for path, label, preview in scan_secrets(secret_targets):
        errors.append(f"Possível segredo ({label}) em {path.relative_to(root) if path.is_relative_to(root) else path}: {preview}")

    if args.secrets_only:
        report(errors, warnings, [])
        return

    if not article:
        print(f"ERRO: artigo não encontrado em {article_path}")
        sys.exit(1)
    if not evidence:
        errors.append("Pasta evidence/ vazia ou inexistente — o artigo não tem saídas reais registradas.")

    code_files = read_files(root)
    code_lines = {p: t.splitlines() for p, t in code_files.items() if args.evidence not in p.relative_to(root).parts}
    evidence_lines = {p: t.splitlines() for p, t in evidence.items()}
    readme = (root / "README.md").read_text(encoding="utf-8") if (root / "README.md").exists() else ""

    blocks = FENCE.findall(article)
    n_code = n_out = 0
    for i, (lang, body) in enumerate(blocks, 1):
        lang = lang.strip().lower().split()[0] if lang.strip() else ""
        lines = norm_lines(body)
        if not lines or "TK" in body:
            if "TK" in body:
                warnings.append(f"Bloco {i} ({lang or 'sem linguagem'}) ainda é TK.")
            continue
        preview = lines[0][:60]
        if lang in OUTPUT_LANGS:
            n_out += 1
            if not any(contains_sequence(h, lines) for h in evidence_lines.values()):
                errors.append(f"Bloco {i} (saída) não encontrado em evidence/: «{preview}»")
        elif lang in COMMAND_LANGS:
            for cmd in lines:
                c = cmd.lstrip("$ ").strip()
                if c and not c.startswith("#") and c not in readme:
                    warnings.append(f"Bloco {i} (comando) não aparece no README: «{c[:60]}»")
        else:
            n_code += 1
            if not lang:
                warnings.append(f"Bloco {i} sem linguagem declarada: «{preview}»")
            if not any(contains_sequence(h, lines) for h in code_lines.values()):
                errors.append(f"Bloco {i} ({lang or '?'}) não encontrado no repositório: «{preview}»")

    if n_code == 0:
        errors.append("O artigo não tem nenhum bloco de código do projeto.")
    if n_out == 0:
        errors.append("O artigo não mostra nenhuma saída real (blocos ```text vindos de evidence/).")

    tks = [l.strip() for l in article.splitlines() if re.search(r"\bTK\b", l)]
    report(errors, warnings, tks)


def report(errors, warnings, tks):
    for e in errors:
        print(f"ERRO   {e}")
    for w in warnings:
        print(f"AVISO  {w}")
    if tks:
        print(f"\n{len(tks)} TK pendente(s):")
        for t in tks:
            print(f"  - {t[:100]}")
    print(f"\nResultado: {'FALHOU' if errors else 'OK'} — {len(errors)} erro(s), {len(warnings)} aviso(s), {len(tks)} TK(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
