from typing import List
from pydantic import Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    USE_PYDANTIC_V2 = True
except ImportError:
    from pydantic import BaseSettings
    SettingsConfigDict = None
    USE_PYDANTIC_V2 = False


class Settings(BaseSettings):
    """
    Centralized Application Configuration.
    Enforces strict Pydantic parsing with zero direct os.getenv calls across the project.
    """
    PROJECT_NAME: str = "FLUX ONE API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="INFO")

    # Networking & Security
    ALLOWED_ORIGINS: List[str] = ["*"]
    SECRET_KEY: str = Field(default="temporary_dev_secret_key_change_in_production_32chars_min")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30    # 30 days
    ADMIN_METRICS_SECRET: str = Field(default="internal_admin_metrics_secret_token")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgrespassword@localhost:5432/flux_one",
        description="Async SQLAlchemy database connection string"
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # Gemini academic copilot. Keep the API key server-side only.
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-3.6-flash")
    GEMINI_API_ENDPOINT: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    )
    GEMINI_TIMEOUT_SECONDS: float = Field(default=25.0, gt=0, le=120)

    if USE_PYDANTIC_V2:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=True,
            extra="ignore"
        )
    else:
        class Config:
            env_file = ".env"
            case_sensitive = True
            extra = "ignore"


settings = Settings()
