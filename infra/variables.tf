variable "regiao" {
  type    = string
  default = "us-east-1"
}

variable "email_alertas" {
  description = "Recebe os alertas do Budgets (e, no ticket 06, as falhas dos jobs)"
  type        = string
}

variable "prefixo" {
  description = "Prefixo dos buckets e recursos"
  type        = string
  default     = "goodlion"
}
