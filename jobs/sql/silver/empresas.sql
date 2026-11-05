-- Nó SQL Query do Glue Studio: entrada com alias bronze_empresas.
-- Porte vazio vira '00' (não informado), que a Gold conta como Demais.
-- Um cnpj_basico por mês: o arquivo da Receita traz raras duplicatas (2026-09 e 2026-10: o 08314885 duas vezes,
-- uma com porte 05 e outra sem porte). Fica a linha com porte preenchido e, no empate, a de maior capital.
SELECT
    cnpj_basico,
    natureza_juridica,
    qualificacao_responsavel,
    capital_social,
    porte,
    ente_federativo,
    ano_mes
FROM (
    SELECT
        cnpj_basico,
        natureza_juridica,
        qualificacao_responsavel,
        capital_social,
        COALESCE(NULLIF(trim(porte), ''), '00') AS porte,
        ente_federativo,
        ano_mes,
        ROW_NUMBER() OVER (
            PARTITION BY cnpj_basico, ano_mes
            ORDER BY NULLIF(trim(porte), '') IS NULL, capital_social DESC
        ) AS ordem
    FROM bronze_empresas
) AS empresas
WHERE ordem = 1
