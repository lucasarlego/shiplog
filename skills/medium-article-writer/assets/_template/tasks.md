# Tarefas — [Nome da feature/projeto]

> Status: RASCUNHO | **APROVADAS em AAAA-MM-DD por [autor]**
> Spec: `./spec.md` · Plano: `./plan.md` (ambos APROVADOS)

Formato: `- [ ] T### [P] descrição — refs: RF/CA/CD`
`[P]` = pode ser feita em paralelo. Marque `[x]` ao concluir e referencie o ID no commit.

## Fase 1 — Setup
- [ ] T001 Estrutura do repositório conforme o plano, `.gitignore`, `.env.example` — refs: RNF-03
- [ ] T002 Dependências com versões fixadas — refs: plano §2

## Fase 2 — Testes (antes da implementação, quando viável)
- [ ] T010 Teste para CA-01.1 — refs: HU-01, CA-01.1

## Fase 3 — Implementação
- [ ] T020 [descrição] — refs: RF-01

## Fase 4 — Demonstração e evidências
- [ ] T030 Executar CD-01 e gravar `evidence/[arquivo].txt` — refs: CD-01
- [ ] T031 Gerar `evidence/manifest.json`
- [ ] T032 Revisar e mascarar segredos nas evidências
- [ ] T033 Listar prints que o autor precisa capturar

## Fase 5 — Documentação e encerramento
- [ ] T040 README com setup e reprodução de cada cenário
- [ ] T041 Teardown dos recursos de nuvem
- [ ] T042 Commit final e tag `article-v1`

## Aprovação
- [ ] Autor aprovou as tarefas (data: ____)
