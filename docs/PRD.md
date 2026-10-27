# PRD — Pipeline Good Lion: Data Lake de CNPJ no AWS Glue

| | |
|---|---|
| **Disciplina** | Infnet — projeto de pipeline de dados distribuído com AWS Glue |
| **Entrega** | 09/11/2026, 23:59 (Moodle) |
| **Status** | Decisões fechadas em 21/10/2026, implementação não iniciada |
| **Orçamento AWS** | Até US$ 10 (sem créditos do plano gratuito) |

---

## 1. Contexto e problema

O enunciado pede um pipeline distribuído no ecossistema AWS Glue (Glue Studio, Data Catalog, Crawlers, Workflows) que leve dados brutos do S3 até informações estruturadas, governadas e eficientes. As camadas são Bronze, Silver e Gold, com modelagem dimensional, qualidade de dados e proteção de dados pessoais (PII).

O corpus é a base pública de **CNPJ da Receita Federal** (`br_me_cnpj`), que tem dezenas de milhões de registros, atributos temporais e dados pessoais reais.

## 2. Objetivos

### 2.1 Perguntas de negócio (dashboard)

1. **Em quais regiões há mais MEI, ME, EPP e Demais?** Em contagem e em proporção, por município, UF e região.
2. **Onde as empresas têm maior capital social?** Mediana e soma por município, UF e região.
3. **Onde mais se abrem e se fecham empresas e MEIs?** Movimentação mensal vinda do CDC.

> A base CNPJ **não contém faturamento nem lucro**. A métrica financeira é o `capital_social` declarado na abertura, chamado assim no dashboard, nunca de "lucro". Usamos a **mediana** como medida principal, porque há valores extremos (R$ 1 em muitos MEIs e erros na casa dos bilhões).

### 2.2 Objetivos técnicos (rubrica)

| Item da rubrica | Como será atendido | Seção |
|---|---|---|
| Ingestão e transformação visual no Glue Studio | Jobs Bronze, Silver e Gold no editor visual; *Custom Transform* só para `MERGE` e manutenção | 5.3 |
| Camadas no S3 | `raw` → `bronze` → `silver` → `gold` (+ `artifacts`) | 5.1 |
| Job Bookmarks ou execução limitada | Bookmarks de `raw` para Bronze; demais etapas limitadas por `--ano_mes` | 5.4 |
| Arquivos pequenos e formato de Data Lake | Delta Lake (Parquet + Snappy) com `OPTIMIZE`/`VACUUM` e medição de antes e depois | 5.8 |
| Partições com foco em custo | Partição única por `ano_mes`; nada de partição por UF | 5.1 |
| Tarefas parametrizadas | `--ano_mes`, `--bucket`, `--ambiente` (`sample`/`full`) em todos os jobs | 5.4 |
| Integridade e metadados | Glue Data Quality (regras bloqueantes) + Data Catalog via crawlers | 5.6, 5.9 |
| Modelagem dimensional | Esquema estrela com 2 fatos e 5 dimensões | 6 |
| Idempotência, falhas e novas tentativas | `replaceWhere`/`MERGE`, retry 1×, retomada do Workflow | 5.5, 7 |
| Workflow nativo do Glue | Glue Workflow com gatilho mensal e sob demanda | 7 |
| **Fontes JDBC** | **Não atendido (decisão consciente)**, ver seção 11 | — |
| Monitoramento de saúde operacional | EventBridge + SNS (e-mail), CloudWatch Logs e dashboard | 7.3 |
| CDC | Delta **Change Data Feed** sobre a `silver_empresa_consolidada` | 5.5 |
| Implantação automatizada | Terraform + jobs visuais versionados como JSON | 8 |
| PII automatizado | Nó **Detect Sensitive Data** na entrada da Bronze | 5.7 |
| DataBrew (limpeza e perfilamento) | Receita de limpeza do IBGE + perfilamento da Silver | 5.10 |
| Evolução de esquema e catálogo | Crawler com `MergeNewColumns` + versões de tabela no Catalog | 5.9 |

