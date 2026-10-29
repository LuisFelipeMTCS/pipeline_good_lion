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

**Status:** ready-for-agent

- [ ] Jobs visuais da Bronze de Empresas e Simples, seguindo o padrão do ticket 04 (Bookmarks, parâmetros, JSON em `glue/jobs/` com o SQL de `jobs/sql/bronze/` injetado pelo deploy)
- [ ] Jobs visuais da Silver de Empresas, Estabelecimentos e Simples, limitados por `--ano_mes`, com SQL em `jobs/sql/silver/` (a de Estabelecimentos já existe desde o ticket 02)
- [ ] `dim_categoria` (4 linhas), `dim_cnae`, `dim_natureza_juridica` e `dim_tempo` na Gold, com SQL em `jobs/sql/gold/`
- [ ] `fato_empresa_mensal` com grão 1 empresa ativa × `ano_mes`, `cnpj_basico` como dimensão degenerada, medidas `capital_social` e `qtd_estabelecimentos`
- [ ] Testes locais com pytest (via `jobs/local.py`) para a regra de categoria (incluindo MEI com data de exclusão e MEI com porte 01)
- [ ] Reprocessar o mesmo `ano_mes` dá o mesmo resultado
- [ ] Crawler ou registro manual deixa a fato e as dimensões consultáveis no Athena
- [ ] Visões materializadas por município, UF e região no Postgres (`dashboard/schema.sql`)
- [ ] Gráficos no Metabase com contagem e proporção por categoria nos três níveis
- [ ] A Gold provisória `ativas_por_uf` do ticket 02 sai de cena: SQL, job no `jobs/local.py`, tabela e visão no `dashboard/schema.sql` e testes removidos (a contagem de ativas passa a vir da `fato_empresa_mensal`)
