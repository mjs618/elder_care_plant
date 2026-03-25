"""
患者管理模块 - 事件订阅者
"""
from shared.event_bus import Event
import structlog

logger = structlog.get_logger()


async def on_assessment_completed(event: Event):
    """
    评估完成事件处理
    可用于更新患者的评估状态
    """
    logger.info(
        "patient_module_assessment_completed",
        patient_id=event.payload.get("patient_id"),
        assessment_id=event.payload.get("assessment_id")
    )


async def setup_subscribers(event_bus):
    """
    设置患者模块的事件订阅
    """
    await event_bus.subscribe(
        module_name="patient_mgmt",
        event_pattern="assessment.assessment.completed",
        handler=on_assessment_completed
    )
    
    logger.info("patient_module_subscribers_setup_complete")
