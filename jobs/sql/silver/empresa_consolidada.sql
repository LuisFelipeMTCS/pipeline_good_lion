-- Nó SQL Query do Glue Studio: entradas com alias silver_estabelecimentos, silver_empresas e silver_simples,
-- já limitadas ao --ano_mes. Estado da empresa no mês, uma linha por cnpj_basico (a matriz), que o
-- MERGE (jobs/custom/merge_consolidada.py) aplica na silver_empresa_consolidada.
-- A categoria segue a mesma regra da fato_empresa_mensal.
SELECT
    m.cnpj_basico,
    m.situacao_cadastral,
    m.empresa_ativa,
    m.id_municipio_rf,
    e.porte,
    COALESCE(s.mei_ativo, FALSE) AS mei_ativo,
    CASE
        WHEN s.mei_ativo THEN 'MEI'
        WHEN e.porte = '01' THEN 'ME'
        WHEN e.porte = '03' THEN 'EPP'
        ELSE 'DEMAIS'
    END AS id_categoria
FROM silver_estabelecimentos AS m
LEFT JOIN silver_empresas AS e ON e.cnpj_basico = m.cnpj_basico AND e.ano_mes = m.ano_mes
LEFT JOIN silver_simples AS s ON s.cnpj_basico = m.cnpj_basico AND s.ano_mes = m.ano_mes
WHERE m.identificador_matriz_filial = 1
