"""
Elder Care Platform - Authentication API Router
Endpoints:
  POST /api/v1/auth/login    - Email/password login -> JWT tokens
  POST /api/v1/auth/refresh  - Refresh access token
  POST /api/v1/auth/logout   - Revoke refresh token
  GET  /api/v1/auth/me       - Current user profile
  GET  /api/v1/auth/modules  - Authenticated module bootstrap payload
"""
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_user_permission_codes
from app.core.module_registry import module_registry
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.tenant import SystemModule, TenantModule
from app.models.user import RefreshToken, User, UserScope
from app.schemas.response import ok

router = APIRouter()
logger = structlog.get_logger()

LOGIN_FAILURE_PREFIX = "login_failure"
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 900


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfile(BaseModel):
    id: str
    email: str
    username: str
    full_name: str | None
    scope: str
    tenant_id: str | None
    permissions: list[str]
    active_modules: list[str]

    model_config = {"from_attributes": True}


async def _get_login_failure_key(email: str) -> str:
    return f"{LOGIN_FAILURE_PREFIX}:{email.lower()}"


async def _check_login_attempts(email: str) -> int:
    key = await _get_login_failure_key(email)
    count = await cache_service.get(key)
    return int(count) if count else 0


async def _record_login_failure(email: str) -> None:
    key = await _get_login_failure_key(email)
    current = await _check_login_attempts(email)
    await cache_service.set(key, current + 1, ttl=LOGIN_LOCKOUT_SECONDS)


async def _clear_login_failures(email: str) -> None:
    key = await _get_login_failure_key(email)
    await cache_service.delete(key)


def _payload_expiry(payload: dict) -> datetime:
    exp = payload.get("exp")
    if exp is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return datetime.fromtimestamp(int(exp), tz=timezone.utc)


async def _issue_refresh_token(db: AsyncSession, user: User) -> str:
    token_jti = str(uuid.uuid4())
    refresh_token = create_refresh_token(subject=str(user.id), token_id=token_jti)
    payload = decode_token(refresh_token)
    db.add(
        RefreshToken(
            user_id=user.id,
            tenant_id=user.tenant_id,
            token_jti=token_jti,
            expires_at=_payload_expiry(payload),
        )
    )
    await db.flush()
    return refresh_token


async def _get_refresh_token_record(db: AsyncSession, payload: dict) -> RefreshToken:
    token_jti = payload.get("jti")
    user_id = payload.get("sub")
    if not token_jti or not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    try:
        user_uuid = uuid.UUID(str(user_id))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_jti == token_jti,
            RefreshToken.user_id == user_uuid,
            RefreshToken.is_deleted == False,  # noqa: E712
        )
    )
    token_record = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if (
        token_record is None
        or token_record.revoked_at is not None
        or token_record.expires_at <= now
    ):
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")
    return token_record


async def _get_active_module_slugs(db: AsyncSession, user: User) -> list[str]:
    if user.scope == UserScope.PLATFORM:
        return sorted(module_registry.all_slugs())

    result = await db.execute(
        select(TenantModule.module_slug).where(
            TenantModule.tenant_id == user.tenant_id,
            TenantModule.is_active == True,  # noqa: E712
        )
    )
    return sorted(result.scalars().all())


@router.post("/login", response_model=TokenResponse, summary="User login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    failed_attempts = await _check_login_attempts(body.email)
    if failed_attempts >= MAX_LOGIN_ATTEMPTS:
        logger.warning("login_locked_out", email=body.email, attempts=failed_attempts)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account locked. Try again in {LOGIN_LOCKOUT_SECONDS // 60} minutes.",
        )

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        await _record_login_failure(body.email)
        logger.warning("login_failed", email=body.email, attempts=failed_attempts + 1)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    await _clear_login_failures(body.email)

    access_token = create_access_token(
        subject=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
    )
    refresh_token = await _issue_refresh_token(db, user)
    await db.commit()

    logger.info("login_success", user_id=str(user.id), email=body.email)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse, summary="Refresh token pair")
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        user_id = uuid.UUID(str(payload["sub"]))
    except (JWTError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc

    token_record = await _get_refresh_token_record(db, payload)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or user.is_deleted:
        raise HTTPException(status_code=401, detail="User not found")

    token_record.revoked_at = datetime.now(timezone.utc)
    new_refresh_token = await _issue_refresh_token(db, user)
    new_payload = decode_token(new_refresh_token)
    token_record.replaced_by_jti = new_payload.get("jti")
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(
            str(user.id),
            str(user.tenant_id) if user.tenant_id else None,
        ),
        refresh_token=new_refresh_token,
    )


@router.post("/logout", summary="User logout")
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        token_record = await _get_refresh_token_record(db, payload)
        token_record.revoked_at = datetime.now(timezone.utc)
        await db.commit()
    except HTTPException as exc:
        if exc.status_code not in {400, 401}:
            raise
        await db.rollback()
    except JWTError:
        await db.rollback()

    return ok(message="Logged out successfully")


@router.get("/modules", summary="Current user modules")
async def current_user_modules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    active_slugs = set(await _get_active_module_slugs(db, current_user))
    system_result = await db.execute(select(SystemModule))
    system_modules = {module.slug: module for module in system_result.scalars().all()}

    modules_data = []
    for module_def in module_registry.all():
        system_module = system_modules.get(module_def.slug)
        is_enabled = system_module.is_enabled if system_module is not None else True
        is_active = is_enabled and (
            current_user.scope == UserScope.PLATFORM or module_def.slug in active_slugs
        )

        module_data = {
            "slug": module_def.slug,
            "display_name": module_def.display_name,
            "description": module_def.description,
            "version": system_module.version if system_module is not None else module_def.version,
            "permissions": module_def.permissions,
            "is_active": is_active,
        }
        if module_def.ui_meta:
            module_data["ui_meta"] = {
                "icon": module_def.ui_meta.icon,
                "path": module_def.ui_meta.path,
                "children": [
                    {"title": child.title, "path": child.path}
                    for child in module_def.ui_meta.children
                ],
            }
        modules_data.append(module_data)

    return ok(modules_data)


@router.get("/me", response_model=UserProfile, summary="Current user profile")
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    permissions = await get_user_permission_codes(db, current_user)
    active_modules = await _get_active_module_slugs(db, current_user)
    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        scope=current_user.scope.value,
        tenant_id=str(current_user.tenant_id) if current_user.tenant_id else None,
        permissions=permissions,
        active_modules=active_modules,
    )
