-- Nó SQL Query do Glue Studio: entrada com alias bronze_empresas.
-- Porte vazio vira '00' (não informado), que a Gold conta como Demais.
SELECT
    cnpj_basico,
    natureza_juridica,
    qualificacao_responsavel,
    capital_social,
    COALESCE(NULLIF(trim(porte), ''), '00') AS porte,
    ente_federativo,
    ano_mes
FROM bronze_empresas
