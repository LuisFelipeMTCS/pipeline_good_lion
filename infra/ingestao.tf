# Jobs Python shell de ingestão: o código vem do repositório e vai para o artifacts.
resource "aws_s3_object" "ingest_receita" {
  bucket = aws_s3_bucket.camada["artifacts"].id
  key    = "scripts/ingest_receita.py"
  source = "${path.module}/../ingest/receita.py"
  etag   = filemd5("${path.module}/../ingest/receita.py")
}

# Download limitado pela Receita (~1,7 MB/s por conexão): um mês completo leva por volta de uma hora.
resource "aws_glue_job" "ingest_receita" {
  name         = "ingest_receita"
  role_arn     = aws_iam_role.glue_pipeline.arn
  glue_version = "3.0" # Python shell com Python 3.9
  max_capacity = 0.0625
  max_retries  = 1
  timeout      = 240 # minutos

  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = "s3://${aws_s3_object.ingest_receita.bucket}/${aws_s3_object.ingest_receita.key}"
  }

  # --ano_mes vem em cada execução (Workflow ou manual); --tabelas=a,b restringe para refazer só o que falhou.
  default_arguments = {
    "--bucket" = aws_s3_bucket.camada["raw"].bucket
  }
}

resource "aws_s3_object" "ingest_ibge" {
  bucket = aws_s3_bucket.camada["artifacts"].id
  key    = "scripts/ingest_ibge.py"
  source = "${path.module}/../ingest/ibge.py"
  etag   = filemd5("${path.module}/../ingest/ibge.py")
}

# Uma chamada à API do IBGE (~1,5 MB): segundos.
resource "aws_glue_job" "ingest_ibge" {
  name         = "ingest_ibge"
  role_arn     = aws_iam_role.glue_pipeline.arn
  glue_version = "3.0"
  max_capacity = 0.0625
  max_retries  = 1
  timeout      = 10

  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = "s3://${aws_s3_object.ingest_ibge.bucket}/${aws_s3_object.ingest_ibge.key}"
  }

  default_arguments = {
    "--bucket" = aws_s3_bucket.camada["raw"].bucket
  }
}

resource "aws_s3_object" "trigger_databrew" {
  bucket = aws_s3_bucket.camada["artifacts"].id
  key    = "scripts/trigger_databrew.py"
  source = "${path.module}/../ingest/trigger_databrew.py"
  etag   = filemd5("${path.module}/../ingest/trigger_databrew.py")
}

# Dispara a receita do IBGE (infra/databrew.tf) e espera: assim o DataBrew vira um passo do Workflow.
resource "aws_glue_job" "trigger_databrew" {
  name         = "trigger_databrew"
  role_arn     = aws_iam_role.glue_pipeline.arn
  glue_version = "3.0"
  max_capacity = 0.0625
  max_retries  = 1
  timeout      = 30

  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = "s3://${aws_s3_object.trigger_databrew.bucket}/${aws_s3_object.trigger_databrew.key}"
  }

  default_arguments = {
    "--job_databrew" = local.job_limpeza_ibge
  }
}
