resource "aws_glue_catalog_database" "camada" {
  for_each = toset(["raw", "bronze", "silver", "gold"])
  name     = "${var.prefixo}_${each.key}"
}

# Resultados das consultas do Athena vão para o artifacts.
resource "aws_athena_workgroup" "projeto" {
  name          = var.prefixo
  force_destroy = true
  configuration {
    result_configuration {
      output_location = "s3://${aws_s3_bucket.camada["artifacts"].bucket}/athena/"
    }
  }
}
