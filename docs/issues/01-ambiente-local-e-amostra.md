# 01: Ambiente local e amostra AC/AP/RR

**O que construir:** um ambiente local que sobe com um único comando e já tem dados reais da Receita para desenvolver. A ingestão da Receita roda localmente contra o MinIO e grava o `raw` exatamente como fará na AWS (UTF-8, com cabeçalho, particionado por `ano_mes`). A partir dos meses completos, gera-se a amostra de desenvolvimento: o recorte de AC, AP e RR com as empresas e os registros do Simples correspondentes. Os dois meses (2026-09 e 2026-10) entram na amostra, porque o CDC (ticket 12) precisa comparar um mês com o outro.

**Bloqueado por:** nada (pode começar já)

**Status:** done

- [x] `docker compose` sobe glue-libs (Glue 5), MinIO, Postgres e Metabase sem erro
- [x] `ingest_receita` lista o mês no WebDAV, baixa os ZIPs (sem Sócios), converte de latin1 para UTF-8, adiciona cabeçalho com os nomes do SDK da Base dos Dados e grava no `raw` do MinIO
- [x] A ingestão recebe o mês e o destino (MinIO ou S3) como parâmetro; a virada para a AWS é só trocar parâmetro e credenciais
- [x] A amostra de 2026-09 e 2026-10 foi gerada com DuckDB e está no MinIO
- [x] Consistência da amostra verificada: toda empresa tem ao menos um estabelecimento e todo registro do Simples tem empresa correspondente
- [x] Contagens por tabela e por mês da amostra anotadas (servem de referência para os testes seguintes)

## Resultado (26/10/2026)

**Ingestão local do `raw` completo:** 27 arquivos por mês (sem Sócios), ~25,8 GB de CSV em 2026-09. Levou ~65 min por mês a ~1,7 MB/s (limite do servidor da Receita por conexão).

**Amostra AC/AP/RR** em `raw/sample/`, gerada em ~47 s por mês, com pico de 3,4 GB de RAM (DuckDB limitado a 3 GB).

| Tabela | 2026-09 | 2026-10 |
|---|---:|---:|
| estabelecimentos | 474.123 | 476.553 |
| empresas | 455.563 | 457.904 |
| simples | 296.481 | 298.700 |
| cnaes | 1.359 | 1.359 |
| motivos | 63 | 63 |
| municipios | 5.572 | 5.572 |
| naturezas | 91 | 92 |
| paises | 255 | 255 |
| qualificacoes | 68 | 68 |

**Consistência (os dois meses):**
- UFs presentes nos estabelecimentos: só AC, AP e RR
- Empresas sem estabelecimento: 0
- Registros do Simples sem empresa: 0
- Estabelecimentos sem empresa: 0
- Estabelecimentos com as 30 colunas do layout (sem coluna `ano_mes` extra)

**Referências para os próximos tickets:** matrizes ativas (`identificador_matriz_filial = 1` e `situacao_cadastral = 02`): 145.721 em 2026-09 e 145.932 em 2026-10. Registros com `opcao_mei = 'S'`: 94.706 e 95.489.

**Notas:**
- A imagem oficial do MinIO saiu do Docker Hub; usamos o fork `pgsty/minio`.
- O Metabase ficou em `localhost:3001` (a 3000 costuma estar ocupada).
- O recorte é por UF do estabelecimento (literal do PRD): uma empresa com matriz fora de AC/AP/RR e filial dentro entra sem a matriz e fica fora da fato (que usa a matriz).
