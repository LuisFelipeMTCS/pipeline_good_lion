# 09: Pergunta 2: capital social por região

**O que construir:** o dashboard responde onde as empresas têm maior capital social, com mediana (medida principal, por causa dos valores extremos) e soma por município, UF e região. O nome no dashboard é sempre "capital social" e nunca "lucro" ou "faturamento", que não existem na base.

**Bloqueado por:** 08

**Status:** done

- [x] Visões materializadas com mediana e soma de `capital_social` por município, UF e região, com a mediana já calculada no Postgres (`dashboard/schema.sql`)
- [x] Gráficos no Metabase com mediana e soma nos três níveis
- [x] Texto explicativo no dashboard: capital social declarado na abertura, não é faturamento nem lucro
- [x] Conferência manual da mediana de uma UF da amostra contra uma consulta direta na Gold

## Andamento (03/11/2026)

**Visões** (`dashboard/schema.sql`, atualizadas pelo `make dashboard-load`): `mv_capital_municipio`, `mv_capital_uf` e `mv_capital_regiao`, com `qtd_empresas`, `mediana_capital_social` (`percentile_cont(0.5)`) e `soma_capital_social`. Teste: `test_capital_social_com_mediana_e_soma_por_uf_e_regiao` (um valor extremo muda a soma, não a mediana).

**Amostra local:**

| UF | 2026-09: mediana / soma | 2026-10: mediana / soma |
|---|---|---|
| AC | R$ 10.000,00 / R$ 12,53 bi | R$ 10.000,00 / R$ 12,59 bi |
| AP | R$ 10.500,00 / R$ 13,81 bi | R$ 12.000,00 / R$ 13,96 bi |
| RR | R$ 10.000,00 / R$ 13,35 bi | R$ 10.000,00 / R$ 13,62 bi |

**Conferência manual:** AC 2026-09 calculado direto na Gold (`deltalake` + `statistics.median`, sem o Postgres): 50.139 empresas, mediana R$ 10.000,00, soma R$ 12.526.886.661,39. Igual à visão. O maior capital do AC é R$ 3,0 bilhões, sozinho um quarto da soma do estado: é por isso que a mediana é a medida principal.

**Falta (Metabase, com o seu usuário):** gráficos de mediana e soma nos três níveis e o texto "Capital social declarado na abertura da empresa. Não é faturamento nem lucro, que a base não tem."

## Metabase (05/11/2026)

Painel "Empresas no Brasil: categorias, capital social e movimentação" (coleção Good Lion, http://localhost:3001/dashboard/2), montado por `scripts/metabase.py` (pode rodar de novo; usa `METABASE_API_KEY` do `.env`). Cada pergunta mostra o mês mais recente carregado no Postgres. Hoje os dados são a amostra (AC, AP, RR); o Brasil inteiro chega com o ticket 17.
