"""
Elder Care Platform - Application Settings
Centralized configuration using pydantic-settings.
All values are read from environment variables or .env file.
"""
from functools import lru_cache
from typing import Literal
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_NAME: str = "Elder Care Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    SECRET_KEY: str

    # ── Database (PostgreSQL + asyncpg) ──────────────────────────────────────
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── API Key (3rd-party integrations) ─────────────────────────────────────
    API_KEY_HEADER_NAME: str = "X-API-Key"

    # ── SLA / Rate Limiting (requests per minute per tenant tier) ────────────
    RATE_LIMIT_FREE: int = 60
    RATE_LIMIT_STANDARD: int = 300
    RATE_LIMIT_ENTERPRISE: int = 3000

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[AnyHttpUrl] = []

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list) -> list:
        if isinstance(v, str):
            return json.loads(v)
        return v

    # ── Bootstrap Super Admin ────────────────────────────────────────────────
    SUPERADMIN_EMAIL: str = "admin@eldercare.com"
    SUPERADMIN_PASSWORD: str

    # ── Feature Flags ────────────────────────────────────────────────────────
    ENABLE_PGVECTOR: bool = True
    ENABLE_POSTGIS: bool = False

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — import this throughout the app."""
    return Settings()
