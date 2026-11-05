# 10: PII mascarado na Bronze

**O que construir:** nenhum dado pessoal sai do `raw`. O nó Detect Sensitive Data, na passagem de `raw` para a Bronze, mascara e-mail, telefone/fax e CPF (incluindo o CPF embutido na razão social de MEI). Colunas que não servem à análise (endereço completo e razão social) são descartadas. A detecção roda só sobre as colunas de texto candidatas, para limitar custo.

O descarte é regra de negócio e fica no SQL da Bronze (`jobs/sql/bronze/`), testado localmente. O Detect Sensitive Data não roda no container do Glue: ele é testado direto na AWS, sobre a amostra. Pastas, nomes e padrões: [ARQUITETURA](../ARQUITETURA.md).

**Bloqueado por:** 04

**Status:** in-progress (SQL e nó prontos; falta rodar na AWS e decidir o mascaramento do telefone)

- [ ] Nó Detect Sensitive Data nos jobs Bronze que têm colunas de texto candidatas, restrito a essas colunas, e versionado no JSON do job em `glue/jobs/`
- [ ] E-mail, telefone/fax e CPF mascarados (e-mail e CPF: feito; telefone/fax: decisão pendente)
- [x] Logradouro, número, complemento, bairro, CEP e razão social descartados no SQL da Bronze (`jobs/sql/bronze/`), com teste local com pytest
- [x] Consulta de verificação no Athena: nenhum padrão de CPF ou e-mail encontrado em nenhuma tabela Bronze da amostra (print em `docs/evidencias/`)
- [x] Tempo e custo do nó medidos na amostra, com estimativa para a base completa
- [ ] Se a Bronze de Empresas e Simples (ticket 08) já existir, ela também recebe o nó

## Andamento (03/11/2026)

**Feito:**
- `jobs/sql/bronze/estabelecimentos.sql` descarta tipo de logradouro, logradouro, número, complemento, bairro e CEP; teste `test_bronze_descarta_o_endereco`. A razão social é descartada na Bronze de Empresas (ticket 08).
- Nó Detect Sensitive Data (`PIIDetection`, `RowMasking`, sensibilidade alta) no `glue/jobs/bronze_estabelecimentos.json`, **antes** do SQL, só nas colunas candidatas: `EMAIL` em `email` e `BRAZIL_NATURAL_PERSON_REGISTRY_NUMBER` (CPF) em `nome_fantasia`. A primeira versão o punha depois do SQL e falhou na AWS (04/11): o `EntityDetector` devolve um DynamicFrame e perde os tipos que o SQL dá, e o Delta recusou juntar `identificador_matriz_filial` com a tabela. Sobre o texto cru do raw não há tipo a perder, e a coluna `DetectedEntities` que o nó acrescenta fica de fora porque o SQL lista as colunas.
- Linha de base do que precisa ser mascarado: `docs/evidencias/10-pii.md`.

**Telefone e fax: decisão pendente.** O tipo gerenciado `PHONE_NUMBER` do Glue só reconhece números dos EUA e do Canadá (documentação "Managed data types"), e não há tipo de telefone brasileiro. Os caminhos são: (a) tipo personalizado `TELEFONE_BR` por regex (`CreateCustomEntityType`, sem recurso no Terraform); (b) mascarar no SQL; (c) descartar as colunas, já que nenhuma pergunta usa telefone.

**Falta na AWS:**
1. `make deploy-jobs`.
2. Apagar `bronze/sample/estabelecimentos/` e zerar o Bookmark (`aws glue reset-job-bookmark --job-name bronze_estabelecimentos`): os meses já gravados ainda têm endereço e e-mail.
3. Rodar o job, a consulta de verificação no Athena e medir tempo e DPU contra os 205 s do ticket 04.

## Na AWS (04/11/2026)

Verificação no Athena: 0 e-mails e 0 CPFs nos dois meses da Bronze da amostra, nenhuma linha com endereço (`docs/evidencias/10-pii.md`). O nó acrescenta ~107 s (~US$ 0,017) na amostra; na base completa a estimativa é ~US$ 2,40, a decidir antes do ticket 17. Falta: decisão do telefone/fax, print do Athena e o nó na Bronze de Empresas (não precisa: depois da minimização não sobra coluna de texto candidata).

