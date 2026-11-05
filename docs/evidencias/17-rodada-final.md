# Evidência do ticket 17: rodada final na base completa (05/11/2026)

Brasil inteiro, 2026-09 e 2026-10, pelo Glue Workflow `goodlion`, com os jobs publicados por `uv run python scripts/deploy_jobs.py --ambiente full` (caminhos na raiz dos buckets, tabelas `full_<tabela>` no Catalog, até 10 workers G.1X Flex, `--enable-metrics` e `--enable-observability-metrics` ligados).

## Ingestão

| Mês | Job | Tempo | Arquivos |
|---|---|---|---|
| 2026-09 | `ingest_receita` (ticket 05) | 2h02 | 27 (25,8 GB de CSV) |
| 2026-10 | `ingest_receita` (05/11) | 2h02 (7.304 s) | 27 |

## Execuções do Workflow

| Execução | Mês | Resultado |
|---|---|---|
| `wr_d5b53aba…` | 2026-09 | Bronzes (as dos dois meses: o Bookmark leu todos os arquivos novos), Silvers, consolidada (carga inicial), `dim_municipio`, dimensões, fato de movimentação OK. **`gold_fato_empresa_mensal` barrada pelo DQ** (`IsUnique "cnpj_basico"` = 0,99999985) nas 2 tentativas; Workflow parado ali |
| `wr_cdce03f5…` (retomada da `silver_empresas`) | 2026-09 | Silver de Empresas deduplicada; **fato barrada de novo** (0,99999993) |
| `wr_e7665903…` (retomada da consolidada) | 2026-09 | Uma matriz por empresa: **COMPLETED, 20 de 20** |
| `wr_ba5b05a2…` | 2026-10 | **COMPLETED, 20 de 20, de primeira** |
| `wr_6884c836…` | 2026-10 (repetição, Bookmark da Bronze zerado) | **COMPLETED, 20 de 20**: Bronze completa regravada (3.015 s) com a regra nova do CPF |

**O que o DQ pegou:** o CNPJ básico `08314885` aparece **duas vezes no arquivo de Empresas** da Receita (uma linha com porte 05, outra sem porte) e tem **duas matrizes ativas** no de Estabelecimentos (ordem 0039 e 0047, municípios diferentes de SP), nos dois meses. A amostra AC/AP/RR não tinha o caso. Correções: a Silver de Empresas fica com uma linha por CNPJ (a com porte) e ganhou a regra `IsUnique`; a fato e a consolidada ficam com uma matriz por empresa (a ativa mais antiga); reprocessar o mês da carga inicial reconstrói a consolidada.

**Regras de DQ:** com essas correções, todas as regras bloqueantes passaram nos dois meses (Silver de Empresas, Simples e Estabelecimentos; fato; `dim_municipio` com 100% dos 5.571 municípios casados com o IBGE). Os alertas de variação de linhas (±5% sobre o mês anterior) dispararam na 1ª execução completa, como esperado, e o job seguiu (é alerta, não bloqueia): na `silver_empresas`, `RowCount <= avg(last(1)) * 1.05` falhou com 70.085.592 linhas contra o histórico da amostra (~458 mil). Nas execuções seguintes, com o histórico já da base completa, passou.

## Números da Gold (Athena, `goodlion_gold.full_*`)

| | 2026-09 | 2026-10 |
|---|---:|---:|
| Empresas ativas (`fato_empresa_mensal`) | 26.937.243 | 27.049.048 |
| MEI | 13.396.674 | 13.419.767 |
| ME | 8.937.535 | 8.991.034 |
| EPP | 1.448.303 | 1.463.838 |
| Demais | 3.154.731 | 3.174.409 |

Eventos de 2026-10 (`fato_movimentacao_empresa`, Change Data Feed da consolidada de 70.517.437 empresas): **417.791 aberturas** (315.025 de MEI), **222.107 baixas**, 188.277 saídas do MEI, 9.156 mudanças de porte, 46 entradas no MEI. Saldo: +195.684.

Capital social declarado: os MEIs somam R$ 571,7 bilhões em 2026-09, por causa de cadastros com valores na casa dos bilhões; é por isso que o dashboard usa a mediana.

## PII na base completa (Bronze, ~73 milhões de estabelecimentos por mês)

0 e-mails, 0 telefones/fax com dígitos; 51,5 milhões de e-mails mascarados; a Bronze completa nem tem as colunas de endereço. Na 1ª passada sobraram 6 CPFs por mês **com pontuação colados ao texto** (`NOME123.456.789-01`); a regra do SQL passou a cobrir esse formato e a Bronze foi regravada na repetição. **Depois: 0 e-mails, 0 CPFs, 0 telefones** nos 73.366.147 (2026-09) e 73.809.379 (2026-10) estabelecimentos. A Silver de 2026-09 foi refeita à mão com a Bronze nova (`silver_estabelecimentos --ano_mes 2026-09`, 933 s); conferida no Athena em `goodlion_silver.full_estabelecimentos`:

| Mês | Linhas | E-mails | CPFs | Matrizes ativas |
|---|---:|---:|---:|---:|
| 2026-09 | 73.366.147 | 0 | 0 | 26.937.244 |
| 2026-10 | 73.809.379 | 0 | 0 | 27.049.049 |

A Silver tem uma matriz ativa a mais que a fato: a segunda matriz do CNPJ `08314885`, que a fato descarta de propósito (uma matriz por empresa).

## Dashboard

`make dashboard-load-aws ANO_MES=<mês> AMBIENTE=full` (papel `analista`, só leitura da Gold): 3 min e 1,1 GB de memória por mês (leitura em lotes). Metabase atualizado com `scripts/metabase.py`: "A categoria mais comum é MEI: 49,6% das empresas ativas"; "No mês, abriram 417.394 empresas e 222.047 foram baixadas: saldo de +195.347" (o painel exclui os eventos de empresas no exterior, que não têm município).

## Idempotência

Antes e depois da repetição de 2026-10 (com a Bronze completa regravada no meio): **Gold idêntica**. Mesmas contagens da `fato_empresa_mensal` por mês e categoria, **mesmas somas de capital social até o centavo** (ex.: Demais 2026-10 = R$ 18.164.952.674.834,61), mesmos eventos de 2026-10, mesmos 5.571 municípios e 70.517.437 empresas na consolidada.

## Custo

| Fonte | Valor |
|---|---|
| Jobs Spark da rodada completa (DPU-s × US$ 0,29/DPU-h do Flex) | 220.052 DPU-s ≈ **US$ 17,70** |
| Maiores parcelas | manutenção compactando tudo (~US$ 2,60, já corrigido para só o mês), Bronze de Estabelecimentos com PII (~US$ 2,40 por passada, 2 passadas), 4 tentativas da fato barradas pelo DQ (~US$ 0,80) |
| Uso registrado no Billing até 05/11 (atrasa ~1 dia) | US$ 3,91 |
| Créditos | cobrem todo o uso: custo líquido US$ 0 |

**Acima da meta de US$ 10 do PRD** (em valor bruto). O que faria caber: OPTIMIZE só no mês (já feito), trocar o Detect Sensitive Data pela regra do SQL na base completa (a regra sozinha já zerou e-mail e CPF) e uma passada só da Bronze completa.
