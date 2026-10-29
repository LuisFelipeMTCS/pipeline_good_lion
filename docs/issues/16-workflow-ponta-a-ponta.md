# 16: Workflow ponta a ponta

**O que construir:** o pipeline inteiro orquestrado por um Glue Workflow (seção 7.1 do PRD), disparado por gatilho mensal (dia 20) ou sob demanda. O Workflow para quando uma regra bloqueante falha, pode ser retomado a partir do passo que falhou e, se reprocessar um mês, produz exatamente o mesmo resultado.

**Bloqueado por:** 05, 06, 09, 10, 11, 12, 13, 14

**Status:** ready-for-agent

- [ ] Workflow e gatilhos criados pelo Terraform (`infra/workflow.tf`), na ordem: ingestões em paralelo → crawler do `raw` → Bronzes em paralelo → DataBrew do IBGE → Silvers + consolidada → dimensões → fatos → manutenção → crawler Silver/Gold
- [ ] Gatilho mensal (dia 20) e gatilho sob demanda
- [ ] Todos os jobs visuais publicados pelo `scripts/deploy_jobs.py` a partir de `glue/jobs/`, com 1 nova tentativa e timeout próprio
- [ ] Execução completa na amostra termina com sucesso
- [ ] Prova de retomada: forçar falha num passo do meio, corrigir e retomar a partir dele
- [ ] Prova de idempotência: rodar o mesmo mês duas vezes e comparar as contagens da Gold
- [ ] Falha de regra bloqueante interrompe o Workflow e dispara o e-mail do ticket 06
