# 11: Data Quality na Silver

**O que construir:** dados ruins param o pipeline. As regras de Glue Data Quality da seção 5.6 do PRD rodam na Silver: as bloqueantes fazem o job falhar e as de alerta só registram. Os resultados ficam gravados para servir de evidência.

**Bloqueado por:** 08

**Status:** ready-for-agent

- [ ] Bloqueante: `cnpj_basico` com 8 dígitos e sem nulos
- [ ] Bloqueante: `cnpj_basico` único por `ano_mes` na fato
- [ ] Bloqueante: `porte` ∈ {00, 01, 03, 05}
- [ ] Bloqueante: `capital_social` ≥ 0
- [ ] Alerta: variação de linhas do mês de no máximo ±5% em relação ao mês anterior
- [ ] Alerta: `data_inicio_atividade` não futura
- [ ] Alerta: percentual de e-mails nulos
- [ ] Regras criadas pelo Terraform
- [ ] Teste: injetar uma linha inválida na amostra faz o job falhar; remover a linha faz o job passar
- [ ] Resultados de DQ gravados no `artifacts`
