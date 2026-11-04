-- Nó SQL Query do Glue Studio (job gold_dimensoes): entrada com alias bronze_cnaes. Vale o mês mais recente.
SELECT codigo AS id_cnae, descricao
FROM bronze_cnaes
WHERE ano_mes = (SELECT MAX(ano_mes) FROM bronze_cnaes)
