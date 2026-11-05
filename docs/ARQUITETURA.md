# Arquitetura do repositório

Complementa o [PRD](PRD.md): o PRD diz **o que** o pipeline faz; este documento diz **onde** cada coisa fica no código e **qual padrão** seguir.

## Princípio

> **SQL é a lógica, Python é o encanamento, JSON é o desenho.**

No Glue Studio o próprio job visual já é dividido em camadas:

```
[Nó Source S3]  →  [Nó SQL Query]  →  [Evaluate Data Quality]  →  [Nó Target Delta]
   gateway            service              contrato                  repository
        ↑ parâmetros do job (--ano_mes, --bucket, --ambiente) = controller
```

Por isso o repositório guarda só o que é nosso de verdade:

- **Regras de negócio** em `jobs/sql/` (e `jobs/custom/` onde o SQL não alcança). São testadas localmente com pytest.
- **Regras de qualidade** em `jobs/quality/` (DQDL).
- **Desenho visual** em `glue/jobs/*.json`, com marcadores no lugar do SQL e do DQDL.

O `scripts/deploy_jobs.py` injeta os `.sql`/`.dqdl` nos nós do JSON e roda `create-job`/`update-job`. Assim o SQL testado no pytest é exatamente o que roda na AWS, sem copiar e colar no editor.

## Estrutura

```
pipeline_good_lion/
├── amostra/
│   └── gerar_amostra.py         # gera o recorte AC/AP/RR em raw/sample/ (os dados não entram no Git)
│
├── dashboard/                   # consumo: perguntas de negócio
│   ├── carga.py                 # make dashboard-load: lê a Gold (deltalake) e regrava o mês no Postgres
│   └── schema.sql               # tabelas e visões materializadas lidas pelo Metabase
│
├── docs/
│   ├── PRD.md                   # escopo e decisões
│   ├── ARQUITETURA.md           # este arquivo
│   ├── issues/                  # backlog em tickets
│   └── evidencias/              # prints e medições para o relatório (PII, DQ, custos, antes/depois)
│
├── glue/
│   └── jobs/                    # grafos visuais exportados, um JSON por job
│       └── bronze_estabelecimentos.json
│
├── infra/                       # Terraform: um módulo raiz, um arquivo por assunto
│   ├── versions.tf              # provider AWS
│   ├── variables.tf             # região, e-mail dos alertas, prefixo dos buckets
│   ├── terraform.tfvars.example
│   ├── s3.tf                    # buckets raw/bronze/silver/gold/artifacts; expiração de 30 dias só no raw
│   ├── iam.tf                   # perfis glue-pipeline e analista
│   ├── catalog.tf               # bancos goodlion_<camada>
│   ├── colunas_raw.json         # colunas das tabelas do raw no Catalog (um teste garante que batem com a ingestão)
│   ├── crawlers.tf              # tabelas do raw (tudo texto) + crawler que só acrescenta partições/colunas; e um crawler Delta por camada (silver, gold)
│   ├── ingestao.tf              # jobs Python shell de ingestão (código enviado ao artifacts)
│   ├── workflow.tf              # Glue Workflow e gatilhos
│   ├── databrew.tf              # receita de limpeza do IBGE e perfilamento (pilha do CloudFormation)
│   ├── databrew_receita_ibge.json # passos da receita do IBGE
│   ├── monitoring.tf            # EventBridge → SNS (e-mail), logs e dashboard do CloudWatch
│   └── budget.tf                # alertas em US$ 5 e US$ 8 (o Budgets avisa, não bloqueia gastos)
│
├── ingest/                      # GATEWAYS: jobs Python shell (Py 3.9, só stdlib + boto3, sem Spark)
│   ├── definir_mes.py           # 1º passo do Workflow: fixa o ano_mes nas propriedades da execução
│   ├── receita.py               # WebDAV da Receita → ZIP → UTF-8 com cabeçalho → raw
│   ├── ibge.py                  # API de municípios do IBGE → raw
│   └── trigger_databrew.py      # dispara a receita do DataBrew e espera terminar
│
├── jobs/                        # SERVICES: lógica de transformação
│   ├── sql/                     # conteúdo dos nós SQL Query
│   │   ├── bronze/              # tipagem + descarte de endereço e razão social (minimização)
│   │   ├── silver/              # limpeza, padronização, regra de empresa ativa
│   │   └── gold/                # dim_* e fato_* (esquema estrela)
│   ├── quality/                 # regras DQDL dos nós Evaluate Data Quality
│   ├── referencias/             # tabelas manuais versionadas (correções Receita × IBGE), enviadas ao artifacts
│   ├── custom/                  # corpo dos nós Custom Transform (o Glue embrulha numa função)
│   │   ├── garantir_esquema.py  # Bronze: dá as colunas do Catalog ao lote vazio do Bookmark
│   │   ├── gravar_delta.py      # grava Delta com replaceWhere nos meses do lote (dimensão: regrava inteira)
│   │   ├── filtrar_mes.py       # Silver e Gold: limita a origem Delta ao --ano_mes
│   │   ├── merge_consolidada.py # MERGE (em SQL) na silver_empresa_consolidada, Change Data Feed ligado
│   │   ├── ler_mudancas.py      # Gold: lê o CDF das versões de MERGE do --ano_mes
│   │   └── manutencao.py        # OPTIMIZE + VACUUM (7 dias)
│   ├── spark.py                 # SparkSession com Delta para o container local
│   └── local.py                 # executor local: lê/grava Delta no MinIO, roda os mesmos .sql e os Custom Transforms
│
├── scripts/
│   ├── exportar_job.py          # get-job → glue/jobs/*.json; o texto dos marcadores volta para os arquivos
│   └── deploy_jobs.py           # troca os marcadores "@arquivo:<caminho>" pelo conteúdo → create-job/update-job
│
├── tests/                       # um arquivo de teste por módulo ou job
│
├── docker-compose.yml  Makefile  pyproject.toml  uv.lock
└── .env.example  ruff.toml  pytest.ini
```

