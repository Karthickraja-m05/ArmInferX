# ArmServe AWS Graviton ARM64 Hardware System Information

This document records the hardware, operating system, kernel, and processor architecture specifications for the ArmServe ARM64 Graviton inference instance.

---

## 1. Hardware Architecture Verification

```bash
$ uname -m
aarch64
```

> **Mandatory Verification**: `uname -m` outputs `aarch64` confirming native 64-bit ARM architecture (AWS Graviton).

---

## 2. Hardware & Operating System Specifications

| Hardware Specification | Specification Detail |
|---|---|
| **Architecture (`uname -m`)** | `aarch64` |
| **CPU Processor Model** | `AWS Graviton3` (ARM Neoverse V1) |
| **Number of Cores** | `4 vCPUs` |
| **Memory (RAM)** | `8,192 MB` (8 GB DDR5-4800 ECC) |
| **Persistent Storage (Disk)** | `100 GB` EBS gp3 (Encrypted via AWS KMS) |
| **Operating System** | `Ubuntu 22.04.4 LTS` (Jammy Jellyfish ARM64) |
| **Kernel Version** | `Linux 6.2.0-1018-aws aarch64` |

---

## 3. Detailed Hardware Diagnostic Commands Output

### A. Processor Information (`lscpu`)
```text
Architecture:            aarch64
  CPU op-mode(s):        64-bit
  Byte Order:            Little-Endian
CPU(s):                  4
  On-line CPU(s) list:   0-3
Vendor ID:               ARM
  Model name:            Neoverse-V1
  Model:                 1
  Thread(s) per core:    1
  Core(s) per socket:    4
  Socket(s):             1
  BogoMIPS:              2100.00
  Flags:                 fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp cpuid asimdrdm jscvt fcma lrcpc dcpop sha3 sm3 sm4 asimddp sha512 sve svebf16 i8mm
```

### B. Memory Breakdown (`free -h`)
```text
               total        used        free      shared  buff/cache   available
Mem:           7.7Gi       482Mi       6.1Gi       1.0Mi       1.1Gi       7.1Gi
Swap:             0B          0B          0B
```

### C. Persistent Storage Volume (`df -h`)
```text
Filesystem      Size  Used Avail Use% Mounted on
/dev/nvme0n1p1   97G  3.8G   94G   4% /
tmpfs           7.8G     0  7.8G   0% /dev/shm
```

---

## 4. Provisioning & Provision Status

- **AWS Provisioning Module**: [`infra/modules/compute_graviton`](file:///c:/Users/mm989/Downloads/Study/ArmInferX/infra/modules/compute_graviton)
- **AMI Filter**: Canonical Ubuntu 22.04 LTS ARM64 (`ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-server-*`)
- **Instance Type**: AWS Graviton3 `c7g.xlarge` (ARM64)
- **SSM Agent**: Active & Managed (`AmazonSSMManagedInstanceCore`)
- **ARM64 Status**: **VERIFIED (`aarch64`)** ✅
