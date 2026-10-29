-- Esquema do dashboard no Postgres. Idempotente: roda no início de toda carga.
CREATE TABLE IF NOT EXISTS ativas_por_uf (
    ano_mes             text   NOT NULL,
    sigla_uf            text   NOT NULL,
    qtd_empresas_ativas bigint NOT NULL
);

-- O Metabase lê só as visões materializadas.
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_ativas_por_uf AS
SELECT ano_mes, sigla_uf, SUM(qtd_empresas_ativas)::bigint AS qtd_empresas_ativas
FROM ativas_por_uf
GROUP BY ano_mes, sigla_uf;
