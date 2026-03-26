"""
Elder Care Platform - Health Check Module
Provides comprehensive health checks for:
  - Database connectivity
  - Redis connectivity
  - RabbitMQ connectivity
  - Application status
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.database import engine

logger = structlog.get_logger()
settings = get_settings()


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    name: str
    status: HealthStatus
    latency_ms: float | None = None
    error: str | None = None
    details: dict[str, Any] | None = None


class HealthCheckResponse(BaseModel):
    status: HealthStatus
    version: str
    timestamp: str
    components: dict[str, dict[str, Any]]


async def check_database() -> ComponentHealth:
    """Check PostgreSQL database connectivity."""
    import time
    from sqlalchemy import text
    
    start = time.perf_counter()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        logger.error("health_check_database_failed", error=str(e))
        return ComponentHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 2),
            error=str(e),
        )


async def check_redis() -> ComponentHealth:
    """Check Redis connectivity."""
    import time
    
    start = time.perf_counter()
    try:
        import redis.asyncio as redis
        
        client = redis.from_url(settings.REDIS_URL)
        await client.ping()
        await client.close()
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        logger.warning("health_check_redis_failed", error=str(e))
        return ComponentHealth(
            name="redis",
            status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 2),
            error=str(e),
        )


async def check_rabbitmq() -> ComponentHealth:
    """Check RabbitMQ connectivity."""
    import time
    
    if not settings.RABBITMQ_URL:
        return ComponentHealth(
            name="rabbitmq",
            status=HealthStatus.HEALTHY,
            details={"message": "RabbitMQ not configured"},
        )
    
    start = time.perf_counter()
    try:
        from shared.event_bus import get_event_bus
        
        event_bus = get_event_bus()
        if event_bus.connection and not event_bus.connection.is_closed:
            latency = (time.perf_counter() - start) * 1000
            return ComponentHealth(
                name="rabbitmq",
                status=HealthStatus.HEALTHY,
                latency_ms=round(latency, 2),
            )
        return ComponentHealth(
            name="rabbitmq",
            status=HealthStatus.DEGRADED,
            error="Event bus not connected",
        )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        logger.warning("health_check_rabbitmq_failed", error=str(e))
        return ComponentHealth(
            name="rabbitmq",
            status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 2),
            error=str(e),
        )


router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(response: Response):
    """
    Comprehensive health check endpoint.
    Returns detailed status of all system components.
    """
    components = await _check_all_components()
    
    overall_status = _compute_overall_status(components)
    
    if overall_status == HealthStatus.UNHEALTHY:
        response.status_code = 503
    elif overall_status == HealthStatus.DEGRADED:
        response.status_code = 200
    
    return HealthCheckResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        components={
            c.name: {
                "status": c.status.value,
                "latency_ms": c.latency_ms,
                "error": c.error,
                **(c.details or {}),
            }
            for c in components
        },
    )


@router.get("/health/live")
async def liveness():
    """Kubernetes liveness probe - is the app running?"""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(response: Response):
    """Kubernetes readiness probe - is the app ready to serve traffic?"""
    db_health = await check_database()
    
    if db_health.status == HealthStatus.UNHEALTHY:
        response.status_code = 503
        return {"status": "not_ready", "reason": "database_unavailable"}
    
    return {"status": "ready"}


async def _check_all_components() -> list[ComponentHealth]:
    """Run all health checks concurrently."""
    import asyncio
    
    results = await asyncio.gather(
        check_database(),
        check_redis(),
        check_rabbitmq(),
    )
    return list(results)


def _compute_overall_status(components: list[ComponentHealth]) -> HealthStatus:
    """Compute overall health status from component statuses."""
    statuses = [c.status for c in components]
    
    if HealthStatus.UNHEALTHY in statuses:
        return HealthStatus.UNHEALTHY
    if HealthStatus.DEGRADED in statuses:
        return HealthStatus.DEGRADED
    return HealthStatus.HEALTHY
