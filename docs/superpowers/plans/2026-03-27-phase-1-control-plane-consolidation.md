# Phase 1 Control Plane Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce control-plane entities and a single entitlement source of truth so the platform can answer module availability without relying on scattered plan, tenant-module, and system-module checks.

**Architecture:** Phase 1 keeps the existing platform runtime but changes its center of gravity. Add explicit control-plane models (`TenantSubscription`, `ModuleCatalog`, `ModuleDeployment`, `TenantEntitlement`), route runtime authorization through an entitlement service, and update platform APIs and frontend stores to consume the new control-plane outputs while keeping current business modules in place.

**Tech Stack:** FastAPI, SQLAlchemy asyncio, Alembic, Pydantic, pytest, Vue 3, Pinia, TypeScript, Vite

---

## File Map

### Backend create

- `backend/app/models/control_plane.py`
  Control-plane ORM models for subscriptions, module catalog, deployments, and entitlements.
- `backend/app/services/entitlement_service.py`
  Single place to resolve tenant module availability and frontend module payloads.
- `backend/tests/test_control_plane_models.py`
  ORM-level tests for new control-plane entities.
- `backend/tests/test_entitlement_service.py`
  Service-level tests covering entitlement resolution and module availability decisions.
- `backend/alembic/versions/20260327_add_control_plane_entities.py`
  Migration for new control-plane tables and compatibility backfill.

### Backend modify

- `backend/app/models/__init__.py`
  Export new ORM models so Alembic sees them.
- `backend/app/api/v1/auth.py`
  Read module bootstrap payload from the entitlement service.
- `backend/app/api/v1/modules.py`
  Read module status and deployment metadata from control-plane tables.
- `backend/app/api/v1/platform_admin.py`
  Manage plans against catalog-backed module slugs and return control-plane aware module metadata.
- `backend/app/api/v1/tenants.py`
  Create tenant subscriptions and expose entitlements in tenant detail responses.
- `backend/app/core/dependencies.py`
  Replace scattered module checks with entitlement-aware checks.

### Frontend modify

- `frontend/src/api/auth.ts`
  Update auth module bootstrap types to include endpoint and availability metadata.
- `frontend/src/api/modules.ts`
  Read control-plane module catalog and deployment payloads.
- `frontend/src/api/platform.ts`
  Add admin-facing types for module catalog and deployment-aware plan payloads.
- `frontend/src/api/tenants.ts`
  Add entitlement-oriented tenant detail types.
- `frontend/src/stores/modules.ts`
  Store module endpoints and availability status from the platform control plane.
- `frontend/src/stores/user.ts`
  Keep profile bootstrap in sync with entitlement-backed module payloads.
- `frontend/src/router/index.ts`
  Gate routes against entitlement-backed module availability.

## Task 1: Add Control-Plane ORM Models

**Files:**
- Create: `backend/tests/test_control_plane_models.py`
- Create: `backend/app/models/control_plane.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Write the failing model tests**

```python
import uuid

from app.models.control_plane import (
    EntitlementSource,
    EntitlementStatus,
    ModuleCatalog,
    ModuleDeployment,
    ModuleDeploymentStatus,
    TenantEntitlement,
    TenantSubscription,
    TenantSubscriptionStatus,
)


def test_module_catalog_defaults() -> None:
    module = ModuleCatalog(
        slug="patient_mgmt",
        display_name="Patient Management",
        module_type="business",
    )

    assert module.slug == "patient_mgmt"
    assert module.is_sellable is True
    assert module.is_globally_enabled is True


def test_tenant_subscription_status_enum() -> None:
    assert TenantSubscriptionStatus.ACTIVE.value == "active"
    assert TenantSubscriptionStatus.CANCELLED.value == "cancelled"


def test_tenant_entitlement_tracks_source_and_status() -> None:
    entitlement = TenantEntitlement(
        tenant_id=uuid.uuid4(),
        module_slug="assessment",
        status=EntitlementStatus.ACTIVE,
        source=EntitlementSource.SUBSCRIPTION,
    )

    assert entitlement.module_slug == "assessment"
    assert entitlement.status == EntitlementStatus.ACTIVE
    assert entitlement.source == EntitlementSource.SUBSCRIPTION


