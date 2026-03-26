"""
Elder Care Platform - Metrics Collection Module
Collects and aggregates metrics for:
  - Response times and latency
  - Request rates and error rates
  - Resource utilization (CPU, memory, connections)
  - Service availability and uptime
"""
import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import threading

import psutil
import structlog

logger = structlog.get_logger()


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricPoint:
    timestamp: datetime
    value: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    name: str
    metric_type: MetricType
    description: str
    unit: str = ""
    points: deque[MetricPoint] = field(default_factory=lambda: deque(maxlen=10000))
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record(self, value: float, labels: dict[str, str] | None = None):
        with self._lock:
            self.points.append(MetricPoint(
                timestamp=datetime.now(timezone.utc),
                value=value,
                labels=labels or {},
            ))

    def get_latest(self) -> MetricPoint | None:
        with self._lock:
            return self.points[-1] if self.points else None

    def get_values(self, since: datetime | None = None) -> list[MetricPoint]:
        with self._lock:
            if since:
                return [p for p in self.points if p.timestamp >= since]
            return list(self.points)

    def get_statistics(self, window_seconds: int = 300) -> dict[str, float]:
        with self._lock:
            cutoff = datetime.now(timezone.utc).timestamp() - window_seconds
            recent = [p for p in self.points if p.timestamp.timestamp() >= cutoff]
            
            if not recent:
                return {"count": 0, "min": 0, "max": 0, "avg": 0, "sum": 0}
            
            values = [p.value for p in recent]
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "sum": sum(values),
            }


class MetricsRegistry:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._metrics: dict[str, Metric] = {}
                    cls._instance._initialized = True
        return cls._instance

    def register(
        self,
        name: str,
        metric_type: MetricType,
        description: str,
        unit: str = "",
    ) -> Metric:
        if name not in self._metrics:
            self._metrics[name] = Metric(
                name=name,
                metric_type=metric_type,
                description=description,
                unit=unit,
            )
        return self._metrics[name]

    def get(self, name: str) -> Metric | None:
        return self._metrics.get(name)

    def all(self) -> list[Metric]:
        return list(self._metrics.values())

    def export_prometheus(self) -> str:
        lines = []
        for metric in self._metrics.values():
            lines.append(f"# HELP {metric.name} {metric.description}")
            lines.append(f"# TYPE {metric.name} {metric.metric_type.value}")
            latest = metric.get_latest()
            if latest:
                label_str = ""
                if latest.labels:
                    label_str = "{" + ",".join(f'{k}="{v}"' for k, v in latest.labels.items()) + "}"
                lines.append(f"{metric.name}{label_str} {latest.value}")
        return "\n".join(lines)


metrics_registry = MetricsRegistry()


REQUEST_COUNT = metrics_registry.register(
    "http_requests_total",
    MetricType.COUNTER,
    "Total number of HTTP requests",
)

REQUEST_LATENCY = metrics_registry.register(
    "http_request_duration_seconds",
    MetricType.HISTOGRAM,
    "HTTP request latency in seconds",
    "seconds",
)

REQUEST_ERRORS = metrics_registry.register(
    "http_errors_total",
    MetricType.COUNTER,
    "Total number of HTTP errors",
)

ACTIVE_REQUESTS = metrics_registry.register(
    "http_active_requests",
    MetricType.GAUGE,
    "Number of active HTTP requests",
)

DATABASE_CONNECTIONS = metrics_registry.register(
    "db_connections",
    MetricType.GAUGE,
    "Number of database connections",
)

DATABASE_LATENCY = metrics_registry.register(
    "db_query_duration_seconds",
    MetricType.HISTOGRAM,
    "Database query latency in seconds",
    "seconds",
)

REDIS_CONNECTIONS = metrics_registry.register(
    "redis_connections",
    MetricType.GAUGE,
    "Number of Redis connections",
)

REDIS_LATENCY = metrics_registry.register(
    "redis_operation_duration_seconds",
    MetricType.HISTOGRAM,
    "Redis operation latency in seconds",
    "seconds",
)

SERVICE_AVAILABILITY = metrics_registry.register(
    "service_availability_ratio",
    MetricType.GAUGE,
    "Service availability ratio (0-1)",
)

ERROR_RATE = metrics_registry.register(
    "error_rate",
    MetricType.GAUGE,
    "Error rate per minute",
)

CPU_USAGE = metrics_registry.register(
    "process_cpu_percent",
    MetricType.GAUGE,
    "Process CPU usage percentage",
    "percent",
)

MEMORY_USAGE = metrics_registry.register(
    "process_memory_bytes",
    MetricType.GAUGE,
    "Process memory usage in bytes",
    "bytes",
)


