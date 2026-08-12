variable "project_name" {
  type        = string
  description = "Project name prefix"
  default     = "armserve"
}

variable "environment" {
  type        = string
  description = "Target deployment environment (dev, staging, production)"
}

variable "instance_type" {
  type        = string
  description = "AWS Graviton (ARM64) instance type (e.g. c7g.xlarge, c6g.xlarge, t4g.medium)"
  default     = "c7g.xlarge"
}

variable "vpc_id" {
  type        = string
  description = "Target VPC ID"
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for Auto Scaling Group placement"
}

variable "security_group_ids" {
  type        = list(string)
  description = "Security Group IDs attached to Graviton instances"
}

variable "instance_profile_name" {
  type        = string
  description = "IAM Instance Profile name attached to Graviton instances"
}

variable "min_size" {
  type        = number
  description = "Minimum number of instances in Auto Scaling Group"
  default     = 1
}

variable "max_size" {
  type        = number
  description = "Maximum number of instances in Auto Scaling Group"
  default     = 5
}

variable "desired_capacity" {
  type        = number
  description = "Desired number of instances in Auto Scaling Group"
  default     = 2
}

variable "root_volume_size" {
  type        = number
  description = "Root EBS volume size in GB"
  default     = 100
}

variable "user_data_extra" {
  type        = string
  description = "Additional shell script commands to execute during EC2 initialization"
  default     = ""
}

variable "tags" {
  type        = map(string)
  description = "Resource tags applied to compute resources"
  default     = {}
}
