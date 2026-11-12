# Títulos, subtítulos e ganchos

Título, subtítulo e capa são tudo o que o leitor vê no feed antes de decidir clicar. O Medium não dá Boost quando esse trio não representa bem a história — e isso vale nos dois sentidos: sensacionalista é ruim, mas genérico, misterioso ou formulaico também.

## Princípios

1. **Clareza acima de esperteza.** Trate o título como nome de função: o mais claro, impossível de entender errado.
2. **Enquadre no interesse do leitor.** "A importância da escrita numa carreira tech" funciona melhor que "Blogging e escrita técnica" porque diz por que o leitor deveria ligar.
3. **Promessa específica e cumprível.** O artigo precisa entregar exatamente o que o título promete — nem mais, nem menos.
4. **Título curto, subtítulo mais longo.** Título com ~6 a 12 palavras (em inglês, idealmente menos de 70 caracteres). O subtítulo completa: para quem, como, com o quê, qual o diferencial. Ele aparece nas prévias e ajuda o clique.
5. **Palavras-chave reais.** Use os nomes que as pessoas buscam (o nome da ferramenta, o problema), pensando no Google também.
6. **Proibições:** CAIXA ALTA, palavrão, a palavra "Medium", promessas exageradas ("vai mudar sua vida"), números inventados, emojis em excesso.

## Fórmulas que funcionam (adapte, não copie mecanicamente)

| Fórmula | Exemplo pt-BR | Exemplo en |
|---|---|---|
| Como [resultado] com [ferramenta] | Como transformar sua API REST em tools para agentes com o Google ADK | How to Turn Your REST API Into Agent Tools with Google ADK |
| Como [resultado] sem [dor] | Como dar memória persistente a um agente sem gerenciar banco de sessões | Persistent Agent Memory Without Running Your Own Session Store |
| [Conceito] explicado [visualmente/de verdade] | MCP explicado com um exemplo de ponta a ponta | MCP, Explained with One End-to-End Example |
| O que aprendi [fazendo X] | O que aprendi colocando um agente de IA em produção no WhatsApp | What I Learned Shipping an AI Agent on WhatsApp |
| Por que [tese contraintuitiva] | Por que seu agente não precisa de um banco vetorial | Why Your Agent Probably Doesn't Need a Vector Database |
| [A] vs [B]: [critério] | Cloud Run vs GKE para agentes: custo e latência na prática | Cloud Run vs GKE for Agents: Real Cost and Latency Numbers |
| Construindo [sistema] ([detalhe]) | Construindo um triador de e-mails com agentes (e o que deu errado) | Building an Email-Triage Agent (and What Broke) |

Números no título só se forem reais e verificáveis ("Reduzi o custo em 63%" exige o dado no texto).

## Ruim → melhor

- "Agentes de IA: o futuro chegou" → genérico e vago. Melhor: "Seu primeiro agente com tools em 30 linhas de Python".
- "Você não vai acreditar no que o ADK faz" → clickbait. Melhor: "O ADK gera tools a partir de uma especificação OpenAPI. Veja como".
- "Algumas reflexões sobre RAG" → misterioso. Melhor: "Três erros de RAG que só aparecem em produção".
- "O GUIA DEFINITIVO DE LLMs" → caixa alta e promessa impossível.

## Subtítulo

Complementa o título, não o repete. Bons subtítulos respondem a uma destas: *para quem?*, *como?*, *qual o diferencial?*, *qual o resultado?*

- Título: "Como transformar sua API REST em tools para agentes com o Google ADK"
- Subtítulo: "Um guia prático com OpenAPIToolset, autenticação e os erros que encontrei no caminho"

## Abertura (os três primeiros parágrafos)

O leitor decide em segundos se continua. A introdução precisa responder: **o que há de novo aqui, por que eu deveria me importar, e como você vai provar.** Depois disso, o texto pode ser tão conversacional quanto o autor quiser.

Tipos de gancho (escolha um):

- **Problema concreto:** "Toda vez que eu queria que o agente consultasse um endpoint novo, escrevia mais uma função wrapper. Na décima, desisti."
- **Resultado primeiro:** "No fim deste artigo, você terá um agente que conversa com qualquer API documentada em OpenAPI — sem escrever uma função por endpoint."
- **Cena (bom para lições aprendidas e ensaios):** "Às 3h da manhã, o agente começou a responder a mesma mensagem em loop."
- **Dado surpreendente (só se for real e com fonte).**
- **Pergunta:** use com moderação, e nunca como abertura genérica ("Você já se perguntou…?").

Depois do gancho, um parágrafo de mapa curto pode ajudar em artigos longos ("Vamos ver X, depois Y, e terminar com Z"), mas sem o clichê "Neste artigo, vamos explorar".
