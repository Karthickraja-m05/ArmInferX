output "alb_security_group_id" {
  description = "Security Group ID of the Application Load Balancer"
  value       = aws_security_group.alb.id
}

output "backend_api_security_group_id" {
  description = "Security Group ID of the Backend API service"
  value       = aws_security_group.backend_api.id
}

output "graviton_compute_security_group_id" {
  description = "Security Group ID of the Graviton ARM64 compute nodes"
  value       = aws_security_group.graviton_compute.id
}

output "database_security_group_id" {
  description = "Security Group ID of the database layer"
  value       = aws_security_group.database.id
}
