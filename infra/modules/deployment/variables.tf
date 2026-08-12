variable "project_name" {
  type        = string
  description = "Project name prefix"
  default     = "armserve"
}

variable "environment" {
  type        = string
  description = "Target deployment environment (dev, staging, production)"
}

variable "vpc_id" {
  type        = string
  description = "Target VPC ID"
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "Public subnet IDs for ALB placement"
}

variable "alb_security_group_id" {
  type        = string
  description = "Security group ID attached to ALB"
}

variable "backend_port" {
  type        = number
  description = "Port number on which target group forwards to backend API"
  default     = 8000
}

variable "health_check_path" {
  type        = string
  description = "HTTP path for ALB health check probe"
  default     = "/health"
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to deployment resources"
  default     = {}
}
