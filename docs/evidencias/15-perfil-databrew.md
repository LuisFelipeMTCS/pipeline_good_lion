# Evidência do ticket 15: perfilamento DataBrew da silver_estabelecimentos

Job `goodlion-perfil-silver-estabelecimentos` (AWS, 05/11/2026): **SUCCEEDED em 146 s**, 2 nós (mínimo do DataBrew), amostra de 20.000 linhas. Custo: 2 nós × 146 s × US$ 0,48/nó-hora ≈ **US$ 0,04**. Resultado em `s3://goodlion-artifacts-724793286570/databrew/perfil/` (JSON de 87 KB, também visível no console do DataBrew, aba "Data profile overview"). Agenda própria: `goodlion-perfil-mensal`, dia 25 às 12h UTC.

**1ª execução falhou:** o dataset apontava para a raiz da tabela e o DataBrew tentou ler o `_delta_log/*.json` como Parquet. O dataset passou a ler só as pastas de partição (`ano_mes={ano_mes}/`, com `ano_mes` virando coluna).

## Destaques do perfil

| Coluna | Ausentes | Distintos | Mais comuns |
|---|---:|---:|---|
| `situacao_cadastral` | 0 | 5 | 08 (10.691), 02 (5.111), 04 (4.129), 03 (53) |
| `empresa_ativa` | 0 | 2 | falso 15.320, verdadeiro 4.680 |
| `sigla_uf` | 0 | 3 | AC 7.077, AP 6.683, RR 6.240 |
| `email` | 11.366 | 15 | `*****` (8.619): mascarado na Bronze; o resto são sobras não pessoais (`www.saude.com.br`, `000`) |
| `nome_fantasia` | 9.257 | 10.446 | nomes de comércio |

Linhas duplicadas na amostra: 0.

**Limitações:** a amostra de 20 mil linhas veio inteira de 2026-10 (o DataBrew pega as primeiras linhas). E o DataBrew não lê tabela Delta: até o `VACUUM` (7 dias), a pasta pode ter arquivos de versões antigas; o perfil vale para distribuições e nulos, não para contar linhas.
