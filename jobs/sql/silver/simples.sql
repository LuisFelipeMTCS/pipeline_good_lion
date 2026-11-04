-- Nó SQL Query do Glue Studio: entrada com alias bronze_simples.
-- MEI (PRD, seção 6): optante do MEI e sem data de exclusão.
SELECT
    *,
    (opcao_mei = 'S' AND data_exclusao_mei IS NULL) AS mei_ativo
FROM bronze_simples
