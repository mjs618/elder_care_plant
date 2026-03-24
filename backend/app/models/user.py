"""
Elder Care Platform - User & Role Models (IAM)
Supports:
  - Platform super admins (tenant_id = NULL)
  - Tenant-level admins and staff users
  - RBAC via roles and permissions
  - API key authentication for 3rd-party integrations
"""
import uuid
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModel


class UserScope(str, PyEnum):
    """Determines whether a user belongs to the platform or a tenant."""
    PLATFORM = "platform"   # Super admins — cross-tenant access
    TENANT = "tenant"       # Tenant-specific users


class User(BaseModel):
    """Platform and tenant user account."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    scope: Mapped[UserScope] = mapped_column(
        Enum(UserScope), default=UserScope.TENANT, nullable=False
    )

    # NULL for platform-scope users; set for all tenant users
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=True,
        index=True,
    )
    tenant: Mapped["Tenant"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="users", foreign_keys=[tenant_id]
    )

    # RBAC
    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="user")

    # API keys for 3rd-party / integration use
    api_keys: Mapped[list["APIKey"]] = relationship(back_populates="user")


class Role(BaseModel):
    """
    RBAC Role. Roles are scoped per tenant (tenant_id != NULL)
    or are platform-level roles (tenant_id = NULL).
    """
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )

    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="role")
    role_permissions: Mapped[list["RolePermission"]] = relationship(back_populates="role")


class Permission(BaseModel):
    """Fine-grained permission string, e.g. 'patient:read', 'assessment:write'."""
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    module_slug: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Which feature module this permission belongs to"
    )

    role_permissions: Mapped[list["RolePermission"]] = relationship(back_populates="permission")


class UserRole(Base):
    """Many-to-many: User ↔ Role."""
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True
    )
    user: Mapped[User] = relationship(back_populates="user_roles")
    role: Mapped[Role] = relationship(back_populates="user_roles")


class RolePermission(Base):
    """Many-to-many: Role ↔ Permission."""
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permissions.id"), primary_key=True
    )
    role: Mapped[Role] = relationship(back_populates="role_permissions")
    permission: Mapped[Permission] = relationship(back_populates="role_permissions")


class APIKey(BaseModel):
    """
    Long-lived API keys for 3rd-party system integrations.
    Keys are stored hashed; the plain value is only shown once at creation.
    """
    __tablename__ = "api_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="Human-readable label")
    key_prefix: Mapped[str] = mapped_column(
        String(12), nullable=False, comment="First 8 chars, shown in UI for identification"
    )
    hashed_key: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="api_keys")
