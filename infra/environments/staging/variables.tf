variable "aws_region" {
  type        = string
  description = "Target AWS Region for deployment"
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
  default     = "staging"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for staging VPC"
  default     = "10.20.0.0/16"
}

variable "availability_zones" {
  type        = list(string)
  description = "Availability zones for subnet placement"
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "graviton_instance_type" {
  type        = string
  description = "AWS Graviton (ARM64) instance type for staging"
  default     = "c6g.xlarge"
}

variable "alert_email" {
  type        = string
  description = "Email address for SNS alert notifications"
  default     = null
}

variable "tags" {
  type        = map(string)
  description = "Default resource tags"
  default = {
    Project     = "ArmServe"
    Environment = "staging"
    ManagedBy   = "Terraform"
    Repository  = "ArmInferX"
  }
}
