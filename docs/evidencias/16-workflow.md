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
