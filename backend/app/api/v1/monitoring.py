"""
Elder Care Platform - Monitoring API Endpoints
Provides comprehensive monitoring and observability endpoints:
  - Service status and health
  - Metrics and performance data
  - Alert management
  - Circuit breaker status
  - Prometheus-compatible metrics export
"""
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

from app.core.service_monitor import service_monitor
from app.core.metrics import metrics_registry, performance_monitor
from app.core.alerts import alert_manager, AlertSeverity, AlertStatus
from app.core.circuit_breaker import circuit_breaker_registry

logger = structlog.get_logger()
router = APIRouter(prefix="/monitoring", tags=["监控"])


class ServiceStatusResponse(BaseModel):
    service: str
    healthy: bool
    consecutive_failures: int
    recovery_attempts: int
    last_check: str
    last_error: str | None


class MonitoringSummaryResponse(BaseModel):
    uptime_seconds: float
    availability_percent: float
    target_availability: float
    services: dict[str, dict]
    performance: dict
    circuit_breakers: dict[str, dict]
    active_alerts_count: int


class AlertResponse(BaseModel):
    id: str
    name: str
    severity: str
    status: str
    message: str
    labels: dict[str, str]
    starts_at: str
    ends_at: str | None


class SilenceRequest(BaseModel):
    duration_minutes: int = 60


@router.get("/status", response_model=MonitoringSummaryResponse)
async def get_monitoring_status():
    """
    Get comprehensive monitoring status summary.
    Includes availability, performance metrics, and service health.
    """
    summary = service_monitor.get_summary()
    return MonitoringSummaryResponse(**summary)


@router.get("/services")
async def get_all_services():
    """
    Get status of all monitored services.
    """
    services = service_monitor.get_all_statuses()
    return {
        "services": [
            ServiceStatusResponse(
                service=status.name,
                healthy=status.healthy,
                consecutive_failures=status.consecutive_failures,
                recovery_attempts=status.recovery_attempts,
                last_check=status.last_check.isoformat(),
                last_error=status.last_error,
            )
            for status in services.values()
        ],
        "total": len(services),
        "healthy_count": sum(1 for s in services.values() if s.healthy),
    }


@router.get("/services/{service_name}", response_model=ServiceStatusResponse)
async def get_service_status(service_name: str):
    """
    Get detailed status for a specific service.
    """
    status = service_monitor.get_service_status(service_name)
    if not status:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    return ServiceStatusResponse(
        service=status.name,
        healthy=status.healthy,
        consecutive_failures=status.consecutive_failures,
        recovery_attempts=status.recovery_attempts,
        last_check=status.last_check.isoformat(),
        last_error=status.last_error,
    )


@router.post("/services/{service_name}/reset-recovery")
async def reset_service_recovery(service_name: str):
    """
    Reset recovery attempt counter for a service.
    """
    status = service_monitor.get_service_status(service_name)
    if not status:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    service_monitor.reset_recovery_attempts(service_name)
    return {"message": f"Recovery attempts reset for {service_name}"}


@router.get("/availability")
async def get_availability(hours: int = Query(default=24, ge=1, le=168)):
    """
    Get availability metrics for the specified time window.
    """
    availability = service_monitor.calculate_availability(hours)
    uptime = service_monitor.get_uptime()
    
    return {
        "availability_percent": round(availability, 3),
        "target_percent": service_monitor.config.target_availability,
        "meeting_sla": availability >= service_monitor.config.target_availability,
        "uptime_seconds": uptime.total_seconds(),
        "uptime_human": str(uptime).split(".")[0],
        "window_hours": hours,
    }


@router.get("/performance")
async def get_performance():
    """
    Get performance metrics including latency percentiles and error rates.
    """
    summary = performance_monitor.get_summary()
    
    return {
        "availability": summary["availability"],
        "error_rate_per_minute": summary["error_rate_per_minute"],
        "latency": {
            "p50_ms": summary["latency_p50_ms"],
            "p95_ms": summary["latency_p95_ms"],
            "p99_ms": summary["latency_p99_ms"],
        },
        "window_seconds": summary["window_seconds"],
    }


