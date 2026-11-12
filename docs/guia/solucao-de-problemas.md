# Solução de problemas

| Sintoma | O que fazer |
| --- | --- |
| Banner "Claude Code não encontrado/autenticado" | Rode `claude` no terminal e faça `/login`; ou informe o caminho do executável em Configurações. |
| "Sem acesso ao repositório" | Teste `git ls-remote <url>` no terminal; configure sua chave SSH ou credential helper. |
| "Limite de uso" | Limite da assinatura atingido; tente mais tarde — os parâmetros ficam salvos ("Tentar novamente"). |
| Atalho não abre nada | Veja `~/.shiplog/logs/server.out` no WSL; rode `make run` para ver o erro no terminal. |
| Porta ocupada | `PORT=8766 make run` (ou `SHIPLOG_PORT=8766`). |

---

[← Voltar ao README](../../README.md)
