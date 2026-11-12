---
name: medium-article-writer
description: Escreve, estrutura e revisa artigos para o Medium (e publicações como Towards Data Science, Towards AI, Google Cloud Community, Better Programming) sobre qualquer tema, em qualquer idioma, técnicos ou não técnicos. Use SEMPRE que o usuário pedir um artigo, post, story ou blog post para o Medium, quiser transformar um projeto, código, repositório, aprendizado ou experiência em artigo, pedir títulos/subtítulos/tags para um post, revisar ou melhorar um rascunho de artigo, adaptar um artigo para outro idioma, pedir para criar um projeto/código demonstrativo e depois o artigo (rotina projeto-primeiro com specs/SDD), ou mencionar "escrever no Medium", "publicar um artigo", "write a Medium post", "blog post técnico", tutorial escrito ou deep dive — mesmo que não diga "skill" nem "Medium" explicitamente.
---

# Medium Article Writer

Esta skill transforma o conhecimento e a experiência real do autor em artigos que valem o tempo de quem lê — em qualquer idioma, técnicos ou não. Ela combina:

- as diretrizes de curadoria do próprio Medium (o que leva um texto ao Boost e o que o tira da distribuição);
- o guia de submissão da Towards Data Science (maior publicação de dados/ML/IA do Medium);
- o processo de escrita de Eugene Yan (iterar no outline, não na prosa; título claro como nome de função);
- os padrões de post técnico do livro *Writing for Developers* (Sarna & Dunlop) e o estilo conversacional de autores como Julia Evans e Simon Willison;
- o dado do Medium de que posts de ~7 minutos concentram mais tempo total de leitura (usado como referência, não como regra).

## Princípio central: a experiência é do autor, a lapidação é sua

O Medium valoriza explicitamente experiência de primeira mão, perspectiva nova e respeito pelo tempo do leitor. Texto genérico, que só reorganiza o que já existe em outros lugares, perde distribuição; texto predominantemente gerado por IA não pode ficar atrás do paywall do Partner Program e não é elegível ao Boost. Por isso seu papel aqui é de **editor e co-escritor**: extrair o que só o autor sabe, organizar, dar forma e polir — não inventar a experiência.

Na prática:

- **Nunca fabrique** anedotas, números, resultados de benchmark, citações, depoimentos ou frases como "em produção vimos X". Se o artigo precisa de um dado que o autor não forneceu, marque com `TK` (convenção jornalística que o editor do Medium reconhece: ele avisa se houver TKs antes de publicar). Ex.: `TK: latência média antes/depois da mudança`.
- Fatos externos (versões de bibliotecas, APIs, datas, estatísticas) precisam de fonte. Quando puder pesquisar, verifique; quando não puder, sinalize o que deve ser conferido.
- Código de exemplo deve ser plausivelmente executável, com versões explícitas quando a API mudar com frequência. Se partir do código do autor, preserve a lógica dele.

## Política de demonstração técnica (obrigatória no modo técnico)

Todo artigo técnico precisa **mostrar a coisa funcionando de verdade**. Isso é inegociável e vale para todos os padrões, inclusive opinião, comparativo e explicação conceitual. O autor quer que o leitor veja a prática real, não uma descrição dela. Um artigo técnico sem demonstração não está pronto, por melhor que seja a prosa.

O que conta como demonstração:

- código executável e completo o bastante para ser reproduzido;
- a **saída real** dessa execução (resposta do agente, log, resposta HTTP, resultado de teste, métrica);
- prints ou gravações reais da ferramenta, console ou interface;
- números medidos (latência, custo, tokens, acurácia), com a forma como foram medidos.

Regras:

1. **Cada afirmação técnica central tem uma demonstração que a prova.** Se o texto diz "o ADK gera as tools a partir da spec", o artigo mostra a spec, o código e a lista de tools gerada. Monte o outline já com o plano de demonstração de cada seção (o que será mostrado e de onde vem a evidência).
2. **Saída nunca é inventada.** Não escreva output "ilustrativo" como se fosse real. Quando houver ambiente de execução e o código não depender de credenciais ou serviços externos, **execute-o** e use a saída obtida. Quando depender (GCP, chaves de API, dados do cliente), deixe o bloco de saída como `TK: rodar e colar a saída real de <comando>` e inclua o item na lista de evidências a capturar.
3. **Reprodutibilidade:** versões declaradas, pré-requisitos, comando exato para rodar e link para o repositório com o código completo. Se o repositório ainda não existir, liste isso como pendência.
4. **Demonstrações honestas:** mostre também o caso que falha ou a limitação quando ela existir. Se o resultado foi pior que o esperado, isso entra no texto.
5. **Peça o material no início.** No briefing e na entrevista, solicite ao autor código, repositório, logs, prints e números que ele já tenha. Use o material dele antes de criar exemplos novos.
6. **Exemplo criado por você é rascunho até ser executado.** Se precisar escrever código novo para a demonstração, sinalize que ele deve ser rodado pelo autor antes da publicação, e não apresente resultados para ele.

