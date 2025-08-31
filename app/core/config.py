from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, field_validator, PostgresDsn, ConfigDict, model_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict
import secrets
from enum import Enum
from functools import lru_cache
import os
import re
import contextlib


class LogLevel(str, Enum):
    """Log levels enum for configuration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive log level values."""
        if isinstance(value, str):
            # Try to match case-insensitive
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        return None


class AppEnvironment(str, Enum):
    """Application execution environments."""
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


def clean_env_value(value: str) -> str:
    """
    Clean environment values by removing comments.
    
    Args:
        value: Raw environment variable value that might include a comment
        
    Returns:
        Cleaned value with comments removed
    """
    if not value or not isinstance(value, str):
        return value
    
    # Remove comments (everything after #)
    comment_start = value.find("#")
    if comment_start != -1:
        value = value[:comment_start]
    
    # Special case: don't strip spaces from PostgreSQL URLs
    if value.startswith("postgresql:"):
        return value
    
    return value.strip()


class Settings(BaseSettings):
    """
    Application settings with environment variable loading.
    
    Inherits from Pydantic's BaseSettings to automatically read environment variables.
    Values are loaded with the following priority:
        1. Environment variables
        2. .env file
        3. Default values
    """
    # CORE APPLICATION SETTINGS
    APP_NAME: str = "Daily Challenge"
    API_PREFIX: str = "/api"
    DEBUG: bool = False
    ENVIRONMENT: AppEnvironment = AppEnvironment.DEV
    PROJECT_NAME: str = "Daily Challenge"
    VERSION: str = "0.1.0"
    LOG_LEVEL: LogLevel = LogLevel.INFO
    TESTING: bool = False  # Flag to indicate we're in a test environment
    
    # SECURITY SETTINGS
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # CORS SETTINGS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ["http://localhost:3000", "http://localhost"]
    
    # EMAIL SETTINGS
    DEFAULT_FROM_EMAIL: str = "Daily Challenge <no-reply@daily-challenge.app>"
    RESEND_API_KEY: Optional[str] = None
    RESEND_WEBHOOK_SECRET: Optional[str] = None  # Secret for verifying Resend webhook signatures
    EMAIL_ENABLED: bool = True
    
    # FRONTEND SETTINGS
    FRONTEND_URL: str = "http://localhost"
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """Validate and parse CORS origins from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # DATABASE SETTINGS
    POSTGRES_USER: str = "dcq_user"
    POSTGRES_PASSWORD: str = "dcq_pass"
    POSTGRES_DB: str = "dcq_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5433"
    DATABASE_URL: Optional[str] = None
    
    @field_validator("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "POSTGRES_HOST", "POSTGRES_PORT")
    def clean_string(cls, v: str) -> str:
        """
        Clean string values by removing extra whitespace.
        
        Args:
            v: The string value to clean
            
        Returns:
            Cleaned string with no extra whitespace
        """
        if isinstance(v, str):
            return v.strip()
        return v
    
    @field_validator("DATABASE_URL")
    def assemble_db_url(cls, v: Optional[str], info: ValidationInfo) -> str:
        """
        Assemble the database URL from individual components, but if v is set (from env or .env), use it directly.
        This ensures that if DATABASE_URL is provided (e.g. via command line or environment), it is used as-is.
        """
        # If DATABASE_URL is provided (via env or .env), use it directly
        if v and isinstance(v, str) and v.strip():
            print(f"[Settings] Using DATABASE_URL from env/.env: {v}")
            return v.strip()
        # Otherwise, assemble from components as before
        data = info.data
        user = data.get('POSTGRES_USER')
        password = data.get('POSTGRES_PASSWORD')
        host = data.get('POSTGRES_HOST')
        port = data.get('POSTGRES_PORT')
        db = data.get('POSTGRES_DB')
        
        print(f"Database components: user={user}, password=***, host={host}, port={port}, db={db}")
        
        # Ensure all required values are present
        if not all([user, password, host, port, db]):
            raise ValueError("Missing required database configuration")
            
        # Use the port from environment variables, don't hardcode it
        try:
            port_int = int(port)
        except (ValueError, TypeError):
            # Default to 5433 only if port cannot be converted to int
            port_int = 5433
            
        # Escape special characters in URL components
        from urllib.parse import quote_plus
        escaped_user = quote_plus(user)
        escaped_password = quote_plus(password)
        escaped_host = quote_plus(host)
        escaped_db = quote_plus(db)
        
        # Construct the URL with proper escaping
        url = f"postgresql://{escaped_user}:{escaped_password}@{escaped_host}:{port_int}/{escaped_db}"
        print(f"Final Database URL: {url}")
        
        # Validate the URL
        if not url.startswith("postgresql://"):
            raise ValueError("URL must start with postgresql://")
            
        # Test the connection
        try:
            import psycopg2
            conn = psycopg2.connect(url)
            conn.close()
            print("Database connection test successful")
        except Exception as e:
            print(f"Database connection test failed: {str(e)}")
            raise
            
        return url
    
    # FEATURE FLAGS
    ENABLE_CACHING: bool = False
    BYPASS_EMAIL_VERIFICATION: bool = False  # When True, email verification is not required in development
    
    # REDIS SETTINGS
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: Optional[str] = None
    
    # RATE LIMITING SETTINGS
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_REGISTER: str = "5/minute"
    RATE_LIMIT_LOGIN: str = "1000/minute"
    
    # Additional fields that may be in .env but not directly used by the app
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GITHUB_API_KEY: Optional[str] = None
    STACKOVERFLOW_APP_KEY: Optional[str] = None
    PERPLEXITY_API_KEY: Optional[str] = None
    MODEL: Optional[str] = None
    PERPLEXITY_MODEL: Optional[str] = None
    MAX_TOKENS: Optional[int] = None
    TEMPERATURE: Optional[float] = None
    DEFAULT_SUBTASKS: Optional[int] = None
    DEFAULT_PRIORITY: Optional[str] = None
    
    # Content Pipeline Settings
    DEFAULT_AI_PROVIDER: str = "gemini"
    CONTENT_PIPELINE_ENABLED: bool = True
    CONTENT_AUTO_APPROVE: bool = False
    CONTENT_BATCH_SIZE: int = 3
    CONTENT_TEMPERATURE: float = 0.7
    GEMINI_MODEL: str = "gemini-1.5-pro"
    CLAUDE_MODEL: str = "claude-3-opus-20240229"
    
    # Logging Configuration
    LOG_JSON_FORMAT: bool = True
    LOG_FILE_ENABLED: bool = True
    LOG_FILE_PATH: str = "./logs"
    LOG_MAX_SIZE_MB: int = 10
    LOG_RETENTION_COUNT: int = 5
    
    # Clean all string values before validation
    @model_validator(mode='before')
    @classmethod
    def clean_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean all string values in the input data."""
        if not isinstance(data, dict):
            return data
            
        return {
            k: clean_env_value(v) if isinstance(v, str) else v
            for k, v in data.items()
        }
    
    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Create test settings for use during tests
