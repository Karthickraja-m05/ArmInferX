variable "project_name" {
  type        = string
  description = "Project name prefix"
  default     = "armserve"
}

variable "environment" {
  type        = string
  description = "Target deployment environment (dev, staging, production)"
}

variable "kms_key_arn" {
  type        = string
  description = "Optional KMS key ARN for encrypting secrets in Secrets Manager"
  default     = null
}

variable "db_username" {
  type        = string
  description = "Master database username"
  default     = "armserve_admin"
}

variable "tags" {
  type        = map(string)
  description = "Resource tags applied to secret resources"
  default     = {}
}
