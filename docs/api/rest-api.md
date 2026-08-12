# ArmServe — REST API Specification

**Base URL**: `/api/v1`

---

## 1. Auth Endpoints

### POST `/auth/token`
Issue JWT access token.
- **Request**: `grant_type=password&username=...&password=...` (`application/x-www-form-urlencoded`)
- **Response**: `200 OK` → `{ "access_token": "...", "token_type": "bearer", "expires_in": 3600 }`

### POST `/auth/api-keys`
Create a programmatic API key.
- **Request**: `{ "name": "CI-Key", "scopes": ["experiments:write", "models:read"] }`
- **Response**: `201 Created` → `{ "key_id": "...", "raw_key": "arm_live_..." }`

---

## 2. Model Management Endpoints

### GET `/models`
List registered models.
- **Query Params**: `page=1&limit=20&format=onnx`
- **Response**: `200 OK` → `{ "items": [...], "total": 12 }`

### POST `/models`
Register or import a new model.
- **Request**:
  ```json
  {
    "name": "llama-3-8b",
    "source": "huggingface:meta-llama/Meta-Llama-3-8B",
    "format": "SAFETENSORS",
    "quantization": "NONE"
  }
  ```
- **Response**: `202 Accepted` → `{ "model_id": "uuid", "task_id": "celery-task-id", "status": "DOWNLOADING" }`

---

## 3. Experiment Endpoints

### POST `/experiments`
Create an optimization experiment.
- **Request**:
  ```json
  {
    "name": "resnet50-latency-opt",
    "model_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "constraints": {
      "max_latency_p99_ms": 15.0,
      "min_throughput_rps": 500,
      "max_cost_per_1k": 0.002,
      "min_quality_score": 0.92
    },
    "search_space": {
      "runtimes": ["onnxruntime"],
      "quantizations": ["fp32", "fp16", "int8"],
      "instance_types": ["c7g.xlarge", "c7g.2xlarge"],
      "batch_sizes": [1, 2, 4, 8]
    },
    "budget": 20
  }
  ```
- **Response**: `201 Created` → `{ "experiment_id": "uuid", "status": "CREATED" }`

### POST `/experiments/{id}/start`
Trigger execution of optimization loop.
- **Response**: `202 Accepted` → `{ "experiment_id": "uuid", "status": "RUNNING" }`

### GET `/experiments/{id}`
Retrieve experiment status and trial results.
- **Response**: `200 OK` → Full `Experiment` object with nested `Trial` array.

---

## 4. Deployment Endpoints

### POST `/deployments`
Deploy selected trial configuration to Kubernetes.
- **Request**: `{ "experiment_id": "uuid", "trial_id": "uuid", "cluster_name": "staging-eks-arm" }`
- **Response**: `202 Accepted` → `{ "deployment_id": "uuid", "status": "DEPLOYING" }`

### POST `/deployments/{id}/rollback`
Trigger automated rollback to prior stable deployment.
- **Response**: `202 Accepted` → `{ "deployment_id": "uuid", "status": "ROLLING_BACK" }`

---

## 5. System & Health

### GET `/system/health`
System health check endpoint.
- **Response**: `200 OK` → `{ "status": "healthy", "database": "up", "redis": "up", "version": "0.1.0" }`
