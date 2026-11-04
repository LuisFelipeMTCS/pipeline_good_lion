# DataBrew: receita de limpeza do IBGE (PRD, 5.10). O provider aws não tem recursos de DataBrew (e o awscc
# não tem receita), então dataset, receita e job vão numa pilha do CloudFormation.
locals {
  job_limpeza_ibge = "${var.prefixo}-limpeza-ibge"
}

resource "aws_iam_role" "databrew" {
  name = "databrew-pipeline"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "databrew.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "databrew_servico" {
  role       = aws_iam_role.databrew.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueDataBrewServiceRole"
}

# Lê o JSON do IBGE no raw e grava o resultado limpo na silver.
resource "aws_iam_role_policy" "databrew_buckets" {
  role = aws_iam_role.databrew.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = "s3:ListBucket", Resource = [aws_s3_bucket.camada["raw"].arn, aws_s3_bucket.camada["silver"].arn] },
      { Effect = "Allow", Action = "s3:GetObject", Resource = "${aws_s3_bucket.camada["raw"].arn}/ibge_municipios/*" },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = "${aws_s3_bucket.camada["silver"].arn}/ibge_municipios/*"
      },
    ]
  })
}

resource "aws_cloudformation_stack" "databrew" {
  name = "${var.prefixo}-databrew"
  template_body = jsonencode({
    Resources = {
      # Só o arquivo mais recente de raw/ibge_municipios/ano_mes=*/ (a lista do IBGE é a mesma para todos os meses).
      DatasetIbge = {
        Type = "AWS::DataBrew::Dataset"
        Properties = {
          Name          = "${var.prefixo}-ibge-municipios"
          Format        = "JSON"
          FormatOptions = { Json = { MultiLine = true } }
          Input = { S3InputDefinition = {
            Bucket = aws_s3_bucket.camada["raw"].bucket
            Key    = "ibge_municipios/ano_mes={ano_mes}/municipios.json"
          } }
          PathOptions = {
            Parameters = [{
              PathParameterName = "ano_mes"
              DatasetParameter  = { Name = "ano_mes", Type = "String", CreateColumn = false }
            }]
            FilesLimit = { MaxFiles = 1, OrderedBy = "LAST_MODIFIED_DATE", Order = "DESCENDING" }
          }
        }
      }
      ReceitaIbge = {
        Type = "AWS::DataBrew::Recipe"
        Properties = {
          Name  = "${var.prefixo}-limpeza-ibge"
          Steps = jsondecode(file("${path.module}/databrew_receita_ibge.json"))
        }
      }
      JobLimpezaIbge = {
        Type      = "AWS::DataBrew::Job"
        DependsOn = ["DatasetIbge", "ReceitaIbge"]
        Properties = {
          Name        = local.job_limpeza_ibge
          Type        = "RECIPE"
          RoleArn     = aws_iam_role.databrew.arn
          DatasetName = "${var.prefixo}-ibge-municipios"
          Recipe      = { Name = "${var.prefixo}-limpeza-ibge", Version = "LATEST_WORKING" }
          MaxCapacity = 1
          MaxRetries  = 0
          Timeout     = 15 # minutos
          Outputs = [{
            Location       = { Bucket = aws_s3_bucket.camada["silver"].bucket, Key = "ibge_municipios/" }
            Format         = "PARQUET"
            Overwrite      = true
            MaxOutputFiles = 1
          }]
        }
      }
    }
  })
}
