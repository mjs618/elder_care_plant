"""
日志配置模块
提供统一的日志配置和结构化日志输出
"""
import sys
import structlog
from typing import Any
from datetime import datetime


def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    json_output: bool = True
):
    """
    设置结构化日志
    
    Args:
        service_name: 服务名称
        log_level: 日志级别
        json_output: 是否输出JSON格式
    """
    
    def add_service_info(
        logger: structlog.BoundLogger,
        method_name: str,
        event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        event_dict["service"] = service_name
        event_dict["timestamp"] = datetime.utcnow().isoformat()
        return event_dict
    
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_service_info,
    ]
    
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    import logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """获取结构化日志记录器"""
    return structlog.get_logger(name)


class LogContext:
    """
    日志上下文管理器
    用于在请求范围内添加上下文信息
    """
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self._token = None
    
    def __enter__(self):
        self._token = structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, *args):
        if self._token:
            structlog.contextvars.unbind_contextvars(*self.context.keys())


def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: str | None = None,
    tenant_id: str | None = None,
    **extra
):
    """
    记录请求日志
    
    Args:
        method: HTTP方法
        path: 请求路径
        status_code: 响应状态码
        duration_ms: 请求耗时（毫秒）
        user_id: 用户ID
        tenant_id: 租户ID
        **extra: 额外信息
    """
    logger = get_logger("request")
    
    log_data = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        **extra
    }
    
    if user_id:
        log_data["user_id"] = user_id
    if tenant_id:
        log_data["tenant_id"] = tenant_id
    
    if status_code >= 500:
        logger.error("request_failed", **log_data)
    elif status_code >= 400:
        logger.warning("request_error", **log_data)
    else:
        logger.info("request_completed", **log_data)


def log_event(
    event_type: str,
    source_module: str,
    payload: dict,
    success: bool = True,
    **extra
):
    """
    记录事件日志
    
    Args:
        event_type: 事件类型
        source_module: 来源模块
        payload: 事件负载
        success: 是否成功
        **extra: 额外信息
    """
    logger = get_logger("event")
    
    log_data = {
        "event_type": event_type,
        "source_module": source_module,
        "success": success,
        **extra
    }
    
    if success:
        logger.info("event_processed", **log_data)
    else:
        logger.error("event_failed", **log_data)
