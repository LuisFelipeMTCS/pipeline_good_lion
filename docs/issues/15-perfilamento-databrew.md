# 15: Perfilamento DataBrew da silver_estabelecimentos

**O que construir:** um perfil de dados da `silver_estabelecimentos` gerado pelo DataBrew, numa agenda própria fora do Workflow (é informativo e não deve atrasar o pipeline).

**Bloqueado por:** 08

**Status:** done

- [x] Dataset e job de perfilamento do DataBrew criados pelo Terraform (`infra/databrew.tf`)
- [x] Agenda própria configurada
- [x] Perfil gerado sobre a amostra, com resultado gravado no `artifacts`
- [x] Custo da execução anotado

## Andamento (03/11/2026)

- Na pilha do CloudFormation de `infra/databrew.tf`: dataset `goodlion-silver-estabelecimentos` (Parquet da pasta `silver/sample/estabelecimentos/`), job `goodlion-perfil-silver-estabelecimentos` (1 nó, amostra de 20.000 linhas, resultado em `artifacts/databrew/perfil/`) e agenda `goodlion-perfil-mensal` (dia 25, às 12h UTC, depois do gatilho mensal do dia 20).
- **Por que o Parquet da pasta:** o DataBrew não lê tabela Delta do Catalog (resposta da AWS no re:Post). A pasta também guarda, até o `VACUUM` (7 dias), arquivos que já saíram do Delta. O perfil vale para distribuições, nulos e valores distintos; a contagem de linhas vem do Athena.

**Falta:** `terraform apply`, rodar o job uma vez (`aws databrew start-job-run --name goodlion-perfil-silver-estabelecimentos`), guardar o print do perfil e anotar o custo (US$ 0,48 por nó-hora, cobrado por minuto).

## Na AWS (05/11/2026)

Perfil gerado em 146 s (~US$ 0,04), resultado no `artifacts`: `docs/evidencias/15-perfil-databrew.md`. A 1ª execução falhou lendo o `_delta_log` como Parquet; o dataset agora lê só as pastas de partição.
