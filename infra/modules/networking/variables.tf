variable "project_name" {
  type        = string
  description = "Project name prefix used for resource naming (e.g. armserve)"
  default     = "armserve"
}

variable "environment" {
  type        = string
  description = "Target deployment environment (dev, staging, production)"
}

variable "vpc_cidr" {
  type        = string
  description = "Primary CIDR block for the VPC"
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  type        = list(string)
  description = "List of AWS Availability Zones for multi-AZ subnet placement"
  default     = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_cidrs" {
  type        = list(string)
  description = "CIDR blocks for public subnets"
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  type        = list(string)
  description = "CIDR blocks for private application subnets"
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
}

variable "database_subnet_cidrs" {
  type        = list(string)
  description = "CIDR blocks for isolated database subnets"
  default     = ["10.0.100.0/24", "10.0.200.0/24"]
}

variable "enable_single_nat_gateway" {
  type        = bool
  description = "If true, provision a single NAT gateway to save costs in non-production environments"
  default     = true
}

variable "tags" {
  type        = map(string)
  description = "Resource tags to be applied to all networking resources"
  default     = {}
}
