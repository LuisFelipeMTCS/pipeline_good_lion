# 05: Ingestão da Receita rodando na AWS

**O que construir:** a mesma `ingest_receita` do ticket 01, agora como job Python shell na AWS, baixando um mês completo do WebDAV da Receita direto para o `raw` no S3. O objetivo é testar cedo o risco de o download a partir da AWS ser lento e saber quanto tempo a rodada final vai levar.

**Custo esperado:** ~US$ 0,03/h do Python shell, mais o armazenamento do `raw` (alguns GB, apagados automaticamente em 30 dias).

**Bloqueado por:** 03

**Status:** ready-for-agent

- [ ] Job Python shell criado pelo Terraform, com o `ingest/receita.py` enviado para o `artifacts`
- [ ] Baixa um mês completo (sem Sócios) e grava em `raw/<tabela>/ano_mes=AAAA-MM/` em UTF-8 e com cabeçalho
- [ ] Os arquivos grandes (`Empresas0`, `Estabelecimentos0`) são processados em fluxo, sem estourar a memória do job
- [ ] Tempo total do download e custo da execução anotados
- [ ] Rodar de novo o mesmo mês sobrescreve sem duplicar arquivos
- [ ] 1 nova tentativa e timeout configurados
