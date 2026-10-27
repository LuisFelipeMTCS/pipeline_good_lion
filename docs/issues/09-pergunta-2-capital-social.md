# 09: Pergunta 2: capital social por região

**O que construir:** o dashboard responde onde as empresas têm maior capital social, com mediana (medida principal, por causa dos valores extremos) e soma por município, UF e região. O nome no dashboard é sempre "capital social" e nunca "lucro" ou "faturamento", que não existem na base.

**Bloqueado por:** 08

**Status:** ready-for-agent

- [ ] Visões materializadas com mediana e soma de `capital_social` por município, UF e região, com a mediana já calculada no Postgres
- [ ] Gráficos no Metabase com mediana e soma nos três níveis
- [ ] Texto explicativo no dashboard: capital social declarado na abertura, não é faturamento nem lucro
- [ ] Conferência manual da mediana de uma UF da amostra contra uma consulta direta na Gold
