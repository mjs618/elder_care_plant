"""
Elder Care Platform - Service Monitor
Continuous monitoring with auto-recovery:
  - Periodic health checks
  - Performance monitoring
  - Automatic failure detection
  - Auto-recovery mechanisms
  - SLA tracking (99.9% availability target)
"""
import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable
import threading

import structlog

from app.core.config import get_settings
from app.core.health import (
    check_database,
    check_redis,
    check_rabbitmq,
    HealthStatus,
    ComponentHealth,
)
from app.core.metrics import (
    performance_monitor,
    SERVICE_AVAILABILITY,
    ERROR_RATE,
    CPU_USAGE,
    MEMORY_USAGE,
    system_metrics_collector,
)
from app.core.alerts import alert_manager, AlertSeverity, setup_default_alert_rules
from app.core.circuit_breaker import circuit_breaker_registry, CircuitState

logger = structlog.get_logger()
settings = get_settings()


class RecoveryAction(str, Enum):
    RESTART_CONNECTION = "restart_connection"
    CLEAR_CACHE = "clear_cache"
    SCALE_RESOURCES = "scale_resources"
    NOTIFY_ADMIN = "notify_admin"
    CIRCUIT_BREAKER_RESET = "circuit_breaker_reset"


@dataclass
class RecoveryPolicy:
    action: RecoveryAction
    max_attempts: int = 3
    cooldown_seconds: int = 60
    backoff_multiplier: float = 2.0


@dataclass
class ServiceStatus:
    name: str
    healthy: bool
    last_check: datetime
    consecutive_failures: int = 0
    last_error: str | None = None
    recovery_attempts: int = 0
    last_recovery: datetime | None = None


@dataclass
class MonitoringConfig:
    check_interval_seconds: int = 30
    availability_window_hours: int = 24
    target_availability: float = 99.9
    recovery_enabled: bool = True
    max_recovery_attempts: int = 3
    recovery_cooldown_seconds: int = 60


