# Checklist de revisão

Os cinco primeiros blocos seguem os pilares que a curadoria do Medium usa para decidir o Boost (experiência do autor, valor, respeito ao leitor, originalidade, qualidade de escrita), complementados pelo guia da Towards Data Science.

## 0. Demonstração técnica (bloqueante no modo técnico)
- [ ] Toda afirmação técnica central tem uma demonstração que a prova (código + saída real, print, log ou métrica medida)?
- [ ] Nenhuma saída, log ou número foi inventado? O que não foi executado está marcado com `TK`?
- [ ] O leitor consegue reproduzir: versões, pré-requisitos, comando exato e repositório?
- [ ] Limitações ou casos de falha relevantes aparecem demonstrados, não escondidos?
- [ ] A lista de evidências a capturar está no pacote de publicação?

Se algum item falhar, o artigo não está pronto para publicação — diga isso ao autor.

## 1. Experiência do autor
- [ ] Fica claro por que **este** autor está escrevendo sobre **este** tema?
- [ ] Há pelo menos um elemento que só o autor poderia trazer (decisão, erro, número, contexto real)?
- [ ] Nenhuma experiência, número ou citação foi inventada? Pendências estão marcadas com `TK`?

## 2. Valor
- [ ] O leitor sai capaz de fazer ou entender algo que não conseguia antes?
- [ ] O título promete e o texto entrega exatamente isso?
- [ ] A introdução diz o que é novo, por que importa e como será provado?

## 3. Respeito ao leitor
- [ ] Não há trecho que soe como pitch de venda ou autopromoção?
- [ ] O fechamento recapitula e aponta caminhos sem CTA agressivo?
- [ ] O texto não gasta parágrafos com aquecimento antes de chegar ao ponto?

## 4. Originalidade
- [ ] O artigo não é paráfrase da documentação, de outro artigo ou do anúncio oficial?
- [ ] O ângulo diferenciado aparece já no título/subtítulo ou na abertura?

## 5. Qualidade de escrita e precisão
- [ ] Fatos externos têm fonte; versões estão declaradas.
- [ ] Código é coerente entre blocos, sem segredos reais, explicado antes e depois.
- [ ] Gramática e ortografia revisadas no idioma e variante corretos.
- [ ] Transições entre seções fazem sentido; quem só lê os subtítulos entende o arco.
- [ ] Cortei 10 a 20%? A versão mais curta preserva todas as ideias-chave?

## 6. Formatação Medium
- [ ] Só dois níveis de cabeçalho; sem tabelas, listas aninhadas, notas de rodapé ou LaTeX.
- [ ] Toda imagem tem legenda com crédito e alt text; imagens de IA identificadas.
- [ ] Parágrafos curtos (leitura no celular).

## 7. Pacote
- [ ] Título (sem caixa alta, sem "Medium", sem clickbait) + subtítulo que complementa.
- [ ] Até 5 tags, honestas e específicas.
- [ ] Sugestão de capa, lista de TKs e fatos a verificar.

---

## Vícios de texto de IA — remova ao revisar

Esses padrões deixam o texto genérico, cansam o leitor e fazem o artigo parecer gerado automaticamente. Reescreva sempre que aparecerem.

**Aberturas e fechamentos clichê**
- pt: "No mundo atual, em constante evolução…", "Nos dias de hoje…", "Neste artigo, vamos explorar/mergulhar…", "Em resumo," / "Em conclusão," como abertura do último parágrafo, "E você, o que acha? Deixe nos comentários!"
- en: "In today's fast-paced world…", "In this article, we'll dive deep into…", "In conclusion,", "Let's dive in!"

**Vocabulário inflado**
- pt: revolucionar, divisor de águas, desbloquear o potencial, alavancar, robusto (sem métrica), poderoso (sem exemplo), jornada, cenário em constante mudança, "uma verdadeira virada de jogo", superpoderes (quando vago)
- en: delve, leverage, unlock, seamless, robust, game-changer, landscape, tapestry, realm, cutting-edge, "it's worth noting that"

**Tiques de estrutura**
- "Não apenas X, mas também Y" repetido.
- Trios em sequência por hábito ("rápido, eficiente e escalável") em vez de um adjetivo comprovado.
- Perguntas retóricas como transição em toda seção.
- Frase de efeito isolada no fim de cada parágrafo.
- Emojis em subtítulos e listas sem necessidade.
- Negrito espalhado em meia página.
- Seção de conclusão que só repete a introdução.
- Hedging excessivo ("pode potencialmente ajudar a talvez melhorar").
- Afirmações genéricas sem exemplo ("isso melhora muito a performance") — substitua por número real ou `TK`.

**Teste final:** leia o primeiro parágrafo em voz alta. Se ele caberia em qualquer artigo sobre o mesmo tema, reescreva.
