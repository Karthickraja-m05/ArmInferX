output "aws_account_id" {
  description = "Production AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "vpc_id" {
  description = "Production VPC ID"
  value       = module.networking.vpc_id
}

output "alb_dns_name" {
  description = "Production Load Balancer DNS Name"
  value       = module.deployment.alb_dns_name
}

output "backend_ecr_repository_url" {
  description = "Production Backend ECR Repository URL"
  value       = module.deployment.backend_ecr_repository_url
}

output "frontend_ecr_repository_url" {
  description = "Production Frontend ECR Repository URL"
  value       = module.deployment.frontend_ecr_repository_url
}

output "s3_models_bucket" {
  description = "Production S3 Models Bucket Name"
  value       = module.storage.bucket_id
}

output "graviton_autoscaling_group_name" {
  description = "Production Graviton Auto Scaling Group Name"
  value       = module.compute_graviton.autoscaling_group_name
}

output "db_secret_arn" {
  description = "Secrets Manager ARN for Production DB Credentials"
  value       = module.secrets.db_secret_arn
}