## 3. Escopo

### Dentro
- Tabelas da Receita: **Empresas, Estabelecimentos, Simples** e domínios (CNAE, Naturezas, Motivos, Municípios, Qualificações, Países).
- Fonte JSON: **API de localidades do IBGE** (municípios, UF, região).
- Meses de referência: **2026-09 e 2026-10**, Brasil inteiro.
- Ambiente local (Docker) para desenvolvimento e para o dashboard.

### Fora
- Tabela **Sócios** (não serve às perguntas de negócio; o PII já aparece nas demais tabelas).
- Fonte JDBC / RDS.
- Faturamento ou lucro (não existe na base).
- Relatório técnico em PDF (fica a cargo do aluno; este projeto gera as evidências).

## 4. Fontes de dados

| Fonte | Formato | Acesso | Volume |
|---|---|---|---|
| Receita Federal (CNPJ) | ZIP com CSV (`;`, latin1, sem cabeçalho) | WebDAV público: `https://arquivos.receitafederal.gov.br/public.php/webdav/<AAAA-MM>/` (usuário = token `YggdBLfdninEJX9`, senha vazia) | ~6,8 GB zip/mês sem Sócios (Estabelecimentos 5,2 GB, Empresas 1,3 GB, Simples 0,3 GB) |
| IBGE Localidades | JSON | `https://servicodados.ibge.gov.br/api/v1/localidades/municipios` | ~5.570 municípios |

**Observações sobre a fonte:**
- O endereço antigo `dadosabertos.rfb.gov.br` não responde mais.
- Os arquivos `Empresas0.zip` e `Estabelecimentos0.zip` são de 6 a 7× maiores que os demais (assimetria de volume).
- Os nomes e tipos de colunas seguem o SDK da Base dos Dados (`basedosdados/sdk/bases/br_me_cnpj`).
- O código de município da Receita (`id_municipio_rf`) **não é** o código do IBGE.

## 5. Arquitetura

```
Receita (WebDAV/ZIP) ─┐                                                     ┌─► crawler silver/gold ─► Catalog
IBGE (JSON) ──────────┴─► raw (CSV UTF-8) ─► bronze (Delta) ─► silver (Delta) ─► gold (Delta) ─► OPTIMIZE/VACUUM
                           │  crawler raw       │ PII mascarado   │ DQ + MERGE/CDF
                           └ exclusão em 30d    │ Bookmarks       └ DataBrew perfilamento
                                                                                    │
                                                    local: deltalake → Postgres → Metabase
```

### 5.1 Buckets e camadas

| Bucket | Conteúdo | Formato | Partição | Retenção |
|---|---|---|---|---|
| `raw` | Cópia fiel da origem, já em UTF-8 e com cabeçalho | CSV sem compressão (permite dividir a leitura entre workers) | `<tabela>/ano_mes=AAAA-MM/` | Exclusão automática em **30 dias** |
| `bronze` | Dados tipados, **PII mascarado** | Delta Lake | `ano_mes` | `VACUUM` 7 dias |
| `silver` | Limpo, padronizado, consolidado | Delta Lake | `ano_mes` (exceto a consolidada) | `VACUUM` 7 dias |
| `gold` | Esquema estrela | Delta Lake | `ano_mes` nas fatos | `VACUUM` 7 dias |
| `artifacts` | Scripts, temporários, resultados de DQ, Athena e perfis do DataBrew | — | — | — |

Todos os buckets usam SSE-S3, bloqueio de acesso público e região **us-east-1**.

> **Não** usar exclusão automática do S3 em buckets Delta: ela apaga arquivos referenciados pelo histórico do Delta e corrompe a tabela. A retenção ali é feita por `VACUUM`.

### 5.2 Ingestão (Python shell)
- **`ingest_receita`:**
  1. lista o mês no WebDAV e baixa os ZIPs (exceto Sócios);
  2. descompacta em fluxo;
  3. converte de latin1 para UTF-8;
  4. adiciona cabeçalho com os nomes do SDK;
  5. grava em `raw/<tabela>/ano_mes=AAAA-MM/`.
