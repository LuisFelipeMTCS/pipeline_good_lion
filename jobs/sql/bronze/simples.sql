-- Nó SQL Query do Glue Studio: entrada com alias raw_simples.
-- Datas AAAAMMDD viram DATE ('00000000' e vazio viram nulo).
SELECT
    cnpj_basico,
    opcao_simples,
    to_date(data_opcao_simples, 'yyyyMMdd') AS data_opcao_simples,
    to_date(data_exclusao_simples, 'yyyyMMdd') AS data_exclusao_simples,
    opcao_mei,
    to_date(data_opcao_mei, 'yyyyMMdd') AS data_opcao_mei,
    to_date(data_exclusao_mei, 'yyyyMMdd') AS data_exclusao_mei,
    ano_mes
FROM raw_simples
