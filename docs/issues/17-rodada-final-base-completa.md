# 17: Rodada final na base completa

**O que construir:** o pipeline roda sobre o Brasil inteiro em 2026-09 e 2026-10, e o Metabase responde as três perguntas de negócio com os dados reais. Esta é a rodada que gera as evidências finais para a entrega de 09/11/2026.

**Custo:** é a etapa mais cara do projeto. Conferir o Budgets antes de começar.

**Bloqueado por:** 15, 16

**Status:** ready-for-agent

- [ ] Métricas detalhadas de observabilidade do Glue ligadas para esta rodada
- [ ] Workflow com `--ambiente full` e até 10 workers, para 2026-09 e depois 2026-10
- [ ] Uma repetição de um mês para provar a idempotência na base completa
- [ ] Todas as regras de Data Quality passaram
- [ ] `make dashboard-load` para os dois meses
- [ ] Metabase com as 3 perguntas respondidas por município, UF e região
- [ ] Custo total do projeto conferido no Billing (meta: abaixo de US$ 10)
- [ ] Prints e números de evidência (DQ, antes/depois, Catalog, alertas, dashboard) reunidos para o relatório
