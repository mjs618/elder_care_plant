"""
Elder Care Platform - FastAPI Dependencies
Provides reusable dependency functions for:
  - JWT-based user authentication
  - API Key authentication
  - Tenant-aware database sessions
  - Module permission gates (component licensing)
  - Fine-grained permission checking
  - Rate limiting by tenant SLA tier
"""
import uuid

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import distinct, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db, _reset_tenant_context, _set_tenant_context
from app.core.security import decode_token, verify_api_key
from app.core.module_registry import CORE_MODULES, module_registry
from app.models.user import APIKey, Permission, Role, RolePermission, User, UserRole, UserScope
from app.models.tenant import Tenant, TenantModule, TenantStatus

bearer_scheme = HTTPBearer(auto_error=False)


async def _get_user_by_id(db: AsyncSession, user_id: str) -> User:
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.user_roles)
            .selectinload(UserRole.role)
            .selectinload(Role.role_permissions)
            .selectinload(RolePermission.permission)
        )
        .where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active or user.is_deleted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def _iter_module_definitions():
    return module_registry.all() or CORE_MODULES


def _get_module_definition_by_permission(permission_code: str):
    for module_def in _iter_module_definitions():
        if permission_code in module_def.permissions:
            return module_def
    return None


async def get_user_permission_codes(db: AsyncSession, user: User) -> list[str]:
    if user.scope == UserScope.PLATFORM:
        return sorted({perm for module_def in _iter_module_definitions() for perm in module_def.permissions})

    stmt = (
        select(distinct(Permission.code))
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
        .where((Role.tenant_id == user.tenant_id) | (Role.tenant_id.is_(None)))
    )
    result = await db.execute(stmt)
    return sorted(result.scalars().all())


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolves the current authenticated user from either:
      1. Bearer JWT token
      2. X-API-Key header (for 3rd-party integrations)
    """
    if x_api_key:
        prefix = x_api_key[:12]
        result = await db.execute(
            select(APIKey).where(APIKey.key_prefix == prefix, APIKey.is_active == True)  # noqa: E712
        )
        key_obj = result.scalar_one_or_none()
        if not key_obj or not verify_api_key(x_api_key, key_obj.hashed_key):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        return await _get_user_by_id(db, str(key_obj.user_id))

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id: str = payload["sub"]
    except (JWTError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate token")

    return await _get_user_by_id(db, user_id)


async def get_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the user to be a platform-level super admin."""
    if current_user.scope != UserScope.PLATFORM:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform admin access required")
    return current_user


async def get_tenant_db(
    current_user: User = Depends(get_current_user),
) -> AsyncSession:
    """
    Yields an AsyncSession pre-configured with the current user's tenant RLS context.
    This makes all subsequent queries automatically scoped to the tenant.
    
    For platform admins (scope=PLATFORM), returns a regular session without RLS context.
    """
    async with AsyncSessionLocal() as session:
        if current_user.scope == UserScope.PLATFORM:
            try:
                yield session
            finally:
                pass
            return
            
        if not current_user.tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant associated with user")
        await _set_tenant_context(session, str(current_user.tenant_id))
        try:
            yield session
        finally:
            await _reset_tenant_context(session)


def require_module(module_slug: str):
    """
    Dependency factory — gates an endpoint behind a module license check.
    Usage:
        @router.get("/assessments", dependencies=[Depends(require_module("assessment"))])
    """
    async def _check(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        if current_user.scope == UserScope.PLATFORM:
            return

        result = await db.execute(
            select(TenantModule).where(
                TenantModule.tenant_id == current_user.tenant_id,
                TenantModule.module_slug == module_slug,
                TenantModule.is_active == True,  # noqa: E712
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Module '{module_slug}' is not activated for your subscription. Please upgrade your plan.",
            )

    return _check


def require_permission(permission: str):
    """
    Dependency factory — gates an endpoint behind a specific permission check.
    Usage:
        @router.delete("/patients/{id}", dependencies=[Depends(require_permission("patient:delete"))])
    """
    async def _check(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.scope == UserScope.PLATFORM:
            return current_user

        module_def = _get_module_definition_by_permission(permission)
        if not module_def:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Permission '{permission}' is not registered in any module"
            )
        current_user = await require_tenant_active(current_user=current_user, db=db)

        result = await db.execute(
            select(TenantModule).where(
                TenantModule.tenant_id == current_user.tenant_id,
                TenantModule.module_slug == module_def.slug,
                TenantModule.is_active == True,  # noqa: E712
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission '{permission}'. Module '{module_def.slug}' is not activated.",
            )

        permission_codes = await get_user_permission_codes(db, current_user)
        if permission not in permission_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission '{permission}'.",
            )

        return current_user

    return _check


async def require_tenant_active(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency — ensures the user's tenant is active.
    """
    if current_user.scope == UserScope.PLATFORM:
        return current_user
    
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenant associated with user"
        )
    
    result = await db.execute(
        select(Tenant.status).where(Tenant.id == current_user.tenant_id)
    )
    tenant_status = result.scalar_one_or_none()
    
    if tenant_status != TenantStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is not active"
        )
    
    return current_user


def require_any_module(*module_slugs: str):
    """
    Dependency factory — gates an endpoint if user has ANY of the specified modules.
    Usage:
        @router.get("/dashboard", dependencies=[Depends(require_any_module("assessment", "health_monitoring"))])
    """
    async def _check(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        if current_user.scope == UserScope.PLATFORM:
            return

        result = await db.execute(
            select(TenantModule.module_slug).where(
                TenantModule.tenant_id == current_user.tenant_id,
                TenantModule.module_slug.in_(module_slugs),
                TenantModule.is_active == True,  # noqa: E712
            )
        )
        active_modules = [row[0] for row in result.all()]
        
        if not active_modules:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"None of the required modules {module_slugs} are activated for your subscription.",
            )

    return _check
