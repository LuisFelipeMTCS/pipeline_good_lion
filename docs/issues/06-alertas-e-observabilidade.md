# 06: Alertas de falha por e-mail e observabilidade

**O que construir:** quando qualquer job do pipeline falhar ou estourar o tempo, chega um e-mail. Os logs ficam no CloudWatch por 7 dias e um dashboard mostra duração, falhas e linhas processadas por job. Tudo em Terraform, no `infra/monitoring.tf`.

**Bloqueado por:** 04

**Status:** in-progress (falta confirmar a assinatura do e-mail e repetir a falha forçada)

- [x] Regra do EventBridge para jobs do Glue em `FAILED` ou `TIMEOUT` publicando no SNS
- [ ] Falha forçada no job do ticket 04 gera e-mail recebido de verdade (print em `docs/evidencias/`)
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
