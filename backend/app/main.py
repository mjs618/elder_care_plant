"""
Elder Care Platform - Application Factory
Assembles the FastAPI application with:
  - Lifespan context (DB init, module registry boot, super-admin bootstrap)
  - Core API routers (auth, tenants, platform admin)
  - Middleware stack
  - Health check endpoint
  - Event bus initialization
  - Background tasks for outbox processing
"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.middleware import register_middleware
from app.core.module_registry import CORE_MODULES, module_registry
from shared.event_bus import init_event_bus, get_event_bus

log = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup / shutdown handler.
    Runs once when the server starts and once when it shuts down.
    """
    log.info("elder_care_startup", env=settings.APP_ENV, version=settings.APP_VERSION)

    if settings.RABBITMQ_URL:
        try:
            await init_event_bus(settings.RABBITMQ_URL)
            log.info("event_bus_initialized")
            
            from app.core.background import start_background_tasks
            await start_background_tasks()
            log.info("background_tasks_started")
        except Exception as e:
            log.warning("event_bus_init_failed", error=str(e))

    for module_def in CORE_MODULES:
        module_registry.register(module_def)
        log.info("module_registered", slug=module_def.slug)

    from app.api.v1 import patients, assessments
    if (m := module_registry.get("patient_mgmt")):
        m.router = patients.router
    if (m := module_registry.get("assessment")):
        m.router = assessments.router

    for module_def in module_registry.all():
        if module_def.router is not None:
            app.include_router(
                module_def.router,
                prefix=module_def.router_prefix,
                tags=module_def.router_tags,
            )

    log.info("all_modules_mounted", count=len(module_registry.all()))

    yield

    log.info("elder_care_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Commercial Elder Care Platform — Multi-tenant SaaS API",
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    register_middleware(app)

    # ── Core routers (always mounted, not behind module gate) ─────────────────
    from app.api.v1 import auth, tenants, platform_admin
    app.include_router(auth.router,           prefix="/api/v1/auth",    tags=["认证"])
    app.include_router(tenants.router,        prefix="/api/v1/tenants", tags=["租户管理"])
    app.include_router(platform_admin.router, prefix="/api/v1/admin",   tags=["平台运营"])

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", include_in_schema=False)
    async def health():
        return JSONResponse({"status": "ok", "version": settings.APP_VERSION})

    @app.get("/api/v1/modules", tags=["平台运营"])
    async def list_modules():
        """Returns all registered modules. Used by frontend to build navigation."""
        modules_data = []
        for m in module_registry.all():
            module_dict = {
                "slug": m.slug,
                "display_name": m.display_name,
                "description": m.description,
                "version": m.version,
                "permissions": m.permissions,
            }
            if m.ui_meta:
                module_dict["ui_meta"] = {
                    "icon": m.ui_meta.icon,
                    "path": m.ui_meta.path,
                    "children": [{"title": c.title, "path": c.path} for c in m.ui_meta.children],
                }
            modules_data.append(module_dict)
        
        return {
            "code": 200,
            "message": "success",
            "data": modules_data,
        }

    return app


app = create_app()
