# Evidência do ticket 14: catálogo da Silver/Gold e evolução de esquema

## Crawlers (AWS, 05/11/2026)

| Crawler | Banco | Tabelas | Resultado da 1ª execução |
|---|---|---|---|
| `goodlion-silver` | `goodlion_silver` | `estabelecimentos`, `empresas`, `simples`, `empresa_consolidada` | 4 atualizadas, 0 criadas, 19 s |
| `goodlion-gold` | `goodlion_gold` | `dim_municipio`, `dim_categoria`, `dim_cnae`, `dim_natureza_juridica`, `dim_tempo`, `fato_empresa_mensal`, `fato_movimentacao_empresa` | 7 atualizadas, 0 criadas, 22 s |

As tabelas tinham sido registradas à mão no Athena durante os tickets 08 e 12; os crawlers as assumiram no lugar, sem duplicatas. Todas respondem no Athena.

## Teste controlado de evolução de esquema (`goodlion_gold.dim_categoria`)

1. `gold_dimensoes` publicado temporariamente com uma coluna a mais na `dim_categoria` (`concat('Categoria ', nome) AS descricao`); o `GravarDelta` regrava a dimensão com `overwriteSchema`.
2. Crawler `goodlion-gold`.
3. `gold_dimensoes` republicado com o SQL do repositório, rodado de novo, e crawler de novo.

`aws glue get-table-versions --database-name goodlion_gold --table-name dim_categoria`:

| Versão | Atualizada em (UTC) | Colunas |
|---|---|---|
| 1 | 2026-11-04 21:39 | `id_categoria`, `nome`, `ordem` (registro manual no Athena) |
| 2 | 2026-11-04 23:28 | `id_categoria`, `nome`, `ordem` (1ª execução do crawler) |
| **3** | 2026-11-04 23:33 | `id_categoria`, `nome`, `ordem`, **`descricao`** |
| 4 | 2026-11-04 23:37 | `id_categoria`, `nome`, `ordem` (revertido) |

Entre as versões 3 e 4, `SELECT * FROM goodlion_gold.dim_categoria` no Athena trouxe a coluna `descricao` (`Categoria MEI`, …); depois da reversão, só as 3 colunas.

**Custo:** 4 execuções de crawler (~US$ 0,07 cada, mínimo de 10 min cobrado) e 2 do `gold_dimensoes` (~US$ 0,03 cada).
