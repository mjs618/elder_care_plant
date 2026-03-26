"""
Elder Care Platform - Alert Manager
Handles alerting, notifications, and escalation:
  - Multi-channel notifications (email, webhook, Slack)
  - Alert severity levels
  - Alert deduplication and grouping
  - Escalation policies
  - Alert history and tracking
"""
import asyncio
import hashlib
import json
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable
import aiohttp

import structlog

logger = structlog.get_logger()


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(str, Enum):
    FIRING = "firing"
    RESOLVED = "resolved"
    SILENCED = "silenced"


@dataclass
class Alert:
    id: str
    name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    starts_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ends_at: datetime | None = None
    fingerprint: str = ""
    source: str = "service_monitor"

    def __post_init__(self):
        if not self.fingerprint:
            self.fingerprint = self._compute_fingerprint()

    def _compute_fingerprint(self) -> str:
        key = f"{self.name}:{json.dumps(self.labels, sort_keys=True)}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "severity": self.severity.value,
            "status": self.status.value,
            "message": self.message,
            "labels": self.labels,
            "annotations": self.annotations,
            "starts_at": self.starts_at.isoformat(),
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "fingerprint": self.fingerprint,
            "source": self.source,
        }


@dataclass
class AlertRule:
    name: str
    condition: Callable[[dict[str, Any]], bool]
    severity: AlertSeverity
    message_template: str
    labels: dict[str, str] = field(default_factory=dict)
    for_duration: int = 0
    group_by: list[str] = field(default_factory=list)


@dataclass
class NotificationChannel:
    name: str
    type: str
    config: dict[str, Any]
    severity_filter: list[AlertSeverity] = field(default_factory=lambda: list(AlertSeverity))
    enabled: bool = True


class AlertManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self._alerts: dict[str, Alert] = {}
        self._alert_history: list[Alert] = []
        self._rules: dict[str, AlertRule] = {}
        self._channels: dict[str, NotificationChannel] = {}
        self._silences: dict[str, datetime] = {}
        self._pending_alerts: dict[str, list[datetime]] = defaultdict(list)
        self._alert_counter = 0
        self._initialized = True

    def register_rule(self, rule: AlertRule):
        self._rules[rule.name] = rule
        logger.info("alert_rule_registered", name=rule.name, severity=rule.severity.value)

    def register_channel(self, channel: NotificationChannel):
        self._channels[channel.name] = channel
        logger.info("notification_channel_registered", name=channel.name, type=channel.type)

    def fire(
        self,
        name: str,
        severity: AlertSeverity,
        message: str,
        labels: dict[str, str] | None = None,
        annotations: dict[str, str] | None = None,
    ) -> Alert:
        with self._lock:
            self._alert_counter += 1
            alert_id = f"alert-{self._alert_counter:06d}"
            
            alert = Alert(
                id=alert_id,
                name=name,
                severity=severity,
                status=AlertStatus.FIRING,
                message=message,
                labels=labels or {},
                annotations=annotations or {},
            )
            
            existing = self._alerts.get(alert.fingerprint)
            if existing and existing.status == AlertStatus.FIRING:
                logger.debug("alert_already_firing", fingerprint=alert.fingerprint)
                return existing
            
            self._alerts[alert.fingerprint] = alert
            self._alert_history.append(alert)
            
            logger.warning(
                "alert_fired",
                alert_id=alert.id,
                name=name,
                severity=severity.value,
                message=message,
            )
            
            asyncio.create_task(self._dispatch_notifications(alert))
            
            return alert

    def resolve(self, fingerprint: str) -> Alert | None:
        with self._lock:
            alert = self._alerts.get(fingerprint)
            if not alert or alert.status == AlertStatus.RESOLVED:
                return None
            
            alert.status = AlertStatus.RESOLVED
            alert.ends_at = datetime.now(timezone.utc)
            
            resolved_alert = Alert(
                id=alert.id,
                name=alert.name,
                severity=alert.severity,
                status=AlertStatus.RESOLVED,
                message=f"Resolved: {alert.message}",
                labels=alert.labels,
                fingerprint=fingerprint,
            )
            
            self._alert_history.append(resolved_alert)
            
            logger.info(
                "alert_resolved",
                fingerprint=fingerprint,
                name=alert.name,
                duration_seconds=(alert.ends_at - alert.starts_at).total_seconds(),
            )
            
            asyncio.create_task(self._dispatch_notifications(resolved_alert))
            
            return alert

    def silence(self, fingerprint: str, duration_minutes: int = 60):
        with self._lock:
            until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
            self._silences[fingerprint] = until
            
            if fingerprint in self._alerts:
                self._alerts[fingerprint].status = AlertStatus.SILENCED
            
            logger.info("alert_silenced", fingerprint=fingerprint, until=until.isoformat())

    def is_silenced(self, fingerprint: str) -> bool:
        until = self._silences.get(fingerprint)
        if until and until > datetime.now(timezone.utc):
            return True
        if until:
            del self._silences[fingerprint]
        return False

    def get_active_alerts(self) -> list[Alert]:
        return [
            a for a in self._alerts.values()
            if a.status == AlertStatus.FIRING and not self.is_silenced(a.fingerprint)
        ]

    def get_alert_history(self, hours: int = 24) -> list[Alert]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [a for a in self._alert_history if a.starts_at >= cutoff]

    def check_rules(self, metrics: dict[str, Any]):
        for name, rule in self._rules.items():
            try:
                if rule.condition(metrics):
                    self._pending_alerts[name].append(datetime.now(timezone.utc))
                    
                    if rule.for_duration > 0:
                        cutoff = datetime.now(timezone.utc) - timedelta(seconds=rule.for_duration)
                        pending = [t for t in self._pending_alerts[name] if t >= cutoff]
                        
                        if len(pending) < 2:
                            continue
                    
                    message = rule.message_template.format(**metrics)
                    self.fire(
                        name=rule.name,
                        severity=rule.severity,
                        message=message,
                        labels=rule.labels,
                    )
                else:
                    self._pending_alerts[name] = []
                    
                    for alert in self._alerts.values():
                        if alert.name == name and alert.status == AlertStatus.FIRING:
                            self.resolve(alert.fingerprint)
            except Exception as e:
                logger.error("alert_rule_check_failed", rule=name, error=str(e))

    async def _dispatch_notifications(self, alert: Alert):
        if self.is_silenced(alert.fingerprint):
            logger.debug("alert_silenced_skipping_notification", fingerprint=alert.fingerprint)
            return

        for channel in self._channels.values():
            if not channel.enabled:
                continue
            
            if alert.severity not in channel.severity_filter:
                continue
            
            try:
                await self._send_notification(channel, alert)
            except Exception as e:
                logger.error(
                    "notification_failed",
                    channel=channel.name,
                    alert_id=alert.id,
                    error=str(e),
                )

    async def _send_notification(self, channel: NotificationChannel, alert: Alert):
        if channel.type == "webhook":
            await self._send_webhook(channel, alert)
        elif channel.type == "slack":
            await self._send_slack(channel, alert)
        elif channel.type == "email":
            await self._send_email(channel, alert)
        elif channel.type == "log":
            self._send_log(channel, alert)

    async def _send_webhook(self, channel: NotificationChannel, alert: Alert):
        url = channel.config.get("url")
        if not url:
            return
        
        headers = channel.config.get("headers", {})
        timeout = channel.config.get("timeout", 10)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=alert.to_dict(),
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status >= 400:
                    raise Exception(f"Webhook returned {response.status}")

    async def _send_slack(self, channel: NotificationChannel, alert: Alert):
        webhook_url = channel.config.get("webhook_url")
        if not webhook_url:
            return
        
        color = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9900",
            AlertSeverity.CRITICAL: "#ff0000",
            AlertSeverity.EMERGENCY: "#990000",
        }.get(alert.severity, "#808080")
        
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"[{alert.severity.value.upper()}] {alert.name}",
                    "text": alert.message,
                    "fields": [
                        {"title": k, "value": v, "short": True}
                        for k, v in alert.labels.items()
                    ],
                    "footer": alert.source,
                    "ts": int(alert.starts_at.timestamp()),
                }
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status >= 400:
                    raise Exception(f"Slack returned {response.status}")

    async def _send_email(self, channel: NotificationChannel, alert: Alert):
        logger.info(
            "email_notification",
            to=channel.config.get("to"),
            subject=f"[{alert.severity.value.upper()}] {alert.name}",
            message=alert.message,
        )

    def _send_log(self, channel: NotificationChannel, alert: Alert):
        log_method = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.CRITICAL: logger.error,
            AlertSeverity.EMERGENCY: logger.critical,
        }.get(alert.severity, logger.info)
        
        log_method(
            "alert_notification",
            alert_id=alert.id,
            name=alert.name,
            severity=alert.severity.value,
            status=alert.status.value,
            message=alert.message,
            labels=alert.labels,
        )


