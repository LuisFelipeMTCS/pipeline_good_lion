# Evidência do ticket 16: Workflow ponta a ponta (amostra, AWS)

`aws glue start-workflow-run --name goodlion --run-properties ano_mes=2026-10,ingestao=nao` (o `make workflow`).

## 1ª execução: falha real e retomada (04–05/11/2026)

| Execução | O que aconteceu |
|---|---|
| `wr_ff6fb8ba…` | `definir_mes` → ingestões (`ingest_receita` pulada por `ingestao=nao`; `ingest_ibge` pelo plano B, a API não responde da AWS) → crawler do raw → 4 Bronzes + `trigger_databrew` → 3 Silvers → consolidada + `dim_municipio` + dimensões → `gold_fato_empresa_mensal` OK, **`gold_fato_movimentacao_empresa` FAILED nas 2 tentativas**. O Workflow parou ali: manutenção e crawlers da Silver/Gold não rodaram. 16 de 20 ações com sucesso, 1 falha |
| `wr_4cea530a…` (retomada) | `aws glue resume-workflow-run --node-ids <nó da fato de movimentação>` depois da correção publicada: só a fato de movimentação, a `manutencao` e os 2 crawlers rodaram. **COMPLETED, 20 de 20 ações** |

**A falha:** a fato de movimentação procurou a consolidada no bucket da Gold. O `getResolvedOptions` do Glue aceita abreviação, e o `--bucket` do job (Gold) era lido como `--bucket_silver` conforme a ordem dos argumentos; nas execuções manuais a ordem calhava de funcionar. O argumento virou `--origem_silver`. A 2ª tentativa automática já pegou o script novo, mas com os argumentos da execução original, e falhou de novo; por isso a retomada.

**Alerta:** a falha final da `gold_fato_movimentacao_empresa` (as duas tentativas) passou pela regra `goodlion-falha-glue` do EventBridge → SNS → e-mail.

**Gatilho inicial:** o Glue aceita um gatilho inicial só, e com o agendado desligado o `start-workflow-run` não disparava nada (a execução terminava com 0 ações). O `goodlion-mensal` (dia 20, 9h UTC) fica ligado; depois da entrega, `aws glue stop-trigger --name goodlion-mensal`.

## Contagens da Gold depois da 1ª execução

| Tabela | Contagem |
|---|---|
| `fato_empresa_mensal` 2026-10 | MEI 64.231, ME 54.534, EPP 10.751, Demais 16.416 |
| `fato_empresa_mensal` 2026-09 | MEI 64.717, ME 54.140, EPP 10.622, Demais 16.242 |
| `fato_movimentacao_empresa` 2026-10 | abertura 2.308, baixa 1.016, mudança de porte 67, entrada no MEI 1, saída do MEI 895 |
| `dim_municipio` | 53 |
| `silver.empresa_consolidada` | 452.546 |

## 2ª execução de 2026-10: idempotência (05/11/2026)

`wr_cba0a256…` parou logo na `ingest_receita` (uma execução por vez, e a ingestão completa de 2026-10 do ticket 17 estava rodando: o Workflow parou, como deve). Retomada automática quando a ingestão terminou: `wr_ff58fdf1…`, **COMPLETED, 20 de 20 ações**.

Antes desta execução o Bookmark da Bronze de Estabelecimentos foi zerado, para regravar os dois meses com o telefone mascarado (ticket 10). Mesmo com a Bronze regravada, **as contagens da Gold ficaram idênticas** às da 1ª execução (tabela acima: fato por categoria nos dois meses, eventos de 2026-10, `dim_municipio`, consolidada).

Telefone na Bronze depois da execução: 0 valores com dígitos; 388.456 (2026-09) e 390.900 (2026-10) mascarados, DDD mantido.

## Provas do ticket

| Critério | Onde |
|---|---|
| Execução completa na amostra | `wr_4cea530a…` (retomada) e `wr_ff58fdf1…` |
| Retomada a partir do passo que falhou | `resume-workflow-run` em `wr_ff6fb8ba…` (falha real) e em `wr_cba0a256…` |
| Idempotência | 2ª execução de 2026-10: Gold idêntica |
| Falha bloqueante para o Workflow e manda o e-mail | DQ do ticket 11 (`docs/evidencias/11-data-quality.md`) + a falha da fato de movimentação, que parou o Workflow e passou pela regra do EventBridge |

