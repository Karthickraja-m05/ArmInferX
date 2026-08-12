# ArmServe — Configuration and Secrets Architecture

This document specifies ArmServe's production configuration design, secrets management rules, environment separation strategy, and complete variable reference.

---

## 1. Core Principles

1. **Separation of Code and Configuration**: Application logic reads configuration strictly from typed models. Zero hardcoded secrets, credentials, or URLs in code.
2. **Environment Separation**: Support for `development`, `test`, `staging`, and `production`. Environment-specific validation rules enforce security before the application boots.
3. **Secret Masking (`SecretStr`)**: Sensitive credentials (passwords, secret keys, API tokens, AWS keys) are typed as `pydantic.SecretStr`. They are automatically masked as `'**********'` in string representations, logs, traces, and exception tracebacks.
4. **Zero Cloud Secret Hardcoding**: AWS/Azure/GCP credentials must be supplied via environment variables or managed identity roles (e.g. AWS IRSA, EC2 Instance Profiles, Azure Managed Identity).
5. **Fail-Fast Startup Validation**: Missing or invalid required parameters immediately prevent backend initialization with descriptive, non-leaking error messages.

---

## 2. Environment Rules Matrix

| Requirement / Rule | `development` | `test` | `staging` | `production` |
|--------------------|---------------|--------|-----------|--------------|
| `ARMSERVE_APP__DEBUG` | `true` | `false` | `false` | **MUST be `false`** |
| `ARMSERVE_AUTH__SECRET_KEY` | Dev default allowed | Test default allowed | Custom 32+ chars | **MUST be custom (min 32 chars)** |
| `ARMSERVE_DATABASE__PASSWORD` | Dev default allowed | Test default allowed | Custom password | **MUST be non-default** |
| Log Format | Console colored | Console | JSON structlog | **JSON structlog** |

---

## 3. Configuration Variables Reference

### Application Configuration (`app`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ARMSERVE_APP__ENV` | `str` | `development` | Environment (`development`, `test`, `staging`, `production`) |
| `ARMSERVE_APP__DEBUG` | `bool` | `true` | Enable debug logs and FastAPI interactive docs |
| `ARMSERVE_APP__LOG_LEVEL` | `str` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `ARMSERVE_APP__API_HOST` | `str` | `0.0.0.0` | Server network bind address |
| `ARMSERVE_APP__API_PORT` | `int` | `8000` | Server port (1-65535) |
| `ARMSERVE_APP__STORAGE_PATH` | `str` | `./storage` | Base path for local storage artifacts |

### Database Configuration (`database`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ARMSERVE_DATABASE__HOST` | `str` | `localhost` | PostgreSQL host address |
| `ARMSERVE_DATABASE__PORT` | `int` | `5432` | PostgreSQL port |
| `ARMSERVE_DATABASE__USER` | `str` | `armserve` | Database username |
| `ARMSERVE_DATABASE__PASSWORD` | `SecretStr` | `armserve_dev_pass` | Database user password (masked) |
| `ARMSERVE_DATABASE__NAME` | `str` | `armserve_dev` | Target database name |
| `ARMSERVE_DATABASE__MAX_CONNECTIONS` | `int` | `20` | Max connection pool size |
| `ARMSERVE_DATABASE__DATABASE_URL` | `SecretStr` | `None` | Optional direct connection URI override |

### Cloud Provider Configuration (`cloud`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ARMSERVE_CLOUD__AWS_REGION` | `str` | `us-east-1` | Target AWS region for Graviton instances |
| `ARMSERVE_CLOUD__AWS_ACCESS_KEY_ID` | `SecretStr` | `None` | AWS Access Key ID (masked) |
| `ARMSERVE_CLOUD__AWS_SECRET_ACCESS_KEY` | `SecretStr` | `None` | AWS Secret Access Key (masked) |
| `ARMSERVE_CLOUD__AWS_S3_BUCKET` | `str` | `armserve-models` | S3 bucket name for model artifacts |
| `ARMSERVE_CLOUD__AZURE_SUBSCRIPTION_ID` | `SecretStr` | `None` | Azure subscription ID |
| `ARMSERVE_CLOUD__AZURE_TENANT_ID` | `SecretStr` | `None` | Azure tenant ID |
| `ARMSERVE_CLOUD__GCP_PROJECT_ID` | `str` | `None` | GCP project ID |
| `ARMSERVE_CLOUD__GCP_CREDENTIALS_JSON` | `SecretStr` | `None` | GCP service account JSON (masked) |

### Model Configuration (`model`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ARMSERVE_MODEL__DEFAULT_STORAGE_BUCKET` | `str` | `armserve-models` | Default bucket name |
| `ARMSERVE_MODEL__MAX_MODEL_SIZE_BYTES` | `int` | `53687091200` | Max allowed model file size (50 GB) |
| `ARMSERVE_MODEL__ALLOWED_FORMATS` | `list` | `["ONNX", ...]` | Allowed model weight formats |

### Inference Configuration (`inference`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ARMSERVE_INFERENCE__DEFAULT_RUNTIME` | `str` | `onnxruntime` | Default inference engine |
| `ARMSERVE_INFERENCE__MAX_NUM_THREADS` | `int` | `64` | CPU thread allocation limit |
| `ARMSERVE_INFERENCE__MAX_BATCH_SIZE` | `int` | `128` | Max request batch size |
| `ARMSERVE_INFERENCE__MEMORY_LIMIT_MB_DEFAULT` | `int` | `4096` | Memory allocation per runtime pod (MB) |

### Optimization Configuration (`optimization`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ARMSERVE_OPTIMIZATION__DEFAULT_STRATEGY` | `str` | `tpe` | Optimization algorithm strategy |
| `ARMSERVE_OPTIMIZATION__MAX_TRIALS_LIMIT` | `int` | `100` | Maximum trial budget per experiment |
| `ARMSERVE_OPTIMIZATION__DEFAULT_TIMEOUT_SECONDS` | `int` | `3600` | Default experiment timeout (seconds) |

### Observability Configuration (`observability`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ARMSERVE_OBSERVABILITY__OTLP_ENDPOINT` | `str` | `None` | OpenTelemetry OTLP collector URL |
| `ARMSERVE_OBSERVABILITY__PROMETHEUS_ENABLED` | `bool` | `true` | Expose `/metrics` endpoint |
| `ARMSERVE_OBSERVABILITY__ENABLE_TRACING` | `bool` | `false` | Enable distributed tracing |

### Authentication & Security (`auth`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ARMSERVE_AUTH__SECRET_KEY` | `SecretStr` | *Dev default* | Master JWT signature key (masked) |
| `ARMSERVE_AUTH__JWT_ALGORITHM` | `str` | `HS256` | JWT signing algorithm |
| `ARMSERVE_AUTH__ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | `60` | Token expiration time in minutes |
| `ARMSERVE_AUTH__API_KEY_HEADER_NAME` | `str` | `X-API-Key` | HTTP header name for API keys |
