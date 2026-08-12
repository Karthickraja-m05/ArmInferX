output "aws_account_id" {
  description = "Dynamically detected AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "Target AWS Region"
  value       = data.aws_region.current.name
}

output "vpc_id" {
  description = "Dev VPC ID"
  value       = module.networking.vpc_id
}

output "public_subnet_ids" {
  description = "Public Subnet IDs"
  value       = module.networking.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private Subnet IDs"
  value       = module.networking.private_subnet_ids
}

output "s3_models_bucket" {
  description = "S3 Model Artifacts Bucket Name"
  value       = module.storage.bucket_id
}

output "backend_ecr_repository_url" {
  description = "Backend Docker Image ECR Repository URL"
  value       = module.deployment.backend_ecr_repository_url
}

output "frontend_ecr_repository_url" {
  description = "Frontend Web UI Docker Image ECR Repository URL"
  value       = module.deployment.frontend_ecr_repository_url
}

output "alb_dns_name" {
  description = "Public Application Load Balancer DNS Name"
  value       = module.deployment.alb_dns_name
}

output "graviton_autoscaling_group_name" {
  description = "Graviton ARM64 Auto Scaling Group Name"
  value       = module.compute_graviton.autoscaling_group_name
}

output "db_secret_arn" {
  description = "Secrets Manager ARN for DB Credentials"
  value       = module.secrets.db_secret_arn
}
