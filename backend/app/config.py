from __future__ import annotations

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """Application settings.
    
    All values are loaded from environment variables or .env file.
    """
    
    # Application
    APP_NAME: str = "ProfitLens"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Supabase / PostgreSQL
    SUPABASE_URL: str = "https://jcqlowjmcjyrbilwqjnj.supabase.co"
    SUPABASE_ANON_KEY: str = ""
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/profitlens"
    DATABASE_URL_SYNC: str = "postgresql://postgres:password@localhost:5432/profitlens"
    
    # JWT Authentication
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_DIR: str = "data/uploads"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    class Config:
        env_file = (".env", "../.env")
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
