output "db_secret_arn" {
  description = "ARN of the AWS Secrets Manager entry for DB credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

output "db_secret_name" {
  description = "Name of the AWS Secrets Manager entry for DB credentials"
  value       = aws_secretsmanager_secret.db_credentials.name
}

output "auth_secret_arn" {
  description = "ARN of the AWS Secrets Manager entry for JWT auth secret key"
  value       = aws_secretsmanager_secret.auth_secret.arn
}

output "ssm_app_env_parameter_name" {
  description = "SSM Parameter Store name for app env"
  value       = aws_ssm_parameter.app_env.name
}
