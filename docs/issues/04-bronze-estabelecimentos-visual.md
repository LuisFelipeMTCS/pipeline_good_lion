# 04: Primeiro job visual: Bronze de Estabelecimentos com Bookmarks

**O que construir:** o primeiro job no editor visual do Glue Studio, levando Estabelecimentos do `raw` para a Bronze em Delta, com Job Bookmarks e parâmetros. Este ticket estabelece o padrão que todos os outros jobs visuais vão seguir (parâmetros, Flex, exportação em JSON e recriação por script) e responde cedo ao risco de o editor visual não aceitar parâmetros em todos os nós.

O grafo é `Source S3 → SQL Query → Target Delta`. O SQL do nó é o `jobs/sql/bronze/estabelecimentos.sql` já testado localmente no ticket 02: ele é injetado pelo script de deploy, nunca copiado e colado no editor. Pastas, nomes e padrões: [ARQUITETURA](../ARQUITETURA.md).

**Bloqueado por:** 02, 03

**Status:** ready-for-agent

- [ ] Job criado no editor visual: Glue 5.0, G.1X, classe Flex, 2 workers, pré-visualização de dados desligada
- [ ] Recebe `--ano_mes`, `--bucket` e `--ambiente` (`sample`/`full`)
- [ ] Grava Delta em `bronze/sample/estabelecimentos/` particionado por `ano_mes`, com sobrescrita por `replaceWhere`
- [ ] Job Bookmarks ligado: uma segunda execução sem arquivos novos não reprocessa nada
- [ ] Registrado no ARQUITETURA.md quais nós aceitam parâmetro e onde foi preciso Custom Transform (vira referência para os próximos jobs)
- [ ] `scripts/exportar_job.py` exporta o job (`get-job`) para `glue/jobs/bronze_estabelecimentos.json`, trocando o SQL por um marcador
- [ ] `scripts/deploy_jobs.py` injeta `jobs/sql/bronze/estabelecimentos.sql` no marcador e roda `create-job`/`update-job`; o job recriado continua abrindo no editor visual
- [ ] Contagem da Bronze no Athena bate com o `raw` da amostra (print em `docs/evidencias/`)
- [ ] 1 nova tentativa e timeout configurados no job
