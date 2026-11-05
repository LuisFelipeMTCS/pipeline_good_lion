# 14: Catálogo da Silver/Gold e evolução de esquema

**O que construir:** um crawler único cataloga Silver e Gold (o destino Delta do Studio não atualiza o Catalog sozinho), e um teste controlado mostra o esquema evoluindo: adiciona-se uma coluna e o Catalog registra uma nova versão da tabela.

**Bloqueado por:** 08

**Status:** done

- [x] Crawler único para Silver e Gold criado pelo Terraform (`infra/crawlers.tf`), gravando nos bancos `goodlion_silver` e `goodlion_gold`
- [x] Todas as tabelas Silver e Gold aparecem no Catalog e respondem no Athena
- [x] Teste controlado: adicionar uma coluna numa tabela, rodar o crawler e ver a nova versão no histórico do Catalog
- [x] Evidência (histórico de versões) registrada em `docs/evidencias/`
- [x] Teste controlado revertido depois de registrado

## Andamento (03/11/2026)

**Um crawler por camada, não um só:** um crawler grava num banco só, e o alvo Delta (`DeltaTarget`) não tem banco próprio. Com um crawler único, a Silver iria parar no `goodlion_gold` (ou o contrário). Em `infra/crawlers.tf` ficaram `goodlion-silver` e `goodlion-gold`: tabelas Delta nativas (o Athena lê sem manifest), `UPDATE_IN_DATABASE` e remoções só no log. Custo: cada execução de crawler cobra no mínimo 10 min (~US$ 0,07), então são ~US$ 0,07 a mais por execução do Workflow. **Decisão para você:** manter os dois, ou um crawler só gravando tudo no `goodlion_gold`.

**Falta na AWS:**
1. `terraform apply` e rodar os dois crawlers depois da Silver e da Gold da amostra; conferir as tabelas no Athena.
2. Teste de evolução de esquema: acrescentar uma coluna numa tabela pequena (ex.: `ALTER TABLE delta.\`s3://goodlion-gold-<conta>/sample/dim_categoria\` ADD COLUMNS (descricao string)` num job ou no Athena), rodar o `goodlion-gold`, ver a versão nova em `aws glue get-table-versions --database-name goodlion_gold --table-name dim_categoria` e registrar em `docs/evidencias/`.
3. Reverter: regravar a `dim_categoria` com o `gold_dimensoes` (o `overwriteSchema` tira a coluna) e rodar o crawler de novo.

## Na AWS (05/11/2026)

Crawlers rodando e tabelas no Athena; versão nova da `dim_categoria` com a coluna `descricao` e reversão: `docs/evidencias/14-catalogo-evolucao.md`. Ficaram dois crawlers (um por camada); a decisão de juntar num só continua em aberto.
