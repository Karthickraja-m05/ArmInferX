output "backend_ecr_repository_url" {
  description = "URL of the backend Docker image ECR repository"
  value       = aws_ecr_repository.backend.repository_url
}

output "backend_ecr_repository_arn" {
  description = "ARN of the backend ECR repository"
  value       = aws_ecr_repository.backend.arn
}

output "frontend_ecr_repository_url" {
  description = "URL of the frontend Docker image ECR repository"
  value       = aws_ecr_repository.frontend.repository_url
}

output "alb_dns_name" {
  description = "Public DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.main.arn
}

output "target_group_arn" {
  description = "ARN of the backend ALB Target Group"
  value       = aws_lb_target_group.backend.arn
}
