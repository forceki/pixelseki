from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pixel_generation"

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Default AI provider: "gemini" or "openai"
    DEFAULT_PROVIDER: str = "gemini"

    # AWS S3 Storage (leave S3_BUCKET empty to use local disk)
    S3_BUCKET: str = ""
    S3_REGION: str = "ap-southeast-1"
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_PREFIX: str = "staging"

    # Base URL for serving assets (S3 host, CDN, etc.)
    # e.g. "https://pixelseki.s3.ap-southeast-1.amazonaws.com"
    # Leave empty to auto-build from S3_BUCKET/S3_REGION, or use "" for local /static/
    BASE_ASSETS_URL: str = ""

    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str = "change-this-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "https://pixelseki.online"]

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_ENV: str = "development"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
