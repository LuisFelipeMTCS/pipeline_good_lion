# Evidência do ticket 10: PII mascarado na Bronze

## Linha de base: o que chega do raw (amostra 2026-09, DuckDB local, 03/11/2026)

| Tabela | Linhas | Com e-mail | CPF (11 dígitos) no nome | Com telefone 1 | Com fax |
|---|---:|---:|---:|---:|---:|
| estabelecimentos | 474.123 | 285.272 | 16 (`nome_fantasia`) | 388.456 | 55.909 |
| empresas | 455.563 | — | 108.568 (`razao_social`, MEI) | — | — |

O CPF na razão social de MEI não chega à Bronze porque a `razao_social` é descartada no SQL (minimização). No nome fantasia ele é mascarado pelo nó Detect Sensitive Data.

## Verificação no Athena (depois de regravar a Bronze)

```sql
-- Esperado: 0 em todas as colunas.
SELECT
  count_if(regexp_like(email, '[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}')) AS emails,
  count_if(regexp_like(nome_fantasia, '\d{3}\.?\d{3}\.?\d{3}-?\d{2}')) AS cpfs
FROM goodlion_bronze.estabelecimentos;
```

### Resultado na AWS (04/11/2026, amostra)

| ano_mes | Linhas | E-mails (padrão) | Com `@` | CPFs no nome | E-mails mascarados | Nomes mascarados | Com endereço |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09 | 474.123 | **0** | 0 | **0** | 284.850 | 131 | 0 |
| 2026-10 | 476.553 | **0** | 0 | **0** | 287.363 | 131 | 0 |

**Só o detector não bastou.** Na primeira execução, com só o Detect Sensitive Data, sobraram por mês ~50 e-mails malformados (ponto antes do `@`, `..`, vírgula, acento) e 2 CPFs colados ao texto do nome fantasia: o detector só reconhece formatos válidos. A rede de segurança no SQL da Bronze (e-mail que ainda tem `@` e 11+ dígitos seguidos no nome viram `*****`) zerou os dois.

**Endereço:** as colunas continuam no esquema da tabela Delta (o `replaceWhere` não remove colunas), mas estão vazias em todas as linhas da versão atual. Os arquivos das versões antigas, com endereço e e-mail, só saem do S3 com o `VACUUM` (7 dias).

## Tempo e custo do nó

| Execução do `bronze_estabelecimentos` (2 meses, 950.676 linhas, Flex G.1X × 2) | Tempo | DPU-s | Custo (US$ 0,29/DPU-h) |
|---|---:|---:|---:|
| Sem o nó (ticket 04) | 205 s | 410 | US$ 0,033 |
| Com o nó (04/11) | 312 s | 625 | US$ 0,050 |
| **Diferença (o nó)** | **~107 s** | **~215** | **~US$ 0,017** |

**Estimativa para a base completa:** Estabelecimentos tem ~66 milhões de linhas por mês, ~139 vezes a amostra nos dois meses. Se o custo do nó crescer em proporção às linhas, são ~30.000 DPU-s, ou seja, ~8,3 DPU-h ≈ **US$ 2,40** só para o detector nos dois meses. É uma parte grande do orçamento de US$ 10. Antes do ticket 17, vale medir num arquivo da base completa ou trocar o detector pela regra do SQL (que já cobre e-mail e CPF sozinha).
