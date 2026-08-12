variable "project_name" {
  type        = string
  description = "Project name prefix"
  default     = "armserve"
}

variable "environment" {
  type        = string
  description = "Target deployment environment (dev, staging, production)"
}

variable "autoscaling_group_name" {
  type        = string
  description = "Name of the Graviton Auto Scaling Group to monitor"
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days (e.g. 14 for dev, 90 for prod)"
  default     = 14
}

variable "alert_email" {
  type        = string
  description = "Optional email address to receive SNS alert notifications"
  default     = null
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to monitoring resources"
  default     = {}
}
