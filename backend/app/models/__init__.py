"""Models package — exports all ORM models for Alembic autogenerate."""
from app.models.base import Base, BaseModel, TenantBaseModel  # noqa: F401
from app.models.tenant import Tenant, SubscriptionPlan, TenantModule  # noqa: F401
from app.models.user import User, Role, Permission, UserRole, RolePermission, APIKey  # noqa: F401
from app.models.patient import Patient  # noqa: F401
from app.models.assessment import Assessment  # noqa: F401
from app.models.outbox import EventOutbox, OutboxStatus, ProcessedEvent  # noqa: F401
from app.models.version import (  # noqa: F401
    PlatformVersion,
    VersionChangelog,
    ModuleVersion,
    VersionCompatibility,
    TenantVersionBinding,
    VersionRollback,
    VersionStatus,
    ChangeType,
    CompatibilityLevel,
)
