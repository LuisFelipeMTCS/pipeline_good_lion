# 16: Workflow ponta a ponta

**O que construir:** o pipeline inteiro orquestrado por um Glue Workflow (seção 7.1 do PRD), disparado por gatilho mensal (dia 20) ou sob demanda. O Workflow para quando uma regra bloqueante falha, pode ser retomado a partir do passo que falhou e, se reprocessar um mês, produz exatamente o mesmo resultado.

**Bloqueado por:** 05, 06, 09, 10, 11, 12, 13, 14

**Status:** in-progress (Workflow no Terraform; falta aplicar e as provas na AWS)

- [x] Workflow e gatilhos criados pelo Terraform (`infra/workflow.tf`), na ordem: ingestões em paralelo → crawler do `raw` → Bronzes em paralelo → DataBrew do IBGE → Silvers + consolidada → dimensões → fatos → manutenção → crawler Silver/Gold
- [x] Gatilho mensal (dia 20) e gatilho sob demanda
- [x] Todos os jobs visuais publicados pelo `scripts/deploy_jobs.py` a partir de `glue/jobs/`, com 1 nova tentativa e timeout próprio
- [ ] Execução completa na amostra termina com sucesso
- [ ] Prova de retomada: forçar falha num passo do meio, corrigir e retomar a partir dele
- [ ] Prova de idempotência: rodar o mesmo mês duas vezes e comparar as contagens da Gold
- [ ] Falha de regra bloqueante interrompe o Workflow e dispara o e-mail do ticket 06

## Andamento (03/11/2026)

**`infra/workflow.tf`:** Workflow `goodlion` (uma execução por vez, por causa do `MERGE` da consolidada) com 8 gatilhos condicionais em sequência: `definir_mes` → ingestões → crawler do raw → Bronzes + `trigger_databrew` → Silvers → consolidada + `dim_municipio` + `gold_dimensoes` → fatos → `manutencao` → crawlers da Silver e da Gold. Cada etapa espera todas as da anterior terminarem com `SUCCEEDED`. Uma falha (inclusive de regra bloqueante de DQ) para o Workflow ali, e `aws glue resume-workflow-run` retoma do passo que falhou.

**Como o mês chega aos jobs:** o Workflow não passa argumento dinâmico. O mês fica nas propriedades da execução: sob demanda, `make workflow ANO_MES=2026-09` (`ingestao=nao` por padrão, para rodar sobre a amostra que já está no raw, sem baixar 2 h de Receita; `INGESTAO=sim` baixa). No gatilho mensal, o `definir_mes` (`ingest/definir_mes.py`) grava o mês corrente. As ingestões e os Custom Transforms (`FiltrarMes`, `MergeConsolidada`, `LerMudancas`) leem o `--ano_mes` ou, dentro do Workflow, as propriedades (testes em `tests/test_workflow.py` e `tests/test_filtrar_mes.py`).

**Gatilho mensal desligado:** `goodlion-mensal` (dia 20, 9h UTC) é criado com `enabled = false`, para não rodar e gastar todo mês sem ninguém pedir. Liga com `aws glue start-trigger --name goodlion-mensal`. Ainda não conferido: se o `start-workflow-run` funciona com o gatilho inicial desligado (se não funcionar, ligar o gatilho ou trocá-lo por `ON_DEMAND`).

**Todos os jobs visuais** em `glue/jobs/` têm 1 nova tentativa e timeout próprio (30 min; `manutencao`, 60).

**Ordem na AWS:**
1. `make deploy-jobs` (os gatilhos referenciam os jobs visuais pelo nome);
2. `terraform apply`;
3. `make workflow ANO_MES=2026-09`, depois `make workflow ANO_MES=2026-10` (nessa ordem, por causa do CDC);
4. Provas: retomada (ex.: apagar o `silver/ibge_municipios/` para o `gold_dim_municipio` falhar, recriar e `resume-workflow-run`); idempotência (repetir 2026-10 e comparar as contagens da Gold); regra bloqueante (linha com `cnpj_basico` inválido) parando o Workflow e mandando o e-mail.