def get_test_settings() -> Settings:
    """Create settings with minimal test configuration."""
    # Start with completely empty environment to avoid any cross-contamination
    clean_env = {}
    
    # Set only the required test values    
    clean_env.update({
        "POSTGRES_USER": "dcq_test_user",
        "POSTGRES_PASSWORD": "dcq_test_pass",
        "POSTGRES_DB": "dcq_test_db",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5434",
        "DEBUG": "true",
        "PROJECT_NAME": "Daily Challenge",
        "TESTING": "true",  # Set testing mode to true
        # Disable rate limiting for tests
        "RATE_LIMIT_DEFAULT": "1000/minute",
        "RATE_LIMIT_REGISTER": "1000/minute",
        "RATE_LIMIT_LOGIN": "1000/minute",
        # Explicitly set DATABASE_URL to None to force constructing from components
        "DATABASE_URL": "",
    })
    
    with patch_env(clean_env):
        return Settings()


def patch_env(new_env):
    """Create a context manager to patch os.environ"""
    @contextlib.contextmanager
    def _patch_env(new_env):
        old_env = os.environ.copy()
        os.environ.clear()
        os.environ.update(new_env)
        try:
            yield
        finally:
            os.environ.clear()
            os.environ.update(old_env)
    
    return _patch_env(new_env)


settings = None

@lru_cache()
def get_settings():
    """
    Get cached application settings.
    
    Uses lru_cache for performance, so settings are loaded only once per process.
    
    Returns:
        Settings instance with values from environment variables and .env file
    """
    global settings
    if settings is None:
        settings = Settings()
        print(f"Settings initialized: {settings}")
        print(f"Database URL: {settings.DATABASE_URL}")
    return settings

settings = get_settings()


def init_settings() -> Settings:
    """
    Initialize the settings singleton.
    
    This is called at application startup to ensure settings are loaded.
    Tests can call this explicitly after patching environment variables.
    
    Returns:
        Settings instance
    """
    global settings
    settings = get_settings()
    return settings