- **`ingest_ibge`:** chama a API e grava o JSON em `raw/ibge_municipios/ano_mes=AAAA-MM/`.
- Os dois são desenvolvidos localmente contra o MinIO; a "virada" para a AWS é só trocar parâmetro e credenciais.

### 5.3 Glue Studio
- Jobs Bronze, Silver e Gold criados no **editor visual**.
- Onde o visual não alcança, usar o nó **SQL Query** (consultas testadas localmente) ou o **Custom Transform** (`MERGE`, `replaceWhere`, manutenção).
- O destino Delta no Studio **não atualiza o Catalog**, então um crawler roda depois (ver 5.9).
- Glue **5.0**, workers **G.1X**, classe **Flex**: 2 workers na amostra, até 10 na base completa.

### 5.4 Processamento incremental e parâmetros
- **Job Bookmarks** apenas de `raw` para Bronze (origem CSV). O Bookmark não suporta origem Delta.
- De Bronze para Silver e de Silver para Gold: leitura limitada por `--ano_mes`.
- Parâmetros comuns: `--ano_mes`, `--bucket`, `--ambiente` (`sample` | `full`).

### 5.5 Idempotência e CDC
- As tabelas por mês são sobrescritas com **`replaceWhere ano_mes = X`**. Reprocessar um mês dá o mesmo resultado.
- A **`silver_empresa_consolidada`** tem uma linha por `cnpj_basico` (estado atual) e recebe `MERGE` mensal:
  - insere o que é novo;
  - atualiza o que mudou;
  - remove o que deixou de existir (`whenNotMatchedBySource`).
- O **Change Data Feed** fica ligado nela. A `fato_movimentacao_empresa` lê as mudanças entre versões e classifica os eventos: abertura, baixa, mudança de porte, entrada no MEI e saída do MEI.

### 5.6 Qualidade de dados (Glue Data Quality)

| Tipo | Regra | Ação |
|---|---|---|
| Bloqueante | `cnpj_basico` com 8 dígitos e sem nulos | Job falha e o Workflow para |
| Bloqueante | `cnpj_basico` único por `ano_mes` na fato | Job falha |
| Bloqueante | `porte` ∈ {00, 01, 03, 05} | Job falha |
| Bloqueante | 100% dos municípios da Receita casados com o IBGE | Job falha |
| Bloqueante | `capital_social` ≥ 0 | Job falha |
| Alerta | Quantidade de linhas do mês variando no máximo ±5% em relação ao mês anterior | Registra e segue |
| Alerta | `data_inicio_atividade` não futura | Registra e segue |
| Alerta | Percentual de e-mails nulos | Registra e segue |

### 5.7 Proteção de PII
- O nó **Detect Sensitive Data** fica na passagem de **`raw` para a Bronze**. Ele mascara e-mail, telefone/fax e CPF, incluindo o CPF embutido na razão social de MEI.
- A detecção roda só sobre as colunas de texto candidatas, para limitar custo.
- **Minimização:** endereço (logradouro, número, complemento, bairro, CEP) e razão social são descartados, porque não servem à análise.
- O único local com PII cru é o bucket `raw`, que é excluído em 30 dias e só o perfil `glue-pipeline` acessa.

### 5.8 Arquivos pequenos
- Job de manutenção no fim do Workflow: `OPTIMIZE` (compacta arquivos pequenos) + `VACUUM` (retenção de 7 dias).
- **Evidência:** uma rodada na amostra sem tratamento ("antes") contra uma com tratamento ("depois"). Medimos a quantidade de arquivos por partição, o tamanho médio, e o volume lido e o tempo de uma consulta de referência no Athena.

### 5.9 Catálogo e evolução de esquema
- **Crawler do `raw`:**
  - colunas novas são acrescentadas ao esquema (`MergeNewColumns`);
  - as partições herdam o esquema da tabela;
  - remoções só são registradas em log (`DeleteBehavior = LOG`).
