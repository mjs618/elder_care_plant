"""
Elder Care Platform - Background Tasks
后台任务处理
"""
import asyncio
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from shared.event_bus import get_event_bus, OutboxService

logger = structlog.get_logger()


async def process_outbox_task():
    """
    定期处理 Outbox 中待发布的事件
    应在应用启动时作为后台任务运行
    """
    while True:
        try:
            async with AsyncSessionLocal() as db:
                event_bus = get_event_bus()
                outbox_service = OutboxService(db, event_bus)
                
                published_count = await outbox_service.publish_pending_events()
                
                if published_count > 0:
                    logger.info("outbox_processed", published_count=published_count)
        except Exception as e:
            logger.error("outbox_task_error", error=str(e))
        
        await asyncio.sleep(5)


async def start_background_tasks():
    """
    启动所有后台任务
    """
    logger.info("starting_background_tasks")
    asyncio.create_task(process_outbox_task())
