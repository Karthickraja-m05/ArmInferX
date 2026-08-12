variable "aws_region" {
  type        = string
  description = "Target AWS Region for deployment"
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Project name prefix used for resource naming"
  default     = "armserve"
}

variable "environment" {
  type        = string
  description = "Deployment environment name"
  default     = "dev"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for dev VPC"
  default     = "10.10.0.0/16"
}

variable "availability_zones" {
  type        = list(string)
  description = "Availability zones for subnet placement"
  default     = ["us-east-1a", "us-east-1b"]
}

variable "graviton_instance_type" {
  type        = string
  description = "AWS Graviton (ARM64) instance type for dev environment"
  default     = "t4g.medium"
}

variable "alert_email" {
  type        = string
  description = "Optional email address for SNS alert notifications"
  default     = null
}

variable "tags" {
  type        = map(string)
  description = "Default resource tags"
  default = {
    Project     = "ArmServe"
    Environment = "dev"
    ManagedBy   = "Terraform"
    Repository  = "ArmInferX"
  }
}
