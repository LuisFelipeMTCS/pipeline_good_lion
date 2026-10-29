-- Nó SQL Query do Glue Studio: entrada com alias bronze_estabelecimentos.
-- Empresa ativa (PRD, seção 6): situação cadastral 02 no estabelecimento matriz.
SELECT *, (identificador_matriz_filial = 1 AND situacao_cadastral = '02') AS empresa_ativa
FROM bronze_estabelecimentos
