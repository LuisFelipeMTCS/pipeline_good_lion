# shortcut: um perfil só para todos os jobs, com acesso aos 5 buckets; separar por etapa se a rubrica cobrar.
resource "aws_iam_role" "glue_pipeline" {
  name = "glue-pipeline"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "glue.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

# Catalog, logs e métricas do Glue.
resource "aws_iam_role_policy_attachment" "glue_servico" {
  role       = aws_iam_role.glue_pipeline.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_buckets" {
  role = aws_iam_role.glue_pipeline.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = "s3:ListBucket", Resource = [for b in aws_s3_bucket.camada : b.arn] },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = [for b in aws_s3_bucket.camada : "${b.arn}/*"]
      },
    ]
  })
}

# Usado pelo make dashboard-load: só lê a Gold. Assumido a partir da sua conta (perfil `analista` no ~/.aws/config).
resource "aws_iam_role" "analista" {
  name = "analista"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.atual.account_id}:root" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "analista_gold" {
  role = aws_iam_role.analista.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = "s3:ListBucket", Resource = aws_s3_bucket.camada["gold"].arn },
      { Effect = "Allow", Action = "s3:GetObject", Resource = "${aws_s3_bucket.camada["gold"].arn}/*" },
    ]
  })
}

output "perfil_analista" {
  value = aws_iam_role.analista.arn
}
