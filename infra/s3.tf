locals {
  # Nome de bucket é único no mundo: o id da conta no fim evita colisão.
  buckets = {
    for camada in ["raw", "bronze", "silver", "gold", "artifacts"] :
    camada => "${var.prefixo}-${camada}-${data.aws_caller_identity.atual.account_id}"
  }
}

# Criptografia SSE-S3 já é obrigatória e automática em todo bucket novo da AWS.
resource "aws_s3_bucket" "camada" {
  for_each = local.buckets
  bucket   = each.value
}

resource "aws_s3_bucket_public_access_block" "camada" {
  for_each                = aws_s3_bucket.camada
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Só no raw: nos buckets Delta a exclusão automática apagaria arquivos do histórico e corromperia a tabela.
resource "aws_s3_bucket_lifecycle_configuration" "raw" {
  bucket = aws_s3_bucket.camada["raw"].id
  rule {
    id     = "expira-em-30-dias"
    status = "Enabled"
    filter {}
    expiration {
      days = 30
    }
  }
}

output "buckets" {
  value = local.buckets
}