@router.get("/metrics")
async def get_metrics():
    """
    Get all collected metrics in JSON format.
    """
    metrics_data = []
    for metric in metrics_registry.all():
        latest = metric.get_latest()
        stats = metric.get_statistics(window_seconds=300)
        
        metrics_data.append({
            "name": metric.name,
            "type": metric.metric_type.value,
            "description": metric.description,
            "unit": metric.unit,
            "latest_value": latest.value if latest else None,
            "latest_timestamp": latest.timestamp.isoformat() if latest else None,
            "statistics_5min": stats,
        })
    
    return {
        "metrics": metrics_data,
        "total": len(metrics_data),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """
    Export metrics in Prometheus format.
    """
    prometheus_output = metrics_registry.export_prometheus()
    return Response(
        content=prometheus_output,
        media_type="text/plain; version=0.0.4",
    )


@router.get("/circuit-breakers")
async def get_circuit_breakers():
    """
    Get status of all circuit breakers.
    """
    status = circuit_breaker_registry.get_status()
    
    return {
        "circuit_breakers": [
            {
                "name": name,
                **data,
            }
            for name, data in status.items()
        ],
        "total": len(status),
        "open_count": sum(1 for d in status.values() if d["state"] == "open"),
    }


@router.post("/circuit-breakers/{name}/reset")
async def reset_circuit_breaker(name: str):
    """
    Reset a specific circuit breaker.
    """
    breaker = circuit_breaker_registry.get(name)
    if not breaker:
        raise HTTPException(status_code=404, detail=f"Circuit breaker '{name}' not found")
    
    breaker.reset()
    return {"message": f"Circuit breaker '{name}' has been reset"}


@router.get("/alerts", response_model=list[AlertResponse])
async def get_alerts(
    status: AlertStatus | None = None,
    severity: AlertSeverity | None = None,
    hours: int = Query(default=24, ge=1, le=168),
):
    """
    Get alerts, optionally filtered by status and severity.
    """
    alerts = alert_manager.get_alert_history(hours)
    
    if status:
        alerts = [a for a in alerts if a.status == status]
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    
    return [
        AlertResponse(
            id=alert.id,
            name=alert.name,
            severity=alert.severity.value,
            status=alert.status.value,
            message=alert.message,
            labels=alert.labels,
            starts_at=alert.starts_at.isoformat(),
            ends_at=alert.ends_at.isoformat() if alert.ends_at else None,
        )
        for alert in alerts
    ]


@router.get("/alerts/active", response_model=list[AlertResponse])
async def get_active_alerts():
    """
    Get all currently active (firing) alerts.
    """
    alerts = alert_manager.get_active_alerts()
    
    return [
        AlertResponse(
            id=alert.id,
            name=alert.name,
            severity=alert.severity.value,
            status=alert.status.value,
            message=alert.message,
            labels=alert.labels,
            starts_at=alert.starts_at.isoformat(),
            ends_at=alert.ends_at.isoformat() if alert.ends_at else None,
        )
        for alert in alerts
    ]


@router.post("/alerts/{fingerprint}/silence")
async def silence_alert(fingerprint: str, request: SilenceRequest):
    """
    Silence an alert for a specified duration.
    """
    alert_manager.silence(fingerprint, request.duration_minutes)
    return {
        "message": f"Alert {fingerprint} silenced for {request.duration_minutes} minutes",
    }


@router.post("/alerts/{fingerprint}/resolve")
async def resolve_alert(fingerprint: str):
    """
    Manually resolve an alert.
    """
    alert = alert_manager.resolve(fingerprint)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{fingerprint}' not found or already resolved")
    
    return {"message": f"Alert {fingerprint} resolved"}


@router.get("/dashboard")
async def get_monitoring_dashboard():
    """
    Get comprehensive dashboard data for monitoring UI.
    Aggregates all monitoring information in a single endpoint.
    """
    summary = service_monitor.get_summary()
    active_alerts = alert_manager.get_active_alerts()
    circuit_status = circuit_breaker_registry.get_status()
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overview": {
            "uptime_seconds": summary["uptime_seconds"],
            "availability_percent": summary["availability_percent"],
            "target_availability": summary["target_availability"],
            "meeting_sla": summary["availability_percent"] >= summary["target_availability"],
            "active_alerts": len(active_alerts),
            "critical_alerts": sum(1 for a in active_alerts if a.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]),
        },
        "services": summary["services"],
        "performance": summary["performance"],
        "circuit_breakers": {
            "total": len(circuit_status),
            "open": sum(1 for d in circuit_status.values() if d["state"] == "open"),
            "half_open": sum(1 for d in circuit_status.values() if d["state"] == "half_open"),
            "closed": sum(1 for d in circuit_status.values() if d["state"] == "closed"),
            "details": circuit_status,
        },
        "alerts": {
            "active": [
                {
                    "id": a.id,
                    "name": a.name,
                    "severity": a.severity.value,
                    "message": a.message,
                    "duration_seconds": (datetime.now(timezone.utc) - a.starts_at).total_seconds(),
                }
                for a in active_alerts
            ],
        },
        "recovery_status": {
            service: {
                "recovery_attempts": status["recovery_attempts"],
                "healthy": status["healthy"],
            }
            for service, status in summary["services"].items()
        },
    }
