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

# Lê o JSON do IBGE no raw, grava o resultado limpo na silver, lê a silver_estabelecimentos para o perfil e
# grava o perfil no artifacts.
resource "aws_iam_role_policy" "databrew_buckets" {
  role = aws_iam_role.databrew.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = [for c in ["raw", "silver", "artifacts"] : aws_s3_bucket.camada[c].arn]
      },
      { Effect = "Allow", Action = "s3:GetObject", Resource = "${aws_s3_bucket.camada["raw"].arn}/ibge_municipios/*" },
      { Effect = "Allow", Action = "s3:GetObject", Resource = "${aws_s3_bucket.camada["silver"].arn}/sample/estabelecimentos/*" },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = "${aws_s3_bucket.camada["artifacts"].arn}/databrew/*"
      },
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
      # O CloudFormation cria a receita sem publicar, e job com dataset + receita só aceita versão publicada.
      # Job com projeto usa a receita do projeto como está. Projeto parado não cobra (sessão só se aberto no console).
      ProjetoIbge = {
        Type      = "AWS::DataBrew::Project"
        DependsOn = ["DatasetIbge", "ReceitaIbge"]
        Properties = {
          Name        = "${var.prefixo}-limpeza-ibge"
          DatasetName = "${var.prefixo}-ibge-municipios"
          RecipeName  = "${var.prefixo}-limpeza-ibge"
          RoleArn     = aws_iam_role.databrew.arn
        }
      }
      JobLimpezaIbge = {
        Type      = "AWS::DataBrew::Job"
        DependsOn = ["ProjetoIbge"]
        Properties = {
          Name        = local.job_limpeza_ibge
          Type        = "RECIPE"
          RoleArn     = aws_iam_role.databrew.arn
          ProjectName = "${var.prefixo}-limpeza-ibge"
          MaxCapacity = 2 # mínimo do DataBrew
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
      # Perfilamento da silver_estabelecimentos (ticket 15). O DataBrew não lê tabela Delta, então o dataset é
      # o Parquet da pasta. Até o VACUUM (7 dias) ela também tem arquivos já fora do Delta: o perfil serve para
      # distribuições e nulos, não para contar linhas (isso é do Athena).
      DatasetSilverEstabelecimentos = {
        Type = "AWS::DataBrew::Dataset"
        Properties = {
          Name   = "${var.prefixo}-silver-estabelecimentos"
          Format = "PARQUET"
          Input = { S3InputDefinition = {
            Bucket = aws_s3_bucket.camada["silver"].bucket
            Key    = "sample/estabelecimentos/"
          } }
        }
      }
      JobPerfil = {
        Type      = "AWS::DataBrew::Job"
        DependsOn = ["DatasetSilverEstabelecimentos"]
        Properties = {
          Name           = "${var.prefixo}-perfil-silver-estabelecimentos"
          Type           = "PROFILE"
          RoleArn        = aws_iam_role.databrew.arn
          DatasetName    = "${var.prefixo}-silver-estabelecimentos"
          MaxCapacity    = 2 # mínimo do DataBrew
          MaxRetries     = 0
          Timeout        = 30 # minutos
          JobSample      = { Mode = "CUSTOM_ROWS", Size = 20000 }
          OutputLocation = { Bucket = aws_s3_bucket.camada["artifacts"].bucket, Key = "databrew/perfil/" }
        }
      }
      # Agenda própria, fora do Workflow (o perfil é informativo): dia 25, depois do gatilho mensal do dia 20.
      AgendaPerfil = {
        Type      = "AWS::DataBrew::Schedule"
        DependsOn = ["JobPerfil"]
        Properties = {
          Name           = "${var.prefixo}-perfil-mensal"
          CronExpression = "cron(0 12 25 * ? *)"
          JobNames       = ["${var.prefixo}-perfil-silver-estabelecimentos"]
        }
      }
    }
  })
}