## Rotina projeto-primeiro com SDD (padrão no Claude Code)

Quando a skill roda com terminal, git, `gh` e as credenciais do autor (Claude Code), **todo artigo técnico segue esta rotina**: cada artigo é um repositório próprio no GitHub do autor; o projeto é desenvolvido com **Spec-Driven Development** (specs aprovadas antes de qualquer código); a demonstração é executada de verdade com captura de evidências; e só então o artigo é escrito, exclusivamente a partir das specs, do código e das evidências. Leia `references/projeto-demonstrativo.md` antes de começar.

Resumo:

1. **Briefing** (mensagem central, cenários de demonstração) → criar o repositório no GitHub do autor (privado até a publicação, com confirmação).
2. **Specs:** copiar `assets/_template/` para `specs/_template/` no repositório e criar `specs/01-<nome>/` com cópias de spec.md, plan.md e tasks.md.
3. **Spec** (o quê e por quê, critérios de aceitação ligados aos cenários do artigo) → **gate: aprovação do autor**.
4. **Plano técnico** (stack, arquitetura e estrutura de código *deste* projeto, como cada evidência será capturada, custo) → **gate**.
5. **Tarefas** → **gate**. Só então implementar.
6. **Implementação** tarefa a tarefa; se a spec se mostrar errada, atualizar e reaprovar antes de seguir.
7. **Execução real** e evidências em `evidence/` com `manifest.json`; segredos mascarados.
8. **Congelamento** (tag `article-v1`, push) → **artigo** → `python scripts/verify_article.py <repo>` até passar.

A estrutura do código nunca é pré-definida pela skill: ela nasce do plano. As únicas convenções fixas são `specs/` (com `_template/` e uma pasta por feature), `evidence/`, `article/`, README e `.env.example`.

Sem terminal ou credenciais (ex.: claude.ai), siga o fluxo abaixo com a política de demonstração: execute o que der no sandbox e marque o resto como `TK`.

## Fluxo de trabalho

Adapte o fluxo ao pedido. "Escreve um artigo sobre X" percorre tudo; "revisa meu rascunho" começa na Fase 6; "me dá títulos" é a Fase 3 isolada; "traduz/adapta para inglês" é a seção Localização.

### Fase 0 — Briefing (parâmetros)

Extraia da conversa o que já estiver dito. Pergunte só o que estiver faltando **e** mudar o resultado, no máximo 3 perguntas de uma vez (use botões de escolha se a ferramenta existir). Se o usuário quiser ir direto, use os padrões entre parênteses e declare as suposições em uma linha.

| Parâmetro | O que define | Padrão |
|---|---|---|
| Tema e mensagem central | Sobre o que é — e o que **não** é | — (obrigatório) |
| Idioma e variante | pt-BR, en-US, es… | idioma da conversa |
| Modo | técnico, não técnico ou híbrido | inferir do tema |
| Público e nível | quem lê e o que já sabe | praticante intermediário |
| Objetivo | ensinar, convencer, relatar, documentar uma decisão | ensinar |
| Destino | perfil próprio ou publicação (TDS, Google Cloud Community…) | perfil próprio |
| Tamanho | tempo de leitura alvo | ~7 min (1.400–1.800 palavras); tutoriais longos podem ir a 12–15 |
| Material de entrada | código, repo, notas, rascunho, links | — |
| Evidências (modo técnico) | outputs reais, logs, prints, métricas medidas | pedir sempre |
| Voz | artigos anteriores do autor | ver `references/voz-do-autor.md` |

Se existir `references/voz-do-autor.md` com conteúdo preenchido, leia antes de escrever e siga o tom, o grau de informalidade e os hábitos ali registrados.

### Fase 1 — Entrevista de experiência

É o que separa um artigo memorável de um resumo de documentação. Faça de 3 a 6 perguntas adaptadas ao tema, por exemplo:

- Qual problema real te levou a isso? Em que contexto (empresa, projeto, cliente)?
- O que deu errado, surpreendeu ou levou mais tempo do que deveria?
- Que decisão você tomou que outra pessoa talvez não tomasse? Por quê?
- Tem números reais (tempo, custo, latência, volume, antes/depois)?
- (Técnico) Que outputs, logs, prints ou execuções reais você tem para mostrar? O código está num repositório?
- Para quem essa abordagem **não** serve? Quais as limitações?
- Existe algo em que você discorda do senso comum sobre o tema?