**Fica de fora de propósito:** CI no GitHub Actions. Os testes de Spark precisam do container do Glue, e isso não é avaliado. Fica como melhoria futura.

## Convenções

| O quê | Padrão | Exemplo |
|---|---|---|
| Nome do job | `<camada>_<tabela>`, igual no job do Glue, no JSON e no teste | `silver_estabelecimentos` |
| Arquivo de SQL | `jobs/sql/<camada>/<tabela>.sql` | `jobs/sql/silver/estabelecimentos.sql` |
| Arquivo de DQ | `jobs/quality/<nome do job>.dqdl` | `jobs/quality/silver_estabelecimentos.dqdl` |
| Caminho no S3 | `<bucket da camada>/[sample/]<tabela>/ano_mes=AAAA-MM/`: amostra no prefixo `sample/`, base completa na raiz | `bronze/sample/estabelecimentos/ano_mes=2026-09/` |
| Bucket na AWS | `goodlion-<camada>-<id da conta>` (nome único no mundo); localmente só `<camada>` | `goodlion-bronze-123456789012` |
| Banco do Catalog | `goodlion_<camada>` | `goodlion_gold` |
| Tabelas da Gold | `dim_<entidade>` no singular, `fato_<assunto>` | `dim_municipio`, `fato_empresa_mensal` |
| Colunas | snake_case com os nomes do SDK da Base dos Dados | `id_municipio_rf` |
| Gravação | Nunca `append`: `replaceWhere` por `ano_mes` ou `MERGE` | — |
| Parâmetros | Todo job recebe `--ano_mes`, `--bucket` (bucket de destino), `--ambiente` (`sample`/`full`). Dentro do Glue Workflow o `--ano_mes` não vem: o mês está nas propriedades da execução (fixadas pelo `ingest/definir_mes.py`), e os jobs leem de lá. Na Bronze o `--ano_mes` não é usado: quem limita a leitura é o Bookmark (PRD, 5.4) | `--bucket goodlion-bronze-<conta>` |
| O ambiente | É parâmetro do job, **não** variável do Terraform: a infraestrutura é uma só. Os JSON de `glue/jobs/` descrevem a amostra; `scripts/deploy_jobs.py --ambiente full` publica os mesmos jobs para a base completa (caminhos sem `sample/`, tabelas `full_<tabela>` do raw, até 10 workers). No Catalog, a base completa tem as tabelas `full_<tabela>` (raw, Silver e Gold) | — |
| Nomes de argumento | Nenhum argumento pode ser prefixo de outro (`--bucket` × `--bucket_silver`): o `getResolvedOptions` aceita abreviação e um lê o valor do outro conforme a ordem | `--origem_silver` |
| Código | Nomes em português, ruff, `ingest/` compatível com Py 3.9 | — |
| Testes | `make test` no host (sem Spark); `make test-spark` no container do Glue | — |
| Commits | `Conclui o ticket NN: …` | — |