class ServiceMonitor:
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
        
        self.config = MonitoringConfig()
        self._running = False
        self._task: asyncio.Task | None = None
        self._service_statuses: dict[str, ServiceStatus] = {}
        self._availability_history: list[tuple[datetime, bool]] = []
        self._recovery_handlers: dict[str, Callable] = {}
        self._recovery_cooldowns: dict[str, datetime] = {}
        self._uptime_start = datetime.now(timezone.utc)
        self._initialized = True
        
        self._register_default_recovery_handlers()

    def _register_default_recovery_handlers(self):
        self._recovery_handlers["database"] = self._recover_database
        self._recovery_handlers["redis"] = self._recover_redis
        self._recovery_handlers["rabbitmq"] = self._recover_rabbitmq

    def register_recovery_handler(self, service: str, handler: Callable):
        self._recovery_handlers[service] = handler
        logger.info("recovery_handler_registered", service=service)

    async def start(self):
        if self._running:
            return
        
        self._running = True
        setup_default_alert_rules()
        
        await system_metrics_collector.start()
        
        self._task = asyncio.create_task(self._monitoring_loop())
        
        logger.info(
            "service_monitor_started",
            check_interval=self.config.check_interval_seconds,
            target_availability=self.config.target_availability,
        )

    async def stop(self):
        self._running = False
        
        await system_metrics_collector.stop()
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("service_monitor_stopped")

    async def _monitoring_loop(self):
        while self._running:
            try:
                await self._run_health_checks()
                await self._check_availability()
                await self._update_metrics()
                await self._check_alert_rules()
            except Exception as e:
                logger.error("monitoring_loop_error", error=str(e))
            
            await asyncio.sleep(self.config.check_interval_seconds)

    async def _run_health_checks(self):
        checks = [
            ("database", check_database),
            ("redis", check_redis),
            ("rabbitmq", check_rabbitmq),
        ]
        
        for service_name, check_func in checks:
            try:
                start_time = time.perf_counter()
                health: ComponentHealth = await check_func()
                duration = time.perf_counter() - start_time
                
                is_healthy = health.status == HealthStatus.HEALTHY
                
                self._update_service_status(
                    service_name,
                    is_healthy,
                    health.error,
                )
                
                performance_monitor.record_response_time(duration)
                
                if is_healthy:
                    performance_monitor.record_request()
                else:
                    performance_monitor.record_error()
                
                if not is_healthy and self.config.recovery_enabled:
                    await self._attempt_recovery(service_name)
                
            except Exception as e:
                logger.error(
                    "health_check_failed",
                    service=service_name,
                    error=str(e),
                )
                self._update_service_status(service_name, False, str(e))
                
                if self.config.recovery_enabled:
                    await self._attempt_recovery(service_name)

    def _update_service_status(
        self,
        service_name: str,
        is_healthy: bool,
        error: str | None = None,
    ):
        now = datetime.now(timezone.utc)
        
        if service_name not in self._service_statuses:
            self._service_statuses[service_name] = ServiceStatus(
                name=service_name,
                healthy=is_healthy,
                last_check=now,
                last_error=error,
            )
        else:
            status = self._service_statuses[service_name]
            status.last_check = now
            status.healthy = is_healthy
            status.last_error = error
            
            if is_healthy:
                status.consecutive_failures = 0
            else:
                status.consecutive_failures += 1
        
        self._availability_history.append((now, is_healthy))
        
        cutoff = now - timedelta(hours=self.config.availability_window_hours)
        self._availability_history = [
            (t, h) for t, h in self._availability_history if t >= cutoff
        ]

    async def _attempt_recovery(self, service_name: str):
        status = self._service_statuses.get(service_name)
        if not status:
            return
        
        if status.recovery_attempts >= self.config.max_recovery_attempts:
            logger.warning(
                "recovery_max_attempts_reached",
                service=service_name,
                attempts=status.recovery_attempts,
            )
            return
        
        cooldown_until = self._recovery_cooldowns.get(service_name)
        if cooldown_until and cooldown_until > datetime.now(timezone.utc):
            logger.debug(
                "recovery_cooldown_active",
                service=service_name,
                cooldown_remaining=(cooldown_until - datetime.now(timezone.utc)).total_seconds(),
            )
            return
        
        handler = self._recovery_handlers.get(service_name)
        if not handler:
            logger.warning("no_recovery_handler", service=service_name)
            return
        
        status.recovery_attempts += 1
        
        logger.warning(
            "attempting_recovery",
            service=service_name,
            attempt=status.recovery_attempts,
            consecutive_failures=status.consecutive_failures,
        )
        
        try:
            await handler()
            status.last_recovery = datetime.now(timezone.utc)
            
            cooldown_seconds = (
                self.config.recovery_cooldown_seconds * 
                (2 ** (status.recovery_attempts - 1))
            )
            self._recovery_cooldowns[service_name] = (
                datetime.now(timezone.utc) + timedelta(seconds=cooldown_seconds)
            )
            
            logger.info(
                "recovery_attempt_completed",
                service=service_name,
                attempt=status.recovery_attempts,
            )
            
            alert_manager.fire(
                name="recovery_attempted",
                severity=AlertSeverity.WARNING,
                message=f"Recovery attempted for {service_name} (attempt {status.recovery_attempts})",
                labels={"service": service_name, "action": "recovery"},
            )
            
        except Exception as e:
            logger.error(
                "recovery_failed",
                service=service_name,
                error=str(e),
            )
            
            alert_manager.fire(
                name="recovery_failed",
                severity=AlertSeverity.CRITICAL,
                message=f"Recovery failed for {service_name}: {str(e)}",
                labels={"service": service_name, "action": "recovery"},
            )

    async def _recover_database(self):
        logger.info("database_recovery_initiated")
        
        try:
            from app.core.database import engine
            
            pool = engine.pool
            logger.info(
                "database_pool_status",
                size=pool.size(),
                checked_in=pool.checkedin(),
                checked_out=pool.checkedout(),
                overflow=pool.overflow(),
            )
            
            circuit_breaker = circuit_breaker_registry.get("database")
            if circuit_breaker and circuit_breaker.state == CircuitState.OPEN:
                circuit_breaker.reset()
                logger.info("database_circuit_breaker_reset")
                
        except Exception as e:
            logger.error("database_recovery_error", error=str(e))
            raise

    async def _recover_redis(self):
        logger.info("redis_recovery_initiated")
        
        try:
            from app.core.cache import get_redis_client
            
            client = await get_redis_client()
            await client.ping()
            
            circuit_breaker = circuit_breaker_registry.get("redis")
            if circuit_breaker and circuit_breaker.state == CircuitState.OPEN:
                circuit_breaker.reset()
                logger.info("redis_circuit_breaker_reset")
                
        except Exception as e:
            logger.error("redis_recovery_error", error=str(e))
            raise

    async def _recover_rabbitmq(self):
        logger.info("rabbitmq_recovery_initiated")
        
        try:
            from shared.event_bus import get_event_bus, init_event_bus
            
            event_bus = get_event_bus()
            
            if event_bus.connection and event_bus.connection.is_closed:
                await init_event_bus(settings.RABBITMQ_URL)
                logger.info("rabbitmq_reconnected")
                
        except Exception as e:
            logger.error("rabbitmq_recovery_error", error=str(e))
            raise

    async def _check_availability(self):
        if not self._availability_history:
            return
        
        availability = self.calculate_availability()
        
        SERVICE_AVAILABILITY.record(availability / 100)
        
        if availability < self.config.target_availability:
            logger.warning(
                "availability_below_target",
                current=availability,
                target=self.config.target_availability,
            )

    async def _update_metrics(self):
        error_rate = performance_monitor.get_error_rate()
        ERROR_RATE.record(error_rate)
        
        latest_cpu = CPU_USAGE.get_latest()
        latest_memory = MEMORY_USAGE.get_latest()
        
        return {
            "error_rate": error_rate,
            "cpu_percent": latest_cpu.value if latest_cpu else 0,
            "memory_bytes": latest_memory.value if latest_memory else 0,
        }

    async def _check_alert_rules(self):
        metrics = {
            "error_rate": performance_monitor.get_error_rate(),
            "availability": self.calculate_availability(),
            "latency_p50_ms": performance_monitor.get_p50_latency() * 1000,
            "latency_p95_ms": performance_monitor.get_p95_latency() * 1000,
            "latency_p99_ms": performance_monitor.get_p99_latency() * 1000,
        }
        
        for service_name, status in self._service_statuses.items():
            metrics[f"{service_name}_status"] = "healthy" if status.healthy else "unhealthy"
        
        latest_memory = MEMORY_USAGE.get_latest()
        
        if latest_memory:
            import psutil
            total_memory = psutil.virtual_memory().total
            metrics["memory_usage_percent"] = (latest_memory.value / total_memory) * 100
        
        alert_manager.check_rules(metrics)

    def calculate_availability(self, hours: int | None = None) -> float:
        if not self._availability_history:
            return 100.0
        
        window_hours = hours or self.config.availability_window_hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        
        recent = [(t, h) for t, h in self._availability_history if t >= cutoff]
        
        if not recent:
            return 100.0
        
        healthy_count = sum(1 for _, h in recent if h)
        return (healthy_count / len(recent)) * 100

    def get_uptime(self) -> timedelta:
        return datetime.now(timezone.utc) - self._uptime_start

    def get_service_status(self, service_name: str) -> ServiceStatus | None:
        return self._service_statuses.get(service_name)

    def get_all_statuses(self) -> dict[str, ServiceStatus]:
        return dict(self._service_statuses)

    def get_summary(self) -> dict[str, Any]:
        return {
            "uptime_seconds": self.get_uptime().total_seconds(),
            "availability_percent": round(self.calculate_availability(), 3),
            "target_availability": self.config.target_availability,
            "services": {
                name: {
                    "healthy": status.healthy,
                    "consecutive_failures": status.consecutive_failures,
                    "recovery_attempts": status.recovery_attempts,
                    "last_check": status.last_check.isoformat(),
                    "last_error": status.last_error,
                }
                for name, status in self._service_statuses.items()
            },
            "performance": performance_monitor.get_summary(),
            "circuit_breakers": circuit_breaker_registry.get_status(),
            "active_alerts": len(alert_manager.get_active_alerts()),
        }

    def reset_recovery_attempts(self, service_name: str):
        if service_name in self._service_statuses:
            self._service_statuses[service_name].recovery_attempts = 0
            logger.info("recovery_attempts_reset", service=service_name)


service_monitor = ServiceMonitor()


async def start_service_monitor():
    await service_monitor.start()


async def stop_service_monitor():
    await service_monitor.stop()
