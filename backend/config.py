"""
Flask configuration classes for the Real Estate Analyzer backend.

Usage
-----
Pass a config object (class or instance) or a plain dict to ``create_app()``:

    from config import TestingConfig
    app = create_app(TestingConfig)

or supply a dict of overrides:

    app = create_app({'TESTING': True, 'JWT_SECRET_KEY': 'test-secret'})

The module-level ``app`` in ``app.py`` uses ``BaseConfig`` by default (reading
all settings from environment variables at startup).
"""

from __future__ import annotations

import os
import logging

logger = logging.getLogger(__name__)


def _resolve_jwt_secret(env_value: str | None) -> str:
    """Return a safe JWT secret, generating a random one when the env value is
    absent or is a known placeholder."""
    placeholders = {"your_secret_key", "changeme", "secret"}
    if not env_value or env_value in placeholders:
        logger.warning(
            "JWT_SECRET is missing or set to a placeholder. Using a random secret."
        )
        return os.urandom(32).hex()
    return env_value


class BaseConfig:
    """Shared configuration read from environment variables."""

    # ------------------------------------------------------------------ Flask
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16 MB
    TESTING: bool = False

    # --------------------------------------------------------------------- JWT
    JWT_SECRET_KEY: str = _resolve_jwt_secret(os.getenv("JWT_SECRET"))
    SECRET_KEY: str = JWT_SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES: int = int(os.getenv("JWT_EXPIRY_SECONDS", 3600))

    # ----------------------------------------------------------------- MongoDB
    MONGODB_URI: str | None = os.getenv("DATABASE_URL")

    # ----------------------------------------------------------------- Caching
    @classmethod
    def _cache_config(cls) -> dict:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            return {"CACHE_TYPE": "RedisCache", "CACHE_REDIS_URL": redis_url}
        return {"CACHE_TYPE": "SimpleCache"}

    # -------------------------------------------------------------- Rate limit
    RATELIMIT_ENABLED: bool = True

    # -------------------------------------------------------------------- CORS
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000"
    ).split(",")


class DevelopmentConfig(BaseConfig):
    """Development-friendly settings (debug mode on, relaxed limits)."""

    DEBUG: bool = True


class TestingConfig(BaseConfig):
    """Isolated test configuration.

    - TESTING=True  ⟹ Flask test client behaves correctly
    - Random JWT secret so tests never depend on a real env var
    - Rate limiting disabled so tests are not throttled
    - SimpleCache so no Redis dependency
    - No MongoDB URI so init_db() is a no-op (tests mock it anyway)
    """

    TESTING: bool = True
    JWT_SECRET_KEY: str = "testing-jwt-secret-do-not-use-in-production"
    SECRET_KEY: str = JWT_SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES: int = 3600
    MONGODB_URI: str | None = None
    RATELIMIT_ENABLED: bool = False
    CACHE_TYPE: str = "SimpleCache"


class ProductionConfig(BaseConfig):
    """Strict production settings."""

    DEBUG: bool = False

    @classmethod
    def validate(cls) -> None:
        """Raise at startup if required production settings are missing."""
        if not os.getenv("JWT_SECRET"):
            raise RuntimeError(
                "JWT_SECRET environment variable must be set in production."
            )
        if not os.getenv("DATABASE_URL"):
            raise RuntimeError(
                "DATABASE_URL environment variable must be set in production."
            )


#: Convenience mapping from string name to config class.
config_map: dict[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": BaseConfig,
}
