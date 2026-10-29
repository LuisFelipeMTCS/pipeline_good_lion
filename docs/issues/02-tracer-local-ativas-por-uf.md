# 02: Tracer local: empresas ativas por UF no Metabase

**O que construir:** o caminho completo mais fino possível, rodando só no Docker: Estabelecimentos da amostra atravessam bronze → silver → gold e aparecem num gráfico do Metabase com a quantidade de empresas ativas por UF. O objetivo é provar o esqueleto local de ponta a ponta (Spark lendo e gravando Delta no MinIO, carga idempotente no Postgres, Metabase lendo uma visão materializada) antes de qualquer regra de negócio complexa.

**Bloqueado por:** 01

**Status:** in-progress (falta o gráfico no Metabase)

- [x] Bronze de Estabelecimentos em Delta, tipada, particionada por `ano_mes`, com sobrescrita por `replaceWhere`
- [x] Silver de Estabelecimentos com a regra de empresa ativa (`situacao_cadastral = 02` na matriz)
- [x] Gold mínima com a contagem de empresas ativas por UF e `ano_mes`
- [x] As consultas SQL de cada camada ficam em `jobs/sql/<camada>/<tabela>.sql`, as mesmas que o `deploy_jobs.py` vai injetar nos nós SQL Query (ticket 04)
- [x] `make dashboard-load ANO_MES=2026-09` lê a Gold com `deltalake`, apaga e reinsere o mês no Postgres e atualiza a visão materializada
- [x] Rodar a carga duas vezes dá o mesmo resultado (idempotência)
- [ ] Gráfico "empresas ativas por UF" no Metabase mostra AC, AP e RR
- [x] Testes com pytest cobrindo a regra de empresa ativa

## Resultado (28/10/2026)

**Como rodar:** `make pipeline ANO_MES=2026-09` (roda os três jobs do `jobs/local.py` no container do Glue, ~18 s na amostra) e depois `make dashboard-load ANO_MES=2026-09`.

**Onde está cada coisa:**
- SQL de cada camada: `jobs/sql/bronze/estabelecimentos.sql`, `jobs/sql/silver/estabelecimentos.sql`, `jobs/sql/gold/ativas_por_uf.sql`. O alias do nó de entrada no Glue Studio é o nome da view (`raw_estabelecimentos`, `bronze_estabelecimentos`, `silver_estabelecimentos`)
- Executor local: `jobs/local.py`, uma função por job (`bronze_estabelecimentos`, `silver_estabelecimentos`, `gold_ativas_por_uf`), gravando Delta com `replaceWhere ano_mes = X`; Spark com Delta e MinIO: `jobs/spark.py`
- Carga: `dashboard/carga.py` (DELETE + COPY do mês numa transação, depois `REFRESH MATERIALIZED VIEW`); esquema em `dashboard/schema.sql`

**Decisões:**
- A Silver mantém todos os estabelecimentos e acrescenta `empresa_ativa` (matriz com `situacao_cadastral = '02'`), em vez de filtrar: o ticket 08 reaproveita a Silver inteira.
- Bronze tipada: datas `AAAAMMDD` viram `DATE` (`00000000` e vazio viram nulo), `identificador_matriz_filial` vira `INT`, códigos continuam texto (zeros à esquerda). PII e descarte de endereço ficam no ticket 10.

**Empresas ativas por UF (`mv_ativas_por_uf`)**, batendo com as matrizes ativas do ticket 01:

| UF | 2026-09 | 2026-10 |
|---|---:|---:|
| AC | 50.139 | 50.842 |
| AP | 47.073 | 47.905 |
| RR | 48.509 | 47.185 |
| **Total** | **145.721** | **145.932** |

**Testes:** `make test-spark` (6, Spark no container: regra de ativa, tipagem, `replaceWhere`) e `make test` (3 da carga no Postgres, num banco temporário por teste).
