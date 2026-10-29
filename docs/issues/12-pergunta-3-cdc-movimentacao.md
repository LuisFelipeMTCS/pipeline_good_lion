# 12: Pergunta 3: aberturas e fechamentos via CDC

**O que construir:** o dashboard mostra onde mais se abrem e fecham empresas e MEIs, a partir da mudança entre 2026-09 e 2026-10. A `silver_empresa_consolidada` guarda o estado atual (uma linha por `cnpj_basico`) e recebe um `MERGE` mensal com o Change Data Feed ligado. A `fato_movimentacao_empresa` lê as mudanças entre versões e classifica os eventos.

Pastas, nomes e padrões: [ARQUITETURA](../ARQUITETURA.md).

**Bloqueado por:** 08

**Status:** ready-for-agent

- [ ] `silver_empresa_consolidada` com Change Data Feed ligado
- [ ] `MERGE` mensal no Custom Transform `jobs/custom/merge_consolidada.py`: insere novos, atualiza alterados e remove os que deixaram de existir (`whenNotMatchedBySource`)
- [ ] `fato_movimentacao_empresa` (`jobs/sql/gold/fato_movimentacao_empresa.sql`) com os 5 tipos de evento: abertura, baixa, mudança de porte, entrada no MEI e saída do MEI
- [ ] Testes locais com pytest (via `jobs/local.py`) para a classificação de cada tipo de evento
- [ ] Rodar o `MERGE` do mesmo mês duas vezes não gera eventos duplicados
- [ ] Na amostra, 2026-09 seguido de 2026-10 produz eventos plausíveis (conferir alguns CNPJs à mão)
- [ ] Visões (`dashboard/schema.sql`) e gráfico no Metabase com aberturas e fechamentos por município, UF e região
