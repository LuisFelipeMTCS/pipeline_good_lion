# Tópico dos alertas. O ticket 06 acrescenta o EventBridge, os logs e o dashboard.
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
      Principal = { Service = "budgets.amazonaws.com" }
      Action    = "SNS:Publish"
      Resource  = aws_sns_topic.alertas.arn
    }]
  })
}
