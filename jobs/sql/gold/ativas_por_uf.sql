-- Nó SQL Query do Glue Studio: entrada com alias silver_estabelecimentos.
SELECT ano_mes, sigla_uf, COUNT(*) AS qtd_empresas_ativas
FROM silver_estabelecimentos
WHERE empresa_ativa
GROUP BY ano_mes, sigla_uf
