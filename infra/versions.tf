terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
  # Estado local (terraform.tfstate), fora do Git. Estado no S3 fica como melhoria futura.
}

provider "aws" {
  region = var.regiao
  default_tags {
    tags = { projeto = "good-lion" }
  }
}

data "aws_caller_identity" "atual" {}
