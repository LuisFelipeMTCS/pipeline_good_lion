-- Nó SQL Query do Glue Studio: entradas com alias bronze_municipios (domínio da Receita),
-- bronze_estabelecimentos, silver_ibge_municipios (saída da receita do DataBrew) e
-- municipios_correcoes (jobs/referencias/municipios_correcoes.csv).
-- O código da Receita não é o do IBGE e o domínio não traz UF: a UF vem dos estabelecimentos (a com mais
-- estabelecimentos no código, porque há cadastros com UF trocada) e o casamento é por nome + UF.
-- EX (exterior) fica de fora: não tem município no IBGE.
WITH uf_do_municipio AS (
    SELECT id_municipio_rf, sigla_uf
    FROM (
        SELECT
            id_municipio_rf,
            sigla_uf,
            ROW_NUMBER() OVER (PARTITION BY id_municipio_rf ORDER BY COUNT(*) DESC, sigla_uf) AS ordem
        FROM bronze_estabelecimentos
        WHERE sigla_uf <> 'EX'
        GROUP BY id_municipio_rf, sigla_uf
    ) AS contagem
    WHERE ordem = 1
),
receita AS (
    SELECT codigo AS id_municipio_rf, descricao AS nome_receita
    FROM bronze_municipios
    WHERE ano_mes = (SELECT MAX(ano_mes) FROM bronze_municipios)
)
SELECT
    r.id_municipio_rf,
    CAST(i.id_municipio_ibge AS STRING) AS id_municipio_ibge,
    COALESCE(i.nome, r.nome_receita) AS nome,
    u.sigla_uf,
    i.regiao
FROM receita AS r
JOIN uf_do_municipio AS u ON u.id_municipio_rf = r.id_municipio_rf
LEFT JOIN municipios_correcoes AS c ON c.id_municipio_rf = r.id_municipio_rf
-- Sem par aqui, id_municipio_ibge fica nulo e a regra bloqueante de qualidade derruba o job.
LEFT JOIN silver_ibge_municipios AS i
    ON i.sigla_uf = u.sigla_uf AND i.nome_normalizado = COALESCE(c.nome_ibge, r.nome_receita)
