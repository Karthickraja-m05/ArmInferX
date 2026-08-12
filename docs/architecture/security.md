# ArmServe — Security Model

---

## 1. Authentication & Authorization

### User & Client Authentication
- **REST API**: JWT-based access tokens (OAuth 2.0 Password Flow / OIDC) + Refresh Tokens.
- **CLI & Automation**: Hashed API Keys (`arm_live_...`) with scoped permissions.
- **Frontend**: Session tokens issued via secure, HttpOnly, SameSite cookies.

### Inter-Service Communication
- **API ↔ Celery Workers**: Shared secrets / TLS encrypted Redis connection.
- **Controller ↔ Target Nodes**: mTLS for gRPC communication, or SSH with dedicated ephemeral key pairs.
- **Cluster Internal**: Kubernetes NetworkPolicies restricting pod-to-pod communication.

---

## 2. Network Isolation & Microsegmentation

```
┌─────────────────────────────────────────────────────────────┐
│ DMZ / Public Subnet                                          │
│   - Application Load Balancer (WAF Enabled)                 │
│   - CloudFront CDN                                          │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS / Port 443
┌──────────────────────────────▼──────────────────────────────┐
│ Private App Subnet                                          │
│   - Backend API Pods                                        │
│   - Celery Worker & Controller Pods                         │
│   - Database Instances (PostgreSQL / TimescaleDB / Redis)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ Private Endpoint / Ephemeral VPC
┌──────────────────────────────▼──────────────────────────────┐
│ Isolated Execution Subnet                                   │
│   - Arm64 Ephemeral Benchmark Instances                     │
│   - Production Inference Pods                               │
│   - Isolated container execution                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Secrets & Credentials Management

1. **No Credentials in DB**: Cloud credentials (AWS Access Keys, Azure Service Principals) are fetched at runtime from AWS Secrets Manager / HashiCorp Vault or attached via IAM Roles for Service Accounts (IRSA).
2. **Ephemeral SSH Keys**: SSH access to benchmark instances uses single-use key pairs generated per trial and destroyed upon completion.
3. **Encryption at Rest**:
   - PostgreSQL / TimescaleDB encrypted using AES-256 (KMS).
   - S3 buckets enforced with server-side encryption (SSE-KMS).

---

## 4. Workload Isolation & Threat Prevention

- **Container Hardening**: Inference & Benchmark containers run as unprivileged users (`uid 10001`), with read-only root filesystems and dropped capabilities (`CAP_DROP_ALL`).
- **Resource Constraints**: Strict memory (`cgroup`) limits per benchmark run to prevent Out-Of-Memory (OOM) cascading failures to node hosts.
- **Network Egress Filtering**: Ephemeral benchmark nodes have restricted outbound internet access (whitelisted to model repositories like HuggingFace and internal artifact S3 storage).
