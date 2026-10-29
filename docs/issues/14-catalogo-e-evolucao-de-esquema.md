# 14: Catálogo da Silver/Gold e evolução de esquema

**O que construir:** um crawler único cataloga Silver e Gold (o destino Delta do Studio não atualiza o Catalog sozinho), e um teste controlado mostra o esquema evoluindo: adiciona-se uma coluna e o Catalog registra uma nova versão da tabela.

**Bloqueado por:** 08

**Status:** ready-for-agent

- [ ] Crawler único para Silver e Gold criado pelo Terraform (`infra/crawlers.tf`), gravando nos bancos `goodlion_silver` e `goodlion_gold`
- [ ] Todas as tabelas Silver e Gold aparecem no Catalog e respondem no Athena
- [ ] Teste controlado: adicionar uma coluna numa tabela, rodar o crawler e ver a nova versão no histórico do Catalog
- [ ] Evidência (histórico de versões) registrada em `docs/evidencias/`
- [ ] Teste controlado revertido depois de registrado
