output "aws_account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "vpc_id" {
  description = "Staging VPC ID"
  value       = module.networking.vpc_id
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS Name"
  value       = module.deployment.alb_dns_name
}

output "backend_ecr_repository_url" {
  description = "Backend ECR Repository URL"
  value       = module.deployment.backend_ecr_repository_url
}

output "s3_models_bucket" {
  description = "S3 Models Bucket Name"
  value       = module.storage.bucket_id
}

output "graviton_autoscaling_group_name" {
  description = "Graviton Auto Scaling Group Name"
  value       = module.compute_graviton.autoscaling_group_name
}
