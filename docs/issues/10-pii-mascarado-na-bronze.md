# 10: PII mascarado na Bronze

**O que construir:** nenhum dado pessoal sai do `raw`. O nó Detect Sensitive Data, na passagem de `raw` para a Bronze, mascara e-mail, telefone/fax e CPF (incluindo o CPF embutido na razão social de MEI). Colunas que não servem à análise (endereço completo e razão social) são descartadas. A detecção roda só sobre as colunas de texto candidatas, para limitar custo.

O descarte é regra de negócio e fica no SQL da Bronze (`jobs/sql/bronze/`), testado localmente. O Detect Sensitive Data não roda no container do Glue: ele é testado direto na AWS, sobre a amostra. Pastas, nomes e padrões: [ARQUITETURA](../ARQUITETURA.md).

**Bloqueado por:** 04

**Status:** ready-for-agent

- [ ] Nó Detect Sensitive Data nos jobs Bronze que têm colunas de texto candidatas, restrito a essas colunas, e versionado no JSON do job em `glue/jobs/`
- [ ] E-mail, telefone/fax e CPF mascarados
- [ ] Logradouro, número, complemento, bairro, CEP e razão social descartados no SQL da Bronze (`jobs/sql/bronze/`), com teste local com pytest
- [ ] Consulta de verificação no Athena: nenhum padrão de CPF ou e-mail encontrado em nenhuma tabela Bronze da amostra (print em `docs/evidencias/`)
- [ ] Tempo e custo do nó medidos na amostra, com estimativa para a base completa
- [ ] Se a Bronze de Empresas e Simples (ticket 08) já existir, ela também recebe o nó
