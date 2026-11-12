# Rotina projeto-primeiro com SDD (Claude Code)

Rotina padrão para artigos técnicos quando a skill roda no Claude Code, com terminal, git, `gh` e as credenciais do autor. Cada artigo é **um repositório próprio no GitHub do autor**, e o projeto segue **Spec-Driven Development (SDD)**: nenhuma linha de código de implementação é escrita antes de as specs estarem aprovadas pelo autor.

Ordem fixa: **briefing → spec → plano → tarefas → implementação → evidências → artigo → verificação**. Cada seta até a implementação é um gate com aprovação explícita do autor.

## Sumário

1. O que é fixo e o que não é
2. Estrutura das specs: `_template/`
3. Etapa 0 — Briefing e repositório
4. Etapa 1 — Preparar as specs
5. Etapa 2 — Spec (gate)
6. Etapa 3 — Plano técnico (gate)
7. Etapa 4 — Tarefas (gate)
8. Etapa 5 — Implementação
9. Etapa 6 — Execução e evidências
10. Etapa 7 — Congelamento
11. Etapa 8 — Artigo e verificação
12. Segurança, custo e permissões

---

## 1. O que é fixo e o que não é

**Não é fixo:** a estrutura do código, a stack, como a demonstração é executada (CLI, servidor, notebook, teste end-to-end, deploy em Cloud Run, interface web…). Tudo isso nasce do plano técnico de cada projeto, de acordo com o que o artigo precisa mostrar. Não imponha pastas como `src/` ou `demo/`.

**É fixo (convenções mínimas para a rotina funcionar):**
- a pasta `specs/` com `_template/` (spec.md, plan.md, tasks.md) e uma pasta por feature, versionadas no repositório;
- uma pasta de evidências (padrão `evidence/`, outro nome se o plano definir) com as saídas reais e um `manifest.json`;
- uma pasta do artigo (padrão `article/`);
- `README.md` com setup e como reproduzir cada demonstração;
- `.env.example` e `.gitignore` sem segredos.

## 2. Estrutura das specs: `_template/`

O autor usa a seguinte convenção de SDD (não use o GitHub Spec Kit nem outra ferramenta, a menos que ele peça):

```
specs/
├── _template/          # referência: copiada da skill, nunca editada por feature
│   ├── spec.md
│   ├── plan.md
│   └── tasks.md
└── 01-<nome-da-feature>/
    ├── spec.md         # cópia de _template/spec.md, preenchida
    ├── plan.md         # cópia de _template/plan.md, preenchida
    └── tasks.md        # cópia de _template/tasks.md, preenchida
```

- `_template/` vem de `assets/_template/` da skill e é commitada em todo repositório como referência.
- Cada feature ganha uma pasta numerada (`01-`, `02-`…). A maioria dos projetos de artigo terá uma única feature; crie mais só se o projeto tiver partes realmente independentes.
- Cada documento só é preenchido depois que o anterior foi aprovado: spec → plan → tasks.
- O status de aprovação fica no cabeçalho de cada arquivo e no checkbox da seção "Aprovação", com data.
- Se o autor tiver templates próprios atualizados (no repositório ou colados na conversa), use os dele no lugar dos da skill.

## 3. Etapa 0 — Briefing e repositório

1. Faça o briefing e a entrevista da skill (Fases 0 e 1) e defina a **mensagem central** e o **padrão de artigo**.
2. Liste os **cenários de demonstração**: 2 a 5 afirmações centrais do artigo, cada uma com o que precisa ser mostrado para prová-la. Isso alimenta a spec.
3. Grave em `article/brief.md`.
4. Proponha o repositório: nome (slug do tema), descrição, visibilidade (**privado até a publicação** é o padrão sugerido) e licença. **Peça confirmação** e então crie com `gh repo create` e faça o primeiro commit (brief + `.gitignore`).

## 4. Etapa 1 — Preparar as specs

Crie `specs/_template/` copiando `assets/_template/` da skill e a pasta da primeira feature (`specs/01-<nome>/`) com cópias dos três templates. Faça commit (`specs: estrutura inicial`).

## 5. Etapa 2 — Spec (gate)

A spec descreve **o quê e por quê**, sem tecnologia:
- problema e público do projeto (o leitor do artigo);
- user stories / cenários com critérios de aceitação verificáveis — cada cenário de demonstração do brief vira pelo menos um;
- requisitos funcionais e não funcionais (ex.: "a demo roda em menos de 2 minutos", "custo de nuvem por execução abaixo de US$ X");
- fora de escopo;
- pontos em aberto marcados como `[PRECISA DE ESCLARECIMENTO]` — resolva com o autor antes de pedir aprovação.