## O que não se testa localmente

O container do Glue não roda **Detect Sensitive Data**, **Glue Data Quality** nem **Job Bookmarks** (PRD, seção 9). Para esses três:

- localmente, os testes cobrem as regras de negócio do SQL e a idempotência;
- na AWS, a evidência é a execução sobre a amostra, com prints salvos em `docs/evidencias/`.

## Padrão dos jobs visuais (descoberto no ticket 04)

Grafo de um job Bronze (`glue/jobs/bronze_estabelecimentos.json`):

```
Catalog (goodlion_raw.<tabela>) → GarantirEsquema → SelectFromCollection → SQL (jobs/sql/bronze/<tabela>.sql) → GravarDelta
```

- **Marcadores:** no JSON, todo valor `"@arquivo:<caminho>"` vira o conteúdo do arquivo no deploy. O `exportar_job.py` faz o caminho inverso: uma edição de SQL feita no editor visual volta para o `.sql`.
- **Parâmetros nos nós:** nenhum nó visual aceita parâmetro do job nas propriedades (banco, tabela, caminho e predicado são texto fixo). Os parâmetros só chegam ao código dos Custom Transforms, via `getResolvedOptions(sys.argv)`.
- **Custom Transform:** o campo `Code` é o **corpo** da função; o Glue o embrulha em `def <ClassName>(glueContext, dfc)`. Por isso os arquivos de `jobs/custom/` têm `return` solto. Para usar a saída num nó seguinte, é preciso um `SelectFromCollection`.
- **Gravação:** o nó Target Delta do Studio não tem `replaceWhere`, então a gravação é o Custom Transform `GravarDelta`. Ele substitui só os meses presentes no lote; tabela sem `ano_mes` (dimensão) é regravada inteira.
- **Nome da tabela vem do nó anterior (ticket 07):** o Glue entrega ao Custom Transform um `dfc` com a chave `<Name do nó anterior>_<id do nó sem hífens>` (ex.: `bronze_cnaes_nodesqlcnaes`). Por isso o nó que alimenta o `GravarDelta` se chama `<camada>_<tabela>`, e a origem que alimenta o `GarantirEsquema` se chama `raw_<tabela>`. É o que permite um job só gravar várias tabelas (`bronze_dominios`, 6 ramos). O `tests/test_deploy_jobs.py` confere a regra em todos os JSON.
- **Silver e Gold (ticket 08):** `S3DeltaSource → FiltrarMes → SelectFromCollection → SQL → GravarDelta`. O `FiltrarMes` lê o `--ano_mes` (nenhum nó visual lê parâmetro) e filtra a partição. Um SQL com várias entradas recebe uma origem filtrada por tabela (`gold_fato_empresa_mensal`). As dimensões sem mês (`gold_dimensoes`, `gold_dim_municipio`) leem a origem inteira.
- **CDC (ticket 12):** o `MergeConsolidada` grava o `ano_mes` no `userMetadata` de cada commit; o `LerMudancas` lê o Change Data Feed só das versões de `MERGE` daquele mês. O `MERGE` é SQL (`MERGE INTO ... WHEN NOT MATCHED BY SOURCE THEN DELETE`), não a API Python do Delta: o módulo `delta` não vem no container local. O `jobs/local.py` roda o corpo desses Custom Transforms como o Glue (embrulhado numa função), então o código testado localmente é o mesmo da AWS.
- **Domínios e IBGE sem recorte:** o domínio de municípios e a lista do IBGE são do Brasil inteiro mesmo na amostra. A saída do DataBrew fica em `silver/ibge_municipios/` (Parquet, sem `sample/`).
- **Bookmark sem arquivos novos:** a origem vem **sem colunas** e o SQL falharia; o `GarantirEsquema` devolve um lote vazio com as colunas do Catalog.
- **Origem pelo Catalog:** é ela que traz a coluna `ano_mes` (partição). O esquema do raw é do Terraform, tudo texto: o crawler deduzia `bigint` e o `cnpj_basico` perdia os zeros à esquerda.
- **Nomes na API:** o nó SQL Query se chama `SparkSQL` no JSON.

