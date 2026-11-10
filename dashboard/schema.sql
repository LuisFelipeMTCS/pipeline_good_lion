-- Esquema do dashboard no Postgres. Idempotente: roda no início de toda carga.

-- Gold provisória do ticket 02, substituída pela fato no ticket 08.
DROP MATERIALIZED VIEW IF EXISTS mv_ativas_por_uf;
DROP TABLE IF EXISTS ativas_por_uf;

CREATE TABLE IF NOT EXISTS fato_empresa_mensal (
    ano_mes               text    NOT NULL,
    cnpj_basico           text    NOT NULL,
    id_municipio_rf       text,
    id_categoria          text    NOT NULL,
    id_cnae               text,
    id_natureza_juridica  text,
    data_inicio_atividade date,
    capital_social        numeric(18, 2),
    qtd_estabelecimentos  bigint  NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_municipio (
    id_municipio_rf   text PRIMARY KEY,
    id_municipio_ibge text,
    nome              text,
    sigla_uf          text,
    regiao            text
);

CREATE TABLE IF NOT EXISTS dim_categoria (
    id_categoria text PRIMARY KEY,
    nome         text NOT NULL,
    ordem        int  NOT NULL
);

-- O Metabase lê só as visões materializadas. Pergunta 1: quantidade e proporção de MEI, ME, EPP e Demais.
-- A proporção é sobre o total de empresas ativas do lugar no mês.
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_categorias_municipio AS
SELECT
    f.ano_mes, m.regiao, m.sigla_uf, m.nome AS municipio, c.nome AS categoria, c.ordem,
    COUNT(*) AS qtd_empresas,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY f.ano_mes, f.id_municipio_rf), 4) AS proporcao
FROM fato_empresa_mensal AS f
JOIN dim_municipio AS m USING (id_municipio_rf)
JOIN dim_categoria AS c USING (id_categoria)
GROUP BY f.ano_mes, f.id_municipio_rf, m.regiao, m.sigla_uf, m.nome, c.nome, c.ordem;

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_categorias_uf AS
SELECT
    f.ano_mes, m.regiao, m.sigla_uf, c.nome AS categoria, c.ordem,
    COUNT(*) AS qtd_empresas,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY f.ano_mes, m.sigla_uf), 4) AS proporcao
FROM fato_empresa_mensal AS f
JOIN dim_municipio AS m USING (id_municipio_rf)
JOIN dim_categoria AS c USING (id_categoria)
GROUP BY f.ano_mes, m.regiao, m.sigla_uf, c.nome, c.ordem;

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_categorias_regiao AS
SELECT
    f.ano_mes, m.regiao, c.nome AS categoria, c.ordem,
    COUNT(*) AS qtd_empresas,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY f.ano_mes, m.regiao), 4) AS proporcao
FROM fato_empresa_mensal AS f
JOIN dim_municipio AS m USING (id_municipio_rf)
JOIN dim_categoria AS c USING (id_categoria)
GROUP BY f.ano_mes, m.regiao, c.nome, c.ordem;

-- Pergunta 2: capital social declarado na abertura (não é faturamento nem lucro), em média e soma. A mediana
-- foi descartada: nas Demais ela é R$ 0 (pelo menos metade declara capital zero). Valores na casa dos bilhões puxam a média.
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_capital_municipio AS
SELECT
    f.ano_mes, m.regiao, m.sigla_uf, m.nome AS municipio,
    COUNT(*) AS qtd_empresas,
    AVG(f.capital_social)::numeric(18, 2) AS media_capital_social,
    SUM(f.capital_social) AS soma_capital_social
FROM fato_empresa_mensal AS f
JOIN dim_municipio AS m USING (id_municipio_rf)
GROUP BY f.ano_mes, f.id_municipio_rf, m.regiao, m.sigla_uf, m.nome;

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_capital_uf AS
SELECT
    f.ano_mes, m.regiao, m.sigla_uf,
    COUNT(*) AS qtd_empresas,
    AVG(f.capital_social)::numeric(18, 2) AS media_capital_social,
    SUM(f.capital_social) AS soma_capital_social
FROM fato_empresa_mensal AS f
JOIN dim_municipio AS m USING (id_municipio_rf)
GROUP BY f.ano_mes, m.regiao, m.sigla_uf;

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_capital_regiao AS
SELECT
    f.ano_mes, m.regiao,
    COUNT(*) AS qtd_empresas,
    AVG(f.capital_social)::numeric(18, 2) AS media_capital_social,
    SUM(f.capital_social) AS soma_capital_social
FROM fato_empresa_mensal AS f
JOIN dim_municipio AS m USING (id_municipio_rf)
GROUP BY f.ano_mes, m.regiao;

-- Pergunta 3: aberturas, baixas e mudanças vindas do Change Data Feed (ticket 12).
CREATE TABLE IF NOT EXISTS fato_movimentacao_empresa (
    ano_mes         text NOT NULL,
    cnpj_basico     text NOT NULL,
    tipo_evento     text NOT NULL,
    id_municipio_rf text,
    id_categoria    text
);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_movimentacao_municipio AS
SELECT f.ano_mes, m.regiao, m.sigla_uf, m.nome AS municipio, f.tipo_evento, c.nome AS categoria, COUNT(*) AS qtd_eventos
FROM fato_movimentacao_empresa AS f
JOIN dim_municipio AS m USING (id_municipio_rf)
JOIN dim_categoria AS c USING (id_categoria)
GROUP BY f.ano_mes, f.id_municipio_rf, m.regiao, m.sigla_uf, m.nome, f.tipo_evento, c.nome;

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_movimentacao_uf AS
SELECT f.ano_mes, m.regiao, m.sigla_uf, f.tipo_evento, c.nome AS categoria, COUNT(*) AS qtd_eventos
FROM fato_movimentacao_empresa AS f
JOIN dim_municipio AS m USING (id_municipio_rf)
JOIN dim_categoria AS c USING (id_categoria)
GROUP BY f.ano_mes, m.regiao, m.sigla_uf, f.tipo_evento, c.nome;

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_movimentacao_regiao AS
SELECT f.ano_mes, m.regiao, f.tipo_evento, c.nome AS categoria, COUNT(*) AS qtd_eventos
FROM fato_movimentacao_empresa AS f
JOIN dim_municipio AS m USING (id_municipio_rf)
JOIN dim_categoria AS c USING (id_categoria)
GROUP BY f.ano_mes, m.regiao, f.tipo_evento, c.nome;
