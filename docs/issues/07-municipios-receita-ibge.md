# 07: Municípios Receita × IBGE → dim_municipio

**O que construir:** a dimensão de municípios com UF e região, casando o código de município da Receita (que não é o do IBGE) com a API de localidades do IBGE. O JSON do IBGE é ingerido, limpo por uma receita do DataBrew (achatar, maiúsculas, sem acento) e casado com o domínio de municípios da Receita, com uma tabela manual de correções para os nomes que divergem. Uma regra bloqueante garante que 100% dos municípios casaram.

**Bloqueado por:** 03, 04

**Status:** ready-for-agent

- [ ] `ingest_ibge` grava o JSON da API no `raw` por `ano_mes`
- [ ] Receita de limpeza no DataBrew criada pelo Terraform
- [ ] Job Python shell `trigger_databrew` dispara a receita e espera terminar
- [ ] Bronze dos domínios da Receita (CNAE, Naturezas, Motivos, Municípios, Qualificações, Países)
- [ ] Tabela manual de correções versionada no repositório
- [ ] `dim_municipio` na Gold com `id_municipio_rf`, `id_municipio_ibge`, nome, UF e região
- [ ] Regra de Data Quality bloqueante: 100% dos municípios da Receita casados com o IBGE; o job falha se algum ficar sem par
- [ ] Verificado na amostra e também contra a lista completa de municípios (o domínio da Receita é pequeno, dá para casar o Brasil inteiro já aqui)
