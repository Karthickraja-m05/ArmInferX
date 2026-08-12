variable "project_name" {
  type        = string
  description = "Project name prefix"
  default     = "armserve"
}

variable "environment" {
  type        = string
  description = "Target deployment environment"
}

variable "s3_model_bucket_arn" {
  type        = string
  description = "ARN of the S3 model storage bucket for IAM policy scope"
  default     = "*"
}

variable "secrets_arn_prefix" {
  type        = string
  description = "ARN prefix for AWS Secrets Manager access"
  default     = "*"
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to IAM resources"
  default     = {}
}
