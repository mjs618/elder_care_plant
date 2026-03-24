"""
Elder Care Platform - Security & JWT Utilities
Handles:
  - Password hashing / verification (bcrypt)
  - JWT access and refresh token creation / decoding
  - API Key generation and hashing
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password helpers ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ──────────────────────────────────────────────────────────────────────

def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    subject: str,
    tenant_id: str | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Creates a short-lived JWT access token.

    Claims:
      sub  — user ID
      tid  — tenant ID (None for platform super admins)
      type — "access"
    """
    data: dict[str, Any] = {"sub": subject, "type": "access"}
    if tenant_id:
        data["tid"] = tenant_id
    if extra_claims:
        data.update(extra_claims)
    return _create_token(data, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(subject: str) -> str:
    """Creates a long-lived refresh token."""
    return _create_token(
        {"sub": subject, "type": "refresh"},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decodes and validates a JWT token.
    Raises jose.JWTError on invalid/expired tokens.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# ── API Key generation ───────────────────────────────────────────────────────

def generate_api_key() -> tuple[str, str, str]:
    """
    Generates a new API key.
    Returns:
        (plain_key, key_prefix, hashed_key)
    The plain_key is shown once to the user; only the hash is stored.
    """
    plain = f"eck_{secrets.token_urlsafe(32)}"
    prefix = plain[:12]
    hashed = hashlib.sha256(plain.encode()).hexdigest()
    return plain, prefix, hashed


def verify_api_key(plain: str, hashed: str) -> bool:
    return hashlib.sha256(plain.encode()).hexdigest() == hashed
