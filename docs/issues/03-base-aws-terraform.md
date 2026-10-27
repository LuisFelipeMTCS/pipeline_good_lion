# 03: Base AWS em Terraform e amostra catalogada

**O que construir:** a fundação na AWS, toda em Terraform, e a amostra já consultável no Athena. Ao final dá para rodar uma consulta SQL no Athena sobre o `raw` da amostra, provando que buckets, permissões, Catalog e crawler funcionam juntos.

**Bloqueado por:** 01

**Status:** ready-for-agent

- [ ] Buckets `raw`, `bronze`, `silver`, `gold` e `artifacts` em us-east-1, com SSE-S3 e bloqueio de acesso público
- [ ] Exclusão automática em 30 dias **somente** no `raw` (nunca nos buckets Delta)
- [ ] Perfil `glue-pipeline` com leitura e escrita só nos buckets e prefixos necessários; perfil `analista` só com leitura no `gold`
- [ ] Bancos do Data Catalog para cada camada
- [ ] AWS Budgets com alertas em US$ 5 e US$ 8 e tópico SNS com assinatura de e-mail confirmada
- [ ] Amostra enviada para o prefixo `sample/` do `raw`
- [ ] Crawler do `raw` com `MergeNewColumns`, partições herdando o esquema da tabela e `DeleteBehavior = LOG`
- [ ] Consulta no Athena sobre o `raw` da amostra retorna as mesmas contagens anotadas no ticket 01
- [ ] Estado do Terraform local e fora do Git
