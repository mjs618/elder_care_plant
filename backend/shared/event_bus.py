"""
Module event bus built on RabbitMQ with outbox-backed delivery.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable

import aio_pika
import structlog
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


class EventType(str, Enum):
    PATIENT_CREATED = "patient.created"
    PATIENT_UPDATED = "patient.updated"
    PATIENT_DELETED = "patient.deleted"

    ASSESSMENT_CREATED = "assessment.created"
    ASSESSMENT_UPDATED = "assessment.updated"
    ASSESSMENT_COMPLETED = "assessment.completed"
    ASSESSMENT_DELETED = "assessment.deleted"

    HEALTH_ALERT = "health.alert"
    VITAL_SIGN_RECORDED = "health.vital_sign_recorded"

    AI_CHAT_COMPLETED = "ai.chat_completed"


@dataclass
class Event:
    event_type: str
    source_module: str
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    version: str = "1.0"
    idempotency_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source_module": self.source_module,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "version": self.version,
        }
        if self.idempotency_key:
            data["idempotency_key"] = self.idempotency_key
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        return cls(
            event_id=data["event_id"],
            event_type=data["event_type"],
            source_module=data["source_module"],
            payload=data["payload"],
            timestamp=data["timestamp"],
            version=data.get("version", "1.0"),
            idempotency_key=data.get("idempotency_key"),
        )


class EventBus:
    EXCHANGE_NAME = "elder_care_events"

    def __init__(self, rabbitmq_url: str):
        self.url = rabbitmq_url
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: aio_pika.Channel | None = None
        self.exchange: aio_pika.Exchange | None = None
        self._subscribers: dict[str, list[Callable[[Event], Any]]] = {}
        self._queues: dict[str, aio_pika.Queue] = {}

    async def connect(self) -> None:
        logger.info("event_bus_connecting", url=self.url)
        self.connection = await aio_pika.connect_robust(self.url)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            self.EXCHANGE_NAME,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        logger.info("event_bus_connected")

    async def disconnect(self) -> None:
        if self.connection:
            await self.connection.close()
            logger.info("event_bus_disconnected")

    async def publish(self, event: Event) -> None:
        if not self.exchange:
            raise RuntimeError("Event bus not connected")

        event_type_value = event.event_type.value if hasattr(event.event_type, "value") else event.event_type
        routing_key = f"{event.source_module}.{event_type_value}"
        message = Message(
            body=json.dumps(event.to_dict()).encode(),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=event.event_id,
            timestamp=datetime.now(UTC),
        )
        await self.exchange.publish(message, routing_key=routing_key)
        logger.info(
            "event_published",
            event_id=event.event_id,
            event_type=event_type_value,
            routing_key=routing_key,
        )

    async def _is_processed(self, idempotency_key: str) -> bool:
        from app.core.database import AsyncSessionLocal
        from app.models.outbox import ProcessedEvent

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ProcessedEvent.idempotency_key).where(
                    ProcessedEvent.idempotency_key == idempotency_key
                )
            )
            return result.scalar_one_or_none() is not None

    async def _mark_processed(self, event: Event) -> bool:
        from app.core.database import AsyncSessionLocal
        from app.models.outbox import ProcessedEvent

        if not event.idempotency_key:
            return True

        async with AsyncSessionLocal() as session:
            session.add(
                ProcessedEvent(
                    idempotency_key=event.idempotency_key,
                    event_id=event.event_id,
                )
            )
            try:
                await session.commit()
                return True
            except IntegrityError:
                await session.rollback()
                return False

    async def subscribe(
        self,
        module_name: str,
        event_pattern: str,
        handler: Callable[[Event], Any],
    ) -> None:
        if not self.channel or not self.exchange:
            raise RuntimeError("Event bus not connected")

        queue_name = f"{module_name}.{event_pattern.replace('*', 'all').replace('.', '_')}"
        if queue_name not in self._queues:
            queue = await self.channel.declare_queue(
                queue_name,
                durable=True,
                arguments={"x-message-ttl": 86400000},
            )
            await queue.bind(self.exchange, routing_key=event_pattern)
            self._queues[queue_name] = queue
            logger.info(
                "event_queue_created",
                queue_name=queue_name,
                event_pattern=event_pattern,
            )

        self._subscribers.setdefault(event_pattern, []).append(handler)

        async def process_message(message: AbstractIncomingMessage) -> None:
            async with message.process():
                try:
                    event = Event.from_dict(json.loads(message.body.decode()))
                    if event.idempotency_key and await self._is_processed(event.idempotency_key):
                        logger.info(
                            "event_already_processed",
                            event_id=event.event_id,
                            idempotency_key=event.idempotency_key,
                        )
                        return

                    logger.info(
                        "event_received",
                        event_id=event.event_id,
                        event_type=event.event_type,
                    )

                    for subscriber in self._subscribers.get(event_pattern, []):
                        result = subscriber(event)
                        if asyncio.iscoroutine(result):
                            await result

                    if event.idempotency_key:
                        marked = await self._mark_processed(event)
                        if not marked:
                            logger.info(
                                "event_mark_processed_skipped",
                                event_id=event.event_id,
                                idempotency_key=event.idempotency_key,
                            )
                except Exception as exc:
                    logger.error("event_process_error", error=str(exc))
                    raise

        await self._queues[queue_name].consume(process_message)
        logger.info("event_subscribed", module=module_name, pattern=event_pattern)


class OutboxService:
    def __init__(self, db_session: AsyncSession, event_bus: EventBus | None = None):
        self.db = db_session
        self.event_bus = event_bus

    async def save_to_outbox(self, event: Event) -> "EventOutbox":
        from app.models.outbox import EventOutbox, OutboxStatus

        event_type_value = event.event_type.value if hasattr(event.event_type, "value") else event.event_type
        routing_key = f"{event.source_module}.{event_type_value}"
        outbox_entry = EventOutbox(
            event_id=event.event_id,
            event_type=event_type_value,
            source_module=event.source_module,
            payload=json.dumps(event.to_dict()),
            routing_key=routing_key,
            status=OutboxStatus.PENDING,
        )
        self.db.add(outbox_entry)
        await self.db.flush()
        logger.info(
            "event_saved_to_outbox",
            event_id=event.event_id,
            event_type=event_type_value,
        )
        return outbox_entry

    async def publish_pending_events(self) -> int:
        from app.models.outbox import EventOutbox, OutboxStatus

        if self.event_bus is None:
            raise RuntimeError("Event bus not configured for outbox publisher")

        result = await self.db.execute(
            select(EventOutbox)
            .where(EventOutbox.status == OutboxStatus.PENDING)
            .where(EventOutbox.retry_count < EventOutbox.max_retries)
            .order_by(EventOutbox.created_at)
            .limit(100)
        )
        pending_events = result.scalars().all()

        published_count = 0
        for outbox_entry in pending_events:
            try:
                event = Event.from_dict(json.loads(outbox_entry.payload))
                await self.event_bus.publish(event)
                outbox_entry.status = OutboxStatus.PUBLISHED
                outbox_entry.published_at = datetime.now(UTC)
                published_count += 1
                logger.info("outbox_event_published", event_id=outbox_entry.event_id)
            except Exception as exc:
                outbox_entry.retry_count += 1
                outbox_entry.last_error = str(exc)
                if outbox_entry.retry_count >= outbox_entry.max_retries:
                    outbox_entry.status = OutboxStatus.FAILED
                logger.error(
                    "outbox_event_failed",
                    event_id=outbox_entry.event_id,
                    error=str(exc),
                    retry_count=outbox_entry.retry_count,
                )

        await self.db.commit()
        return published_count


_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        raise RuntimeError("Event bus not initialized")
    return _event_bus


async def init_event_bus(rabbitmq_url: str) -> EventBus:
    global _event_bus
    _event_bus = EventBus(rabbitmq_url)
    await _event_bus.connect()
    return _event_bus


async def publish_event(
    db: AsyncSession,
    event_type: EventType | str,
    source_module: str,
    payload: dict[str, Any],
    idempotency_key: str | None = None,
) -> "EventOutbox":
    """
    统一的事件发布辅助函数
    
    Args:
        db: 数据库会话
        event_type: 事件类型
        source_module: 来源模块
        payload: 事件载荷
        idempotency_key: 幂等性键，如不提供则自动生成
    
    Returns:
        EventOutbox: 保存的 Outbox 记录
    """
    outbox_service = OutboxService(db)
    event = Event(
        event_type=event_type,
        source_module=source_module,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    return await outbox_service.save_to_outbox(event)
