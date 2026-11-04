-- Nó SQL Query do Glue Studio: entrada com alias raw_empresas.
-- Minimização (PRD, 5.7): a razão social não passa para a Bronze (no MEI ela traz o CPF do dono).
-- capital_social vem como "1000,00" e vira DECIMAL; códigos ficam texto (zeros à esquerda).
SELECT
    cnpj_basico,
    natureza_juridica,
    qualificacao_responsavel,
    CAST(replace(capital_social, ',', '.') AS DECIMAL(18, 2)) AS capital_social,
    porte,
    ente_federativo,
    ano_mes
FROM raw_empresas
