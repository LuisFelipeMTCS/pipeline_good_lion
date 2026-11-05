# 11: Data Quality na Silver

**O que construir:** dados ruins param o pipeline. As regras de Glue Data Quality da seção 5.6 do PRD rodam na Silver: as bloqueantes fazem o job falhar e as de alerta só registram. Os resultados ficam gravados para servir de evidência.

As regras ficam em `jobs/quality/<nome do job>.dqdl` (ex.: `jobs/quality/silver_estabelecimentos.dqdl`). O Glue Data Quality não roda no container, então a prova é feita na AWS, sobre a amostra. Pastas, nomes e padrões: [ARQUITETURA](../ARQUITETURA.md).

**Bloqueado por:** 08

**Status:** done

- [x] Bloqueante: `cnpj_basico` com 8 dígitos e sem nulos
- [x] Bloqueante: `cnpj_basico` único por `ano_mes` na fato
- [x] Bloqueante: `porte` ∈ {00, 01, 03, 05}
- [x] Bloqueante: `capital_social` ≥ 0
- [x] Alerta: variação de linhas do mês de no máximo ±5% em relação ao mês anterior
- [x] Alerta: `data_inicio_atividade` não futura
- [x] Alerta: percentual de e-mails nulos
- [x] O `scripts/deploy_jobs.py` injeta o `.dqdl` no nó Evaluate Data Quality de cada job
- [x] Teste: injetar uma linha inválida na amostra faz o job falhar; remover a linha faz o job passar
- [x] Resultados de DQ gravados no `artifacts`, com prints em `docs/evidencias/`

## Andamento (03/11/2026)

**Como ficou:** o DQDL não tem severidade por regra, e "parar o job na falha" é opção do nó inteiro. Por isso cada job Silver tem dois nós Evaluate Data Quality em sequência: `SQL → bloqueante (para o job) → alertas (só registra) → GravarDelta`. Os resultados vão para `s3://goodlion-artifacts-<conta>/dq/`, cada nó com seu `EvaluationContext`.

| Arquivo | Regras |
|---|---|
| `jobs/quality/silver_estabelecimentos.dqdl` | `cnpj_basico` completo e com 8 dígitos |
| `jobs/quality/silver_estabelecimentos_alertas.dqdl` | linhas entre 95% e 105% do mês anterior (`avg(last(1))`), `data_inicio_atividade <= now()`, e-mail preenchido em pelo menos 50% |
| `jobs/quality/silver_empresas.dqdl` | `cnpj_basico` completo e com 8 dígitos, `porte` em {00, 01, 03, 05}, `capital_social` completo e ≥ 0 |
| `jobs/quality/silver_empresas_alertas.dqdl`, `silver_simples_alertas.dqdl` | variação de linhas de ±5% |
| `jobs/quality/silver_simples.dqdl` | `cnpj_basico` completo e com 8 dígitos |
| `jobs/quality/gold_fato_empresa_mensal.dqdl` | `cnpj_basico` único (o lote é um mês só, então é único por `ano_mes`), 8 dígitos, categoria válida, capital ≥ 0 |

**E-mail nulo:** o CSV da Receita traz `""` no lugar de e-mail ausente, e isso não conta como nulo. A Silver de Estabelecimentos troca vazio por nulo (teste `test_silver_troca_email_vazio_por_nulo`). Na amostra, 60% dos estabelecimentos têm e-mail (285.272 de 474.123), por isso o alerta começa em 50%.

**Ainda não validado:** a sintaxe das regras dinâmicas (`avg(last(1))`) e do `now()` só é conferida pelo Glue na primeira execução. Na primeira execução não há mês anterior no histórico.

**Falta na AWS:** `make deploy-jobs`; rodar as Silver da amostra (2026-09 e depois 2026-10, para o alerta de variação ter histórico); injetar uma linha com `cnpj_basico` de 7 dígitos no raw da amostra e ver o job falhar (e o e-mail do ticket 06 chegar); remover a linha e ver passar; prints em `docs/evidencias/`.

## Na AWS (04/11/2026)

Todas as regras passaram na amostra, inclusive as dinâmicas (`avg(last(1))`) e o `now()`. Prova da regra bloqueante: regra mais rígida publicada temporariamente → job falhou sem gravar; regra correta → a nova tentativa passou. Detalhes e por que não foi uma linha injetada no raw: `docs/evidencias/11-data-quality.md`.

