# 13: Arquivos pequenos: OPTIMIZE/VACUUM com evidência

**O que construir:** um job de manutenção que compacta arquivos pequenos (`OPTIMIZE`) e limpa versões antigas (`VACUUM`, 7 dias) nas tabelas Delta, com uma medição de antes e depois que vira evidência para o relatório.

**Bloqueado por:** 08

**Status:** in-progress (job e medição local prontos; falta a medição no Athena)

- [x] Job de manutenção com o Custom Transform `jobs/custom/manutencao.py`, rodando `OPTIMIZE` e `VACUUM` nas tabelas Bronze, Silver e Gold
- [x] Medição "antes" na amostra sem tratamento: quantidade de arquivos por partição e tamanho médio
- [ ] Consulta de referência no Athena com volume lido e tempo registrados antes e depois
- [x] Medição "depois" com os mesmos indicadores
- [x] Tabela comparativa antes/depois salva em `docs/evidencias/`
- [x] Após o `VACUUM`, a tabela continua íntegra e consultável

## Andamento (03/11/2026)

- `jobs/custom/manutencao.py` (job `glue/jobs/manutencao.json`): descobre as tabelas Delta de cada bucket do `--buckets` pela pasta `_delta_log` e roda `OPTIMIZE` e `VACUUM ... RETAIN 168 HOURS`. Para cada tabela imprime os arquivos antes e depois. O que não é Delta (a saída Parquet do DataBrew) fica de fora.
- No executor local: `docker compose exec glue python3 -m jobs.local --ano_mes 2026-10 --jobs manutencao`. Teste: `tests/test_manutencao.py`.
- Medição local de antes e depois em `docs/evidencias/13-arquivos-pequenos.md`: a Bronze de Estabelecimentos foi de 20 arquivos por partição (1,3 MB em média) para 1 (25 MB), e a fato de 20 para 1.

**Falta na AWS:** rodar a consulta de referência no Athena antes e depois do job `manutencao` e anotar volume lido e tempo.

