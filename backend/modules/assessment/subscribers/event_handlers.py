"""
评估管理模块 - 事件订阅者
"""
from shared.event_bus import Event
import structlog

logger = structlog.get_logger()


async def on_patient_created(event: Event):
    """
    患者创建事件处理
    可用于初始化患者的评估档案
    """
    logger.info(
        "assessment_module_patient_created",
        patient_id=event.payload.get("patient_id"),
        patient_name=event.payload.get("full_name")
    )


async def on_patient_deleted(event: Event):
    """
    患者删除事件处理
    清理相关的评估数据
    """
    patient_id = event.payload.get("patient_id")
    logger.info(
        "assessment_module_patient_deleted",
        patient_id=patient_id
    )


async def setup_subscribers(event_bus):
    """
    设置评估模块的事件订阅
    """
    await event_bus.subscribe(
        module_name="assessment",
        event_pattern="patient_mgmt.patient.created",
        handler=on_patient_created
    )
    
    await event_bus.subscribe(
        module_name="assessment",
        event_pattern="patient_mgmt.patient.deleted",
        handler=on_patient_deleted
    )
    
    logger.info("assessment_module_subscribers_setup_complete")
