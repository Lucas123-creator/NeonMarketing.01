from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from pydantic.networks import EmailStr
import os
from functools import lru_cache
from dotenv import load_dotenv

class SMTPSettings(BaseSettings):
    """SMTP configuration settings."""
    host: str = Field(default="smtp.gmail.com")
    port: int = Field(default=587)
    username: EmailStr
    password: str
    from_email: EmailStr
    use_tls: bool = Field(default=True)
    
    class Config:
        env_prefix = "SMTP_"

class LinkedInSettings(BaseSettings):
    """LinkedIn API configuration settings."""
    username: str
    password: str
    api_key: Optional[str] = None
    
    class Config:
        env_prefix = "LINKEDIN_"

class OpenAISettings(BaseSettings):
    """OpenAI API configuration settings."""
    api_key: str
    model: str = Field(default="gpt-4")
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=1000)
    
    class Config:
        env_prefix = "OPENAI_"

class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    url: str
    pool_size: int = Field(default=5)
    max_overflow: int = Field(default=10)
    echo: bool = Field(default=False)
    
    class Config:
        env_prefix = "DATABASE_"

class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    url: str = Field(default="redis://localhost:6379/0")
    max_connections: int = Field(default=10)
    
    class Config:
        env_prefix = "REDIS_"

class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    json_format: bool = Field(default=True)
    
    class Config:
        env_prefix = "LOG_"

class Settings(BaseSettings):
    """Main application settings."""
    # Environment
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"), env="ENVIRONMENT")
    debug: bool = Field(default=False)
    timezone: str = Field(default="UTC")
    
    # Components
    smtp: SMTPSettings = Field(default_factory=SMTPSettings)
    linkedin: LinkedInSettings = Field(default_factory=LinkedInSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    
    # Rate Limiting
    max_emails_per_hour: int = Field(default=50)
    max_emails_per_day: int = Field(default=200)
    
    # Monitoring
    sentry_dsn: Optional[str] = None
    prometheus_enabled: bool = Field(default=True)
    
    # Strategy (AI Optimization)
    strategy_params: Dict[str, Any] = Field(default_factory=dict)
    
    phantombuster_api_key: str = Field(default="dummy")
    
    def __init__(self, **values):
        # Load the correct .env file based on ENVIRONMENT at instantiation time
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production":
            load_dotenv(".env.prod", override=True)
        else:
            load_dotenv(override=True)
        super().__init__(**values)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"
        
    @validator("environment")
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v
        
    @validator("debug")
    def validate_debug(cls, v: bool, values: Dict[str, Any]) -> bool:
        """Ensure debug is False in production."""
        if values.get("environment") == "production" and v:
            return False
        return v

    def update_strategy_params(self, params: Dict[str, Any]):
        self.strategy_params = params

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings() 