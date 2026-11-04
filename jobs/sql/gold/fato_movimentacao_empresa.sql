-- Nó SQL Query do Glue Studio: entrada com alias mudancas (Change Data Feed da silver_empresa_consolidada
-- nas versões do --ano_mes, lido pelo jobs/custom/ler_mudancas.py). Um evento por empresa e tipo no mês:
-- abertura (empresa nova e ativa), baixa (situação passou a 08), mudança de porte, entrada e saída do MEI.
-- Empresa removida pelo MERGE (sumiu do arquivo da Receita) não é evento.
WITH alteradas AS (
    SELECT
        depois.*,
        antes.situacao_cadastral AS situacao_antes,
        antes.porte AS porte_antes,
        antes.mei_ativo AS mei_antes
    FROM mudancas AS depois
    JOIN mudancas AS antes
        ON antes.cnpj_basico = depois.cnpj_basico
        AND antes._commit_version = depois._commit_version
        AND antes._change_type = 'update_preimage'
    WHERE depois._change_type = 'update_postimage'
),
eventos AS (
    SELECT cnpj_basico, 'abertura' AS tipo_evento, id_municipio_rf, id_categoria, ano_mes
    FROM mudancas
    WHERE _change_type = 'insert' AND empresa_ativa
    UNION ALL
    SELECT cnpj_basico, 'baixa', id_municipio_rf, id_categoria, ano_mes
    FROM alteradas
    WHERE situacao_cadastral = '08' AND NOT (situacao_antes <=> '08')
    UNION ALL
    SELECT cnpj_basico, 'mudanca_porte', id_municipio_rf, id_categoria, ano_mes
    FROM alteradas
    WHERE NOT (porte <=> porte_antes)
    UNION ALL
    SELECT cnpj_basico, 'entrada_mei', id_municipio_rf, id_categoria, ano_mes
    FROM alteradas
    WHERE mei_ativo AND NOT COALESCE(mei_antes, FALSE)
    UNION ALL
    SELECT cnpj_basico, 'saida_mei', id_municipio_rf, id_categoria, ano_mes
    FROM alteradas
    WHERE COALESCE(mei_antes, FALSE) AND NOT mei_ativo
)
SELECT DISTINCT cnpj_basico, tipo_evento, id_municipio_rf, id_categoria, ano_mes
FROM eventos
