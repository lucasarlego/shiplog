# Padrões de artigo

A maioria dos artigos bem-sucedidos cai num padrão reconhecível. Escolher o padrão certo resolve metade da estrutura. Os padrões técnicos se apoiam na tipologia de *Writing for Developers* (Sarna & Dunlop) e nos exemplos que o Medium cita como dignos de Boost; os não técnicos, nas diretrizes de curadoria do Medium.

**Em todos os padrões técnicos, a demonstração real é obrigatória** (ver "Política de demonstração técnica" no SKILL.md). Abaixo, o que conta como demonstração em cada um.

Combine padrões quando fizer sentido (ex.: um "how we built it" com uma seção de lições aprendidas), mas mantenha um padrão dominante.

## Sumário

1. Tutorial prático (how-to)
2. Deep dive conceitual ("X explicado")
3. How we built it (arquitetura e decisões)
4. Lições aprendidas / Bug hunt / Post-mortem
5. Comparativo / Benchmark
6. Opinião / Tendência
7. Paper, release ou ferramenta explicada
8. Ensaio pessoal / carreira (não técnico)
9. Guia prático não técnico ("tutorial empático")
10. Lista — use com cautela

---

## 1. Tutorial prático (how-to)

**Quando:** o leitor quer construir/fazer algo concreto. É o formato mais buscado no Google e o que mais gera salvamentos.

**Estrutura:**
1. Problema e resultado final logo de cara (o que vamos construir; um diagrama, print ou trecho do resultado).
2. Por que essa abordagem (vs. a alternativa óbvia) — em 1 ou 2 parágrafos.
3. Pré-requisitos com versões (linguagem, SDK, contas, permissões).
4. Passos incrementais, cada um com: objetivo do passo → código → explicação do que não é óbvio → como verificar que funcionou.
5. Erros comuns e como resolvê-los (aqui entra a experiência do autor).
6. Próximos passos: extensões, produção, limitações.
7. Repositório completo e referências.

**Armadilhas:** virar paráfrase da documentação oficial; pular o "por quê"; código que não roda por falta de import ou versão; passos grandes demais.

**Demonstração:** cada passo termina com a saída real que comprova que funcionou; o resultado final aparece executado (print, resposta, log).

**Sinal de qualidade:** o leitor consegue reproduzir do zero e entende cada decisão. Antecipa as dúvidas que surgirão no caminho.

## 2. Deep dive conceitual ("X explicado")

**Quando:** explicar como algo funciona por dentro (attention, RAG, MCP, embeddings, consenso distribuído). Referência de estilo: os artigos ilustrados de Jay Alammar e os posts de Lilian Weng — intuição primeiro, formalismo depois.

**Estrutura:**
1. Pergunta motivadora ou cenário concreto em que o conceito importa.
2. Intuição com analogia ou exemplo mínimo.
3. Construção em camadas: versão simplificada → complicações reais → versão completa.
4. Diagramas a cada salto conceitual.
5. Onde o conceito quebra, limitações, equívocos comuns.
6. Para ir além: papers e fontes primárias.

**Demonstração:** um exemplo mínimo executável que torna o conceito observável (ex.: imprimir os embeddings e a similaridade, mostrar a mensagem MCP trafegando).

**Armadilhas:** analogia que engana mais do que ajuda; despejar fórmulas sem intuição; não dizer para quem é.

## 3. How we built it (arquitetura e decisões)

**Quando:** o autor construiu um sistema real e as decisões dele têm valor para quem enfrenta o mesmo problema. É o padrão que mais aproveita a experiência de primeira mão.

**Estrutura:**
1. Contexto e problema de negócio/técnico (com números de escala, se houver).
2. Restrições (custo, latência, equipe, prazo, compliance).
3. Arquitetura geral (diagrama).
4. Decisões-chave como decision log: opção escolhida, alternativas consideradas, trade-off aceito.
5. Resultados medidos (antes/depois).
6. O que faríamos diferente.

**Demonstração:** trechos reais do sistema (código, configuração, logs, traces) e métricas medidas em produção ou em teste, com a forma de medição.

**Armadilhas:** virar peça de marketing da empresa; esconder os problemas; descrever componentes sem explicar por que foram escolhidos. Cuidado com informação confidencial de cliente — pergunte ao autor o que pode ser exposto e anonimize.

## 4. Lições aprendidas / Bug hunt / Post-mortem

