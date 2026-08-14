# Random Secure Password Generation for Database Credentials
resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Random Secure Secret Key for JWT Authentication
resource "random_password" "auth_secret_key" {
  length  = 64
  special = false
}

# AWS Secrets Manager Entry for Database Credentials
resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${var.project_name}/${var.environment}/database"
  description = "ArmServe ${var.environment} Database Master Credentials"
  kms_key_id  = var.kms_key_arn

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-db-secret"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_password.result
    engine   = "postgres"
    port     = 5432
    dbname   = "${var.project_name}_${var.environment}"
  })
}

# AWS Secrets Manager Entry for Auth Secret Key
resource "aws_secretsmanager_secret" "auth_secret" {
  name        = "${var.project_name}/${var.environment}/auth"
  description = "ArmServe ${var.environment} JWT Signing Secret Key"
  kms_key_id  = var.kms_key_arn

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-auth-secret"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

resource "aws_secretsmanager_secret_version" "auth_secret" {
  secret_id = aws_secretsmanager_secret.auth_secret.id
  secret_string = jsonencode({
    secret_key    = random_password.auth_secret_key.result
    jwt_algorithm = "HS256"
  })
}

# SSM Parameter Store for Non-Sensitive Application Parameters
resource "aws_ssm_parameter" "app_env" {
  name        = "/${var.project_name}/${var.environment}/app/env"
  description = "Operating environment name"
  type        = "String"
  value       = var.environment

  tags = merge(
    var.tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

resource "aws_ssm_parameter" "default_runtime" {
  name        = "/${var.project_name}/${var.environment}/inference/default_runtime"
  description = "Default AI inference runtime for Arm64 platform"
  type        = "String"
  value       = "onnxruntime"

  tags = merge(
    var.tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}
