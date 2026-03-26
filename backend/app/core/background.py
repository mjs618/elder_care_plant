"""
Elder Care Platform - Background Tasks
后台任务处理，包含完善的错误处理和重试机制
"""
import asyncio
import structlog
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from shared.event_bus import get_event_bus, OutboxService

logger = structlog.get_logger()

OUTBOX_PROCESS_INTERVAL = 5
OUTBOX_MAX_CONSECUTIVE_ERRORS = 5
OUTBOX_ERROR_BACKOFF_MULTIPLIER = 2


async def process_outbox_task():
    """
    定期处理 Outbox 中待发布的事件
    应在应用启动时作为后台任务运行
    包含指数退避和错误恢复机制
    """
    consecutive_errors = 0
    current_interval = OUTBOX_PROCESS_INTERVAL
    
    while True:
        try:
            async with AsyncSessionLocal() as db:
                event_bus = get_event_bus()
                outbox_service = OutboxService(db, event_bus)
                
                published_count = await outbox_service.publish_pending_events()
                
                if published_count > 0:
                    logger.info("outbox_processed", published_count=published_count)
                
                consecutive_errors = 0
                current_interval = OUTBOX_PROCESS_INTERVAL
                    
        except Exception as e:
            consecutive_errors += 1
            logger.error(
                "outbox_task_error",
                error=str(e),
                consecutive_errors=consecutive_errors,
            )
            
            if consecutive_errors >= OUTBOX_MAX_CONSECUTIVE_ERRORS:
                current_interval = min(
                    OUTBOX_PROCESS_INTERVAL * (OUTBOX_ERROR_BACKOFF_MULTIPLIER ** consecutive_errors),
                    300  # Max 5 minutes
                )
                logger.warning(
                    "outbox_task_backoff",
                    new_interval=current_interval,
                    consecutive_errors=consecutive_errors,
                )
        
        await asyncio.sleep(current_interval)


async def start_background_tasks():
    """
    启动所有后台任务
    """
    logger.info(
        "starting_background_tasks",
        timestamp=datetime.now(UTC).isoformat(),
    )
    asyncio.create_task(process_outbox_task())
