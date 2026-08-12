# Remote State Storage Backend Configuration for Dev Environment
# To initialize remote state, create S3 bucket and DynamoDB table first, then enable backend block:
#
# terraform {
#   backend "s3" {
#     bucket         = "armserve-terraform-state-dev"
#     key            = "dev/terraform.tfstate"
#     region         = "us-east-1"
#     dynamodb_table = "armserve-terraform-locks-dev"
#     encrypt        = true
#   }
# }

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}
