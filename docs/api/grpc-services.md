# ArmServe — gRPC Internal Service Definitions

High-performance internal communication protocol between the Controller, Benchmark Engine, and target Arm64 Runner Pods.

---

## 1. Benchmark Execution Service (`benchmark.v1`)

```protobuf
syntax = "proto3";

package armserve.benchmark.v1;

service BenchmarkService {
  rpc ExecuteTrial (ExecuteTrialRequest) returns (stream TrialProgressResponse);
  rpc AbortTrial (AbortTrialRequest) returns (AbortTrialResponse);
}

message ExecuteTrialRequest {
  string trial_id = 1;
  string model_uri = 2;
  RuntimeConfig runtime_config = 3;
  WorkloadParams workload_params = 4;
}

message RuntimeConfig {
  string runtime_type = 1;      // onnxruntime, llamacpp, vllm
  string quantization = 2;        // fp32, int8, etc.
  int32 num_threads = 3;
  int32 batch_size = 4;
  map<string, string> extra_flags = 5;
}

message WorkloadParams {
  int32 duration_seconds = 1;
  int32 warmup_requests = 2;
  int32 target_concurrency = 3;
}

message TrialProgressResponse {
  string trial_id = 1;
  enum State {
    PROVISIONING = 0;
    WARMING_UP = 1;
    BENCHMARKING = 2;
    COMPLETED = 3;
    FAILED = 4;
  }
  State state = 2;
  double current_latency_p99_ms = 3;
  double current_throughput_rps = 4;
  string error_message = 5;
}

message AbortTrialRequest {
  string trial_id = 1;
  string reason = 2;
}

message AbortTrialResponse {
  bool success = 1;
}
```