- **Um crawler único para Silver e Gold** no fim do Workflow.
- **Evidência:** histórico de versões das tabelas no Catalog, mais um teste controlado em que adicionamos uma coluna e mostramos a nova versão.

### 5.10 DataBrew
- **Receita de limpeza do IBGE:** achata o JSON e padroniza os nomes de município (maiúsculas, sem acento). Entra no Workflow por meio do job Python shell `trigger_databrew`, que dispara a receita e espera terminar.
- **Perfilamento** da `silver_estabelecimentos`, em agenda própria (é informativo).

## 6. Modelo dimensional (Gold)

| Tabela | Grão | Conteúdo |
|---|---|---|
| `fato_empresa_mensal` | 1 empresa ativa × `ano_mes` | Chaves de município (da matriz), categoria, CNAE principal, natureza jurídica, data de início; `cnpj_basico` como dimensão degenerada; medidas `capital_social` e `qtd_estabelecimentos` |
| `fato_movimentacao_empresa` | 1 evento × empresa × `ano_mes` | `tipo_evento` (abertura, baixa, mudança de porte, entrada no MEI, saída do MEI) + chaves |
| `dim_municipio` | 1 município | `id_municipio_rf`, `id_municipio_ibge`, nome, UF, região |
| `dim_categoria` | 4 linhas | MEI, ME, EPP, Demais |
| `dim_cnae` | 1 CNAE | Código e descrição |
| `dim_natureza_juridica` | 1 natureza | Código e descrição |
| `dim_tempo` | 1 mês | Ano, mês, trimestre |

**Regras de negócio:**
- **Categoria:** `MEI` se `simples.opcao_mei = 'S'` e não houver data de exclusão. Senão, é decidida pelo `empresas.porte`: `01` = ME, `03` = EPP, `05` ou `00` = Demais. Todo MEI também tem porte 01, por isso o MEI é avaliado primeiro.
- **Empresa ativa:** `situacao_cadastral = 02` no estabelecimento matriz (`identificador_matriz_filial = 1`).
- **Localização:** município do estabelecimento matriz.
- **Sem `dim_empresa`:** seriam ~60 milhões de linhas de nomes, que são PII.

## 7. Orquestração e operação

### 7.1 Workflow (Glue Workflows)

```
[gatilho mensal (dia 20) | sob demanda]
 → ingest_receita ∥ ingest_ibge
 → crawler_raw
 → bronze_empresas ∥ bronze_estabelecimentos ∥ bronze_simples ∥ bronze_dominios
 → trigger_databrew (receita IBGE)
 → silver_* + silver_empresa_consolidada (DQ + MERGE/CDF)
 → gold_dimensoes → gold_fatos
 → manutencao (OPTIMIZE/VACUUM)
 → crawler_silver_gold
```

### 7.2 Resiliência
- Cada job tem **1 nova tentativa** e um *timeout* próprio. A idempotência garante que repetir não duplica dados.
- Falhas no meio do Workflow podem ser **retomadas** a partir do passo que falhou.

### 7.3 Monitoramento
- **Alertas:** regra do EventBridge para jobs com estado `FAILED` ou `TIMEOUT` → SNS → e-mail.
- **Logs:** CloudWatch Logs contínuos, retenção de 7 dias.
- **Dashboard do CloudWatch:** duração, falhas e linhas processadas por job.
- **Métricas detalhadas de observabilidade do Glue:** ligadas só nas rodadas finais (custo).

### 7.4 Segurança e permissões

| Perfil | Acesso |
|---|---|
| `glue-pipeline` | Leitura e escrita só nos buckets e prefixos de que cada etapa precisa |
| `analista` | Somente leitura no bucket `gold` (usado na carga do dashboard) |

## 8. Infraestrutura como código
- **Terraform** cria buckets, perfis de acesso, bancos do Catalog, crawlers, regras de Data Quality, Workflow e gatilhos, recursos do DataBrew, EventBridge, SNS, Budgets e o dashboard do CloudWatch.
- **Jobs visuais:** exportados com `aws glue get-job` (inclui o grafo visual) e versionados como JSON. Um script os recria com `create-job`/`update-job`, mantendo-os visuais.
- **Estado do Terraform local**, fora do Git. O estado num bucket S3 fica como melhoria futura.

