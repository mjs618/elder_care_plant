"""
Elder Care Platform - Logging Configuration
Provides structured logging with:
  - JSON format for production
  - Human-readable format for development
  - Request context binding
  - Sentry integration for error tracking
"""
import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from app.core.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """
    Configure structured logging for the application.
    Should be called once at application startup.
    """
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    
    if settings.LOG_FORMAT == "json" or settings.is_production:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL),
    )
    
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)


class RequestLogger:
    """
    Context manager for request-scoped logging.
    Automatically binds request context to all log messages.
    """
    
    def __init__(
        self,
        request_id: str,
        method: str,
        path: str,
        user_id: str | None = None,
        tenant_id: str | None = None,
    ):
        self.request_id = request_id
        self.method = method
        self.path = path
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.logger = get_logger("request")
    
    def __enter__(self) -> "RequestLogger":
        structlog.contextvars.bind_contextvars(
            request_id=self.request_id,
            method=self.method,
            path=self.path,
        )
        if self.user_id:
            structlog.contextvars.bind_contextvars(user_id=self.user_id)
        if self.tenant_id:
            structlog.contextvars.bind_contextvars(tenant_id=self.tenant_id)
        return self
    
    def __exit__(self, *args: Any) -> None:
        structlog.contextvars.unbind_contextvars(
            "request_id", "method", "path", "user_id", "tenant_id"
        )
    
    def info(self, message: str, **kwargs: Any) -> None:
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        self.logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        self.logger.debug(message, **kwargs)


def log_performance(
    operation: str,
    duration_ms: float,
    success: bool = True,
    **kwargs: Any,
) -> None:
    """Log performance metrics for operations."""
    logger = get_logger("performance")
    logger.info(
        "operation_completed",
        operation=operation,
        duration_ms=round(duration_ms, 2),
        success=success,
        **kwargs,
    )


def log_business_event(
    event_type: str,
    entity_type: str,
    entity_id: str,
    action: str,
    **kwargs: Any,
) -> None:
    """Log business events for audit trail."""
    logger = get_logger("audit")
    logger.info(
        "business_event",
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        **kwargs,
    )
