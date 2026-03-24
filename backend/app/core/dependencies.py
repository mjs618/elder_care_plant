"""
Elder Care Platform - FastAPI Dependencies
Provides reusable dependency functions for:
  - JWT-based user authentication
  - API Key authentication
  - Tenant-aware database sessions
  - Module permission gates (component licensing)
  - Rate limiting by tenant SLA tier
"""
import uuid

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db, _set_tenant_context
from app.core.security import decode_token, verify_api_key
from app.models.user import APIKey, User, UserScope
from app.models.tenant import Tenant, TenantModule, TenantStatus

bearer_scheme = HTTPBearer(auto_error=False)


# ── Auth helpers ─────────────────────────────────────────────────────────────

async def _get_user_by_id(db: AsyncSession, user_id: str) -> User:
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or user.is_deleted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


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
    # ── API Key auth ──────────────────────────────────────────────────────────
    if x_api_key:
        prefix = x_api_key[:12]
        result = await db.execute(
            select(APIKey).where(APIKey.key_prefix == prefix, APIKey.is_active == True)  # noqa: E712
        )
        key_obj = result.scalar_one_or_none()
        if not key_obj or not verify_api_key(x_api_key, key_obj.hashed_key):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        return await _get_user_by_id(db, str(key_obj.user_id))

    # ── Bearer JWT auth ───────────────────────────────────────────────────────
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


# ── Tenant-aware DB session ───────────────────────────────────────────────────

async def get_tenant_db(
    current_user: User = Depends(get_current_user),
) -> AsyncSession:
    """
    Yields an AsyncSession pre-configured with the current user's tenant RLS context.
    This makes all subsequent queries automatically scoped to the tenant.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant associated with user")
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await _set_tenant_context(session, str(current_user.tenant_id))
            yield session


# ── Module / License gate ─────────────────────────────────────────────────────

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
            return  # platform admins bypass module gates

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
