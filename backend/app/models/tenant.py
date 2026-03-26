"""
Elder Care Platform - Tenant & Subscription Models
Defines:
  - Tenant: A subscribing organization (e.g., an elder care home)
  - SubscriptionPlan: The licensed feature set (Free / Standard / Enterprise)
  - TenantModule: Which optional modules a tenant has activated
"""
import uuid
from enum import Enum as PyEnum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModel


class PlanTier(str, PyEnum):
    FREE = "free"
    STANDARD = "standard"
    ENTERPRISE = "enterprise"


class TenantStatus(str, PyEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    CANCELLED = "cancelled"


class SubscriptionPlan(BaseModel):
    """
    Catalogue of available SaaS plans.
    Managed by platform operators (super admins).
    """
    __tablename__ = "subscription_plans"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    tier: Mapped[PlanTier] = mapped_column(Enum(PlanTier), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Rate limits (requests per minute)
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    # Which module slugs are included, stored as comma-separated string
    # e.g. "patient_mgmt,assessment,health_monitoring"
    included_modules: Mapped[str] = mapped_column(Text, default="", nullable=False)
    max_users: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_patients: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    tenants: Mapped[list["Tenant"]] = relationship(back_populates="plan")


class Tenant(BaseModel):
    """
    Represents one subscribing organisation (e.g., one care home or hospital).
    Each tenant has its own isolated data namespace enforced by RLS.
    """
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus), default=TenantStatus.TRIAL, nullable=False
    )
    contact_email: Mapped[str] = mapped_column(String(200), nullable=False)

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False
    )
    plan: Mapped[SubscriptionPlan] = relationship(back_populates="tenants")

    # White-label customisation
    brand_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Users and modules belonging to this tenant
    users: Mapped[list["User"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="tenant", foreign_keys="[User.tenant_id]"
    )
    activated_modules: Mapped[list["TenantModule"]] = relationship(back_populates="tenant")


class TenantModule(BaseModel):
    """
    Tracks which optional modules are activated for a particular tenant.
    Module slugs must match registered module names in the plugin registry.
    """
    __tablename__ = "tenant_modules"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    module_slug: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="E.g. 'assessment', 'ai_chat', 'learning_center', 'reservation'"
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    tenant: Mapped[Tenant] = relationship(back_populates="activated_modules")


class SystemModule(BaseModel):
    """
    System-level module registry for platform management.
    Stores module metadata, status, and version information.
    """
    __tablename__ = "system_modules"

    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True,
        comment="Module unique identifier, e.g. 'patient_mgmt'"
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    permissions: Mapped[str] = mapped_column(
        Text, default="", nullable=False,
        comment="Comma-separated list of permission codes"
    )
    router_prefix: Mapped[str] = mapped_column(String(200), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    disable_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
