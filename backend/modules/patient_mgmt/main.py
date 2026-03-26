"""
患者管理模块 - 独立入口
可独立运行，也可作为子应用挂载
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog

from shared.event_bus import get_event_bus
from modules.patient_mgmt.api.routes import router
from modules.patient_mgmt.subscribers.event_handlers import setup_subscribers

logger = structlog.get_logger()

MODULE_NAME = "patient_mgmt"
MODULE_VERSION = "1.0.0"


@asynccontextmanager
async def module_lifespan(app: FastAPI):
    """模块生命周期"""
    logger.info("module_starting", module=MODULE_NAME, version=MODULE_VERSION)
    
    try:
        event_bus = get_event_bus()
        await setup_subscribers(event_bus)
    except Exception as e:
        logger.warning("event_bus_not_available", error=str(e))
    
    yield
    
    logger.info("module_stopping", module=MODULE_NAME)


def create_module_app() -> FastAPI:
    """
    创建模块应用
    用于独立部署场景
    """
    app = FastAPI(
        title="患者管理模块",
        version=MODULE_VERSION,
        description="患者基本信息、健康档案、照护等级管理",
        lifespan=module_lifespan,
    )
    
    app.include_router(router, prefix="/api/v1/patients", tags=["患者管理"])
    
    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "module": MODULE_NAME,
            "version": MODULE_VERSION
        }
    
    return app


if __name__ == "__main__":
    import uvicorn
    app = create_module_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)
