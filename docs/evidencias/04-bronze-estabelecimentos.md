# Evidência: Bronze de Estabelecimentos na AWS (ticket 04)

Job `bronze_estabelecimentos` (Glue 5.0, G.1X × 2, Flex, Bookmarks ligados), conta 724793286570, 28/10/2026.

## Execuções

| Execução | Situação | Tempo | DPU-s | Versões Delta depois |
|---|---|---:|---:|---|
| 1ª (Bookmark zerado) | SUCCEEDED | 205 s | 410 | `00000000000000000000.json` |
| 2ª (sem arquivos novos) | SUCCEEDED | 90 s | 180 | `00000000000000000000.json` (nada regravado) |

## Athena (workgroup `goodlion`)

```sql
SELECT ano_mes, COUNT(*) FROM goodlion_raw.estabelecimentos GROUP BY 1;     -- 2026-09: 474123 | 2026-10: 476553
SELECT ano_mes, COUNT(*) FROM goodlion_bronze.estabelecimentos GROUP BY 1;  -- 2026-09: 474123 | 2026-10: 476553
SELECT MIN(cnpj_basico), MIN(length(cnpj_basico)), MAX(length(cnpj_basico))
FROM goodlion_bronze.estabelecimentos;                                      -- 00000000 | 8 | 8
SELECT typeof(cnpj_basico), typeof(identificador_matriz_filial), typeof(situacao_cadastral), typeof(data_inicio_atividade)
FROM goodlion_bronze.estabelecimentos LIMIT 1;                              -- varchar | integer | varchar | date
SELECT ano_mes, COUNT(*) FROM goodlion_bronze.estabelecimentos
WHERE identificador_matriz_filial = 1 AND situacao_cadastral = '02' GROUP BY 1;  -- 2026-09: 145721 | 2026-10: 145932
```

As matrizes ativas batem com o ticket 01 e com o tracer local do ticket 02.

A tabela `goodlion_bronze.estabelecimentos` foi registrada à mão no Athena
(`CREATE EXTERNAL TABLE ... LOCATION 's3://goodlion-bronze-724793286570/sample/estabelecimentos/' TBLPROPERTIES ('table_type'='DELTA')`);
o crawler da Silver/Gold é do ticket 14.
