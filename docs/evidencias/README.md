# Evidências para o relatório

Um arquivo por ticket, com números medidos na AWS (conta 724793286570, us-east-1) e na amostra local. Os prints de console que o relatório precisar podem ser tirados a partir das consultas e dos comandos citados em cada arquivo.

| Item da rubrica | Evidência | Destaque |
|---|---|---|
| Alertas de falha por e-mail | [06-alerta-email.png](06-alerta-email.png), [ticket 06](../issues/06-alertas-e-observabilidade.md) | Falha real do Glue → EventBridge → SNS → e-mail em 1 minuto |
| Bronze com Job Bookmarks, jobs visuais | [04-bronze-estabelecimentos.md](04-bronze-estabelecimentos.md) | 2ª execução sem arquivos novos não regrava nada |
| Fonte JSON + DataBrew (limpeza) + dimensão | [07-dim-municipio.md](07-dim-municipio.md) | 5.571 de 5.571 municípios casados com o IBGE; 22 correções manuais |
| PII automatizado | [10-pii.md](10-pii.md) | 0 e-mails, 0 CPFs, 0 telefones na Bronze (amostra e base completa); o detector sozinho deixava escapar formatos malformados |
| Data Quality (bloqueante e alerta) | [11-data-quality.md](11-data-quality.md), [17-rodada-final.md](17-rodada-final.md) | A regra de unicidade barrou a base completa por um CNPJ duplicado no arquivo da Receita |
| Arquivos pequenos (OPTIMIZE/VACUUM) | [13-arquivos-pequenos.md](13-arquivos-pequenos.md) | Antes e depois por tabela; na base completa, OPTIMIZE só no mês |
| Catálogo e evolução de esquema | [14-catalogo-evolucao.md](14-catalogo-evolucao.md) | Versão 3 da `dim_categoria` com coluna nova, revertida na versão 4 |
| DataBrew (perfilamento) | [15-perfil-databrew.md](15-perfil-databrew.md) | Perfil em 146 s, ~US$ 0,04 |
| Workflow, retomada, idempotência, alertas | [16-workflow.md](16-workflow.md) | Falha real retomada do nó; Gold idêntica na repetição |
| Rodada final na base completa, custos, dashboard | [17-rodada-final.md](17-rodada-final.md) | 27 milhões de empresas ativas; 417.791 aberturas em 2026-10 |

**Fora do escopo por decisão (PRD, seção 11):** fontes JDBC.
