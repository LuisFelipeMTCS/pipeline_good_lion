# 04: Primeiro job visual: Bronze de Estabelecimentos com Bookmarks

**O que construir:** o primeiro job no editor visual do Glue Studio, levando Estabelecimentos do `raw` para a Bronze em Delta, com Job Bookmarks e parâmetros. Este ticket estabelece o padrão que todos os outros jobs visuais vão seguir (parâmetros, Flex, exportação em JSON e recriação por script) e responde cedo ao risco de o editor visual não aceitar parâmetros em todos os nós.

O grafo é `Source S3 → SQL Query → Target Delta`. O SQL do nó é o `jobs/sql/bronze/estabelecimentos.sql` já testado localmente no ticket 02: ele é injetado pelo script de deploy, nunca copiado e colado no editor. Pastas, nomes e padrões: [ARQUITETURA](../ARQUITETURA.md).

**Bloqueado por:** 02, 03

**Status:** done

- [x] Job visual (grafo em `CodeGenConfigurationNodes`): Glue 5.0, G.1X, classe Flex, 2 workers. A pré-visualização de dados é uma sessão do editor, não propriedade do job: basta não ligá-la
- [x] Recebe `--bucket` e `--ambiente` (`sample`/`full`). O `--ano_mes` não se aplica à Bronze: quem limita a leitura é o Bookmark (PRD, 5.4)
- [x] Grava Delta em `bronze/sample/estabelecimentos/` particionado por `ano_mes`, com sobrescrita por `replaceWhere`
- [x] Job Bookmarks ligado: uma segunda execução sem arquivos novos não reprocessa nada
- [x] Registrado no ARQUITETURA.md quais nós aceitam parâmetro e onde foi preciso Custom Transform (vira referência para os próximos jobs)
- [x] `scripts/exportar_job.py` exporta o job (`get-job`) para `glue/jobs/bronze_estabelecimentos.json`, trocando o SQL por um marcador
- [x] `scripts/deploy_jobs.py` injeta `jobs/sql/bronze/estabelecimentos.sql` no marcador e roda `create-job`/`update-job`; o job recriado continua abrindo no editor visual
- [x] Contagem da Bronze no Athena bate com o `raw` da amostra (`docs/evidencias/04-bronze-estabelecimentos.md`)
- [x] 1 nova tentativa e timeout (30 min) configurados no job

## Resultado (28/10/2026)

**Como rodar:** `make deploy-jobs` publica (ou atualiza) o job a partir de `glue/jobs/bronze_estabelecimentos.json`; depois de editar no Glue Studio, `uv run python scripts/exportar_job.py bronze_estabelecimentos` traz a edição de volta.

**Grafo:** `Catalog (goodlion_raw.estabelecimentos) → GarantirEsquema → SelectFromCollection → SQL (jobs/sql/bronze/estabelecimentos.sql) → GravarDelta`. Os detalhes e o porquê de cada nó estão em "Padrão dos jobs visuais" no ARQUITETURA.md.

**Execuções:** a 1ª gravou os dois meses em 205 s; a 2ª, sem arquivos novos, terminou em 90 s sem criar versão Delta nova. Contagens, tipos e matrizes ativas no Athena em `docs/evidencias/04-bronze-estabelecimentos.md`.

**Problemas encontrados no caminho:**
- O crawler deduzia `bigint` para `cnpj_basico`, datas e códigos (zeros à esquerda perdidos), mesmo com `CustomDatatypes = STRING` no classificador. Agora o Terraform cria as tabelas do raw, tudo texto, e o crawler só acrescenta partições e colunas novas (o ticket 03 foi corrigido junto).
- O campo `Code` do Custom Transform é o corpo da função (o Glue o embrulha); a primeira versão ficou aninhada e não gravaria nada.
- Com Bookmark e nenhum arquivo novo, a origem vem sem colunas e o SQL falhava: daí o `GarantirEsquema`.

**Custo:** ~1.180 DPU-s de jobs Flex (incluindo as rodadas de ajuste) ≈ US$ 0,10, mais 4 execuções do crawler e consultas no Athena (centavos).