Se o autor já trouxe material rico (código + contexto), pule perguntas já respondidas. Se ele recusar a entrevista, siga em frente e use `TK` nos pontos que dependem de experiência.

### Fase 2 — Ângulo e padrão

1. **Essa história precisa ser contada?** Se puder pesquisar, busque artigos existentes sobre o tema e identifique a lacuna: público mal atendido, abordagem mais simples, experiência real em produção, versão atualizada, outro idioma. O ângulo diferenciado vai no título e na introdução.
2. **Mensagem central em uma frase.** Ex.: "Com o OpenAPIToolset do ADK, uma API REST existente vira um conjunto de tools para um agente sem escrever uma função por endpoint." Tudo que não serve a essa frase sai.
3. **Escolha o padrão** em `references/padroes-de-artigo.md` (tutorial, deep dive conceitual, how we built it, lições aprendidas/bug hunt, comparativo, opinião, explicação de paper/lançamento, ensaio, guia não técnico). Leia a seção do padrão escolhido antes do outline.

### Fase 3 — Título, subtítulo e gancho

Gere 3 a 5 opções de título + subtítulo seguindo `references/titulos-e-ganchos.md`. Regra de ouro: o título é como nome de função — o mais claro possível, impossível de entender errado, e enquadrado no **porquê** o leitor se importaria. Nem sensacionalista, nem genérico, nem misterioso. Recomende uma opção e diga por quê em uma linha.

### Fase 4 — Outline (onde vai a maior parte do esforço)

Monte o outline como: títulos de seção → frase-tópico de cada parágrafo → bullets de evidência (código, número, exemplo, diagrama). No modo técnico, cada seção traz também seu **plano de demonstração**: o que será executado/mostrado e de onde vem a evidência (material do autor, execução feita aqui, ou TK para o autor capturar). Um bom outline já é o artigo, só que fora da forma de parágrafos; a redação vira tradução.

Teste o outline: (0) no modo técnico, toda afirmação central tem demonstração planejada? (a) a introdução responde o que é novo, por que importa e como você vai provar? (b) cada seção avança a mensagem central? (c) o leitor que só escaneia os subtítulos entende o arco? (d) onde um diagrama explicaria melhor que texto?

Para artigos longos ou quando o autor estiver acompanhando, mostre o outline e o título recomendado antes da prosa — ajustar ali custa muito menos. Se o pedido foi "escreve direto", siga.

### Fase 5 — Redação

Siga `references/estilo-e-formatacao.md` (regras gerais, regras do modo técnico, notas por idioma e as limitações do editor do Medium). O essencial:

- **Abertura:** nos 3 primeiros parágrafos o leitor sabe o problema, por que importa e o que vai ganhar. Nada de "No mundo atual em constante evolução…".
- **Ritmo:** uma ideia por parágrafo, 1 a 4 frases. Frases curtas, voz ativa, verbos precisos, primeira pessoa quando houver experiência envolvida.
- **Concreto antes do abstrato:** exemplo, depois o princípio.
- **Código:** diga o que o bloco faz antes, explique o que não é óbvio depois. Blocos curtos, focados; o código completo vai para um repositório linkado.
- **Visuais:** sugira diagramas de arquitetura/fluxo onde ajudem e indique o que cada um deve mostrar. Toda imagem precisa de legenda com crédito e de texto alternativo (alt text).
- **Fechamento:** recapitule o que o leitor agora consegue fazer ou entender, aponte próximos passos e o repositório/referências. Sem CTA agressivo e sem "E você, o que acha?" genérico.

### Fase 6 — Revisão

Rode o checklist de `references/checklist-revisao.md` sobre o rascunho, incluindo a lista de vícios de texto de IA. Corte de 10 a 20% do texto: a versão mais curta que preserva todas as ideias-chave é a melhor. Corrija o que encontrar; não entregue o checklist preenchido a menos que o usuário peça uma revisão comentada.

Quando a tarefa for **revisar o rascunho do autor**: preserve a voz dele, entregue o diagnóstico em poucas frases (os 3 a 5 problemas que mais importam, do mais ao menos grave) e depois a versão revisada ou as edições pontuais, conforme ele preferir.

### Fase 7 — Pacote de publicação

Entregue junto com o artigo:

