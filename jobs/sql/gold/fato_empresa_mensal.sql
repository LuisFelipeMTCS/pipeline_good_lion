-- Nó SQL Query do Glue Studio: entradas com alias silver_estabelecimentos, silver_empresas e silver_simples,
-- todas já limitadas ao --ano_mes. Grão: 1 empresa ativa × ano_mes (PRD, seção 6).
-- Empresa ativa e localização vêm do estabelecimento matriz; categoria: MEI primeiro (todo MEI tem
-- porte 01), depois o porte (01 = ME, 03 = EPP, 05 ou 00 = Demais).
WITH matriz AS (
    -- Uma matriz por empresa: o cadastro da Receita tem raros CNPJs com duas matrizes ativas (08314885 na base
    -- completa). Vale a mais antiga.
    SELECT *
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY cnpj_basico, ano_mes ORDER BY data_inicio_atividade, cnpj_ordem
            ) AS ordem_matriz
        FROM silver_estabelecimentos
        WHERE empresa_ativa
    ) AS matrizes
    WHERE ordem_matriz = 1
),
estabelecimentos_ativos AS (
    SELECT cnpj_basico, ano_mes, COUNT(*) AS qtd_estabelecimentos
    FROM silver_estabelecimentos
    WHERE situacao_cadastral = '02'
    GROUP BY cnpj_basico, ano_mes
)
SELECT
    m.cnpj_basico,
    m.id_municipio_rf,
    CASE
        WHEN s.mei_ativo THEN 'MEI'
        WHEN e.porte = '01' THEN 'ME'
        WHEN e.porte = '03' THEN 'EPP'
        ELSE 'DEMAIS'
    END AS id_categoria,
    m.cnae_fiscal_principal AS id_cnae,
    e.natureza_juridica AS id_natureza_juridica,
    m.data_inicio_atividade,
    e.capital_social,
    a.qtd_estabelecimentos,
    m.ano_mes
FROM matriz AS m
JOIN silver_empresas AS e ON e.cnpj_basico = m.cnpj_basico AND e.ano_mes = m.ano_mes
LEFT JOIN silver_simples AS s ON s.cnpj_basico = m.cnpj_basico AND s.ano_mes = m.ano_mes
JOIN estabelecimentos_ativos AS a ON a.cnpj_basico = m.cnpj_basico AND a.ano_mes = m.ano_mes
