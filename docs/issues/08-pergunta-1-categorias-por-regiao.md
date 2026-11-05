# 08: Pergunta 1: MEI/ME/EPP/Demais por município, UF e região

**O que construir:** a primeira pergunta de negócio respondida de ponta a ponta sobre a amostra. Empresas, Estabelecimentos e Simples passam pela Bronze e pela Silver, a Gold ganha as dimensões e a `fato_empresa_mensal`, e o Metabase mostra a quantidade e a proporção de MEI, ME, EPP e Demais por município, UF e região.

Regras de negócio (PRD, seção 6):
- **Categoria:** MEI se optante do MEI sem data de exclusão; senão, pelo porte (01 = ME, 03 = EPP, 05 ou 00 = Demais). O MEI é avaliado primeiro, porque todo MEI também tem porte 01.
- **Empresa ativa:** `situacao_cadastral = 02` no estabelecimento matriz.
- **Localização:** município do estabelecimento matriz.
- Sem `dim_empresa`.

Pastas, nomes e padrões: [ARQUITETURA](../ARQUITETURA.md).

> É o maior ticket. Se ficar grande demais, separar em "Bronze/Silver + dimensões" e "fato + dashboard".

**Bloqueado por:** 02, 04, 07

**Status:** in-progress (Gold na AWS igual à local; faltam dim_municipio na AWS e os gráficos no Metabase)

- [x] Jobs visuais da Bronze de Empresas e Simples, seguindo o padrão do ticket 04 (Bookmarks, parâmetros, JSON em `glue/jobs/` com o SQL de `jobs/sql/bronze/` injetado pelo deploy)
- [x] Jobs visuais da Silver de Empresas, Estabelecimentos e Simples, limitados por `--ano_mes`, com SQL em `jobs/sql/silver/` (a de Estabelecimentos já existe desde o ticket 02)
- [x] `dim_categoria` (4 linhas), `dim_cnae`, `dim_natureza_juridica` e `dim_tempo` na Gold, com SQL em `jobs/sql/gold/`
- [x] `fato_empresa_mensal` com grão 1 empresa ativa × `ano_mes`, `cnpj_basico` como dimensão degenerada, medidas `capital_social` e `qtd_estabelecimentos`
- [x] Testes locais com pytest (via `jobs/local.py`) para a regra de categoria (incluindo MEI com data de exclusão e MEI com porte 01)
- [x] Reprocessar o mesmo `ano_mes` dá o mesmo resultado
- [x] Crawler ou registro manual deixa a fato e as dimensões consultáveis no Athena
- [x] Visões materializadas por município, UF e região no Postgres (`dashboard/schema.sql`)
- [ ] Gráficos no Metabase com contagem e proporção por categoria nos três níveis
- [x] A Gold provisória `ativas_por_uf` do ticket 02 sai de cena: SQL, job no `jobs/local.py`, tabela e visão no `dashboard/schema.sql` e testes removidos (a contagem de ativas passa a vir da `fato_empresa_mensal`)

## Andamento (03/11/2026)

**Feito e conferido localmente:**
- SQL: `jobs/sql/bronze/{empresas,simples}.sql` (razão social descartada; `capital_social` em DECIMAL; datas do Simples em DATE), `jobs/sql/silver/{empresas,simples}.sql` (porte vazio vira `00`; `mei_ativo`), `jobs/sql/gold/{fato_empresa_mensal,dim_categoria,dim_cnae,dim_natureza_juridica,dim_tempo}.sql`.
- Jobs visuais em `glue/jobs/`: `bronze_empresas`, `bronze_simples`, `silver_{estabelecimentos,empresas,simples}`, `gold_dimensoes` e `gold_fato_empresa_mensal`. Silver e Gold usam o novo Custom Transform `FiltrarMes` (`jobs/custom/filtrar_mes.py`).
- `qtd_estabelecimentos` conta os estabelecimentos ativos (situação 02) da empresa, matriz e filiais.
- Testes: `tests/test_fato_empresa_mensal.py` (MEI ativo, MEI excluído com porte 01, ME, EPP, Demais, porte vazio, matriz baixada, município da matriz, reprocessamento, dimensões), `tests/test_carga_dashboard.py` (visões e idempotência da carga).
- `ativas_por_uf` removida (SQL, job local, tabela e visão; o `schema.sql` apaga as antigas).
- Dashboard: `mv_categorias_municipio`, `mv_categorias_uf` e `mv_categorias_regiao` com `qtd_empresas` e `proporcao`.

**Amostra local (`make pipeline` + `make dashboard-load`, 2026-09 e 2026-10):** total de ativas igual ao do ticket 02 (145.721 e 145.932) e 53 municípios, todos casados com o IBGE.

| UF | 2026-09: MEI / ME / EPP / Demais | 2026-10: MEI / ME / EPP / Demais |
|---|---|---|
| AC | 21.460 (42,8%) / 19.474 / 2.856 / 6.349 | 21.806 (42,9%) / 19.721 / 2.904 / 6.411 |
| AP | 18.748 (39,8%) / 18.455 / 4.541 / 5.329 | 19.115 (39,9%) / 18.747 / 4.628 / 5.415 |
| RR | 24.509 (50,5%) / 16.211 / 3.225 / 4.564 | 23.310 (49,4%) / 16.066 / 3.219 / 4.590 |

**Falta:**
1. Na AWS: `make deploy-jobs`, rodar Bronze → Silver → Gold na amostra e registrar a fato e as dimensões no Athena (ou esperar o crawler do ticket 14).
2. Metabase: gráficos de contagem e proporção nas três visões (é preciso entrar no Metabase com o seu usuário).

## Na AWS (04/11/2026, amostra)

Rodaram com sucesso: `bronze_empresas`, `bronze_simples`, `bronze_dominios`, `silver_{estabelecimentos,empresas,simples}` (2026-09 e 2026-10), `gold_dimensoes` e `gold_fato_empresa_mensal` (os dois meses). As tabelas foram registradas à mão no Athena (`CREATE EXTERNAL TABLE ... TBLPROPERTIES ('table_type'='DELTA')`) até os crawlers do ticket 14 existirem.

| Conferência no Athena | Resultado |
|---|---|
| Bronze × raw (Empresas, Simples) | iguais nos dois meses (455.563 / 457.904 e 296.481 / 298.700) |
| Ativas na Silver | 145.721 e 145.932, iguais ao ticket 02 |
| `fato_empresa_mensal` 2026-09 por categoria | MEI 64.717, ME 54.140, EPP 10.622, Demais 16.242: iguais à amostra local |

Falta: `dim_municipio` na AWS (depende do `terraform apply`, ticket 07) e os gráficos no Metabase.
