variable "project_name" {
  type        = string
  description = "Project name prefix used for resource naming"
  default     = "armserve"
}

variable "environment" {
  type        = string
  description = "Target deployment environment (dev, staging, production)"
}

variable "vpc_id" {
  type        = string
  description = "ID of the target VPC"
}

variable "api_port" {
  type        = number
  description = "Port number on which backend API listens"
  default     = 8000
}

variable "db_port" {
  type        = number
  description = "Port number on which PostgreSQL database listens"
  default     = 5432
}

variable "tags" {
  type        = map(string)
  description = "Resource tags to be applied to all security groups"
  default     = {}
}
