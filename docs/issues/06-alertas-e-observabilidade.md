# 06: Alertas de falha por e-mail e observabilidade

**O que construir:** quando qualquer job do pipeline falhar ou estourar o tempo, chega um e-mail. Os logs ficam no CloudWatch por 7 dias e um dashboard mostra duração, falhas e linhas processadas por job. Tudo em Terraform, no `infra/monitoring.tf`.

**Bloqueado por:** 04

**Status:** done

- [x] Regra do EventBridge para jobs do Glue em `FAILED` ou `TIMEOUT` publicando no SNS
- [x] Falha forçada gera e-mail recebido de verdade (print em [`docs/evidencias/06-alerta-email.png`](../evidencias/06-alerta-email.png))
- [x] Logs contínuos do Glue no CloudWatch com retenção de 7 dias
- [x] Dashboard do CloudWatch com duração, falhas e linhas processadas por job
- [x] Métricas detalhadas de observabilidade do Glue ficam desligadas por padrão (ligadas só na rodada final, ticket 17)

## Resultado (28/10/2026)

**O que foi criado (`infra/monitoring.tf`):**
- Regra `goodlion-falha-glue` (FAILED, TIMEOUT, ERROR) → SNS `goodlion-alertas` → e-mail, com a mensagem "Job <job> terminou em <estado> (execução <id>): <erro>".
- Regra `goodlion-fim-glue`: todo fim de execução vai para o log `/aws/events/goodlion-glue` (7 dias), de onde o dashboard tira execuções e falhas.
- Os 6 grupos de log do Glue com retenção de 7 dias (5 já existiam, sem retenção, e foram importados no Terraform).
- Dashboard `goodlion` com 3 quadros (Logs Insights): execuções por job e estado, falhas, e resumo por execução (duração e linhas gravadas).

**Duração e linhas sem `--enable-metrics`:** o evento do EventBridge não traz duração, e as métricas do Glue são cobradas como métricas do CloudWatch. Por isso cada job imprime no fim uma linha `resumo job=<nome> segundos=<n> linhas=<n> meses=<...>`: o `GravarDelta` usa o `sparkContext.startTime` e o `numOutputRows` do histórico Delta (sem reler os dados); a `ingest_receita` mede o próprio tempo. O `--enable-metrics` e as métricas detalhadas ficam para a rodada final (ticket 17).

**Falha forçada:** `bronze_estabelecimentos` com `--ambiente full` (recusado de propósito pelo `GravarDelta`) falhou nas 2 tentativas com `ValueError`. O EventBridge publica só a falha final: **1 e-mail** por execução, não um por tentativa. Depois, uma execução normal sem arquivos novos apareceu no dashboard como `bronze_estabelecimentos | 0,95 min | 0 linhas`.

**E-mail que não chegou (03/11/2026):** a assinatura de e-mail do `goodlion-alertas` tinha sumido (provavelmente pelo link "unsubscribe" de um e-mail do SNS), então nada era entregue. O `terraform apply` recriou a assinatura; falta clicar em "Confirm subscription" no e-mail da AWS, repetir a falha forçada e guardar o print.

**E-mail recebido (05/11/2026, 22:39):** a assinatura estava confirmada e o SNS registrava 17 e-mails entregues desde 04/11 (falhas reais da rodada completa, como a `gold_fato_empresa_mensal` barrada pelo DQ). A falha forçada final foi o job `definir_mes` rodado fora do Workflow (sem `--WORKFLOW_NAME`/`--WORKFLOW_RUN_ID`, sai com código 2; Python shell, custo de centavos): `FAILED` às 22:38, evento no log `/aws/events/goodlion-glue` às 22:39 e e-mail "Job definir_mes terminou em FAILED (execução jr_e84d1f93…): Command failed with exit code 2" na caixa de entrada no mesmo minuto ([print](../evidencias/06-alerta-email.png)). O link "unsubscribe" do rodapé remove a assinatura: foi o que apagou a de 03/11 e voltou a acontecer em 05/11 (reconfirmada pelo link do e-mail de confirmação).