## 9. Ambiente local e dashboard

`docker compose` com:
- `public.ecr.aws/glue/aws-glue-libs:5`: Spark e Glue local para os jobs Python, as consultas SQL e os testes com pytest;
- **MinIO**: S3 local;
- **Postgres**: base do dashboard;
- **Metabase**: dashboard.

**Limitações do container** (pela documentação da AWS): ele não roda Job Bookmarks, Glue Data Quality, Detect Sensitive Data nem o gravador Parquet otimizado do Glue. Esses recursos são desenvolvidos e testados direto na AWS, sobre a amostra.

**Amostra de desenvolvimento:** gerada uma vez localmente com DuckDB, a partir de um mês completo. É o recorte de **AC, AP e RR** com as empresas e os registros do Simples correspondentes, para que os joins fiquem consistentes. Ela é usada localmente e no prefixo `sample/` do S3.

**Carga do dashboard:** `make dashboard-load ANO_MES=AAAA-MM`, rodado manualmente depois do Workflow. Ele:
1. lê a Gold do S3 com a biblioteca `deltalake` (delta-rs), usando o perfil `analista`;
2. apaga e reinsere o mês no Postgres via `COPY`, de forma idempotente;
3. atualiza as **visões materializadas** por município, UF e região (com mediana já calculada), que o Metabase lê.

## 10. Custos

| Medida | Efeito |
|---|---|
| Desenvolvimento na amostra; base completa só na rodada final (2 meses + 1 repetição para provar a idempotência) | Limita as horas de DPU |
| Classe Flex (US$ 0,29 por DPU-hora, contra 0,44) | −34% no processamento |
| Somente 2 crawlers (cada execução cobra no mínimo 10 min) | Menos custo de crawler |
| Pré-visualização de dados do Studio desligada | Evita sessões cobradas |
| Sem RDS, NAT Gateway ou chave KMS própria | Evita custo fixo |
| AWS Budgets com alertas em US$ 5 e US$ 8 | Controle |

Estimativa: **~US$ 6–8** no projeto inteiro.

## 11. Riscos e decisões conscientes

| Risco / decisão | Mitigação |
|---|---|
| **Item "fontes JDBC" da rubrica não atendido** | Decisão consciente: evitar RDS e a configuração de rede |
| O editor visual pode não aceitar parâmetros em todos os nós | Verificar no primeiro job; usar *Custom Transform* onde não aceitar |
| Download da Receita a partir da AWS pode ser lento | Testar cedo; o Python shell custa ~US$ 0,03/h |
| Detect Sensitive Data na base completa pode ser lento e caro | Restringir às colunas de texto candidatas |
| Assimetria dos arquivos `0` da Receita | CSV sem compressão no `raw`, que o Spark divide entre workers |
| Nomes de município divergentes entre Receita e IBGE | Padronização no DataBrew + tabela manual de correções + regra bloqueante |
| Orçamento apertado (US$ 10) | Seção 10 |

## 12. Plano de implementação

| # | Etapa | Entregável |
|---|---|---|
| 1 | Repositório, `docker compose` local, geração da amostra | Ambiente local funcionando com a amostra |
| 2 | Terraform da base | Buckets, perfis de acesso, Catalog, Budgets, SNS |
| 3 | Ingestão Receita + IBGE, crawler do `raw` | `raw` populado e catalogado |
| 4 | Bronze com PII mascarado e Bookmarks | Tabelas Bronze em Delta |
| 5 | Silver + `MERGE`/CDF + Data Quality, DataBrew | Silver validada e CDC funcionando |
| 6 | Gold + manutenção + crawler final | Esquema estrela catalogado |
| 7 | Workflow, alertas, dashboard do CloudWatch | Pipeline orquestrado de ponta a ponta |
| 8 | Rodada completa (2026-09 e 2026-10), carga no Postgres, Metabase | Dashboard com as 3 perguntas de negócio |
