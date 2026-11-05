# Evidência do ticket 11: Data Quality na Silver

## Regras passando na amostra (AWS, 04/11/2026)

`silver_empresas` e `silver_simples` em 2026-09 e 2026-10, e `silver_estabelecimentos` e `gold_fato_empresa_mensal` nos dois meses: todas as regras bloqueantes e de alerta com nota 1,0. As regras dinâmicas de variação de linhas (`RowCount >= avg(last(1)) * 0.95`) foram avaliadas em 2026-10 contra o histórico de 2026-09. Resultados em `s3://goodlion-artifacts-724793286570/dq/` e em `aws glue list-data-quality-results`.

## Prova de que a regra bloqueante para o job

Injetar uma linha inválida no raw da amostra não serve aqui: com o Job Bookmark o lote da Bronze traria só o arquivo novo, e o `replaceWhere` trocaria o mês inteiro pela linha de teste. A prova foi feita do outro lado: o `silver_empresas` foi publicado temporariamente com uma regra que os dados reais quebram (`capital_social > 0`; a amostra tem empresas com capital R$ 0,00).

| Execução (2026-10) | Regra | Nota | Estado do job |
|---|---|---:|---|
| `jr_a8536de1…`, 1ª tentativa | `ColumnValues "capital_social" > 0` → **FAIL** ("Value: 0.0 does not meet the constraint requirement!") | 0,8 | **FAILED**: `AssertionError: The job failed due to failing DQ rules for node: limpar_empresas_nodesql`. Nada foi gravado |
| `jr_a8536de1…`, 2ª tentativa (regra correta republicada) | `ColumnValues "capital_social" >= 0` → PASS | 1,0 | SUCCEEDED |

A 2ª tentativa automática já usou o job republicado: a regra bloqueante para o job e, corrigida a causa, a nova tentativa passa.

**E-mail:** o EventBridge só avisa a falha final de uma execução. Como a nova tentativa passou, essa execução não gerou e-mail. O e-mail de falha veio da falha forçada do ticket 06 (as duas tentativas falharam).
