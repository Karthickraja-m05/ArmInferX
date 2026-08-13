# ArmServe Infrastructure & Cloud Provisioning

This directory contains Terraform modules, AWS Graviton architecture definitions, and Docker container manifests for ArmServe deployment on AWS ARM64 `c7g.2xlarge` Neoverse V1 compute nodes.

## Directory Layout

- `modules/aws/` - Terraform IaC definitions for AWS Graviton VPC, Subnets, Security Groups, IAM IRSA roles, and `c7g.2xlarge` EC2 instances.
- `environments/` - Environment configuration variables (`dev`, `staging`, `prod`).

For complete Terraform infrastructure deployment instructions, see [`docs/cloud-architecture.md`](../docs/cloud-architecture.md) and [`docs/deployment-architecture.md`](../docs/deployment-architecture.md).
