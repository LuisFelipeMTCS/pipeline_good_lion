# Glue Workflow (PRD, 7.1). O mês da execução fica nas propriedades do Workflow: sob demanda,
#   aws glue start-workflow-run --name goodlion --run-properties ano_mes=2026-09,ingestao=nao
# (ingestao=nao roda sobre o que já está no raw, ex.: a amostra); no gatilho mensal, o definir_mes usa o mês corrente.
# Os jobs visuais são do scripts/deploy_jobs.py: rode `make deploy-jobs` antes do apply, senão os gatilhos não acham os jobs.
resource "aws_glue_workflow" "pipeline" {
  name                   = var.prefixo
  default_run_properties = { ingestao = "sim" }
  max_concurrent_runs    = 1 # dois meses ao mesmo tempo bagunçariam o MERGE da consolidada
}

resource "aws_s3_object" "definir_mes" {
  bucket = aws_s3_bucket.camada["artifacts"].id
  key    = "scripts/definir_mes.py"
  source = "${path.module}/../ingest/definir_mes.py"
  etag   = filemd5("${path.module}/../ingest/definir_mes.py")
}

resource "aws_glue_job" "definir_mes" {
  name         = "definir_mes"
  role_arn     = aws_iam_role.glue_pipeline.arn
  glue_version = "3.0"
  max_capacity = 0.0625
  max_retries  = 1
  timeout      = 5

  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = "s3://${aws_s3_object.definir_mes.bucket}/${aws_s3_object.definir_mes.key}"
  }
}

locals {
  # Cada etapa começa quando todas as da etapa anterior terminam com sucesso (falha ou regra bloqueante param o Workflow;
  # dá para retomar do passo que falhou com `aws glue resume-workflow-run`).
  etapas = [
    { nome = "ingestao", jobs = ["ingest_receita", "ingest_ibge"], crawlers = [] },
    { nome = "catalogo-raw", jobs = [], crawlers = [aws_glue_crawler.raw.name] },
    { nome = "bronze", jobs = ["bronze_estabelecimentos", "bronze_empresas", "bronze_simples", "bronze_dominios", "trigger_databrew"], crawlers = [] },
    { nome = "silver", jobs = ["silver_estabelecimentos", "silver_empresas", "silver_simples"], crawlers = [] },
    { nome = "consolidada-e-dimensoes", jobs = ["silver_empresa_consolidada", "gold_dim_municipio", "gold_dimensoes"], crawlers = [] },
    { nome = "fatos", jobs = ["gold_fato_empresa_mensal", "gold_fato_movimentacao_empresa"], crawlers = [] },
    { nome = "manutencao", jobs = ["manutencao"], crawlers = [] },
    { nome = "catalogo-silver-gold", jobs = [], crawlers = [for c in aws_glue_crawler.delta : c.name] },
  ]
}

# Gatilho mensal (dia 20, 9h UTC). O Glue aceita um só gatilho inicial por Workflow, e desligado ele também
# impede o start-workflow-run sob demanda (a execução terminava na hora com 0 ações). Por isso fica ligado:
# depois da entrega, `aws glue stop-trigger --name goodlion-mensal` evita a execução mensal (~US$ 1).
resource "aws_glue_trigger" "mensal" {
  name          = "${var.prefixo}-mensal"
  workflow_name = aws_glue_workflow.pipeline.name
  type          = "SCHEDULED"
  schedule      = "cron(0 9 20 * ? *)"
  enabled       = true
  actions {
    job_name = aws_glue_job.definir_mes.name
  }
}

resource "aws_glue_trigger" "etapa" {
  count         = length(local.etapas)
  name          = "${var.prefixo}-${local.etapas[count.index].nome}"
  workflow_name = aws_glue_workflow.pipeline.name
  type          = "CONDITIONAL"

  predicate {
    logical = "AND"
    dynamic "conditions" {
      for_each = count.index == 0 ? [aws_glue_job.definir_mes.name] : local.etapas[count.index - 1].jobs
      content {
        job_name = conditions.value
        state    = "SUCCEEDED"
      }
    }
    dynamic "conditions" {
      for_each = count.index == 0 ? [] : local.etapas[count.index - 1].crawlers
      content {
        crawler_name = conditions.value
        crawl_state  = "SUCCEEDED"
      }
    }
  }

  dynamic "actions" {
    for_each = local.etapas[count.index].jobs
    content {
      job_name = actions.value
    }
  }
  dynamic "actions" {
    for_each = local.etapas[count.index].crawlers
    content {
      crawler_name = actions.value
    }
  }

  depends_on = [aws_glue_job.ingest_receita, aws_glue_job.ingest_ibge, aws_glue_job.trigger_databrew]
}
