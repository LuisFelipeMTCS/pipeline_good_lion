-- Nó SQL Query do Glue Studio: entrada com alias raw_estabelecimentos.
-- Tipagem (SDK da Base dos Dados): datas AAAAMMDD viram DATE ('00000000' e vazio viram nulo);
-- códigos ficam como texto para não perder os zeros à esquerda.
-- Minimização (PRD, 5.7): o endereço (tipo de logradouro, logradouro, número, complemento, bairro, CEP)
-- não serve à análise e não passa para a Bronze. E-mail e CPF já vêm mascarados pelo nó anterior (Detect
-- Sensitive Data); a coluna DetectedEntities que ele acrescenta fica de fora porque as colunas são explícitas.
-- Rede de segurança para o que o detector não reconhece (medido na AWS, 04/11: ~50 e-mails malformados e
-- 2 CPFs colados ao texto por mês; na base completa, 6 por mês com pontuação, como "NOME123.456.789-01"):
-- e-mail que ainda tem @ e, no nome fantasia, CPF com ou sem pontuação e 11+ dígitos seguidos viram *****.
-- Telefone e fax também (PRD, 5.7): o tipo de telefone do detector só reconhece EUA e Canadá, então o número
-- vira ***** aqui; o DDD fica, porque indica a região e não identifica a pessoa.
SELECT
    cnpj_basico,
    cnpj_ordem,
    cnpj_dv,
    CAST(identificador_matriz_filial AS INT) AS identificador_matriz_filial,
    regexp_replace(nome_fantasia, '[0-9]{3}[.]?[0-9]{3}[.]?[0-9]{3}-?[0-9]{2}|[0-9]{11,}', '*****') AS nome_fantasia,
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
    CASE WHEN telefone_1 <> '' THEN '*****' END AS telefone_1,
    ddd_2,
    CASE WHEN telefone_2 <> '' THEN '*****' END AS telefone_2,
    ddd_fax,
    CASE WHEN fax <> '' THEN '*****' END AS fax,
    CASE WHEN email LIKE '%@%' THEN '*****' ELSE email END AS email,
    situacao_especial,
    to_date(data_situacao_especial, 'yyyyMMdd') AS data_situacao_especial,
    ano_mes
FROM raw_estabelecimentos
