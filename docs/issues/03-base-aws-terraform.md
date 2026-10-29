# 03: Base AWS em Terraform e amostra catalogada

**O que construir:** a fundação na AWS, toda em Terraform, e a amostra já consultável no Athena. Ao final dá para rodar uma consulta SQL no Athena sobre o `raw` da amostra, provando que buckets, permissões, Catalog e crawler funcionam juntos.

Pastas, nomes e padrões: [ARQUITETURA](../ARQUITETURA.md).

**Bloqueado por:** 01

**Status:** done

- [x] Terraform em `infra/`, um arquivo por assunto: `versions.tf`, `variables.tf`, `terraform.tfvars.example`, `s3.tf`, `iam.tf`, `catalog.tf`, `crawlers.tf`, `monitoring.tf` (só o tópico SNS por enquanto), `budget.tf`
- [x] Buckets `goodlion-<camada>-<id da conta>` (`raw`, `bronze`, `silver`, `gold` e `artifacts`) em us-east-1, com SSE-S3 e bloqueio de acesso público
- [x] Exclusão automática em 30 dias **somente** no `raw` (nunca nos buckets Delta)
- [x] Perfil `glue-pipeline` com leitura e escrita só nos buckets e prefixos necessários; perfil `analista` só com leitura no `gold`
- [x] Bancos do Data Catalog `goodlion_<camada>`
- [x] AWS Budgets com alertas em US$ 5 e US$ 8 (o Budgets avisa, não bloqueia gastos) e tópico SNS com assinatura de e-mail confirmada
- [x] Amostra enviada para o prefixo `sample/` do `raw` (`raw/sample/<tabela>/ano_mes=AAAA-MM/`)
- [x] Crawler do `raw` com `MergeNewColumns`, partições herdando o esquema da tabela e `DeleteBehavior = LOG`
- [x] Consulta no Athena sobre o `raw` da amostra retorna as mesmas contagens anotadas no ticket 01
- [x] O ambiente (`sample`/`full`) **não** é variável do Terraform: é parâmetro dos jobs, e a infraestrutura é uma só
- [x] Estado do Terraform local e fora do Git (`terraform.tfvars` também, por ter o e-mail)

## Resultado (28/10/2026)

**Conta:** 724793286570, us-east-1. `terraform apply` criou 27 recursos. O estado fica em `infra/terraform.tfstate` (fora do Git).

**Como rodar:** `cd infra && terraform apply`, depois `make amostra-aws` e o crawler `goodlion-raw` (console ou `aws glue start-crawler --name goodlion-raw`).

**Crawler do `raw`:** 9 tabelas em `goodlion_raw`, uma por pasta de `sample/` (nível 3 do agrupamento; sem isso os domínios, que têm o mesmo esquema, virariam uma tabela só), todas com `OpenCSVSerde` (sem aspas nos valores) e partição `ano_mes`.

**Athena (workgroup `goodlion`):** as 18 contagens por tabela e mês batem exatamente com o ticket 01. Estabelecimentos de 2026-09 por UF: AC 167.930, AP 161.673, RR 144.520. As duas consultas de conferência leram 427 MB (~US$ 0,002).

**Notas:**
- SSE-S3 não tem recurso no Terraform: a AWS já aplica em todo bucket novo (conferido: `AES256`).
- O Budgets é trimestral (Q4), porque o projeto atravessa outubro e novembro.
- O crawler cataloga só `sample/`; a base completa é lida direto do S3 pelos jobs.
