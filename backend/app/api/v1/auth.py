"""
Elder Care Platform - Authentication API Router
Endpoints:
  POST /api/v1/auth/login        — Email/password login → JWT tokens
  POST /api/v1/auth/refresh      — Refresh access token
  POST /api/v1/auth/logout       — Invalidate refresh token (client-side)
  GET  /api/v1/auth/me           — Current user profile
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_user_permission_codes
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.core.cache import cache_service
from app.models.user import User

router = APIRouter()
logger = structlog.get_logger()

LOGIN_FAILURE_PREFIX = "login_failure"
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 900  # 15 minutes


# ── Request / Response schemas ────────────────────────────────────────────────

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

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

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


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    failed_attempts = await _check_login_attempts(body.email)
    if failed_attempts >= MAX_LOGIN_ATTEMPTS:
        logger.warning(
            "login_locked_out",
            email=body.email,
            attempts=failed_attempts,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"账户已锁定，请{LOGIN_LOCKOUT_SECONDS // 60}分钟后再试",
        )

    result = await db.execute(select(User).where(User.email == body.email))
    user: User | None = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        await _record_login_failure(body.email)
        logger.warning(
            "login_failed",
            email=body.email,
            attempts=failed_attempts + 1,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )
    if not user.is_active or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )

    await _clear_login_failures(body.email)

    access_token = create_access_token(
        subject=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
    )
    refresh_token = create_refresh_token(subject=str(user.id))
    logger.info("login_success", user_id=str(user.id), email=body.email)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse, summary="刷新Token")
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    from jose import JWTError
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        user_id = payload["sub"]
    except (JWTError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(str(user.id), str(user.tenant_id) if user.tenant_id else None),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserProfile, summary="当前用户信息")
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    permissions = await get_user_permission_codes(db, current_user)
    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        scope=current_user.scope.value,
        tenant_id=str(current_user.tenant_id) if current_user.tenant_id else None,
        permissions=permissions,
    )
