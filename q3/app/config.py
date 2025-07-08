from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    app_name: str = "QuickMed - Medicine Delivery Platform"
    debug: bool = True
    
    # Database - Use PostgreSQL in production, SQLite in development
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./quickmed.db")
    
    # JWT Settings
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # File Upload
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    upload_dir: str = "uploads"
    
    # Delivery Settings
    default_delivery_time: int = 30  # minutes
    emergency_delivery_time: int = 10  # minutes
    
    # Pharmacy Settings
    pharmacy_name: str = "QuickMed Pharmacy"
    pharmacy_address: str = "123 Main St, City, State 12345"
    pharmacy_phone: str = "+1-555-0123"
    
    class Config:
        env_file = ".env"

settings = Settings() 