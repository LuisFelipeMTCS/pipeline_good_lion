-- Nó SQL Query do Glue Studio: entrada com alias bronze_estabelecimentos.
-- Empresa ativa (PRD, seção 6): situação cadastral 02 no estabelecimento matriz.
-- E-mail vazio vira nulo (o CSV da Receita traz "" no lugar de nada): é o que a regra de completude mede.
SELECT
    cnpj_basico,
    cnpj_ordem,
    cnpj_dv,
    identificador_matriz_filial,
    nome_fantasia,
    situacao_cadastral,
    data_situacao_cadastral,
    motivo_situacao_cadastral,
    nome_cidade_exterior,
    id_pais,
    data_inicio_atividade,
    cnae_fiscal_principal,
    cnae_fiscal_secundaria,
    sigla_uf,
    id_municipio_rf,
    ddd_1,
    telefone_1,
    ddd_2,
    telefone_2,
    ddd_fax,
    fax,
    NULLIF(trim(email), '') AS email,
    situacao_especial,
    data_situacao_especial,
    (identificador_matriz_filial = 1 AND situacao_cadastral = '02') AS empresa_ativa,
    ano_mes
FROM bronze_estabelecimentos
