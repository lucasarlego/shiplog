# Segurança e privacidade

- O servidor escuta só em `127.0.0.1` e recusa requisições com outro `Host` (proteção contra DNS rebinding).
- Nada sai da sua máquina, exceto o que o seu próprio Claude Code envia ao Claude. Não há telemetria nem integração com LinkedIn ou Medium.
- O Claude roda com ferramentas mínimas: `Read`/`Grep`/`Glob` no clone do repositório; `Read` só na pasta do currículo ou do comentário; nenhuma ferramenta no post a partir de descrição. Bash, Edit, Write e Web ficam bloqueados.
- O perfil profissional nunca guarda e-mail ou telefone (o prompt proíbe e o backend remove).

---

[← Voltar ao README](../../README.md)
