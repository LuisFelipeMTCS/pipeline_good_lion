# 12: Pergunta 3: aberturas e fechamentos via CDC

**O que construir:** o dashboard mostra onde mais se abrem e fecham empresas e MEIs, a partir da mudança entre 2026-09 e 2026-10. A `silver_empresa_consolidada` guarda o estado atual (uma linha por `cnpj_basico`) e recebe um `MERGE` mensal com o Change Data Feed ligado. A `fato_movimentacao_empresa` lê as mudanças entre versões e classifica os eventos.

Pastas, nomes e padrões: [ARQUITETURA](../ARQUITETURA.md).

**Bloqueado por:** 08

**Status:** done

- [x] `silver_empresa_consolidada` com Change Data Feed ligado
- [x] `MERGE` mensal no Custom Transform `jobs/custom/merge_consolidada.py`: insere novos, atualiza alterados e remove os que deixaram de existir (`whenNotMatchedBySource`)
- [x] `fato_movimentacao_empresa` (`jobs/sql/gold/fato_movimentacao_empresa.sql`) com os 5 tipos de evento: abertura, baixa, mudança de porte, entrada no MEI e saída do MEI
- [x] Testes locais com pytest (via `jobs/local.py`) para a classificação de cada tipo de evento
- [x] Rodar o `MERGE` do mesmo mês duas vezes não gera eventos duplicados
- [x] Na amostra, 2026-09 seguido de 2026-10 produz eventos plausíveis (conferir alguns CNPJs à mão)
- [x] Visões (`dashboard/schema.sql`) e gráfico no Metabase com aberturas e fechamentos por município, UF e região

## Andamento (03/11/2026)

**Como funciona:**
- `jobs/sql/silver/empresa_consolidada.sql` monta o estado do mês, uma linha por `cnpj_basico`: situação e município da matriz, porte, MEI e categoria.
- `jobs/custom/merge_consolidada.py` aplica o `MERGE`, atualizando só as linhas em que alguma coluna mudou (sem isso, todo mês a base inteira viraria mudança no CDF). Cada commit leva o `ano_mes` no `userMetadata`. A primeira carga é uma gravação simples, sem eventos, e liga o Change Data Feed.
- `jobs/custom/ler_mudancas.py` lê o CDF das versões de `MERGE` do mês. Rodar o mês de novo cria uma versão sem mudanças, então nada se repete.
- `jobs/sql/gold/fato_movimentacao_empresa.sql` classifica os eventos: abertura (empresa nova e ativa), baixa (situação passou a 08), mudança de porte, entrada e saída do MEI. Uma empresa pode ter mais de um evento no mês (uma linha por tipo). Empresa removida pelo `MERGE` não é evento.
- Jobs visuais: `glue/jobs/silver_empresa_consolidada.json` e `glue/jobs/gold_fato_movimentacao_empresa.json`.
- Dashboard: `mv_movimentacao_municipio`, `mv_movimentacao_uf` e `mv_movimentacao_regiao` (eventos por tipo e categoria).
- Testes: `tests/test_movimentacao.py` (os 5 tipos, carga inicial sem eventos, empresa que some do arquivo, reprocessamento sem duplicar) e `tests/test_carga_dashboard.py`.

**Amostra local, 2026-10:**

| UF | Aberturas (MEI) | Baixas | Mudança de porte | Entrada no MEI | Saída do MEI |
|---|---:|---:|---:|---:|---:|
| AC | 728 (569) | 355 | 19 | 1 | 333 |
| AP | 797 (577) | 379 | 23 | 0 | 297 |
| RR | 783 (609) | 282 | 25 | 0 | 265 |

O MERGE de 2026-10 mexeu em 6.605 linhas da consolidada (2.390 inseridas, 4.142 atualizadas, 73 removidas).

**Conferência à mão no raw (setembro → outubro):**

| Evento | CNPJ básico | Setembro | Outubro |
|---|---|---|---|
| abertura | 01230302 | não existe | situação 02, porte 01 |
| baixa | 00858442 | situação 04 | situação 08 |
| entrada no MEI | 19362267 | MEI N (excluído em 2018) | MEI S, sem exclusão |
| mudança de porte | 03010697 | porte 03 | porte 05 |
| saída do MEI | 13358871 | MEI S | MEI N (excluído em 01/10/2026) e situação 08 (também conta como baixa) |

**Achado:** as ativas de RR caem 1.324 de setembro para outubro, mas aberturas menos baixas dá +501. A diferença é de inaptidão: 2.012 empresas foram de 02 para 04 (inapta) e 824 voltaram de 04 para 02. O PRD só define "baixa" (08), então inaptidão não vira evento. Se o dashboard precisar explicar a queda, dá para acrescentar o evento "inaptidão".

**Falta:** rodar na AWS (2026-09 e depois 2026-10, nessa ordem) e montar o gráfico de aberturas e fechamentos no Metabase.

## Na AWS (04/11/2026, amostra)

`silver_empresa_consolidada` em 2026-09 (carga inicial) e 2026-10 (`MERGE`) e `gold_fato_movimentacao_empresa` nos dois meses. Eventos de 2026-10 no Athena: 2.308 aberturas (1.755 de MEI), 1.016 baixas, 67 mudanças de porte, 1 entrada e 895 saídas do MEI. São exatamente as somas das três UFs na amostra local. **Idempotência na AWS:** repetir o `MERGE` e a fato de 2026-10 deu as mesmas contagens, um CNPJ por evento, sem duplicar.

Falta: o gráfico no Metabase.

## Metabase (05/11/2026)

Painel "Empresas no Brasil: categorias, capital social e movimentação" (coleção Good Lion, http://localhost:3001/dashboard/2), montado por `scripts/metabase.py` (pode rodar de novo; usa `METABASE_API_KEY` do `.env`). Cada pergunta mostra o mês mais recente carregado no Postgres. Hoje os dados são a amostra (AC, AP, RR); o Brasil inteiro chega com o ticket 17.
