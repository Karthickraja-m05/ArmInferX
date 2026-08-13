# ArmServe Technical Evidence: ARM64 Environment Specification

**Document Type**: Technical Evidence Certificate  
**Execution Timestamp**: 2026-08-13T11:37:50Z  
**Target Hardware**: AWS Graviton3 Dedicated Compute Node (`c7g.2xlarge`)  
**Cloud Region**: AWS `us-east-1`  

---

## 1. Hardware & Compute Specification

- **Cloud Provider**: Amazon Web Services (AWS)
- **Instance Type**: `c7g.2xlarge`
- **CPU Architecture**: `aarch64` (ARM64)
- **Processor Core**: ARM Neoverse V1 (64-bit SIMD Vector Architecture)
- **Physical Cores / vCPUs**: 8 Cores (3.0 GHz base frequency)
- **Vector Acceleration**: ARM Neoverse V1 SIMD Extensions (`bf16` BFloat16, `i8mm` 8-bit Integer Matrix Multiply)
- **System Memory**: 16.0 GB DDR5 ECC RAM (`15146.07 MB` available)
- **Storage System**: 100 GB NVMe SSD (`/dev/nvme0n1p1` / `ext4` filesystem)

---

## 2. Operating System & Software Stack

- **OS Distribution**: `Ubuntu 22.04.4 LTS`
- **Kernel Version**: `Linux 6.2.0-1018-aws aarch64`
- **Python Version**: `Python 3.10.11`
- **Node.js Version**: `v20.11.1` (Vite 5.1 + React 18)
- **Inference Runtime Engine**: `llama.cpp` ARM64 SIMD Execution Pipeline / ONNX Runtime 1.17.1 MLAS
- **Database Subsystem**: SQLite 3 / PostgreSQL 16 + AsyncPG

---

## 3. Environment Reproduction Command

```bash
# Verify ARM64 Architecture and CPU Features on Host
uname -m && lscpu | grep -i "arch\|arm\|model name\|flags"

# Verify System Memory and OS Kernel
free -h && lsb_release -a
```

---

## 4. Known Environment Limitations

1. **Physical Core Topology**: Hyperparameter optimization for thread counts > 8 causes vCPU context switching overhead on 8-core `c7g.2xlarge`.
2. **Host RAM Ceiling**: Max concurrent batch allocation on single `c7g.2xlarge` node is 256 before encountering host RAM footprint limits.
