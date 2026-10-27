# 10: PII mascarado na Bronze

**O que construir:** nenhum dado pessoal sai do `raw`. O nó Detect Sensitive Data, na passagem de `raw` para a Bronze, mascara e-mail, telefone/fax e CPF (incluindo o CPF embutido na razão social de MEI). Colunas que não servem à análise (endereço completo e razão social) são descartadas. A detecção roda só sobre as colunas de texto candidatas, para limitar custo.

**Bloqueado por:** 04

**Status:** ready-for-agent

- [ ] Nó Detect Sensitive Data nos jobs Bronze que têm colunas de texto candidatas, restrito a essas colunas
- [ ] E-mail, telefone/fax e CPF mascarados
- [ ] Logradouro, número, complemento, bairro, CEP e razão social descartados na Bronze
- [ ] Consulta de verificação no Athena: nenhum padrão de CPF ou e-mail encontrado em nenhuma tabela Bronze da amostra
- [ ] Tempo e custo do nó medidos na amostra, com estimativa para a base completa
- [ ] Se a Bronze de Empresas e Simples (ticket 08) já existir, ela também recebe o nó
