# Arquitetura

```
frontend/ (React + Vite + Tailwind v4 + Radix + Motion)  →  build estático servido pelo FastAPI
backend/shiplog/
  api/        rotas REST finas
  services/   projetos, git, metadados, prompts, schemas, geração, fila de jobs, health, perfil, comentários
  services/llm/  interface LLMProvider + ClaudeCliProvider (trocar por outro provedor = nova implementação)
  storage/    SQLite + migrações SQL
```

---

[← Voltar ao README](../../README.md)
