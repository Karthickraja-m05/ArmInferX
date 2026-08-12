provider "aws" {
  region = var.aws_region

  default_tags {
    tags = var.tags
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# 1. Networking Module (Multi-AZ High Availability with 3 NAT Gateways)
module "networking" {
  source = "../../modules/networking"

  project_name              = var.project_name
  environment               = var.environment
  vpc_cidr                  = var.vpc_cidr
  availability_zones        = var.availability_zones
  public_subnet_cidrs       = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnet_cidrs      = ["10.0.10.0/24", "10.0.20.0/24", "10.0.30.0/24"]
  database_subnet_cidrs     = ["10.0.100.0/24", "10.0.200.0/24", "10.0.300.0/24"]
  enable_single_nat_gateway = false
  tags                      = var.tags
}

# 2. Security Groups Module
module "security_groups" {
  source = "../../modules/security_groups"

  project_name = var.project_name
  environment  = var.environment
  vpc_id       = module.networking.vpc_id
  api_port     = 8000
  db_port      = 5432
  tags         = var.tags
}

# 3. Storage Module (S3 Bucket with strict lifecycle retention and prevent destroy)
module "storage" {
  source = "../../modules/storage"

  project_name    = var.project_name
  environment     = var.environment
  force_destroy   = false
  expiration_days = 90
  tags            = var.tags
}

# 4. IAM Module
module "iam" {
  source = "../../modules/iam"

  project_name        = var.project_name
  environment         = var.environment
  s3_model_bucket_arn = module.storage.bucket_arn
  secrets_arn_prefix  = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/${var.environment}/*"
  tags                = var.tags
}

# 5. Secrets Module
module "secrets" {
  source = "../../modules/secrets"

  project_name = var.project_name
  environment  = var.environment
  kms_key_arn  = module.storage.kms_key_arn
  tags         = var.tags
}

# 6. Graviton ARM64 Compute Module (High capacity c7g.2xlarge cluster)
module "compute_graviton" {
  source = "../../modules/compute_graviton"

  project_name          = var.project_name
  environment           = var.environment
  instance_type         = var.graviton_instance_type
  vpc_id                = module.networking.vpc_id
  subnet_ids            = module.networking.private_subnet_ids
  security_group_ids    = [module.security_groups.graviton_compute_security_group_id]
  instance_profile_name = module.iam.graviton_instance_profile_name
  min_size              = 2
  max_size              = 10
  desired_capacity      = 4
  root_volume_size      = 200
  tags                  = var.tags
}

# 7. Monitoring Module (90 day log retention and alert subscription)
module "monitoring" {
  source = "../../modules/monitoring"

  project_name           = var.project_name
  environment            = var.environment
  autoscaling_group_name = module.compute_graviton.autoscaling_group_name
  log_retention_days     = 90
  alert_email            = var.alert_email
  tags                   = var.tags
}

# 8. Deployment Module
module "deployment" {
  source = "../../modules/deployment"

  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = module.networking.vpc_id
  public_subnet_ids     = module.networking.public_subnet_ids
  alb_security_group_id = module.security_groups.alb_security_group_id
  backend_port          = 8000
  health_check_path     = "/api/v1/system/health"
  tags                  = var.tags
}
