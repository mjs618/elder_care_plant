"""
监控中间件
为模块提供统一的监控指标收集
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

logger = structlog.get_logger()

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code', 'module']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint', 'module'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
)

ACTIVE_REQUESTS = Gauge(
    'http_requests_active',
    'Active HTTP requests',
    ['method', 'module']
)

ERROR_COUNT = Counter(
    'http_errors_total',
    'Total HTTP errors',
    ['method', 'endpoint', 'error_type', 'module']
)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    监控中间件
    收集请求指标并暴露Prometheus格式数据
    """
    
    def __init__(self, app, module_name: str = "unknown"):
        super().__init__(app)
        self.module_name = module_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path == "/metrics":
            return Response(
                content=generate_latest(),
                media_type=CONTENT_TYPE_LATEST
            )
        
        method = request.method
        endpoint = self._get_endpoint_pattern(request)
        
        ACTIVE_REQUESTS.labels(method=method, module=self.module_name).inc()
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            status_code = response.status_code
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                module=self.module_name
            ).inc()
            
            return response
            
        except Exception as e:
            ERROR_COUNT.labels(
                method=method,
                endpoint=endpoint,
                error_type=type(e).__name__,
                module=self.module_name
            ).inc()
            raise
            
        finally:
            duration = time.time() - start_time
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=endpoint,
                module=self.module_name
            ).observe(duration)
            
            ACTIVE_REQUESTS.labels(method=method, module=self.module_name).dec()
            
            logger.info(
                "request_completed",
                method=method,
                endpoint=endpoint,
                duration_ms=round(duration * 1000, 2),
                module=self.module_name
            )
    
    def _get_endpoint_pattern(self, request: Request) -> str:
        """获取端点模式（替换路径参数为占位符）"""
        path = request.url.path
        
        import re
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path


def setup_monitoring(app, module_name: str):
    """
    设置监控
    
    Args:
        app: FastAPI应用实例
        module_name: 模块名称
    """
    app.add_middleware(MonitoringMiddleware, module_name=module_name)
    
    @app.get("/metrics")
    async def metrics():
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    
    logger.info("monitoring_setup_complete", module=module_name)
