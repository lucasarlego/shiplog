# Estilo e formatação

## Sumário

1. Regras gerais de prosa
2. Modo técnico
3. Modo não técnico
4. Notas por idioma
5. Recursos e limitações do editor do Medium
6. Tamanho

---

## 1. Regras gerais de prosa

- **Escreva para uma pessoa específica.** Imagine um colega do público-alvo lendo. Se ele não "pega", a experiência de uso do texto está ruim; se não há substância, falta backend.
- **Uma ideia por parágrafo**, 1 a 4 frases. Parágrafos longos no celular viram parede de texto.
- **Frases curtas e diretas.** Varie o comprimento para dar ritmo, mas a média deve ser curta.
- **Voz ativa e verbos precisos.** Troque verbos neutros (ser, ter, fazer, ficar) por verbos de ação quando der. "O agente consulta a API" > "É feita uma consulta à API pelo agente".
- **Concreto antes do abstrato.** Mostre o exemplo, depois nomeie o princípio.
- **Primeira pessoa quando houver experiência.** "Eu tentei X e quebrou" gera confiança. Leitores sentem que aprendem junto, não que recebem um sermão.
- **Escaneável.** Desenvolvedores escaneiam subtítulos, olham os blocos de código e leem o que parece relevante. Subtítulos devem dizer algo ("Autenticação: o passo que a documentação pula") em vez de rótulos ("Autenticação").
- **Transições.** Cada seção deve começar ligando-se à anterior ou à mensagem central.
- **Negrito com parcimônia:** no máximo um ou dois destaques por seção, para termos-chave ou avisos.
- **Fontes.** Todo fato não óbvio tem link para a origem. Em artigos para a TDS, referências no fim seguem o formato `[1] N. Sobrenome, Título (Ano), Fonte`.

## 2. Modo técnico

- **Declare versões** de linguagem, SDK e serviços. APIs de IA mudam rápido; artigo sem versão envelhece mal.
- **Código como texto, nunca como print.** Blocos curtos e focados (idealmente até ~25 linhas). Antes do bloco: o que ele faz. Depois: o que não é óbvio. Código completo num repositório linkado (GitHub; o Medium também incorpora Gists).
- **Comentários no código** só para o não óbvio; a explicação principal fica na prosa.
- **Nomes reais e consistentes** entre os blocos (a variável declarada no passo 2 é a mesma usada no passo 5).
- **Diga como verificar** cada passo (saída esperada, comando de teste).
- **Diagramas** para arquitetura, fluxo de dados e sequência de chamadas. Sugira o conteúdo do diagrama e ofereça um rascunho em Mermaid ou descrição para Excalidraw/draw.io — o Medium só aceita imagem, então o diagrama precisa ser exportado.
- **Segredos:** nunca chaves reais nos exemplos; use variáveis de ambiente e placeholders óbvios.
- **Termos técnicos:** defina no primeiro uso quando o público não for especialista; não defina o básico para especialistas.

## 3. Modo não técnico

- Abra com uma cena ou situação concreta.
- Mostre, não diga: detalhes específicos (lugar, diálogo, número) em vez de adjetivos.
- Corte o que não serve ao fio narrativo, mesmo que seja verdade e interessante.
- Termine com um insight que o leitor leve embora, sem moral da história explícita demais.

## 4. Notas por idioma

### Português (pt-BR)

- Use "você"; evite "tu" e o formalismo de "o leitor".
- Mantenha em inglês os termos que a comunidade brasileira usa assim: deploy, endpoint, prompt, pipeline, framework, token, embedding, fine-tuning, commit, pull request, webhook. Não force traduções ("implantação" pode ficar, "ponto de extremidade" não).
- Verbos aportuguesados comuns na comunidade são aceitáveis em tom conversacional (deployar, commitar), mas use com moderação em artigos mais formais ou para publicações corporativas.
- Evite gerundismo ("vamos estar implementando") e excesso de voz passiva com "se".
- Nomes de produtos e classes ficam como no original e em `código inline` quando forem identificadores.
- Lembre que artigos em português não recebem Boost nem Distribuição Geral no Medium; o alcance vem dos seguidores, de publicações em português e do tráfego externo (Google, LinkedIn). SEO conta mais aqui.

### Inglês (en)

- Inglês americano por padrão (a maioria das publicações usa).
- Tom conversacional com contrações (it's, you'll, don't) é o padrão dos autores técnicos mais lidos.
- Title Case nos títulos é o costume da maioria das publicações técnicas; siga o padrão da publicação de destino quando houver.
- Para falantes não nativos: frases curtas e estrutura simples soam mais naturais do que vocabulário rebuscado.

### Espanhol (es)

- Defina a variante (es-ES ou neutro latino-americano) no briefing; use "tú" em tom conversacional.
- Mesma lógica de anglicismos técnicos do português.

### Outros idiomas

Pergunte ao autor sobre convenções de tratamento (formal/informal) e termos técnicos se não estiver claro; siga as convenções da comunidade técnica daquele idioma.

## 5. Recursos e limitações do editor do Medium

**Recursos disponíveis:**
- Título e subtítulo próprios no topo da história.
- Dois níveis de cabeçalho (grande e pequeno) → use `##` e `###` no Markdown.
- Negrito, itálico, links.
- Dois estilos de citação (blockquote e pull quote) → use `>` e indique "pull quote" se for para destaque.
- Listas simples (com marcador ou numeradas), sem aninhamento.
- Código inline com crases e blocos de código com destaque de sintaxe (no editor, digitar três crases cria o bloco; o idioma pode ser escolhido).
- Imagens com legenda e alt text; embeds (Gist, YouTube, tweets, CodePen…).
- Separador (`---` no Markdown; no editor, as três bolinhas).
- `TK` como marcador de pendência: o editor avisa antes de publicar.
- Kicker (sobretítulo) em publicações, usado para séries/colunas.
- Até 5 tags.

**Limitações e alternativas:**
- **Sem tabelas** → transforme em lista, em texto, em imagem (gráfico ou tabela renderizada) ou em bloco de código alinhado quando for algo pequeno.
- **Sem listas aninhadas** → achate a lista ou use subtítulos.
- **Sem notas de rodapé** → links inline ou seção de referências no fim.
- **Sem LaTeX** → equações como imagem, Unicode simples ou bloco de código.
- **Sem mais de dois níveis de cabeçalho** → reorganize ou use negrito como "terceiro nível".
- Markdown colado cru não é convertido automaticamente em cabeçalhos: renderize antes (preview de Markdown) e cole o conteúdo renderizado, ou importe a partir de uma URL.

**Imagens:**
- Crédito sempre na legenda: "Imagem do autor", "Foto de [Nome] no Unsplash", "Imagem gerada com [ferramenta]". Imagens geradas por IA devem ser identificadas na legenda.
- Nunca use imagem da internet sem permissão (crédito não substitui licença).
- Alt text descreve o conteúdo para quem não vê a imagem, em uma frase.

## 6. Tamanho

O Medium mediu em 2013 que posts de ~7 minutos concentravam o maior tempo total de leitura — mas a métrica era tempo agregado, não leitura por pessoa, e isso não é regra. Use como ponto de partida:

- Opinião, ensaio, lições curtas: 4 a 7 min (800 a 1.500 palavras).
- Tutorial, deep dive, how we built it: 7 a 15 min (1.500 a 3.500 palavras).
- Acima de ~25 min: considere uma série (a TDS recomenda capítulos de 12 a 25 min), com links entre as partes e um sumário no início.

O tamanho certo é o menor que comunica a mensagem completa.
