variable "aws_region" {
  type        = string
  description = "Target AWS Region for production deployment"
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Project name prefix"
  default     = "armserve"
}

variable "environment" {
  type        = string
  description = "Deployment environment name"
  default     = "production"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for production VPC"
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  type        = list(string)
  description = "Multi-AZ availability zones for high availability"
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "graviton_instance_type" {
  type        = string
  description = "Production AWS Graviton3 (ARM64) instance type"
  default     = "c7g.2xlarge"
}

variable "alert_email" {
  type        = string
  description = "Production ops notification email for SNS alerts"
  default     = "ops-alerts@armserve.com"
}

variable "tags" {
  type        = map(string)
  description = "Production default resource tags"
  default = {
    Project     = "ArmServe"
    Environment = "production"
    ManagedBy   = "Terraform"
    Repository  = "ArmInferX"
  }
}
