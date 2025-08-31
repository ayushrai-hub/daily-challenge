"""
Database session module for compatibility and convenience.
Re-exports session components from database.py
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.database import engine, SessionLocal, Base, get_db
from app.core.config import settings

# Create async engine and session for use with Celery tasks
# This converts the standard PostgreSQL URL to an async one
async_engine = create_async_engine(
    settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://'),
    echo=getattr(settings, 'DB_ECHO_LOG', False),
    pool_pre_ping=True,
)

# Create async session factory
async_session = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session."""
    session = async_session()
    try:
        yield session
    finally:
        await session.close()


def get_sync_db():
    """Get a synchronous database session for use in non-async contexts like Celery tasks.
    
    This uses the standard SQLAlchemy sessionmaker (SessionLocal) from database.py.
    """
    return get_db()


__all__ = ["engine", "SessionLocal", "Base", "get_db", "async_session", "get_async_db", "get_sync_db"]
