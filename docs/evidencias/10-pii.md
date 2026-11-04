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

Pendente: execução na AWS (ver o ticket).
