# ArmServe AWS ARM64 (AWS Graviton) Infrastructure-as-Code (IaC)

This directory contains the complete **Terraform 1.6+** Infrastructure-as-Code foundation for ArmServe on **AWS Graviton (ARM64)** architecture.

## Overview

The infrastructure design is fully modularized, parameter-driven, credentials-free, and structured for strict environment separation across `dev`, `staging`, and `production`.

### Target Cloud & Compute
- **Cloud Provider**: AWS (`hashicorp/aws ~> 5.0`)
- **Target Compute Architecture**: AWS Graviton 2/3 (ARM64) (`c7g`, `c6g`, `t4g`)
- **OS Base Image**: Canonical Ubuntu 22.04 LTS ARM64 Server (`architecture = "arm64"`)

---

## Directory Structure

```
infra/
├── README.md                          # Comprehensive IaC architecture & deployment guide
├── modules/
│   ├── networking/                    # Multi-AZ VPC, Public/Private Subnets, IGW, NAT Gateways
│   ├── security_groups/                # ALB, Backend API, Graviton Compute, & DB Security Groups
│   ├── iam/                            # IAM Roles, Instance Profiles, EKS/EC2 Policies, Secrets access
│   ├── compute_graviton/               # Graviton ARM64 Launch Templates & Auto Scaling Groups
│   ├── storage/                        # S3 Model Bucket with SSE-KMS Encryption & Lifecycle Rules
│   ├── secrets/                        # AWS Secrets Manager & SSM Parameter Store Integration
│   ├── monitoring/                     # CloudWatch Log Groups, Metric Alarms, SNS Alert Topics
│   └── deployment/                     # ECR Repositories (Backend/Frontend) & Application Load Balancer
└── environments/
    ├── dev/                            # Development environment root module & tfvars
    ├── staging/                        # Staging environment root module & tfvars
    └── production/                     # Production environment root module & tfvars
```

---

## Key Design Principles

1. **Explicit Typing & Parameterization**:
   - Every module variable includes explicit types (`string`, `list(string)`, `number`, `bool`, `map(string)`), descriptions, and defaults.

2. **Zero Credentials in Source Code**:
   - Authentication relies exclusively on environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`) or IAM instance roles. No credentials or keys are hardcoded.

3. **No Hardcoded Account IDs**:
   - Dynamic identity resolution using `data "aws_caller_identity" "current" {}` and `data "aws_region" "current" {}`.

4. **Dynamic Secrets Management**:
   - High-entropy random passwords (`random_password`) automatically generate database credentials and JWT secret keys stored securely in AWS Secrets Manager (`aws_secretsmanager_secret`).

5. **Resource Naming & Tagging Standard**:
   - Resources follow `${var.project_name}-${var.environment}-${var.resource_name}` (e.g. `armserve-prod-vpc`).
   - Standardized tags applied automatically:
     - `Project`: `"ArmServe"`
     - `Environment`: `"dev" | "staging" | "production"`
     - `ManagedBy`: `"Terraform"`
     - `Architecture`: `"ARM64"`
     - `Repository`: `"ArmInferX"`

6. **Environment Separation**:
   - **`dev`**: Single NAT gateway, `t4g.medium` Graviton instances, force-destroy S3 bucket, 14-day log retention.
   - **`staging`**: Multi-AZ NAT gateways, `c6g.xlarge` Graviton instances, 30-day log retention.
   - **`production`**: Multi-AZ NAT gateways, `c7g.2xlarge` Graviton3 instances, 90-day log retention, prevent destroy rules.

---

## Deployment & Usage Instructions

### Prerequisites
- **Terraform**: `>= 1.6.0`
- **AWS CLI**: `v2.x` configured with deployment credentials.

### Deploying an Environment (e.g., `dev`)

```bash
# 1. Navigate to target environment directory
cd infra/environments/dev

# 2. Initialize Terraform modules & providers
terraform init

# 3. Create active terraform.tfvars configuration
cp terraform.tfvars.example terraform.tfvars

# 4. Perform dry-run plan validation
terraform plan -out=tfplan

# 5. Apply infrastructure changes
terraform apply tfplan
```

### Outputs Exposed
After running `terraform apply`, key resources are available as root outputs:
- `aws_account_id` / `aws_region`
- `vpc_id`, `public_subnet_ids`, `private_subnet_ids`
- `s3_models_bucket`
- `backend_ecr_repository_url` / `frontend_ecr_repository_url`
- `alb_dns_name`
- `graviton_autoscaling_group_name`
- `db_secret_arn`
