# 01: Ambiente local e amostra AC/AP/RR

**O que construir:** um ambiente local que sobe com um único comando e já tem dados reais da Receita para desenvolver. A ingestão da Receita roda localmente contra o MinIO e grava o `raw` exatamente como fará na AWS (UTF-8, com cabeçalho, particionado por `ano_mes`). A partir dos meses completos, gera-se a amostra de desenvolvimento: o recorte de AC, AP e RR com as empresas e os registros do Simples correspondentes. Os dois meses (2026-09 e 2026-10) entram na amostra, porque o CDC (ticket 12) precisa comparar um mês com o outro.

**Bloqueado por:** nada (pode começar já)

**Status:** ready-for-agent

- [ ] `docker compose` sobe glue-libs (Glue 5), MinIO, Postgres e Metabase sem erro
- [ ] `ingest_receita` lista o mês no WebDAV, baixa os ZIPs (sem Sócios), converte de latin1 para UTF-8, adiciona cabeçalho com os nomes do SDK da Base dos Dados e grava no `raw` do MinIO
- [ ] A ingestão recebe o mês e o destino (MinIO ou S3) como parâmetro; a virada para a AWS é só trocar parâmetro e credenciais
- [ ] A amostra de 2026-09 e 2026-10 foi gerada com DuckDB e está no MinIO
- [ ] Consistência da amostra verificada: toda empresa tem ao menos um estabelecimento e todo registro do Simples tem empresa correspondente
- [ ] Contagens por tabela e por mês da amostra anotadas (servem de referência para os testes seguintes)
