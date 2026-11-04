-- Nó SQL Query do Glue Studio (job bronze_dominios): entrada com alias raw_motivos.
-- Domínio da Receita: código fica texto (zeros à esquerda), descrição sem espaços nas pontas.
SELECT codigo, trim(descricao) AS descricao, ano_mes
FROM raw_motivos
