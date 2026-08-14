variable "project_name" {
  type        = string
  description = "Project name prefix"
  default     = "armserve"
}

variable "environment" {
  type        = string
  description = "Target deployment environment (dev, staging, production)"
}

variable "force_destroy" {
  type        = bool
  description = "Whether all objects should be deleted from bucket so bucket can be destroyed without error"
  default     = false
}

variable "expiration_days" {
  type        = number
  description = "Number of days after which non-current object versions expire"
  default     = 90
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to storage resources"
  default     = {}
}
