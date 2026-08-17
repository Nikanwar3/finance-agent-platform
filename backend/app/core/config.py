import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Real-Time Financial Analysis Backend Platform"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Defaults to SQLite for local development without Docker
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./finance.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Rate limiting (requests per window, parsed by slowapi's "N/period" syntax)
    RATE_LIMIT_READ: str = os.getenv("RATE_LIMIT_READ", "60/minute")
    RATE_LIMIT_CLOSE: str = os.getenv("RATE_LIMIT_CLOSE", "5/minute")

    # AWS (close-report archival to S3; falls back to a no-op if unset,
    # mirroring the Redis MockRedis fallback pattern below)
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET", "")

    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    class Config:
        env_file = ".env"

settings = Settings()
