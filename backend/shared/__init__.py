"""
共享代码包
提供跨模块使用的通用功能
"""
from shared.event_bus import (
    Event,
    EventBus,
    EventType,
    get_event_bus,
    init_event_bus,
)
from shared.database import get_db, get_tenant_db

__all__ = [
    "Event",
    "EventBus",
    "EventType",
    "get_event_bus",
    "init_event_bus",
    "get_db",
    "get_tenant_db",
]
