# 03: Base AWS em Terraform e amostra catalogada

**O que construir:** a fundação na AWS, toda em Terraform, e a amostra já consultável no Athena. Ao final dá para rodar uma consulta SQL no Athena sobre o `raw` da amostra, provando que buckets, permissões, Catalog e crawler funcionam juntos.

Pastas, nomes e padrões: [ARQUITETURA](../ARQUITETURA.md).

**Bloqueado por:** 01

**Status:** in-progress (código pronto e validado; falta o `apply`)

- [x] Terraform em `infra/`, um arquivo por assunto: `versions.tf`, `variables.tf`, `terraform.tfvars.example`, `s3.tf`, `iam.tf`, `catalog.tf`, `crawlers.tf`, `monitoring.tf` (só o tópico SNS por enquanto), `budget.tf`
- [ ] Buckets `goodlion-<camada>-<id da conta>` (`raw`, `bronze`, `silver`, `gold` e `artifacts`) em us-east-1, com SSE-S3 e bloqueio de acesso público
- [ ] Exclusão automática em 30 dias **somente** no `raw` (nunca nos buckets Delta)
- [ ] Perfil `glue-pipeline` com leitura e escrita só nos buckets e prefixos necessários; perfil `analista` só com leitura no `gold`
- [ ] Bancos do Data Catalog `goodlion_<camada>`
- [ ] AWS Budgets com alertas em US$ 5 e US$ 8 (o Budgets avisa, não bloqueia gastos) e tópico SNS com assinatura de e-mail confirmada
- [ ] Amostra enviada para o prefixo `sample/` do `raw` (`raw/sample/<tabela>/ano_mes=AAAA-MM/`)
- [ ] Crawler do `raw` com `MergeNewColumns`, partições herdando o esquema da tabela e `DeleteBehavior = LOG`
- [ ] Consulta no Athena sobre o `raw` da amostra retorna as mesmas contagens anotadas no ticket 01
- [x] O ambiente (`sample`/`full`) **não** é variável do Terraform: é parâmetro dos jobs, e a infraestrutura é uma só
- [x] Estado do Terraform local e fora do Git (`terraform.tfvars` também, por ter o e-mail)
