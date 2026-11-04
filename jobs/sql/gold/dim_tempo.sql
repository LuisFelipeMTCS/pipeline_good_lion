-- Nó SQL Query do Glue Studio (job gold_dimensoes): entrada com alias silver_estabelecimentos.
-- Um mês por ano_mes processado.
SELECT
    ano_mes,
    CAST(substr(ano_mes, 1, 4) AS INT) AS ano,
    CAST(substr(ano_mes, 6, 2) AS INT) AS mes,
    CAST(ceil(CAST(substr(ano_mes, 6, 2) AS INT) / 3) AS INT) AS trimestre
FROM (SELECT DISTINCT ano_mes FROM silver_estabelecimentos) AS meses
