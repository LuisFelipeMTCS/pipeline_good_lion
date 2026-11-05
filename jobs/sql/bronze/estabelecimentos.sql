-- Nó SQL Query do Glue Studio: entrada com alias raw_estabelecimentos.
-- Tipagem (SDK da Base dos Dados): datas AAAAMMDD viram DATE ('00000000' e vazio viram nulo);
-- códigos ficam como texto para não perder os zeros à esquerda.
-- Minimização (PRD, 5.7): o endereço (tipo de logradouro, logradouro, número, complemento, bairro, CEP)
-- não serve à análise e não passa para a Bronze. E-mail e CPF já vêm mascarados pelo nó anterior (Detect
-- Sensitive Data); a coluna DetectedEntities que ele acrescenta fica de fora porque as colunas são explícitas.
SELECT
    cnpj_basico,
    cnpj_ordem,
    cnpj_dv,
    CAST(identificador_matriz_filial AS INT) AS identificador_matriz_filial,
    nome_fantasia,
    situacao_cadastral,
    to_date(data_situacao_cadastral, 'yyyyMMdd') AS data_situacao_cadastral,
    motivo_situacao_cadastral,
    nome_cidade_exterior,
    id_pais,
    to_date(data_inicio_atividade, 'yyyyMMdd') AS data_inicio_atividade,
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
    email,
    situacao_especial,
    to_date(data_situacao_especial, 'yyyyMMdd') AS data_situacao_especial,
    ano_mes
FROM raw_estabelecimentos
