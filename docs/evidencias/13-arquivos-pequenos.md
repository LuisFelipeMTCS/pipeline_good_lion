# Evidência do ticket 13: arquivos pequenos, OPTIMIZE e VACUUM

## Amostra local (MinIO, 03/11/2026)

Medição com `DESCRIBE DETAIL` (arquivos ativos e tamanho) antes e depois de `make pipeline` + o job `manutencao` (`jobs/custom/manutencao.py`), sobre 2026-09 e 2026-10. O job achou e tratou 20 tabelas Delta. As tabelas que não mudaram já tinham 1 arquivo por partição (domínios e dimensões).

| Tabela | Arquivos antes | Por partição | Tamanho médio antes (MB) | Arquivos depois | Tamanho médio depois (MB) |
|---|---:|---:|---:|---:|---:|
| `bronze/empresas` | 18 | 9 | 0.38 | 2 | 3.41 |
| `bronze/estabelecimentos` | 40 | 20 | 1.29 | 2 | 24.94 |
| `bronze/simples` | 10 | 5 | 0.54 | 2 | 2.70 |
| `silver/empresa_consolidada` | 26 | 26 | 0.15 | 1 | 3.74 |
| `silver/empresas` | 18 | 9 | 0.38 | 2 | 3.41 |
| `silver/estabelecimentos` | 40 | 20 | 1.29 | 2 | 24.99 |
| `silver/simples` | 10 | 5 | 0.55 | 2 | 2.74 |
| `gold/dim_categoria` | 4 | 4 | 0.00 | 1 | 0.00 |
| `gold/fato_empresa_mensal` | 40 | 20 | 0.11 | 2 | 1.91 |

Consulta de referência (contagem e mediana do capital por categoria na `fato_empresa_mensal` de 2026-10, Spark local): 0.86 s antes, 0.75 s depois. Na amostra a diferença é pequena porque as tabelas são pequenas. O ganho que vale para o relatório é o volume lido e o tempo no Athena (pendente, abaixo).

**Integridade:** depois do `VACUUM` (7 dias, então nada foi apagado ainda: todos os arquivos têm menos de 7 dias) as tabelas continuam legíveis, e a consulta acima roda sobre elas. O teste `tests/test_manutencao.py` confere a contagem de linhas depois da compactação.

## Na AWS (04/11/2026, amostra)

Arquivos ativos por partição (`count(DISTINCT "$path")` no Athena) antes e depois do job `manutencao`:

| Tabela | Antes | Depois |
|---|---:|---:|
| `bronze.estabelecimentos` (por mês) | 2 | 1 |
| `silver.estabelecimentos` (por mês) | 2 | 1 |
| `silver.empresa_consolidada` | 4 | 1 |
| `gold.fato_empresa_mensal` (por mês) | 4 | 1 |
| `gold.fato_movimentacao_empresa` (2026-10) | 4 | 1 |
| `gold.dim_categoria` | 4 | 1 |
| Empresas, Simples (Bronze e Silver), domínios | 1 | 1 |

Na AWS, com 2 workers, o Glue já grava poucos arquivos (no máximo 4 por partição, contra 20 no Spark local). A consulta de referência abaixo lê os mesmos 0,24 MB antes e depois e leva de 1,3 s a 2,4 s nas duas situações (3 execuções cada): na amostra não há diferença mensurável. O ganho aparece com a base completa e com reprocessamentos, que acumulam arquivos (cada `replaceWhere` e cada `MERGE` gera arquivos novos).

**Custo do job:** 742 s, 1.485 DPU-s (~US$ 0,12) para 19 tabelas, uma após a outra. Na base completa, vale limitar o `OPTIMIZE` às partições do mês processado.

**Integridade:** depois do `VACUUM`, as contagens da fato e da Silver no Athena continuam as mesmas.

Consulta de referência, no workgroup `goodlion`:

```sql
SELECT id_categoria, count(*) AS empresas, approx_percentile(capital_social, 0.5) AS mediana
FROM goodlion_gold.fato_empresa_mensal
WHERE ano_mes = '2026-10'
GROUP BY 1;
```

