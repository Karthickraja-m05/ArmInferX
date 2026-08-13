"""ArmServe Operational Alerting and Resource Health Monitoring Engine.

Evaluates system telemetry (CPU, RAM, Disk, Error Rates, Latencies) against alert policies,
generates structured alerts (CRITICAL, HIGH, MEDIUM, INFO), and maintains active alert registries.
"""

import json
from pathlib import Path
import time
import uuid
from typing import Any

import psutil
import structlog
from pydantic import BaseModel

from backend.app.core.metrics import metrics_collector

logger = structlog.get_logger("backend.app.services.alert_service")

ALERTS_DIR = Path("storage/alerts")


class Alert(BaseModel):
    alert_id: str
    rule_name: str
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "INFO"
    message: str
    component: str
    status: str  # "ACTIVE", "RESOLVED"
    triggered_at: str
    resolved_at: str | None = None
    metric_value: float | None = None
    threshold_value: float | None = None


class AlertService:
    """Production Alert Management System."""

    def __init__(self, storage_dir: Path = ALERTS_DIR):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.alerts_file = self.storage_dir / "active_alerts.json"
        self._alerts: dict[str, Alert] = self._load_alerts()

    def _load_alerts(self) -> dict[str, Alert]:
        if self.alerts_file.exists():
            try:
                with open(self.alerts_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {aid: Alert(**item) for aid, item in data.items()}
            except Exception:
                return {}
        return {}

    def _save_alerts(self) -> None:
        try:
            with open(self.alerts_file, "w", encoding="utf-8") as f:
                data = {aid: alert.model_dump() for aid, alert in self._alerts.items()}
                json.dump(data, f, indent=2)
        except Exception as err:
            logger.warning("Failed to persist system alerts", error=str(err))

    def trigger_alert(
        self,
        rule_name: str,
        severity: str,
        message: str,
        component: str,
        metric_value: float | None = None,
        threshold_value: float | None = None,
    ) -> Alert:
        """Trigger or update an active alert."""
        # Check if an active alert already exists for this rule and component
        for alert in self._alerts.values():
            if alert.rule_name == rule_name and alert.component == component and alert.status == "ACTIVE":
                alert.metric_value = metric_value
                alert.message = message
                self._save_alerts()
                return alert

        alert_id = f"alert-{str(uuid.uuid4())[:8]}"
        alert = Alert(
            alert_id=alert_id,
            rule_name=rule_name,
            severity=severity.upper(),
            message=message,
            component=component,
            status="ACTIVE",
            triggered_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            metric_value=metric_value,
            threshold_value=threshold_value,
        )
        self._alerts[alert_id] = alert
        self._save_alerts()

        metrics_collector.record_error(
            error_type=f"SystemAlert_{severity}",
            status_code=500 if severity in ("CRITICAL", "HIGH") else 200,
            endpoint=f"alert:{rule_name}",
        )
        logger.error(
            "System Alert Triggered",
            alert_id=alert_id,
            rule=rule_name,
            severity=severity,
            component=component,
            message=message,
        )
        return alert

    def resolve_alert(self, alert_id: str) -> Alert | None:
        """Resolve an active alert."""
        alert = self._alerts.get(alert_id)
        if alert and alert.status == "ACTIVE":
            alert.status = "RESOLVED"
            alert.resolved_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            self._save_alerts()
            logger.info("System Alert Resolved", alert_id=alert_id, rule=alert.rule_name)
            return alert
        return None

    def evaluate_resource_policies(self) -> list[Alert]:
        """Evaluate system resource thresholds (CPU, Memory, Disk, Latency)."""
        triggered: list[Alert] = []

        # 1. CPU Utilization (> 90%)
        cpu_pct = psutil.cpu_percent(interval=None)
        if cpu_pct > 90.0:
            a = self.trigger_alert(
                rule_name="HighCPUUtilization",
                severity="HIGH",
                message=f"CPU utilization is at {cpu_pct:.1f}% (threshold 90%)",
                component="system.cpu",
                metric_value=cpu_pct,
                threshold_value=90.0,
            )
            triggered.append(a)

        # 2. RAM Utilization (> 90%)
        ram_pct = psutil.virtual_memory().percent
        if ram_pct > 90.0:
            a = self.trigger_alert(
                rule_name="ResourceExhaustionRAM",
                severity="CRITICAL",
                message=f"RAM memory usage is at {ram_pct:.1f}% (threshold 90%)",
                component="system.memory",
                metric_value=ram_pct,
                threshold_value=90.0,
            )
            triggered.append(a)

        # 3. Disk Space Utilization (> 90%)
        disk_pct = psutil.disk_usage(".").percent
        if disk_pct > 90.0:
            a = self.trigger_alert(
                rule_name="DiskExhaustion",
                severity="CRITICAL",
                message=f"Storage disk usage is at {disk_pct:.1f}% (threshold 90%)",
                component="system.disk",
                metric_value=disk_pct,
                threshold_value=90.0,
            )
            triggered.append(a)

        return triggered

    def get_alerts(
        self,
        severity: str | None = None,
        status: str | None = None,
        component: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Alert], int]:
        """List active and historical alerts with filtering and pagination."""
        self.evaluate_resource_policies()

        filtered = list(self._alerts.values())
        if severity:
            filtered = [a for a in filtered if a.severity == severity.upper()]
        if status:
            filtered = [a for a in filtered if a.status == status.upper()]
        if component:
            filtered = [a for a in filtered if a.component == component]

        filtered.sort(key=lambda a: a.triggered_at, reverse=True)
        total = len(filtered)
        paginated = filtered[offset : offset + limit]

        return paginated, total


alert_service = AlertService()
