"""
Elder Care Platform - ORM Base Models
Defines the declarative base and a universal BaseModel that all
domain models inherit from. Multi-tenant isolation is enforced by
including `tenant_id` on every business table, combined with
PostgreSQL Row-Level Security (RLS) policies.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base shared by all models."""
    pass


class TimestampMixin:
    """Adds created_at / updated_at audit columns."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Adds soft-delete support via is_deleted flag."""
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)


class BaseModel(TimestampMixin, SoftDeleteMixin, Base):
    """
    Universal base class for all business entities.
    Combines:
      - UUID primary key
      - Multi-tenant isolation (tenant_id)
      - Timestamps (created_at / updated_at)
      - Soft delete (is_deleted / deleted_at)
    """
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class TenantBaseModel(BaseModel):
    """
    Extends BaseModel with a mandatory `tenant_id`.
    All patient-facing, clinical, and business tables should inherit from this.
    PostgreSQL RLS policy will enforce that queries only see rows matching
    the current session's `app.current_tenant_id` setting.
    """
    __abstract__ = True

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Tenant isolation key — enforced by PostgreSQL RLS policy",
    )