**Quando:** algo deu errado (ou foi difícil) e a jornada ensina algo transferível.

**Estrutura narrativa:**
1. Gancho com o sintoma ("Às 3h da manhã, o agente começou a responder em loop…").
2. Contexto mínimo necessário.
3. Hipóteses testadas e descartadas (é aqui que o leitor aprende a depurar).
4. Causa raiz.
5. Correção.
6. Lição generalizável e como evitar.

**Demonstração:** o erro real (stack trace, log, comportamento), a reprodução mínima e a prova de que a correção resolveu.

**Armadilhas:** contar tudo em ordem cronológica sem cortar; lição tão específica que não serve a ninguém; lição tão genérica que é óbvia.

## 5. Comparativo / Benchmark

**Quando:** o leitor precisa escolher entre opções (frameworks, modelos, serviços).

**Estrutura:**
1. A decisão que o leitor enfrenta.
2. Critérios explícitos e por que importam.
3. Metodologia reproduzível (dataset, hardware, versões, prompts).
4. Resultados por critério (gráfico ou imagem de tabela, já que o Medium não tem tabelas).
5. Recomendação por cenário ("se você precisa de X, use A; se Y, B").
6. Limitações da comparação.

**Demonstração:** o código do benchmark e as saídas reais de cada opção; nada de números de terceiros apresentados como medição própria.

**Armadilhas:** comparar versões desatualizadas; conclusão "depende" sem dizer do quê; viés não declarado (ex.: o autor trabalha com uma das ferramentas).

## 6. Opinião / Tendência

**Quando:** o autor tem uma tese defensável sobre a direção da área.

**Estrutura:**
1. Tese clara já no primeiro ou segundo parágrafo.
2. Evidências e experiência que a sustentam.
3. O melhor argumento contrário, apresentado com honestidade, e por que a tese ainda se sustenta.
4. Implicações práticas: o que o leitor deveria fazer diferente.

**Demonstração (se o tema for técnico):** pelo menos um experimento ou exemplo executado que sustente a tese.

**Armadilhas:** "hot take" sem evidência; desabafo sem insight (o Medium tira de distribuição negatividade não construtiva); hype ("X vai mudar tudo").

## 7. Paper, release ou ferramenta explicada

**Quando:** algo novo saiu (paper, versão de SDK, modelo) e o autor pode explicar com contexto prático.

**Estrutura:**
1. O que é, em uma frase.
2. Por que importa (que problema resolve, o que muda em relação ao anterior).
3. Como funciona (o suficiente para o público alvo).
4. Teste prático ou exemplo do autor — é o que diferencia de um resumo.
5. Limitações e para quem não serve.
6. Links para a fonte primária.

**Demonstração:** o teste prático do item 4, executado de verdade, com saída real.

**Armadilhas:** só resumir o anúncio oficial (conteúdo derivativo); envelhecer rápido — date explicitamente as versões.

## 8. Ensaio pessoal / carreira (não técnico)

**Quando:** experiência pessoal ou profissional que leva a um insight que outras pessoas podem usar ou reconhecer.

**Estrutura:**
1. Abertura em cena (um momento concreto, não uma tese abstrata).
2. Tensão: o que estava em jogo, o que não funcionava.
3. Virada: o que o autor percebeu ou mudou.
4. Insight universal, sem perder os detalhes específicos que tornam a história única.

**Armadilhas:** narrar cada detalhe ("play-by-play"); sentimentalismo; conselho genérico que qualquer um daria. Mostrar, não dizer.

## 9. Guia prático não técnico ("tutorial empático")

**Quando:** ensinar algo fora da tecnologia (produtividade, finanças pessoais, hobby, processo de trabalho).

**Estrutura:** como o tutorial técnico, mas com mais peso em antecipar as dificuldades do leitor e em mostrar que o autor testou o que recomenda.

**Armadilhas:** recomendação sem experiência real por trás; tom de autoajuda genérica.

## 10. Lista — use com cautela

Listas genéricas ("10 ferramentas de IA que você precisa conhecer") são o exemplo clássico de conteúdo derivativo que perde distribuição. Uma lista só funciona se: cada item tem substância própria (experiência, exemplo, critério), existe um fio condutor, e a seleção reflete o julgamento do autor. Se o conteúdo puder ser reorganizado como comparativo ou guia, prefira isso.
