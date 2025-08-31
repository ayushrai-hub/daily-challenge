from typing import Optional, Tuple, Generator

from sqlalchemy import create_engine
# Use SQLAlchemy 2.0 compatible import for declarative base
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from app.core.config import settings

# Create SQLAlchemy base model using SQLAlchemy 2.0 compatible syntax
Base = declarative_base()

# Global variables to hold the engine and session factory
engine = None
SessionLocal = None


def init_db(override_db_url: Optional[str] = None) -> Tuple[any, sessionmaker, any]:
    """
    Initialize the database connection.
    
    Args:
        override_db_url: Optional override for database URL, useful for testing
        
    Returns:
        Tuple containing (engine, SessionLocal, Base)
    """
    global engine, SessionLocal
    
    # Get database URL from settings or override
    db_url = override_db_url or settings.DATABASE_URL
    
    # Create engine with appropriate logging level
    # Use getattr to safely access DB_ECHO_LOG attribute with a default of False
    echo_log = getattr(settings, 'DB_ECHO_LOG', False)
    
    engine = create_engine(
        db_url,
        echo=echo_log,
        pool_pre_ping=True,
    )
    
    # Create sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return engine, SessionLocal, Base


# Initialize the database on module import
if engine is None or SessionLocal is None:
    engine, SessionLocal, Base = init_db()


def get_db() -> Generator[Session, None, None]:
    """
    Get a database session.
    
    Yields:
        SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