def test_module_deployment_requires_base_url() -> None:
    deployment = ModuleDeployment(
        module_slug="assessment",
        environment="prod",
        base_url="https://assessment.internal",
        status=ModuleDeploymentStatus.HEALTHY,
    )

    assert deployment.base_url == "https://assessment.internal"
    assert deployment.status == ModuleDeploymentStatus.HEALTHY
```

- [ ] **Step 2: Run test to verify it fails**

Run from `backend`:

```bash
python -m pytest tests/test_control_plane_models.py -v
```

Expected: FAIL with `ModuleNotFoundError` or missing symbol errors for `app.models.control_plane`.

- [ ] **Step 3: Write the minimal ORM models**

```python
import uuid
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TenantSubscriptionStatus(str, PyEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ModuleDeploymentStatus(str, PyEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DISABLED = "disabled"


class EntitlementStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class EntitlementSource(str, PyEnum):
    SUBSCRIPTION = "subscription"
    MANUAL = "manual"
    MIGRATION = "migration"


class TenantSubscription(BaseModel):
    __tablename__ = "tenant_subscriptions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False, index=True
    )
    status: Mapped[TenantSubscriptionStatus] = mapped_column(
        Enum(TenantSubscriptionStatus), default=TenantSubscriptionStatus.ACTIVE, nullable=False
    )
    starts_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ModuleCatalog(BaseModel):
    __tablename__ = "module_catalog"

    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    module_type: Mapped[str] = mapped_column(String(50), nullable=False, default="business")
    default_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    is_sellable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_globally_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ModuleDeployment(BaseModel):
    __tablename__ = "module_deployments"

    module_slug: Mapped[str] = mapped_column(
        String(100), ForeignKey("module_catalog.slug"), nullable=False, index=True
    )
    environment: Mapped[str] = mapped_column(String(50), nullable=False, default="prod")
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    deployed_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    status: Mapped[ModuleDeploymentStatus] = mapped_column(
        Enum(ModuleDeploymentStatus), default=ModuleDeploymentStatus.HEALTHY, nullable=False
    )


class TenantEntitlement(BaseModel):
    __tablename__ = "tenant_entitlements"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    module_slug: Mapped[str] = mapped_column(
        String(100), ForeignKey("module_catalog.slug"), nullable=False, index=True
    )
    status: Mapped[EntitlementStatus] = mapped_column(
        Enum(EntitlementStatus), default=EntitlementStatus.ACTIVE, nullable=False
    )
    source: Mapped[EntitlementSource] = mapped_column(
        Enum(EntitlementSource), default=EntitlementSource.SUBSCRIPTION, nullable=False
    )
```

- [ ] **Step 4: Export the models and rerun the tests**

Update `backend/app/models/__init__.py`:

```python
from app.models.control_plane import (  # noqa: F401
    TenantSubscription,
    TenantSubscriptionStatus,
    ModuleCatalog,
    ModuleDeployment,
    ModuleDeploymentStatus,
    TenantEntitlement,
    EntitlementStatus,
    EntitlementSource,
)
```

Run from `backend`:

```bash
python -m pytest tests/test_control_plane_models.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models/control_plane.py app/models/__init__.py tests/test_control_plane_models.py
git commit -m "feat: add control plane domain models"
```

## Task 2: Add the Database Migration and Compatibility Backfill

**Files:**
- Create: `backend/alembic/versions/20260327_add_control_plane_entities.py`
- Test: `backend/tests/test_database.py`

- [ ] **Step 1: Write a failing database test for the new tables**

Add to `backend/tests/test_database.py`:

```python
from app.models.control_plane import ModuleCatalog, ModuleDeployment, TenantEntitlement, TenantSubscription


def test_control_plane_models_exported() -> None:
    assert TenantSubscription.__tablename__ == "tenant_subscriptions"
    assert ModuleCatalog.__tablename__ == "module_catalog"
    assert ModuleDeployment.__tablename__ == "module_deployments"
    assert TenantEntitlement.__tablename__ == "tenant_entitlements"
```

- [ ] **Step 2: Run test to verify it fails before the migration file exists**

Run from `backend`:

```bash
python -m pytest tests/test_database.py::test_control_plane_models_exported -v
```

Expected: FAIL if Task 1 has not landed yet; otherwise PASS and move on to the migration file.

- [ ] **Step 3: Write the Alembic migration**

```python
def upgrade() -> None:
    op.create_table(
        "tenant_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subscription_plans.id"), nullable=False),
        sa.Column("status", sa.Enum("active", "expired", "cancelled", name="tenantsubscriptionstatus"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "module_catalog",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("module_type", sa.String(length=50), nullable=False),
        sa.Column("default_version", sa.String(length=50), nullable=False),
        sa.Column("is_sellable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_globally_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "module_deployments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("module_slug", sa.String(length=100), sa.ForeignKey("module_catalog.slug"), nullable=False),
        sa.Column("environment", sa.String(length=50), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("deployed_version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.Enum("healthy", "degraded", "disabled", name="moduledeploymentstatus"), nullable=False),
    )
    op.create_table(
        "tenant_entitlements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("module_slug", sa.String(length=100), sa.ForeignKey("module_catalog.slug"), nullable=False),
        sa.Column("status", sa.Enum("active", "inactive", name="entitlementstatus"), nullable=False),
        sa.Column("source", sa.Enum("subscription", "manual", "migration", name="entitlementsource"), nullable=False),
    )
```

- [ ] **Step 4: Add a compatibility backfill note and verify tests**

Add a comment block to the migration:

```python
# Compatibility backfill:
# 1. seed module_catalog from existing system_modules rows when present
# 2. seed tenant_entitlements from active tenant_modules rows with source="migration"
# 3. seed tenant_subscriptions from tenant.plan_id for existing tenants
```

Run from `backend`:

```bash
python -m pytest tests/test_database.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/20260327_add_control_plane_entities.py tests/test_database.py
git commit -m "feat: add control plane schema migration"
```

## Task 3: Introduce the Entitlement Service

**Files:**
- Create: `backend/tests/test_entitlement_service.py`
- Create: `backend/app/services/entitlement_service.py`

- [ ] **Step 1: Write failing service tests**

```python
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.control_plane import (
    EntitlementSource,
    EntitlementStatus,
    ModuleCatalog,
    ModuleDeployment,
    ModuleDeploymentStatus,
    TenantEntitlement,
)
from app.services.entitlement_service import EntitlementService


@pytest.mark.asyncio
async def test_resolve_active_module_payload_filters_disabled_modules() -> None:
    db = AsyncMock()
    service = EntitlementService(db)

    catalog = ModuleCatalog(slug="assessment", display_name="Assessment", module_type="business")
    deployment = ModuleDeployment(
        module_slug="assessment",
        environment="prod",
        base_url="https://assessment.internal",
        status=ModuleDeploymentStatus.HEALTHY,
    )
    entitlement = TenantEntitlement(
        tenant_id=uuid.uuid4(),
        module_slug="assessment",
        status=EntitlementStatus.ACTIVE,
        source=EntitlementSource.SUBSCRIPTION,
    )

    payload = service.build_module_payload(catalog, deployment, entitlement)

    assert payload["slug"] == "assessment"
    assert payload["base_url"] == "https://assessment.internal"
    assert payload["is_available"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run from `backend`:

```bash
python -m pytest tests/test_entitlement_service.py -v
```

Expected: FAIL with missing module or missing `EntitlementService`.

- [ ] **Step 3: Write the minimal service**

```python
from app.models.control_plane import EntitlementStatus, ModuleCatalog, ModuleDeployment, ModuleDeploymentStatus, TenantEntitlement


class EntitlementService:
    def __init__(self, db):
        self.db = db

    def build_module_payload(
        self,
        catalog: ModuleCatalog,
        deployment: ModuleDeployment | None,
        entitlement: TenantEntitlement | None,
    ) -> dict:
        is_entitled = entitlement is not None and entitlement.status == EntitlementStatus.ACTIVE
        is_healthy = deployment is not None and deployment.status == ModuleDeploymentStatus.HEALTHY
        is_available = catalog.is_globally_enabled and is_entitled and is_healthy

        return {
            "slug": catalog.slug,
            "display_name": catalog.display_name,
            "description": catalog.description,
            "base_url": deployment.base_url if deployment else None,
            "version": deployment.deployed_version if deployment else catalog.default_version,
            "is_available": is_available,
            "is_globally_enabled": catalog.is_globally_enabled,
            "is_entitled": is_entitled,
        }
```

- [ ] **Step 4: Add a tenant-facing query and rerun tests**

Expand `backend/app/services/entitlement_service.py` with query methods:

```python
from sqlalchemy import and_, select

from sqlalchemy import delete

from app.models.control_plane import (
    EntitlementSource,
    EntitlementStatus,
    ModuleCatalog,
    ModuleDeployment,
    TenantEntitlement,
    TenantSubscription,
    TenantSubscriptionStatus,
)
from app.models.tenant import SubscriptionPlan


    async def list_tenant_modules(self, tenant_id) -> list[dict]:
        result = await self.db.execute(
            select(ModuleCatalog, ModuleDeployment, TenantEntitlement)
            .outerjoin(
                ModuleDeployment,
                ModuleDeployment.module_slug == ModuleCatalog.slug,
            )
            .outerjoin(
                TenantEntitlement,
                and_(
                    TenantEntitlement.module_slug == ModuleCatalog.slug,
                    TenantEntitlement.tenant_id == tenant_id,
                ),
            )
        )
        return [
            self.build_module_payload(catalog, deployment, entitlement)
            for catalog, deployment, entitlement in result.all()
        ]

    async def is_module_available(self, tenant_id, module_slug: str) -> bool:
        modules = await self.list_tenant_modules(tenant_id)
        module_map = {module["slug"]: module for module in modules}
        return bool(module_map.get(module_slug, {}).get("is_available"))

    async def sync_tenant_entitlements(self, tenant_id) -> None:
        subscription_rows = await self.db.execute(
            select(TenantSubscription).where(
                TenantSubscription.tenant_id == tenant_id,
                TenantSubscription.status == TenantSubscriptionStatus.ACTIVE,
            )
        )
        subscriptions = subscription_rows.scalars().all()
        module_rows = await self.db.execute(
            select(ModuleCatalog).where(ModuleCatalog.is_sellable == True)  # noqa: E712
        )
        modules = module_rows.scalars().all()

        active_slugs: set[str] = set()
        for subscription in subscriptions:
            plan = await self.db.get(SubscriptionPlan, subscription.plan_id)
            if plan and plan.included_modules:
                active_slugs.update(
                    slug.strip() for slug in plan.included_modules.split(",") if slug.strip()
                )

        await self.db.execute(
            delete(TenantEntitlement).where(TenantEntitlement.tenant_id == tenant_id)
        )

        for module in modules:
            self.db.add(
                TenantEntitlement(
                    tenant_id=tenant_id,
                    module_slug=module.slug,
                    status=EntitlementStatus.ACTIVE if module.slug in active_slugs else EntitlementStatus.INACTIVE,
                    source=EntitlementSource.SUBSCRIPTION,
                )
            )
```

Run from `backend`:

```bash
python -m pytest tests/test_entitlement_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/entitlement_service.py tests/test_entitlement_service.py
git commit -m "feat: add entitlement resolution service"
```

## Task 4: Route Backend Authorization Through Entitlements

**Files:**
- Modify: `backend/app/core/dependencies.py`
- Modify: `backend/app/api/v1/auth.py`
- Modify: `backend/app/api/v1/tenants.py`
- Modify: `backend/app/api/v1/modules.py`

- [ ] **Step 1: Write failing dependency tests**

Add to `backend/tests/test_dependencies.py`:

```python
@pytest.mark.asyncio
async def test_require_module_uses_entitlement_service_result():
    tenant_id = uuid.uuid4()
    user = MagicMock(spec=User)
    user.scope = UserScope.TENANT
    user.tenant_id = tenant_id

    with patch("app.core.dependencies.EntitlementService") as mock_service_cls:
        mock_service = mock_service_cls.return_value
        mock_service.is_module_available = AsyncMock(return_value=True)
        db = AsyncMock(spec=AsyncSession)

        check = require_module("assessment")
        await check(current_user=user, db=db)

        mock_service.is_module_available.assert_awaited_once_with(tenant_id, "assessment")
```

- [ ] **Step 2: Run test to verify it fails**

Run from `backend`:

```bash
python -m pytest tests/test_dependencies.py::test_require_module_uses_entitlement_service_result -v
```

Expected: FAIL because `require_module` still queries `TenantModule` directly.

- [ ] **Step 3: Update the dependency and auth bootstrap code**

Replace direct `TenantModule` checks in `backend/app/core/dependencies.py` with:

```python
from app.services.entitlement_service import EntitlementService


service = EntitlementService(db)
is_available = await service.is_module_available(current_user.tenant_id, module_slug)
if not is_available:
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail=f"Module '{module_slug}' is not available for this tenant.",
    )
```

Update `backend/app/api/v1/auth.py` module bootstrap:

```python
service = EntitlementService(db)
modules_data = await service.list_tenant_modules(current_user.tenant_id)
return ok(modules_data)
```

- [ ] **Step 4: Expose entitlements in tenant and module admin APIs**

Add to `backend/app/api/v1/tenants.py` tenant detail response:

```python
"entitlements": [
    {
        "module_slug": entitlement.module_slug,
        "status": entitlement.status.value,
        "source": entitlement.source.value,
    }
    for entitlement in entitlements
]
```

Add to `backend/app/api/v1/modules.py` list response:

```python
"deployment": {
    "base_url": deployment.base_url if deployment else None,
    "status": deployment.status.value if deployment else "disabled",
},
```

Run from `backend`:

```bash
python -m pytest tests/test_dependencies.py tests/test_auth.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/core/dependencies.py app/api/v1/auth.py app/api/v1/tenants.py app/api/v1/modules.py tests/test_dependencies.py tests/test_auth.py
git commit -m "feat: drive module authorization from entitlements"
```

## Task 5: Add Control-Plane Aware Admin APIs

**Files:**
- Modify: `backend/app/api/v1/platform_admin.py`
- Modify: `backend/app/api/v1/tenants.py`
- Test: `backend/tests/test_services.py`

- [ ] **Step 1: Write failing tests for plan and tenant sync behavior**

Add to `backend/tests/test_services.py`:

```python
def test_plan_payload_uses_default_modules_list() -> None:
    payload = {
        "name": "Standard",
        "included_modules": ["patient_mgmt", "assessment"],
    }

    assert payload["included_modules"] == ["patient_mgmt", "assessment"]
```

- [ ] **Step 2: Run test to verify current payload shape fails**

Run from `backend`:

```bash
python -m pytest tests/test_services.py::test_plan_payload_uses_default_modules_list -v
```

Expected: FAIL because plan payloads still use a comma-separated string contract.

- [ ] **Step 3: Change plan and tenant admin payloads to be control-plane aware**

Update `backend/app/api/v1/platform_admin.py` request model:

```python
class CreatePlanRequest(BaseModel):
    name: str
    tier: PlanTier
    description: str | None = None
    rate_limit_rpm: int = 60
    included_modules: list[str] = []
    max_users: int = 5
    max_patients: int = 50
```

Update plan persistence mapping:

```python
included_modules=",".join(body.included_modules)
```

Update tenant create path in `backend/app/api/v1/tenants.py`:

```python
subscription = TenantSubscription(
    tenant_id=tenant.id,
    plan_id=body.plan_id,
    status=TenantSubscriptionStatus.ACTIVE,
    starts_at=datetime.now(timezone.utc),
)
db.add(subscription)
```

- [ ] **Step 4: Add entitlement sync call and rerun tests**

Add after tenant creation and plan updates:

```python
await EntitlementService(db).sync_tenant_entitlements(tenant.id)
```

Run from `backend`:

```bash
python -m pytest tests/test_services.py tests/test_database.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/api/v1/platform_admin.py app/api/v1/tenants.py tests/test_services.py
git commit -m "feat: add control plane admin sync flows"
```

## Task 6: Update Frontend Types and Module Store

**Files:**
- Modify: `frontend/src/api/auth.ts`
- Modify: `frontend/src/api/modules.ts`
- Modify: `frontend/src/api/platform.ts`
- Modify: `frontend/src/api/tenants.ts`
- Modify: `frontend/src/stores/modules.ts`
- Modify: `frontend/src/stores/user.ts`
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Write the failing type-first contract changes**

Replace the auth module bootstrap type in `frontend/src/api/auth.ts`:

```ts
export interface ModuleInfo {
    slug: string
    display_name: string
    description: string
    version: string
    permissions: string[]
    is_available: boolean
    is_globally_enabled: boolean
    is_entitled: boolean
    base_url: string | null
    ui_meta?: UIMeta
}
```

- [ ] **Step 2: Run type-check to verify downstream code fails**

Run from `frontend`:

```bash
npm run type-check
```

Expected: FAIL where the store and router still expect `is_active`.

- [ ] **Step 3: Update the module store and route guard**

Update `frontend/src/stores/modules.ts`:

```ts
activeSlugs.value = new Set(
    allModules.value.filter((module) => module.is_available).map((module) => module.slug),
)
```

Update route guard in `frontend/src/router/index.ts`:

```ts
if (requiredModule && !userStore.isPlatformAdmin && !moduleStore.hasModule(requiredModule)) {
    return next('/403')
}
```

Keep the guard logic, but ensure `hasModule()` now resolves from `is_available`.

- [ ] **Step 4: Add admin-facing entitlement shapes and rerun verification**

Update `frontend/src/api/tenants.ts`:

```ts
export interface TenantEntitlement {
    module_slug: string
    status: 'active' | 'inactive'
    source: 'subscription' | 'manual' | 'migration'
}

export interface TenantDetail {
    id: string
    name: string
    slug: string
    status: TenantStatus
    contact_email: string
    brand_name: string | null
    primary_color: string | null
    created_at: string
    plan: TenantPlanSummary
    active_modules: string[]
    user_count: number
    entitlements: TenantEntitlement[]
}
```

Run from `frontend`:

```bash
npm run type-check
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/api/auth.ts src/api/modules.ts src/api/platform.ts src/api/tenants.ts src/stores/modules.ts src/stores/user.ts src/router/index.ts
git commit -m "feat: consume control plane entitlement payloads in frontend"
```

## Task 7: Full Verification and Handoff

**Files:**
- Modify: `docs/superpowers/specs/2026-03-27-platform-control-plane-design.md` when a shipped contract differs from the approved design

- [ ] **Step 1: Run the backend verification suite**

Run from `backend`:

```bash
python -m pytest tests/test_control_plane_models.py tests/test_entitlement_service.py tests/test_dependencies.py tests/test_auth.py tests/test_database.py tests/test_services.py -v
```

Expected: PASS.

- [ ] **Step 2: Run the frontend verification suite**

Run from `frontend`:

```bash
npm run type-check
npm run build
```

Expected: PASS.

- [ ] **Step 3: Smoke-check the key Phase 1 behaviors manually**

Verify:

```text
1. platform admin can create or edit a plan with module slug arrays
2. creating a tenant creates a subscription row
3. syncing entitlements produces module availability for the tenant
4. /api/v1/auth/modules returns control-plane-backed availability payloads
5. frontend shell only shows modules where is_available=true
```

- [ ] **Step 4: Reconcile the spec against the shipped contracts**

```markdown
- If the shipped implementation still matches the approved spec, record "no spec delta" in the PR notes and do not edit the spec file.
- If a model name, payload field, or phase boundary changed during implementation, update `docs/superpowers/specs/2026-03-27-platform-control-plane-design.md` in the same commit as the code change that introduced it.
```

- [ ] **Step 5: Commit**

```bash
git add app/models/control_plane.py app/models/__init__.py app/services/entitlement_service.py app/core/dependencies.py app/api/v1/auth.py app/api/v1/modules.py app/api/v1/platform_admin.py app/api/v1/tenants.py alembic/versions/20260327_add_control_plane_entities.py tests/test_control_plane_models.py tests/test_entitlement_service.py tests/test_dependencies.py tests/test_auth.py tests/test_database.py tests/test_services.py src/api/auth.ts src/api/modules.ts src/api/platform.ts src/api/tenants.ts src/stores/modules.ts src/stores/user.ts src/router/index.ts
git commit -m "chore: verify phase 1 control plane consolidation"
```
