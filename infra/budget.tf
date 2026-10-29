# O Budgets avisa, não bloqueia gastos.
# Trimestral porque o projeto atravessa outubro e novembro: um orçamento mensal zeraria no dia 1º.
resource "aws_budgets_budget" "projeto" {
  name         = var.prefixo
  budget_type  = "COST"
  limit_amount = "10"
  limit_unit   = "USD"
  time_unit    = "QUARTERLY"

  dynamic "notification" {
    for_each = [5, 8]
    content {
      comparison_operator       = "GREATER_THAN"
      threshold                 = notification.value
      threshold_type            = "ABSOLUTE_VALUE"
      notification_type         = "ACTUAL"
      subscriber_sns_topic_arns = [aws_sns_topic.alertas.arn]
    }
  }
}
