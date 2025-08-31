"""
Test Configuration

This module provides testing-specific configuration settings.
It overrides the default configuration with test-specific values.
"""

import os
from typing import Dict, Any, List, Optional, Union
from pydantic import field_validator, ValidationInfo
from pydantic import validator
from app.core.config import Settings, AppEnvironment, LogLevel
import psycopg2
from urllib.parse import quote_plus

class TestSettings(Settings):
    """
    Test-specific settings that override the base settings.
    
    This is used to configure the application for testing with:
    - Different database URL
    - Test-specific logging configuration
    - Mock services if needed
    """
    # Core application settings
    APP_NAME: str = "Daily Challenge Test"
    DEBUG: bool = True
    ENVIRONMENT: AppEnvironment = AppEnvironment.TEST
    
    # Override database settings for test database
    POSTGRES_USER: str = "dcq_test_user"
    POSTGRES_PASSWORD: str = "dcq_test_pass"
    POSTGRES_DB: str = "dcq_test_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5434"  # Using test port defined in docker-compose.test.yml
    
    # Testing flags
    TESTING: bool = True
    
    # Override logging for tests
    LOG_FILE_ENABLED: bool = False  # Disable file logging in tests
    LOG_LEVEL: LogLevel = LogLevel.DEBUG  # More verbose logging for tests
    LOG_JSON_FORMAT: bool = False
    
    # Add explicit DATABASE_URL to ensure it's used
    DATABASE_URL: str = None
    
    @field_validator("DATABASE_URL")
    def validate_database_url(cls, v: Optional[str], info: ValidationInfo) -> str:
        """
        Complete override of the database URL assembly to ensure test database uses port 5434.
        """
        # Get the field values from the data dictionary
        data = info.data
        user = data.get('POSTGRES_USER')
        password = data.get('POSTGRES_PASSWORD')
        host = data.get('POSTGRES_HOST')
        port = data.get('POSTGRES_PORT')
        db = data.get('POSTGRES_DB')
        
        print(f"Test Database components: user={user}, password=***, host={host}, port={port}, db={db}")
        
        # Ensure all required values are present
        if not all([user, password, host, port, db]):
            raise ValueError("Missing required test database configuration")
        
        # For test database, explicitly use port 5434
        test_port = 5434
            
        # Escape special characters in URL components
        escaped_user = quote_plus(user)
        escaped_password = quote_plus(password)
        escaped_host = quote_plus(host)
        escaped_db = quote_plus(db)
        
        # Construct the URL with proper escaping and explicit test port
        url = f"postgresql://{escaped_user}:{escaped_password}@{escaped_host}:{test_port}/{escaped_db}"
        print(f"Final Test Database URL: {url}")
        
        # Test the connection
        try:
            conn = psycopg2.connect(url)
            conn.close()
            print("Test database connection successful")
        except Exception as e:
            print(f"Test database connection failed: {str(e)}")
            raise
            
        return url
    
    # Override model_config to avoid loading from .env
    model_config = {
        "env_file": None,  # Don't load from .env file for tests
        "extra": "ignore",
    }

# Create the test settings instance
test_settings = TestSettings()