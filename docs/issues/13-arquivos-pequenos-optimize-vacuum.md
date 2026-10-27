# 13: Arquivos pequenos: OPTIMIZE/VACUUM com evidência

**O que construir:** um job de manutenção que compacta arquivos pequenos (`OPTIMIZE`) e limpa versões antigas (`VACUUM`, 7 dias) nas tabelas Delta, com uma medição de antes e depois que vira evidência para o relatório.

**Bloqueado por:** 08

**Status:** ready-for-agent

- [ ] Job de manutenção (Custom Transform) rodando `OPTIMIZE` e `VACUUM` nas tabelas Bronze, Silver e Gold
- [ ] Medição "antes" na amostra sem tratamento: quantidade de arquivos por partição e tamanho médio
- [ ] Consulta de referência no Athena com volume lido e tempo registrados antes e depois
- [ ] Medição "depois" com os mesmos indicadores
- [ ] Tabela comparativa antes/depois salva no repositório
- [ ] Após o `VACUUM`, a tabela continua íntegra e consultável
