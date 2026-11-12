# Princípios do projeto demonstrativo

Valem para todos os repositórios de artigo. O plano de cada projeto é conferido contra eles (seção "Verificação de princípios" do plan.md).

## I. Demonstrabilidade
Todo requisito existe para provar uma afirmação do artigo. Funcionalidade que não aparece nem sustenta o artigo está fora de escopo.

## II. Evidência real
Toda demonstração gera saída real e registrada (`evidence/` + `manifest.json`). Nenhuma saída, número ou log é inventado ou editado além de cortes marcados e mascaramento de segredos.

## III. Specs antes do código
Nenhum código de implementação antes de spec, plano e tarefas aprovados pelo autor. Mudança de escopo atualiza a spec primeiro.

## IV. Reprodutibilidade
Versões fixadas, `.env.example` completo, README com o passo a passo exato para reproduzir cada demonstração. Um leitor deve conseguir rodar tudo a partir do repositório.

## V. Legibilidade didática
O código é material de ensino: simples, nomeado com clareza, sem abstração desnecessária, comentado só no que não é óbvio. Trechos usados no artigo são marcados com comentários de região.

## VI. Testes ligados à spec
Cada critério de aceitação tem um teste ou uma execução verificável correspondente.

## VII. Segurança e privacidade
Sem credenciais, dados de cliente ou informação confidencial no repositório. Evidências revisadas e mascaradas antes do commit.

## VIII. Custo controlado
Recursos de nuvem mínimos, custo estimado no plano, teardown documentado e executado após a captura de evidências.