class RequestTracker:
    def __init__(self):
        self._active_requests: dict[str, float] = {}
        self._lock = threading.Lock()

    def start_request(self, request_id: str) -> float:
        start_time = time.perf_counter()
        with self._lock:
            self._active_requests[request_id] = start_time
            ACTIVE_REQUESTS.record(len(self._active_requests))
        return start_time

    def end_request(
        self,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        start_time: float,
    ):
        duration = time.perf_counter() - start_time
        labels = {"method": method, "path": path, "status": str(status_code)}
        
        with self._lock:
            self._active_requests.pop(request_id, None)
            ACTIVE_REQUESTS.record(len(self._active_requests))
        
        REQUEST_COUNT.record(1, labels)
        REQUEST_LATENCY.record(duration, labels)
        
        if status_code >= 400:
            REQUEST_ERRORS.record(1, labels)

    def get_active_count(self) -> int:
        with self._lock:
            return len(self._active_requests)


request_tracker = RequestTracker()


class SystemMetricsCollector:
    def __init__(self, collection_interval: int = 60):
        self.collection_interval = collection_interval
        self._running = False
        self._task: asyncio.Task | None = None
        self._process = psutil.Process()

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._collect_loop())
        logger.info("system_metrics_collector_started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("system_metrics_collector_stopped")

    async def _collect_loop(self):
        while self._running:
            try:
                await self._collect()
            except Exception as e:
                logger.error("metrics_collection_error", error=str(e))
            
            await asyncio.sleep(self.collection_interval)

    async def _collect(self):
        try:
            cpu_percent = self._process.cpu_percent()
            CPU_USAGE.record(cpu_percent)
        except Exception:
            pass

        try:
            memory_info = self._process.memory_info()
            MEMORY_USAGE.record(memory_info.rss)
        except Exception:
            pass

        try:
            db_pool_status = await self._get_db_pool_status()
            if db_pool_status:
                DATABASE_CONNECTIONS.record(db_pool_status.get("checked_out", 0))
        except Exception:
            pass

    async def _get_db_pool_status(self) -> dict[str, int] | None:
        try:
            from app.core.database import engine
            pool = engine.pool
            return {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
            }
        except Exception:
            return None


system_metrics_collector = SystemMetricsCollector()


class PerformanceMonitor:
    def __init__(self, window_size: int = 300):
        self.window_size = window_size
        self._response_times: deque[float] = deque(maxlen=10000)
        self._error_counts: deque[tuple[datetime, int]] = deque(maxlen=10000)
        self._request_counts: deque[tuple[datetime, int]] = deque(maxlen=10000)
        self._lock = threading.Lock()

    def record_response_time(self, duration: float):
        with self._lock:
            self._response_times.append(duration)

    def record_error(self):
        with self._lock:
            self._error_counts.append((datetime.now(timezone.utc), 1))

    def record_request(self):
        with self._lock:
            self._request_counts.append((datetime.now(timezone.utc), 1))

    def get_availability(self) -> float:
        with self._lock:
            if not self._request_counts:
                return 1.0
            
            cutoff = datetime.now(timezone.utc).timestamp() - self.window_size
            recent_requests = [
                (ts, count) for ts, count in self._request_counts
                if ts.timestamp() >= cutoff
            ]
            recent_errors = [
                (ts, count) for ts, count in self._error_counts
                if ts.timestamp() >= cutoff
            ]
            
            if not recent_requests:
                return 1.0
            
            total_requests = sum(count for _, count in recent_requests)
            total_errors = sum(count for _, count in recent_errors)
            
            if total_requests == 0:
                return 1.0
            
            return max(0.0, 1.0 - (total_errors / total_requests))

    def get_error_rate(self) -> float:
        with self._lock:
            cutoff = datetime.now(timezone.utc).timestamp() - 60
            recent_errors = [
                (ts, count) for ts, count in self._error_counts
                if ts.timestamp() >= cutoff
            ]
            return sum(count for _, count in recent_errors)

    def get_p50_latency(self) -> float:
        return self._get_percentile(50)

    def get_p95_latency(self) -> float:
        return self._get_percentile(95)

    def get_p99_latency(self) -> float:
        return self._get_percentile(99)

    def _get_percentile(self, percentile: float) -> float:
        with self._lock:
            if not self._response_times:
                return 0.0
            
            recent = list(self._response_times)[-1000:]
            
            if not recent:
                return 0.0
            
            sorted_values = sorted(recent)
            index = int(len(sorted_values) * percentile / 100)
            return sorted_values[min(index, len(sorted_values) - 1)]

    def get_summary(self) -> dict[str, Any]:
        return {
            "availability": round(self.get_availability() * 100, 2),
            "error_rate_per_minute": round(self.get_error_rate(), 2),
            "latency_p50_ms": round(self.get_p50_latency() * 1000, 2),
            "latency_p95_ms": round(self.get_p95_latency() * 1000, 2),
            "latency_p99_ms": round(self.get_p99_latency() * 1000, 2),
            "window_seconds": self.window_size,
        }


performance_monitor = PerformanceMonitor()
