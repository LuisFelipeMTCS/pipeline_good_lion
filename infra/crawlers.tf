# CSV da Receita: ';', aspas e cabeçalho. Sem este classificador o Athena mostraria as aspas nos valores.
resource "aws_glue_classifier" "csv_receita" {
  name = "${var.prefixo}-csv-receita"
  csv_classifier {
    delimiter       = ";"
    quote_symbol    = "\""
    contains_header = "PRESENT"
    serde           = "OpenCSVSerDe"
  }
}

resource "aws_glue_crawler" "raw" {
  name          = "${var.prefixo}-raw"
  role          = aws_iam_role.glue_pipeline.arn
  database_name = aws_glue_catalog_database.camada["raw"].name
  classifiers   = [aws_glue_classifier.csv_receita.name]

  # shortcut: só a amostra é catalogada (os jobs leem o S3 direto); incluir a raiz se o Athena precisar da base completa.
  s3_target {
    path = "s3://${aws_s3_bucket.camada["raw"].bucket}/sample/"
  }

  # Colunas novas entram no esquema; colunas e tabelas sumidas só vão para o log.
  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }
  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Tables     = { AddOrUpdateBehavior = "MergeNewColumns" }
      Partitions = { AddOrUpdateBehavior = "InheritFromTable" }
    }
    # Nível 3 = s3://bucket/sample/<tabela>/: uma tabela por pasta, mesmo os domínios que têm o mesmo esquema.
    Grouping = { TableLevelConfiguration = 3 }
  })
}
