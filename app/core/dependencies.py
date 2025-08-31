from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.database import get_db


def get_settings_dependency() -> Settings:
    """
    FastAPI dependency for accessing application settings.
    
    This function is used with FastAPI's dependency injection system to provide
    application configuration to API route handlers.
    
    Returns:
        Settings instance with configuration values
    """
    return get_settings()


def get_db_with_settings(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dependency)
) -> Session:
    """
    Get database session with settings dependency.
    
    This is useful for operations that need both database access and
    configuration settings.
    
    Args:
        db: SQLAlchemy database session
        settings: Application settings
        
    Returns:
        SQLAlchemy database session
    """
    # Here we could use settings to configure the session if needed
    # For example, set timeout or other connection parameters
    return db
