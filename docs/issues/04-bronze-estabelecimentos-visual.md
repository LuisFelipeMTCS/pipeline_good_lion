# 04: Primeiro job visual: Bronze de Estabelecimentos com Bookmarks

**O que construir:** o primeiro job no editor visual do Glue Studio, levando Estabelecimentos do `raw` para a Bronze em Delta, com Job Bookmarks e parâmetros. Este ticket estabelece o padrão que todos os outros jobs visuais vão seguir (parâmetros, Flex, exportação em JSON e recriação por script) e responde cedo ao risco de o editor visual não aceitar parâmetros em todos os nós.

**Bloqueado por:** 03

**Status:** ready-for-agent

- [ ] Job criado no editor visual: Glue 5.0, G.1X, classe Flex, 2 workers, pré-visualização de dados desligada
- [ ] Recebe `--ano_mes`, `--bucket` e `--ambiente` (`sample`/`full`)
- [ ] Grava Delta na Bronze particionado por `ano_mes`, com sobrescrita por `replaceWhere`
- [ ] Job Bookmarks ligado: uma segunda execução sem arquivos novos não reprocessa nada
- [ ] Registrado quais nós aceitam parâmetro e onde foi preciso Custom Transform (vira referência para os próximos jobs)
- [ ] Job exportado com o grafo visual em JSON e versionado; um script o recria (criar ou atualizar) e ele continua abrindo no editor visual
- [ ] Contagem da Bronze no Athena bate com o `raw` da amostra
- [ ] 1 nova tentativa e timeout configurados no job
