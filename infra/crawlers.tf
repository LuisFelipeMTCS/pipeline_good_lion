# Tabelas do raw com esquema nosso, tudo texto (quem tipa é a Bronze). Deixar o crawler deduzir dá bigint
# e o cnpj_basico perde os zeros à esquerda; nem o classificador com CustomDatatypes = STRING evitou isso.
resource "aws_glue_catalog_table" "raw" {
  for_each      = jsondecode(file("${path.module}/colunas_raw.json"))
  name          = each.key
  database_name = aws_glue_catalog_database.camada["raw"].name
  table_type    = "EXTERNAL_TABLE"
  # compressionType e typeOfData iguais aos que o crawler detecta: se diferirem, ele não mexe na tabela.
  parameters = {
    classification           = "csv"
    "skip.header.line.count" = "1"
    compressionType          = "none"
    typeOfData               = "file"
  }

  partition_keys {
    name = "ano_mes"
    type = "string"
  }

  # shortcut: só a amostra é catalogada (os jobs leem o S3 direto); apontar para a raiz se o Athena precisar da base completa.
  storage_descriptor {
    location      = "s3://${aws_s3_bucket.camada["raw"].bucket}/sample/${each.key}/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"
    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.OpenCSVSerde"
      parameters            = { separatorChar = ";", quoteChar = "\"" }
    }
    dynamic "columns" {
      for_each = each.value
      content {
        name = columns.value
        type = "string"
      }
    }
  }

  # Depois de criada, a tabela é do crawler (partições, colunas novas, parâmetros dele).
  lifecycle {
    ignore_changes = [parameters, storage_descriptor]
  }
}

resource "aws_glue_crawler" "raw" {
  name          = "${var.prefixo}-raw"
  role          = aws_iam_role.glue_pipeline.arn
  database_name = aws_glue_catalog_database.camada["raw"].name

  # O crawler só mantém as tabelas acima: acrescenta partições e colunas novas, sem mudar os tipos.
  catalog_target {
    database_name = aws_glue_catalog_database.camada["raw"].name
    tables        = [for t in aws_glue_catalog_table.raw : t.name]
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
  })
}
