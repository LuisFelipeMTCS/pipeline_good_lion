# 06: Alertas de falha por e-mail e observabilidade

**O que construir:** quando qualquer job do pipeline falhar ou estourar o tempo, chega um e-mail. Os logs ficam no CloudWatch por 7 dias e um dashboard mostra duração, falhas e linhas processadas por job. Tudo em Terraform, no `infra/monitoring.tf`.

**Bloqueado por:** 04

**Status:** ready-for-agent

- [ ] Regra do EventBridge para jobs do Glue em `FAILED` ou `TIMEOUT` publicando no SNS
- [ ] Falha forçada no job do ticket 04 gera e-mail recebido de verdade (print em `docs/evidencias/`)
- [ ] Logs contínuos do Glue no CloudWatch com retenção de 7 dias
- [ ] Dashboard do CloudWatch com duração, falhas e linhas processadas por job
- [ ] Métricas detalhadas de observabilidade do Glue ficam desligadas por padrão (ligadas só na rodada final, ticket 17)
