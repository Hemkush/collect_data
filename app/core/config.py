from pydantic import BaseSettings
from typing import List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/webscraperdb"
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379"
    
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Web Scraping API"
    
    # Security settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS settings
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Scraping settings
    DEFAULT_REQUEST_TIMEOUT: int = 30
    MAX_CONCURRENT_REQUESTS: int = 10
    RATE_LIMIT_PER_MINUTE: int = 60
    USER_AGENT: str = "WebScraperBot/1.0"
    
    # Celery settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # File storage
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Selenium/Browser settings
    HEADLESS_BROWSER: bool = True
    BROWSER_TIMEOUT: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()