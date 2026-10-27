# 02: Tracer local: empresas ativas por UF no Metabase

**O que construir:** o caminho completo mais fino possível, rodando só no Docker: Estabelecimentos da amostra atravessam bronze → silver → gold e aparecem num gráfico do Metabase com a quantidade de empresas ativas por UF. O objetivo é provar o esqueleto local de ponta a ponta (Spark lendo e gravando Delta no MinIO, carga idempotente no Postgres, Metabase lendo uma visão materializada) antes de qualquer regra de negócio complexa.

**Bloqueado por:** 01

**Status:** ready-for-agent

- [ ] Bronze de Estabelecimentos em Delta, tipada, particionada por `ano_mes`, com sobrescrita por `replaceWhere`
- [ ] Silver de Estabelecimentos com a regra de empresa ativa (`situacao_cadastral = 02` na matriz)
- [ ] Gold mínima com a contagem de empresas ativas por UF e `ano_mes`
- [ ] As consultas SQL de cada camada ficam guardadas para reaproveitar nos nós SQL Query do Glue Studio
- [ ] `make dashboard-load ANO_MES=2026-09` lê a Gold com `deltalake`, apaga e reinsere o mês no Postgres e atualiza a visão materializada
- [ ] Rodar a carga duas vezes dá o mesmo resultado (idempotência)
- [ ] Gráfico "empresas ativas por UF" no Metabase mostra AC, AP e RR
- [ ] Testes com pytest cobrindo a regra de empresa ativa
