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
FROM (
    -- Uma matriz por empresa (o cadastro tem raros CNPJs com duas): a ativa e, entre elas, a mais antiga.
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY cnpj_basico, ano_mes ORDER BY empresa_ativa DESC, data_inicio_atividade, cnpj_ordem
        ) AS ordem_matriz
    FROM silver_estabelecimentos
    WHERE identificador_matriz_filial = 1
) AS m
LEFT JOIN silver_empresas AS e ON e.cnpj_basico = m.cnpj_basico AND e.ano_mes = m.ano_mes
LEFT JOIN silver_simples AS s ON s.cnpj_basico = m.cnpj_basico AND s.ano_mes = m.ano_mes
WHERE m.ordem_matriz = 1