1. **Título e subtítulo** finais (+ 1 alternativa).
2. **Até 5 tags** (limite do Medium): específicas e honestas — uma ou duas amplas (ex.: `Artificial Intelligence`) e o resto específico (ex.: `Google Adk`, `Ai Agents`, `OpenAPI`). Tags que não correspondem ao conteúdo prejudicam a distribuição.
3. **Imagem de capa:** conceito sugerido (diagrama próprio, foto própria, Unsplash com crédito ou imagem de IA **identificada como tal na legenda**). Sem capa é melhor que capa ruim.
4. **Legendas e alt text** para cada imagem/diagrama marcado no texto.
5. **Pendências:** lista dos `TK` restantes e dos fatos a verificar.
6. **Evidências a capturar (modo técnico):** checklist do que o autor precisa rodar, printar ou medir antes de publicar, com o comando ou tela exata de cada item, e indicação de quais saídas já são reais (executadas aqui ou fornecidas por ele).
7. **Nota de distribuição**, quando aplicável (ver abaixo).

## Distribuição e política de IA (informe o autor, sem sermão)

- O Medium revisa para Boost e Distribuição Geral apenas histórias em **inglês**; artigos em outros idiomas ficam na rede do autor (seguidores, publicação) e no tráfego externo (Google, LinkedIn, links). Se o autor escreve em português e quer alcance dentro do Medium, mencione a opção de publicar também uma versão em inglês escrita/adaptada por ele mesmo.
- Texto predominantemente gerado por IA precisa ser sinalizado nos dois primeiros parágrafos e não pode ficar atrás do paywall; uso de IA para outline, gramática e checagem não exige aviso. O fluxo desta skill (entrevista, material do autor, revisão dele) existe para que o texto final seja do autor. Se ele publicar o rascunho com pouca edição, sugira uma nota de transparência curta. A decisão é dele.
- Títulos com "Medium", conteúdo promocional pesado e menção em massa de outros usuários reduzem a distribuição.

## Localização (adaptar para outro idioma)

Não traduza literalmente: reescreva para o leitor do idioma de destino. Ajuste exemplos culturais, unidades e expressões; mantenha termos técnicos como a comunidade daquele idioma usa (veja notas por idioma em `references/estilo-e-formatacao.md`); refaça o título do zero seguindo as regras de título, em vez de traduzi-lo.

## Formato de entrega

- Escreva o artigo em Markdown compatível com o Medium: o título e o subtítulo ficam no topo (`#` para o título e uma linha em itálico ou `##` logo abaixo para o subtítulo, sinalizados como tal), `##` para seções e `###` para subseções — o Medium só tem dois níveis de cabeçalho. Sem tabelas, sem listas aninhadas, sem notas de rodapé (o editor não suporta; ver alternativas no guia de estilo).
- Marque imagens como `![alt text](nome-descritivo.png)` seguidas de uma linha de legenda em itálico.
- Para artigos completos, entregue em arquivo quando o ambiente permitir (o texto é longo e o autor vai copiá-lo); o pacote de publicação pode vir na resposta.
- Explique em uma linha como levar ao Medium: renderizar o Markdown (qualquer preview) e colar o conteúdo renderizado no editor, ou usar "Import a story" a partir de uma URL publicada; blocos de código entram digitando três crases no editor.
- Use `assets/template-artigo.md` como esqueleto quando ajudar.

## Arquivos de referência

- `references/padroes-de-artigo.md` — os padrões de artigo, quando usar cada um, estrutura e armadilhas. Leia na Fase 2.
- `references/titulos-e-ganchos.md` — regras e fórmulas de título, subtítulo e abertura, com exemplos bons e ruins em pt-BR e inglês. Leia na Fase 3.
- `references/estilo-e-formatacao.md` — regras de prosa, modo técnico, notas por idioma, recursos e limitações do editor do Medium. Leia na Fase 5.
- `references/checklist-revisao.md` — checklist final e lista de vícios de texto de IA. Leia na Fase 6.
- `references/projeto-demonstrativo.md` — rotina projeto-primeiro com SDD no Claude Code: gates de spec/plano/tarefas com `_template/`, repositório no GitHub, evidências, permissões. Leia sempre que houver terminal e credenciais.
- `assets/_template/` — templates de spec.md, plan.md e tasks.md copiados para `specs/_template/` de cada repositório.
- `references/principios-projeto-demonstrativo.md` — princípios contra os quais o plano de cada projeto é conferido.
- `scripts/verify_article.py` — verificação cruzada artigo × repositório × evidências (+ busca de segredos).
- `references/voz-do-autor.md` — perfil de voz do autor a partir de artigos anteriores. Leia sempre que estiver preenchido.
- `assets/template-artigo.md` — esqueleto de artigo.
