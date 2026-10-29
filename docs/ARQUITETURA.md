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
│   ├── crawlers.tf              # crawler do raw (MergeNewColumns, DeleteBehavior=LOG) e da silver/gold
│   ├── workflow.tf              # Glue Workflow e gatilhos
│   ├── databrew.tf              # receita de limpeza do IBGE e perfilamento
│   ├── monitoring.tf            # EventBridge → SNS (e-mail), logs e dashboard do CloudWatch
│   └── budget.tf                # alertas em US$ 5 e US$ 8 (o Budgets avisa, não bloqueia gastos)
│
├── ingest/                      # GATEWAYS: jobs Python shell (Py 3.9, só stdlib + boto3, sem Spark)
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
│   ├── custom/                  # código dos nós Custom Transform
│   │   ├── merge_consolidada.py # MERGE na silver_empresa_consolidada (Change Data Feed ligado)
│   │   └── manutencao.py        # OPTIMIZE + VACUUM (7 dias)
│   ├── spark.py                 # SparkSession com Delta para o container local
│   └── local.py                 # executor local: lê/grava Delta no MinIO e roda os mesmos .sql
│
├── scripts/
│   ├── exportar_job.py          # get-job → glue/jobs/*.json, trocando SQL/DQDL por marcadores
│   └── deploy_jobs.py           # injeta .sql/.dqdl no JSON → create-job/update-job
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
| Parâmetros | Todo job recebe `--ano_mes`, `--bucket`, `--ambiente` (`sample`/`full`) | — |
| O ambiente | É parâmetro do job, **não** variável do Terraform: a infraestrutura é uma só | — |
| Código | Nomes em português, ruff, `ingest/` compatível com Py 3.9 | — |
| Testes | `make test` no host (sem Spark); `make test-spark` no container do Glue | — |
| Commits | `Conclui o ticket NN: …` | — |

## O que não se testa localmente

O container do Glue não roda **Detect Sensitive Data**, **Glue Data Quality** nem **Job Bookmarks** (PRD, seção 9). Para esses três:

- localmente, os testes cobrem as regras de negócio do SQL e a idempotência;
- na AWS, a evidência é a execução sobre a amostra, com prints salvos em `docs/evidencias/`.
