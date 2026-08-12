# ArmServe ARM64 Graviton Server Preparation Guide

This document specifies the server initialization procedure, package manifest, filesystem configuration, swap setup, time synchronization, hostname setup, and persistent directory structure for AWS Graviton ARM64 nodes.

---

## 1. Server Environment Specification

- **Hostname**: `armserve-graviton-01`
- **Architecture**: `aarch64` (AWS Graviton3 ARM64 Neoverse V1)
- **OS Release**: `Ubuntu 22.04.4 LTS` (Jammy Jellyfish ARM64)
- **Kernel Version**: `Linux 6.2.0-1018-aws aarch64`

---

## 2. Operating System Update & Setup Commands

```bash
# 1. Update OS packages to latest security patches
sudo apt-get update && sudo apt-get dist-upgrade -y

# 2. Configure Hostname
sudo hostnamectl set-hostname armserve-graviton-01

# 3. Configure Time Synchronization (Amazon Time Sync Service)
sudo apt-get install -y chrony
echo "server 169.254.169.123 iburst minpoll 4 maxpoll 4" | sudo tee -a /etc/chrony/chrony.conf
sudo systemctl restart chrony
sudo chronyc tracking

# 4. Configure Swap Space (4 GB Swapfile with swappiness=10)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo "/swapfile swap swap defaults 0 0" | sudo tee -a /etc/fstab
echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

---

## 3. Package Inventory & Installed Manifest

| Package Name | Purpose | Version / Target |
|---|---|---|
| `python3.10` / `python3-pip` | Core Python runtime engine | `3.10.11` |
| `onnxruntime` | ARM64 CPU neural network inference execution engine | `1.17.1` |
| `libopenblas-dev` | High-performance BLAS library optimized for ARM Neoverse | `0.3.20` |
| `libgomp1` | GNU OpenMP parallel execution library for multi-core inference | System Default |
| `amazon-cloudwatch-agent` | Streams CPU, Memory, Disk, and system logs to AWS CloudWatch | `1.300002.0` |
| `chrony` | Amazon Time Sync Service client for microsecond clock sync | `4.2` |
| `htop` / `iotop` | Real-time CLI performance & I/O monitoring | System Default |
| `curl` / `wget` | HTTP payload fetching and health check probes | System Default |

---

## 4. Persistent Storage & Directory Layout

Persistent storage is mounted on the primary SSD volume (`/dev/nvme0n1p1` / `ext4`) with strict permissions owned by unprivileged app user `appuser:appgroup`:

```text
storage/
├── models/         # Registered ONNX & PyTorch model artifacts (.onnx, .pt, .safetensors)
├── benchmarks/     # Latency/throughput trial run logs & execution metrics
├── logs/           # Application JSON access logs & error traces
├── artifacts/      # Model optimization compilation outputs & quantized graphs
└── deployments/    # Active container/process deployment manifests & lock files
```

---

## 5. Storage & Memory Verification Snapshot

```text
Disk Space Verification:
Filesystem      Size  Used Avail Use% Mounted on
/dev/nvme0n1p1   97G  3.8G   94G   4% /

Memory Verification (RAM + Swap):
               total        used        free      shared  buff/cache   available
Mem:           7.7Gi       482Mi       6.1Gi       1.0Mi       1.1Gi       7.1Gi
Swap:          4.0Gi          0B       4.0Gi
```
