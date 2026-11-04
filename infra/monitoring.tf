# Tópico dos alertas: Budgets (ticket 03) e falhas dos jobs (EventBridge).
resource "aws_sns_topic" "alertas" {
  name = "${var.prefixo}-alertas"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alertas.arn
  protocol  = "email"
  endpoint  = var.email_alertas
}

resource "aws_sns_topic_policy" "alertas" {
  arn = aws_sns_topic.alertas.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = ["budgets.amazonaws.com", "events.amazonaws.com"] }
      Action    = "SNS:Publish"
      Resource  = aws_sns_topic.alertas.arn
    }]
  })
}

# Job do Glue em FAILED ou TIMEOUT → e-mail.
resource "aws_cloudwatch_event_rule" "falha_glue" {
  name = "${var.prefixo}-falha-glue"
  event_pattern = jsonencode({
    source        = ["aws.glue"]
    "detail-type" = ["Glue Job State Change"]
    detail        = { state = ["FAILED", "TIMEOUT", "ERROR"] }
  })
}

resource "aws_cloudwatch_event_target" "falha_glue_email" {
  rule = aws_cloudwatch_event_rule.falha_glue.name
  arn  = aws_sns_topic.alertas.arn
  input_transformer {
    input_paths    = { job = "$.detail.jobName", estado = "$.detail.state", execucao = "$.detail.jobRunId", mensagem = "$.detail.message" }
    input_template = "\"Job <job> terminou em <estado> (execução <execucao>): <mensagem>\""
  }
}

# Todo fim de execução vai para um log: é de onde o dashboard tira execuções e falhas por job.
resource "aws_cloudwatch_event_rule" "fim_glue" {
  name = "${var.prefixo}-fim-glue"
  event_pattern = jsonencode({
    source        = ["aws.glue"]
    "detail-type" = ["Glue Job State Change"]
  })
}

resource "aws_cloudwatch_log_group" "eventos_glue" {
  name              = "/aws/events/${var.prefixo}-glue"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_resource_policy" "eventos_glue" {
  policy_name = "${var.prefixo}-eventbridge-logs"
  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = ["events.amazonaws.com", "delivery.logs.amazonaws.com"] }
      Action    = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource  = "${aws_cloudwatch_log_group.eventos_glue.arn}:*"
    }]
  })
}

resource "aws_cloudwatch_event_target" "fim_glue_log" {
  rule = aws_cloudwatch_event_rule.fim_glue.name
  arn  = aws_cloudwatch_log_group.eventos_glue.arn
}

# Logs do Glue com retenção de 7 dias. Os que o Glue já tinha criado são importados.
locals {
  logs_glue = [
    "/aws-glue/crawlers", "/aws-glue/jobs/error", "/aws-glue/jobs/logs-v2", "/aws-glue/jobs/output",
    "/aws-glue/python-jobs/output", "/aws-glue/python-jobs/error",
  ]
}

import {
  for_each = toset(["/aws-glue/crawlers", "/aws-glue/jobs/error", "/aws-glue/jobs/logs-v2", "/aws-glue/jobs/output", "/aws-glue/python-jobs/output"])
  to       = aws_cloudwatch_log_group.glue[each.key]
  id       = each.key
}

resource "aws_cloudwatch_log_group" "glue" {
  for_each          = toset(local.logs_glue)
  name              = each.key
  retention_in_days = 7
}

# Duração, falhas e linhas gravadas por job, tudo de logs (Logs Insights). As métricas do Glue
# (--enable-metrics) são cobradas como métricas do CloudWatch e ficam para a rodada final (ticket 17).
resource "aws_cloudwatch_dashboard" "pipeline" {
  dashboard_name = var.prefixo
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "log", x = 0, y = 0, width = 12, height = 6
        properties = {
          title  = "Execuções por job e estado"
          region = var.regiao
          view   = "table"
          query  = "SOURCE '${aws_cloudwatch_log_group.eventos_glue.name}' | stats count(*) as execucoes by detail.jobName as job, detail.state as estado | sort job"
        }
      },
      {
        type = "log", x = 12, y = 0, width = 12, height = 6
        properties = {
          title  = "Falhas (FAILED, TIMEOUT, ERROR)"
          region = var.regiao
          view   = "table"
          query  = "SOURCE '${aws_cloudwatch_log_group.eventos_glue.name}' | filter detail.state in ['FAILED', 'TIMEOUT', 'ERROR'] | fields @timestamp, detail.jobName as job, detail.state as estado, detail.message as mensagem | sort @timestamp desc"
        }
      },
      {
        # Cada job imprime no fim: "resumo job=<nome> segundos=<n> linhas=<n> meses=<...>".
        type = "log", x = 0, y = 6, width = 24, height = 6
        properties = {
          title  = "Resumo por execução: duração e linhas gravadas"
          region = var.regiao
          view   = "table"
          query  = "SOURCE '/aws-glue/jobs/output' | SOURCE '/aws-glue/python-jobs/output' | filter @message like /resumo job=/ | parse @message /job=(?<job>\\S+) segundos=(?<segundos>\\d+)/ | parse @message /linhas=(?<linhas>\\d+)/ | parse @message /meses=(?<meses>\\S+)/ | fields segundos / 60 as minutos | display @timestamp, job, minutos, linhas, meses | sort @timestamp desc"
        }
      },
    ]
  })
}