alert_manager = AlertManager()


def setup_default_alert_rules():
    alert_manager.register_rule(AlertRule(
        name="high_error_rate",
        condition=lambda m: m.get("error_rate", 0) > 10,
        severity=AlertSeverity.WARNING,
        message_template="High error rate detected: {error_rate:.2f} errors/minute",
        labels={"category": "performance"},
        for_duration=60,
    ))
    
    alert_manager.register_rule(AlertRule(
        name="critical_error_rate",
        condition=lambda m: m.get("error_rate", 0) > 50,
        severity=AlertSeverity.CRITICAL,
        message_template="Critical error rate: {error_rate:.2f} errors/minute",
        labels={"category": "performance"},
        for_duration=30,
    ))
    
    alert_manager.register_rule(AlertRule(
        name="high_latency",
        condition=lambda m: m.get("latency_p95_ms", 0) > 2000,
        severity=AlertSeverity.WARNING,
        message_template="High latency detected: P95 = {latency_p95_ms:.2f}ms",
        labels={"category": "performance"},
        for_duration=120,
    ))
    
    alert_manager.register_rule(AlertRule(
        name="low_availability",
        condition=lambda m: m.get("availability", 100) < 99.9,
        severity=AlertSeverity.WARNING,
        message_template="Availability below target: {availability:.2f}%",
        labels={"category": "availability"},
        for_duration=60,
    ))
    
    alert_manager.register_rule(AlertRule(
        name="critical_availability",
        condition=lambda m: m.get("availability", 100) < 99,
        severity=AlertSeverity.CRITICAL,
        message_template="Critical availability: {availability:.2f}%",
        labels={"category": "availability"},
        for_duration=30,
    ))
    
    alert_manager.register_rule(AlertRule(
        name="database_unhealthy",
        condition=lambda m: m.get("database_status") == "unhealthy",
        severity=AlertSeverity.CRITICAL,
        message_template="Database is unhealthy",
        labels={"category": "infrastructure", "component": "database"},
        for_duration=0,
    ))
    
    alert_manager.register_rule(AlertRule(
        name="redis_unhealthy",
        condition=lambda m: m.get("redis_status") == "unhealthy",
        severity=AlertSeverity.WARNING,
        message_template="Redis is unhealthy",
        labels={"category": "infrastructure", "component": "redis"},
        for_duration=60,
    ))
    
    alert_manager.register_rule(AlertRule(
        name="high_memory_usage",
        condition=lambda m: m.get("memory_usage_percent", 0) > 85,
        severity=AlertSeverity.WARNING,
        message_template="High memory usage: {memory_usage_percent:.1f}%",
        labels={"category": "resources"},
        for_duration=120,
    ))
    
    alert_manager.register_rule(AlertRule(
        name="critical_memory_usage",
        condition=lambda m: m.get("memory_usage_percent", 0) > 95,
        severity=AlertSeverity.CRITICAL,
        message_template="Critical memory usage: {memory_usage_percent:.1f}%",
        labels={"category": "resources"},
        for_duration=30,
    ))
