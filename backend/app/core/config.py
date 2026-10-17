"""Application configuration and environment settings."""
import secrets
from typing import List, Optional, Union
from pydantic import field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core application settings loaded from environment variables."""

    APP_NAME: str = "MRI Analysis API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # Server binding
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Logging
    LOG_LEVEL: str = "INFO"

    # Configurable CORS origins for client applications
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database (Phase 3)
    DATABASE_URL: Optional[str] = None

    # Vector embedding dimension — must match the embedding model used in later phases.
    # 768 is a common default for models like BioBERT / medical imaging encoders.
    EMBEDDING_DIMENSION: int = 768

    # ── Authentication & Security ─────────────────────────────────────────────
    # SECRET_KEY MUST be set via environment variable in production.
    # A random default is generated at startup only if not provided, so it will
    # differ between restarts (tokens issued before restart become invalid).
    # Set SECRET_KEY in your .env to a stable 32+ byte random value.
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60          # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MIN_PASSWORD_LENGTH: int = 8

    # Rate limiting (requests per window)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN: str = "10/minute"             # per IP
    RATE_LIMIT_REGISTER: str = "5/minute"           # per IP
    RATE_LIMIT_ANALYSIS: str = "30/minute"          # per token or IP
    MRI_TUMOR_MODEL_RUN_DIR: Optional[str] = None

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Support comma-separated strings or JSON lists for CORS_ORIGINS."""
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def ensure_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """Generate a random key for development if SECRET_KEY is not configured.

        WARNING: A generated key is NOT stable across restarts.  All issued tokens
        will be invalidated on restart.  Always set SECRET_KEY in production.
        """
        if info.data.get("ENVIRONMENT") == "production" and len(v or "") < 32:
            raise ValueError("Production requires a persistent SECRET_KEY of at least 32 characters")
        if not v or not v.strip():
            import logging
            logging.getLogger(__name__).warning(
                "SECRET_KEY is not set.  Generating a random key — tokens will be "
                "invalidated on restart.  Set SECRET_KEY in your environment for production."
            )
            return secrets.token_hex(32)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