Preencha `specs/01-<nome>/spec.md` seguindo o template.

**Gate:** apresente a spec ao autor, peça aprovação explícita e registre-a no cabeçalho e na seção Aprovação, com commit `spec: aprovada`. Sem aprovação, não avance.

## 6. Etapa 3 — Plano técnico (gate)

O plano define **como**, e é aqui que a estrutura do código nasce:
- stack e versões (consulte a documentação atual das bibliotecas, não confie na memória);
- arquitetura e estrutura de pastas **específicas deste projeto**;
- como cada cenário será demonstrado e **como a evidência será capturada** (qual comando/teste/execução gera qual arquivo em `evidence/`, o que será print de interface);
- recursos de nuvem, custo estimado e teardown;
- estratégia de testes ligada aos critérios de aceitação;
- quais trechos de código provavelmente irão para o artigo (marque-os com comentários de região na implementação, ex. `# region: nome` / `# endregion`).

Preencha `plan.md` seguindo o template, incluindo a tabela de rastreabilidade (requisito → componente → teste) e a verificação contra `references/principios-projeto-demonstrativo.md`. Confira que todo RF e todo CD da spec aparece no plano.

**Gate:** aprovação explícita do autor, registrada no arquivo, commit `plan: aprovado`.

## 7. Etapa 4 — Tarefas (gate)

Preencha `tasks.md` seguindo o template: tarefas pequenas, ordenadas e testáveis, cada uma ligada a um requisito/cenário da spec. Inclua tarefas explícitas para: testes, captura de evidências, README, teardown.

**Gate:** aprovação do autor, registrada no arquivo, commit `tasks: aprovadas`. Pode ser rápida; o importante é ele ver o escopo do que será construído.

## 8. Etapa 5 — Implementação

- Implemente tarefa por tarefa, na ordem de `tasks.md`, marcando `[x]` ao concluir.
- Commits pequenos referenciando o ID da tarefa (ex.: `T020: ...`).
- Código didático: é material de ensino. Clareza acima de abstração.
- **Se a implementação revelar que a spec ou o plano estão errados, pare, atualize o artefato e peça nova aprovação ao autor.** O código nunca diverge silenciosamente da spec.

## 9. Etapa 6 — Execução e evidências

1. Testes verdes. Não "conserte" teste para passar.
2. Execute cada cenário como o plano definiu, com as credenciais reais do autor, gravando as saídas em `evidence/`.
3. `evidence/manifest.json`: data/hora, git sha, versões da linguagem e das dependências principais, modelo de LLM, região, e o comando de cada cenário.
4. Mascare segredos e dados sensíveis; rode `scripts/verify_article.py <repo> --secrets-only`.
5. Registre falhas e limitações relevantes observadas — viram conteúdo honesto do artigo.
6. Se um resultado contradisser o que o artigo pretendia afirmar, **pare e avise o autor**: muda o artigo, não a evidência.
7. Liste os prints de interface que o autor precisa capturar.

## 10. Etapa 7 — Congelamento

Commit final e tag `article-v1`. Push para o GitHub do autor (o repositório já existe; confirme antes de cada push se o autor não tiver autorizado pushes nesta sessão).

## 11. Etapa 8 — Artigo e verificação

Siga as fases de outline, redação, revisão e pacote da skill com as regras:
- o artigo só afirma o que a spec, o código e `evidence/` sustentam; a spec ajuda a estruturar a narrativa (problema → cenários → solução);
- código copiado das regiões marcadas, sem reescrever; saídas em blocos `text` copiadas de `evidence/`; comandos `bash` iguais aos do README;
- link para o repositório na tag `article-v1`;
- escreva em `article/article.md` e o pacote em `article/publish.md`.

Depois rode:

```bash
python <skill>/scripts/verify_article.py <repo>
```

Corrija até passar. Na publicação, proponha tornar o repositório público e atualizar o README com o link do artigo (com confirmação).

## 12. Segurança, custo e permissões

- Credenciais nunca em arquivos versionados.
- **Confirme antes de:** criar o repositório, tornar público, push, criar recursos pagos (diga o quê e o custo estimado), deploy.
- Teardown dos recursos após capturar evidências, a menos que o autor peça para manter.
- Ambientes de teste do autor, nunca produção de cliente; nada de código ou dado de cliente no repositório público.
