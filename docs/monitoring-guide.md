# ArmServe Infrastructure Monitoring Specification & Operations Guide

This document details the infrastructure monitoring architecture, CloudWatch metrics integration, log aggregation, metric alarm thresholds, and verification procedures for ArmServe ARM64 Graviton instances.

---

## 1. Monitoring Architecture & Telemetry Pipeline

```text
┌─────────────────────────────────────────────────────────────┐
│  ArmServe Graviton Server (armserve-graviton-01)            │
├──────────────────────────────┬──────────────────────────────┤
│  Prometheus Metrics Endpoint │  CloudWatch Unified Agent    │
│  GET /metrics                │  /etc/amazon-cloudwatch-agent│
└──────────────┬───────────────┴──────────────┬───────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────────┐┌──────────────────────────────┐
│  Prometheus / Grafana        ││  AWS CloudWatch Service      │
│  - Real-time Dashboards      ││  - Container Insights        │
│  - Latency Histograms        ││  - Metric Alarms (>85% CPU)  │
│  - Request Rates (RPS)       ││  - Log Groups (/aws/armserve)│
└──────────────────────────────┘└──────────────┬───────────────┘
                                               │
                                               ▼
                                ┌──────────────────────────────┐
                                │  AWS SNS Alert Notifications │
                                │  - Email / PagerDuty / Slack │
                                └──────────────────────────────┘
```

---

## 2. Monitored Telemetry Matrix

| Category | Metric Name | Source | Description | Alarm Condition |
|---|---|---|---|---|
| **CPU Metrics** | `cpu_usage_user` / `cpu_usage_system` | CloudWatch / `/proc/stat` | CPU utilization across 4 vCPUs | `> 85% for 3 consecutive minutes` |
| **Memory Metrics** | `mem_used_percent` | CloudWatch / `/proc/meminfo` | Physical RAM utilization | `> 90% for 5 minutes` |
| **Disk Metrics** | `disk_used_percent` | CloudWatch / `df` | Storage consumption on `/storage` volume | `> 80% capacity` |
| **Network Metrics** | `net_bytes_sent` / `net_bytes_recv` | CloudWatch / `/proc/net/dev` | Inbound/outbound throughput | Drop below baseline during peak |
| **Instance Health** | `StatusCheckFailed` | AWS EC2 Infrastructure | Hardware / hypervisor liveness probe | `>= 1 failure` |
| **Application Latency**| `http_request_duration_seconds` | Prometheus Endpoint | P99 request latency histogram | `P99 > 500ms` |
| **Error Rates** | `http_errors_total` | Prometheus Endpoint | Total 4xx / 5xx error counter | `Error Rate > 2%` |

---

## 3. CloudWatch Unified Agent Configuration

Configuration file location: `/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json`

```json
{
  "agent": {
    "metrics_collection_interval": 15,
    "run_as_user": "cwagent"
  },
  "metrics": {
    "append_dimensions": {
      "InstanceId": "${aws:InstanceId}",
      "AutoScalingGroupName": "${aws:AutoScalingGroupName}"
    },
    "metrics_collected": {
      "cpu": {
        "measurement": ["cpu_usage_idle", "cpu_usage_iowait", "cpu_usage_user", "cpu_usage_system"],
        "metrics_collection_interval": 15,
        "totalcpu": true
      },
      "disk": {
        "measurement": ["used_percent", "inodes_free"],
        "metrics_collection_interval": 60,
        "resources": ["/"]
      },
      "mem": {
        "measurement": ["mem_used_percent", "mem_available", "swap_used_percent"],
        "metrics_collection_interval": 15
      },
      "net": {
        "measurement": ["bytes_sent", "bytes_recv", "drop_in", "drop_out"],
        "metrics_collection_interval": 15
      }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/app/storage/logs/*.log",
            "log_group_name": "/aws/armserve/application",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%Y-%m-%dT%H:%M:%S.%fZ"
          }
        ]
      }
    }
  }
}
```

---

## 4. Local & Production Verification Procedures

### A. Verify Local Prometheus Metrics Stream
```bash
curl -s http://127.0.0.1:8000/metrics | grep -E "(http_requests_total|armserve_app_info|db_operations_total)"
```

Expected Output:
```text
armserve_app_info{app="armserve",arch="arm64",version="0.1.0"} 1
http_requests_total{endpoint="/api/v1/system/health",method="GET",status="200"} 15
db_operations_total{operation="health_check",status="success"} 15
```

### B. Verify CloudWatch Agent Status (On EC2 Node)
```bash
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status
```

Expected Output:
```text
{
  "status": "running",
  "starttime": "2026-08-12T21:30:00Z",
  "version": "1.300002.0"
}
```
