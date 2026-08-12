# ArmServe Networking Layer & Security Group Rules Specification

This document details the VPC network topology, subnet routing, IAM policies, and comprehensive Ingress/Egress Security Group microsegmentation matrix for ArmServe.

---

## 1. Network Topology Overview

```text
VPC CIDR: 10.0.0.0/16
├── Public Subnets (3 AZs: us-east-1a, us-east-1b, us-east-1c)
│   ├── Internet Gateway (IGW) attached for inbound/outbound internet routing
│   └── NAT Gateways provisioned for private subnet outbound traffic
├── Private Application Subnets (3 AZs: 10.0.10.0/24, 10.0.11.0/24, 10.0.12.0/24)
│   └── Routed via NAT Gateway for outbound package/model fetching; no inbound internet routing
└── Isolated Database Subnets (3 AZs: 10.0.20.0/24, 10.0.21.0/24, 10.0.22.0/24)
    └── Isolated route table with NO internet gateway or NAT routes
```

---

## 2. Comprehensive Security Group Rules Matrix

### A. Application Load Balancer Security Group (`alb-sg`)

| Rule Type | Protocol | Port Range | Source / Destination | Description | Justification |
|---|---|---|---|---|---|
| **Ingress** | TCP | `80` | `0.0.0.0/0` | HTTP Public Access | Public web traffic entry (redirects to HTTPS) |
| **Ingress** | TCP | `443` | `0.0.0.0/0` | HTTPS Public Access | TLS encrypted public web traffic entry |
| **Egress** | TCP | `8000` | `backend-api-sg` (SG) | Backend API Target | Directs load-balanced requests to private API containers |

---

### B. Backend API Service Security Group (`backend-api-sg`)

| Rule Type | Protocol | Port Range | Source / Destination | Description | Justification |
|---|---|---|---|---|---|
| **Ingress** | TCP | `8000` | `alb-sg` (SG) | ALB Ingress Only | Restricts API access strictly to requests from ALB |
| **Egress** | TCP | `443` | `0.0.0.0/0` | Outbound HTTPS | Package downloads, S3 model artifacts, Secrets Manager |
| **Egress** | TCP | `5432` | `database-sg` (SG) | PostgreSQL DB Egress | Database operations and queries |
| **Egress** | TCP | `6379` | `database-sg` (SG) | Redis Cache Egress | Task queue and caching |

---

### C. AWS Graviton ARM64 Compute Nodes Security Group (`graviton-compute-sg`)

| Rule Type | Protocol | Port Range | Source / Destination | Description | Justification |
|---|---|---|---|---|---|
| **Ingress** | TCP | `1024-65535` | `backend-api-sg` (SG) | Internal API Dispatch | Internal RPC / dispatch communication from Backend API |
| **Egress** | TCP | `443` | `0.0.0.0/0` | Outbound HTTPS | HuggingFace, PyTorch/ONNX model downloads, S3 storage |
| **Egress** | TCP | `5432` | `database-sg` (SG) | PostgreSQL Access | Storing trial optimization benchmark metrics |

---

### D. Isolated Database Security Group (`database-sg`)

| Rule Type | Protocol | Port Range | Source / Destination | Description | Justification |
|---|---|---|---|---|---|
| **Ingress** | TCP | `5432` | `backend-api-sg` (SG) | API Database Access | Allow API backend queries to PostgreSQL |
| **Ingress** | TCP | `5432` | `graviton-compute-sg` | Compute Database Access | Allow Graviton benchmark workers to save trial metrics |
| **Ingress** | TCP | `6379` | `backend-api-sg` (SG) | API Redis Access | Allow API backend access to Redis task queue |
| **Egress** | — | — | Denied (`None`) | No Outbound Access | Strict data exfiltration prevention |

---

## 3. IAM Roles & SSM Session Manager Policies

- **`AmazonSSMManagedInstanceCore`**: Attached to instance profile. Allows shell access via AWS Systems Manager without opening SSH port 22 to any IP range.
- **`CloudWatchAgentServerPolicy`**: Allows streaming system metrics (CPU, Memory, Disk) and application logs to AWS CloudWatch.
- **`ArmServeS3ModelAccessPolicy`**:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
        "Resource": [
          "arn:aws:s3:::armserve-models-*",
          "arn:aws:s3:::armserve-models-*/*"
        ]
      }
    ]
  }
  ```

---

## 4. Hardware System Information Template (`docs/system-information.md`)

When a live AWS Graviton instance is provisioned via `terraform apply` using valid AWS credentials, the system metadata is collected via AWS SSM:

```bash
# Verification Command (Must output 'aarch64'):
uname -m
```

| Metric | Target Specification |
|---|---|
| **CPU Architecture** | `aarch64` (ARM64 AWS Graviton3 Neoverse V1) |
| **CPU Model** | `AWS Graviton3` / `Neoverse-V1` |
| **vCPU Cores** | `4` (`c7g.xlarge`) |
| **Memory** | `8 GB` DDR5 |
| **Disk** | `100 GB` gp3 EBS (Encrypted) |
| **Operating System** | `Ubuntu 22.04.4 LTS` (Jammy Jellyfish) |
| **Kernel Version** | `Linux 6.2.0-aws` |
