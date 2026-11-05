# 07: Municípios Receita × IBGE → dim_municipio

**O que construir:** a dimensão de municípios com UF e região, casando o código de município da Receita (que não é o do IBGE) com a API de localidades do IBGE. O JSON do IBGE é ingerido, limpo por uma receita do DataBrew (achatar, maiúsculas, sem acento) e casado com o domínio de municípios da Receita, com uma tabela manual de correções para os nomes que divergem. Uma regra bloqueante garante que 100% dos municípios casaram.

Pastas, nomes e padrões: [ARQUITETURA](../ARQUITETURA.md).

**Bloqueado por:** 03, 04

**Status:** done

- [x] `ingest/ibge.py` grava o JSON da API em `raw/ibge_municipios/ano_mes=AAAA-MM/`
- [x] Receita de limpeza no DataBrew criada pelo Terraform (`infra/databrew.tf`)
- [x] Job Python shell `ingest/trigger_databrew.py` dispara a receita e espera terminar
- [x] Bronze dos domínios da Receita (CNAE, Naturezas, Motivos, Municípios, Qualificações, Países), com SQL em `jobs/sql/bronze/<dominio>.sql`
- [x] Tabela manual de correções versionada no repositório
- [x] `dim_municipio` na Gold (`jobs/sql/gold/dim_municipio.sql`) com `id_municipio_rf`, `id_municipio_ibge`, nome, UF e região
- [x] Teste local com pytest (via `jobs/local.py`) para o casamento Receita × IBGE, incluindo um nome corrigido pela tabela manual
- [x] Regra de Data Quality bloqueante em `jobs/quality/gold_dim_municipio.dqdl`: 100% dos municípios da Receita casados com o IBGE; o job falha se algum ficar sem par
- [x] Verificado na amostra e também contra a lista completa de municípios (o domínio da Receita é pequeno, dá para casar o Brasil inteiro já aqui)

## Andamento (03/11/2026)

**Feito e testado localmente:**
- `ingest/ibge.py` (job `ingest_ibge`) grava o JSON da API em `raw/ibge_municipios/ano_mes=AAAA-MM/municipios.json`; `make ingest-ibge` faz o mesmo no MinIO.
- `ingest/trigger_databrew.py` (job `trigger_databrew`) dispara o job de limpeza do DataBrew e falha se ele não terminar em `SUCCEEDED`.
- Bronze dos 6 domínios num job só (`glue/jobs/bronze_dominios.json`, um ramo por domínio, SQL em `jobs/sql/bronze/<dominio>.sql`). O `GravarDelta` e o `GarantirEsquema` passaram a tirar a tabela do nome do nó anterior (ARQUITETURA, "Padrão dos jobs visuais").
- `dim_municipio` (`jobs/sql/gold/dim_municipio.sql`, job `gold_dim_municipio`): UF pelos estabelecimentos, casamento por nome normalizado + UF, 22 correções em `jobs/referencias/municipios_correcoes.csv`, DQ bloqueante em `jobs/quality/gold_dim_municipio.dqdl`.
- Brasil inteiro: 5.571 de 5.571 casados (`docs/evidencias/07-dim-municipio.md`).

**Receita do DataBrew:** o provider `aws` não tem DataBrew e o `awscc` não tem receita, então dataset, receita e job estão numa pilha do CloudFormation (`infra/databrew.tf`). Os passos estão em `infra/databrew_receita_ibge.json`. Os nomes das colunas criadas pelo `UNNEST_STRUCT` (níveis separados por ponto) ainda não foram conferidos numa execução.

**Falta na AWS:**
1. `terraform apply` (cria os jobs `ingest_ibge` e `trigger_databrew`, a pilha do DataBrew e o perfil `databrew-pipeline`; envia as correções ao `artifacts`).
2. `make deploy-jobs` (cria `bronze_dominios` e `gold_dim_municipio`).
3. Rodar `ingest_ibge --ano_mes 2026-10`, `bronze_dominios`, `trigger_databrew` e `gold_dim_municipio`, e conferir a regra de DQ e a contagem no Athena.

## Na AWS (05/11/2026)

**O que precisou mudar na primeira execução:**
- **DataBrew no CloudFormation:** o job exige no mínimo 2 nós; e o CloudFormation cria a receita sem publicá-la, então um job com dataset + receita (que só aceita versão publicada) não sobe. O job aponta para um **projeto** (dataset + receita), que usa a receita como está. Projeto parado não cobra.
- **Nomes de coluna:** o `UNNEST_STRUCT` separa os níveis com `_` (`regiao-imediata_regiao-intermediaria_UF_sigla`), não com `.`.
- **Acentos:** o `REPLACE_TEXT` tratou `[ÁÀÂÃÄ]` como texto literal (só o `Ç`, sozinho, foi trocado). Agora é um passo por letra acentuada (13). Saída: 5.571 municípios, nenhum caractere fora do ASCII em `nome_normalizado`.
- **API do IBGE fora do alcance da AWS:** de dentro do Glue (us-east-1) a API dá timeout nas duas tentativas; daqui responde em 0,9 s. O raw foi alimentado rodando o mesmo `ingest/ibge.py` desta máquina para o S3. E o `ingest_ibge` ganhou um plano B: se a API não responder em 3 tentativas, copia o retrato mais recente do raw para o mês (a lista quase nunca muda; a cópia renova o arquivo antes da expiração de 30 dias). Sem retrato anterior, falha. Testes em `tests/test_ingestao_ibge.py`.

**Resultado:** `trigger_databrew` rodou a receita (a falha do DataBrew derrubou o job do Glue, como deve), `gold_dim_municipio` gravou os 53 municípios da amostra (AC 22, AP 16, RR 15), todos com código do IBGE; DQ com nota 1,0 (as 4 regras); nenhuma linha da `fato_empresa_mensal` sem município na dimensão.

