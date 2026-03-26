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

    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_NAME: str = "Elder Care Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    SECRET_KEY: str

    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50
    
    RABBITMQ_URL: str | None = None

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    API_KEY_HEADER_NAME: str = "X-API-Key"

    RATE_LIMIT_FREE: int = 60
    RATE_LIMIT_STANDARD: int = 300
    RATE_LIMIT_ENTERPRISE: int = 3000

    CORS_ORIGINS: list[AnyHttpUrl] = []
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_MAX_AGE: int = 600

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list) -> list:
        if isinstance(v, str):
            return json.loads(v)
        return v

    SUPERADMIN_EMAIL: str = "admin@eldercare.com"
    SUPERADMIN_PASSWORD: str

    ENABLE_PGVECTOR: bool = True
    ENABLE_POSTGIS: bool = False

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"
    LOG_INCLUDE_REQUEST_BODY: bool = False

    SENTRY_DSN: str | None = None
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 9090

    GRACEFUL_SHUTDOWN_TIMEOUT: int = 30
    HEALTH_CHECK_TIMEOUT: int = 5

    MONITORING_ENABLED: bool = True
    MONITORING_INTERVAL_SECONDS: int = 30
    MONITORING_TARGET_AVAILABILITY: float = 99.9
    MONITORING_RECOVERY_ENABLED: bool = True
    MONITORING_MAX_RECOVERY_ATTEMPTS: int = 3
    MONITORING_RECOVERY_COOLDOWN_SECONDS: int = 60

    ALERT_WEBHOOK_URL: str | None = None
    ALERT_SLACK_WEBHOOK_URL: str | None = None
    ALERT_EMAIL_RECIPIENTS: list[str] = []

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — import this throughout the app."""
    return Settings()
