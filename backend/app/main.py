"""
Elder Care Platform - Application Factory
Assembles the FastAPI application with:
  - Lifespan context (DB init, module registry boot, super-admin bootstrap)
  - Core API routers
  - Middleware stack
  - Health check endpoints
  - Event bus initialization
  - Background tasks for outbox processing
  - Service monitoring and auto-recovery
  - Global exception handlers
"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.middleware import register_middleware
from app.core.module_registry import CORE_MODULES, module_registry
from shared.event_bus import get_event_bus, init_event_bus

log = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(
        "elder_care_startup",
        env=settings.APP_ENV,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
    )

    from app.core.service_monitor import start_service_monitor, stop_service_monitor

    await start_service_monitor()
    log.info("service_monitor_started")

    if settings.RABBITMQ_URL:
        try:
            await init_event_bus(settings.RABBITMQ_URL)
            log.info("event_bus_initialized")

            from app.core.background import start_background_tasks

            await start_background_tasks()
            log.info("background_tasks_started")
        except Exception as exc:
            log.warning("event_bus_init_failed", error=str(exc))

    for module_def in CORE_MODULES:
        module_registry.register(module_def)
        log.info("module_registered", slug=module_def.slug)

    from app.api.v1 import assessments, patients

    if (module := module_registry.get("patient_mgmt")):
        module.router = patients.router
    if (module := module_registry.get("assessment")):
        module.router = assessments.router

    for module_def in module_registry.all():
        if module_def.router is not None:
            app.include_router(
                module_def.router,
                prefix=module_def.router_prefix,
                tags=module_def.router_tags,
            )

    log.info("all_modules_mounted", count=len(module_registry.all()))

    yield

    log.info("elder_care_shutdown_initiated")
    await stop_service_monitor()
    log.info("service_monitor_stopped")

    try:
        event_bus = get_event_bus()
        await event_bus.disconnect()
        log.info("event_bus_disconnected")
    except Exception:
        pass

    log.info("elder_care_shutdown_complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Commercial Elder Care Platform - Multi-tenant SaaS API",
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    register_middleware(app)
    register_exception_handlers(app)

    from app.api.v1 import auth, modules, monitoring, platform_admin, tenants, versions

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["tenants"])
    app.include_router(platform_admin.router, prefix="/api/v1/admin", tags=["platform-admin"])
    app.include_router(monitoring.router, prefix="/api/v1", tags=["monitoring"])
    app.include_router(versions.router, prefix="/api/v1", tags=["versions"])
    app.include_router(modules.router, prefix="/api/v1/modules", tags=["modules"])

    from app.core.health import router as health_router

    app.include_router(health_router, tags=["health"])
    return app


app = create_app()
