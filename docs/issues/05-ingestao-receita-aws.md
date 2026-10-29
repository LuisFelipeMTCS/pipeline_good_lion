# 05: Ingestão da Receita rodando na AWS

**O que construir:** a mesma `ingest_receita` do ticket 01, agora como job Python shell na AWS, baixando um mês completo do WebDAV da Receita direto para o `raw` no S3. O objetivo é testar cedo o risco de o download a partir da AWS ser lento e saber quanto tempo a rodada final vai levar.

**Custo esperado:** ~US$ 0,03/h do Python shell, mais o armazenamento do `raw` (alguns GB, apagados automaticamente em 30 dias).

**Bloqueado por:** 03

**Status:** done

- [x] Job Python shell criado pelo Terraform, com o `ingest/receita.py` enviado para o `artifacts`
- [x] Baixa um mês completo (sem Sócios) e grava em `raw/<tabela>/ano_mes=AAAA-MM/` em UTF-8 e com cabeçalho
- [x] Os arquivos grandes (`Empresas0`, `Estabelecimentos0`) são processados em fluxo, sem estourar a memória do job
- [x] Tempo total do download e custo da execução anotados
- [x] Rodar de novo o mesmo mês sobrescreve sem duplicar arquivos
- [x] 1 nova tentativa e timeout configurados

## Resultado (29/10/2026)

**Como rodar:** `terraform apply` em `infra/` publica o `ingest/receita.py` no `artifacts` e cria o job `ingest_receita` (`infra/ingestao.tf`). Cada execução recebe `--ano_mes AAAA-MM`; `--tabelas cnaes,motivos` refaz só o que falhou.

**Execução de 2026-09:** `SUCCEEDED` na 1ª tentativa, **7.306 s (2h02)**, 27 arquivos e **25,8 GB** em `raw/<tabela>/ano_mes=2026-09/`. O gargalo é o servidor da Receita: um único arquivo de ~7 GB levou uns 40 min. O timeout de 240 min dá folga de 2x; a rodada final (ticket 17) precisa reservar ~2 h por mês baixado.

**Memória:** o job tem 1 GB (0,0625 DPU) e os arquivos de vários GB passaram, porque cada ZIP vai para um arquivo temporário (um de cada vez) e o CSV de dentro é descompactado e convertido para UTF-8 em blocos direto para o `upload_fileobj`, sem nunca ficar inteiro na memória.

**Idempotência:** `--tabelas cnaes` de novo (16 s): a mesma chave `cnaes/ano_mes=2026-09/Cnaes.csv`, mesmo ETag, `LastModified` novo, e o total continua em 27 arquivos. Antes de gravar, o job apaga o prefixo do mês da tabela.

**Custo:** 0,0625 DPU × 2,03 h × US$ 0,44 ≈ **US$ 0,06** de Python shell. O armazenamento pesa mais que o previsto ("alguns GB"): 25,8 GB × US$ 0,023 ≈ **US$ 0,59** se ficar o mês inteiro; a expiração de 30 dias do `raw` apaga em 28/11/2026, depois da entrega.
