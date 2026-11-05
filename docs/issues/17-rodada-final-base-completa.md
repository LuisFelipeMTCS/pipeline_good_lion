# 17: Rodada final na base completa

**O que construir:** o pipeline roda sobre o Brasil inteiro em 2026-09 e 2026-10, e o Metabase responde as três perguntas de negócio com os dados reais. Esta é a rodada que gera as evidências finais para a entrega de 09/11/2026.

**Custo:** é a etapa mais cara do projeto. Conferir o Budgets antes de começar.

**Bloqueado por:** 15, 16

**Status:** done (custo acima da meta de US$ 10 em valor bruto, coberto por créditos)

- [x] Métricas detalhadas de observabilidade do Glue ligadas para esta rodada
- [x] Workflow com `--ambiente full` e até 10 workers, para 2026-09 e depois 2026-10
- [x] Uma repetição de um mês para provar a idempotência na base completa
- [x] Todas as regras de Data Quality passaram
- [x] `make dashboard-load` para os dois meses
- [x] Metabase com as 3 perguntas respondidas por município, UF e região
- [x] Custo total do projeto conferido no Billing (meta: abaixo de US$ 10)
- [x] Prints e números de evidência (DQ, antes/depois, Catalog, alertas, dashboard) reunidos em `docs/evidencias/` para o relatório

## Resultado (05/11/2026)

Brasil inteiro nos dois meses, Workflow 20 de 20 depois de duas correções que o DQ forçou (CNPJ duplicado na base da Receita), repetição de 2026-10 com Gold idêntica, PII zerado na Bronze completa, painel do Metabase com os números reais. Detalhes, números e custo: `docs/evidencias/17-rodada-final.md`; índice de todas as evidências: `docs/evidencias/README.md`.

Carga do dashboard a partir da AWS: `make dashboard-load-aws ANO_MES=<mês> AMBIENTE=full` (papel `analista`). Depois da entrega: `aws glue stop-trigger --name goodlion-mensal --region us-east-1`.

