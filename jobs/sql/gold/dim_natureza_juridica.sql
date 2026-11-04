-- Nó SQL Query do Glue Studio (job gold_dimensoes): entrada com alias bronze_naturezas. Vale o mês mais recente.
SELECT codigo AS id_natureza_juridica, descricao
FROM bronze_naturezas
WHERE ano_mes = (SELECT MAX(ano_mes) FROM bronze_naturezas)
