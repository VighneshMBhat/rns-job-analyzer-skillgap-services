"""
Skill Gap Analysis Service Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Server
    HOST_URL: str = "http://localhost:8003"
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    # Gemini AI (Fallback key - used when user's key limit exceeded)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"
    
    # AWS S3 for PDF storage
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = "skillgap-reports"
    AWS_REGION: str = "us-east-1"
    
    # JWT Secret for token validation
    JWT_SECRET: str = ""
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
