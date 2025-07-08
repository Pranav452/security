from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite:///./test.db"
    
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_reset_expire_minutes: int = 15
    bcrypt_rounds: int = 12
    
    redis_url: str = "redis://localhost:6379"
    
    login_rate_limit: int = 5
    registration_rate_limit: int = 3
    password_reset_rate_limit: int = 1
    general_rate_limit: int = 100
    
    cors_origins: list = ["http://localhost:3000", "https://yourdomain.com"]
    password_reset_secret: str = "password-reset-secret-change-this"
    
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@yourapp.com"
    
    class Config:
        env_file = ".env"

settings = Settings() 