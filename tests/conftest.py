"""
Test configuration and fixtures.

This module provides fixtures and configuration for the test suite.
"""

import pytest
import os
from contextlib import contextmanager
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import text, create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect

# Define our test database URL explicitly
TEST_DB_URL = "postgresql://dcq_test_user:dcq_test_pass@localhost:5434/dcq_test_db"

# Before any tests run, make sure we're not connected to the development database
def verify_test_database():
    """Verify we're connecting to the test database"""
    from sqlalchemy import create_engine, text
    engine = create_engine(TEST_DB_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database()")).fetchone()
        db_name = result[0]
        if db_name != "dcq_test_db":
            raise RuntimeError(f"Connected to wrong database! Expected dcq_test_db, got {db_name}")
        print(f">>> Verified connection to test database: {db_name}")

# Run verification
verify_test_database()

# Disable rate limiting globally for tests - patch the module directly
def no_op_rate_limit(limit_value, key_func=None):
    """A no-op replacement for the rate limiting decorator that does nothing."""
    def decorator(func):
        return func  # Just return the original function
    return decorator

# Import and patch the rate_limiter module directly
try:
    import app.core.rate_limiter
    # Store original for debugging purposes
    original_rate_limit = app.core.rate_limiter.rate_limit
    # Replace with our no-op version
    app.core.rate_limiter.rate_limit = no_op_rate_limit
    print(">>> Rate limiting disabled for all tests")
except ImportError:
    print(">>> Could not import rate_limiter module")
except Exception as e:
    print(f">>> Error disabling rate limiting: {e}")

# Original patch_env context manager for config tests
@contextmanager
def patch_env(**env_vars):
    """
    Context manager to temporarily patch environment variables.
    
    Args:
        env_vars: Key-value pairs of environment variables to set.
    """
    original_environ = os.environ.copy()
    os.environ.update(env_vars)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(original_environ)


# Define a function to setup the test database before importing app modules
def setup_test_env():
    """Setup test environment by patching settings"""
    # Force environment variable to use test database
    os.environ["DATABASE_URL"] = TEST_DB_URL
    os.environ["TESTING"] = "true"
    # Use a fixed SECRET_KEY for tests
    os.environ["SECRET_KEY"] = "test_secret_key_consistent_for_all_tests_123"
    # Bypass email verification for tests - make sure it's a string "true" not a boolean
    os.environ["BYPASS_EMAIL_VERIFICATION"] = "true"
    os.environ["ENVIRONMENT"] = "dev"  # Ensure dev environment for tests
    
    # Patch rate limiter to be a no-op during tests
    with patch("app.core.rate_limiter.redis_available", False):
        with patch("app.core.rate_limiter.redis_client", None):
            # Direct patch the database setup
            with patch("app.db.database.settings") as mock_settings:
                # Set required attributes on the mock
                mock_settings.DATABASE_URL = TEST_DB_URL
                mock_settings.TESTING = True
                mock_settings.REDIS_URL = "memory://"
                mock_settings.SECRET_KEY = "test_secret_key_consistent_for_all_tests_123"
                mock_settings.BYPASS_EMAIL_VERIFICATION = True
                
                # Now import app modules after patching
                from app.db.database import Base, engine, SessionLocal, get_db
                
                return Base, engine, SessionLocal, get_db


# Setup test environment
Base, engine, SessionLocal, get_db = setup_test_env()

# Import app after database is configured
from app.main import app

# Note: Do not override the dependency here - we'll do it in the client fixture
# Instead of: app.dependency_overrides[get_db] = lambda: SessionLocal()

# Make sure settings.TESTING is set to True for tests
from app.core.config import settings
settings.TESTING = True

# Import all models to ensure they're registered with SQLAlchemy
from app.db.models.base_model import BaseModel
from app.db.models.user import User
from app.db.models.tag import Tag, TagType
from app.db.models.problem import Problem
from app.db.models.content_source import ContentSource
from app.db.models.delivery_log import DeliveryLog
from app.db.models.association_tables import problem_tags
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, create_access_token

# --- UPDATED TEST AUTH FIXTURES TO MATCH SEEDED USERS ---
import requests

# Helper to get JWT token for seeded user

def get_jwt_token(client, email, password):
    # Use form data with proper URL encoding for the login endpoint
    form_data = {
        "username": email,
        "password": password
    }
    print(f"\n>>> Attempting login for {email} with password {password}")
    
    # Make a direct request without rate limiting
    from app.core.config import settings
    from app.core.security import create_access_token
    from app.repositories.user import UserRepository
    from app.db.database import SessionLocal
    from datetime import timedelta
    
    # Create a direct session
    with SessionLocal() as db:
        user_repo = UserRepository(db)
        user = user_repo.get_by_email(email=email)
        
        if not user or not user.is_active:
            print(f"User not found or not active: {email}")
            raise ValueError(f"User {email} not found or not active")
        
        from app.core.security import verify_password
        if not verify_password(password, user.hashed_password):
            print(f"Invalid password for {email}")
            raise ValueError(f"Invalid password for {email}")
        
        # Create token directly
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(
            subject=str(user.id),
            expires_delta=access_token_expires
        )
        
        print(f"Login successful. Token generated for {email}")
        return token

# Fixture for admin@example.com (is_admin=True)
@pytest.fixture
def admin_auth_headers(client):
    token = get_jwt_token(client, "admin@example.com", "testpassword123")
    return {"accept": "application/json", "Authorization": f"Bearer {token}"}

# Fixture for user@example.com (is_admin=False)
@pytest.fixture
def user_auth_headers(client):
    token = get_jwt_token(client, "user@example.com", "testpassword123")
    return {"accept": "application/json", "Authorization": f"Bearer {token}"}

# Fixture for inactive@example.com (is_active=False)
@pytest.fixture
def inactive_auth_headers(client):
    token = get_jwt_token(client, "inactive@example.com", "testpassword123")
    return {"accept": "application/json", "Authorization": f"Bearer {token}"}

# Fixture for admin2@example.com (is_admin=True)
@pytest.fixture
def admin2_auth_headers(client):
    token = get_jwt_token(client, "admin2@example.com", "testpassword123")
    return {"accept": "application/json", "Authorization": f"Bearer {token}"}

# Remove or update old api_auth_headers to use seeded users
@pytest.fixture(scope="session")
def api_auth_headers(admin_auth_headers):
    """
    Returns headers with a valid JWT token for the seeded admin user.
    """
    return admin_auth_headers

# --- END UPDATED TEST AUTH FIXTURES ---

# Auth test helpers
@pytest.fixture
def auth_headers(admin_auth_headers):
    """
    Return the authorization headers with a valid token.
    """
    return admin_auth_headers


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Set up the test database for the test session.
    
    This fixture:
    1. Ensures all tables exist in the test database (no dropping)
    2. Provides test data if needed
    3. Handles cleanup after tests (no dropping)
    """
    print("\n>>> Ensuring test database tables exist...")
    
    try:
        # Create PostgreSQL enum types if they don't exist (safe, idempotent)
        with engine.begin() as conn:
            # Check if 'sourceplatform' enum exists
            result = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'sourceplatform'"))
            if not result.fetchone():
                print(">>> Creating sourceplatform enum type...")
                conn.execute(text("""
                    CREATE TYPE sourceplatform AS ENUM 
                    ('stackoverflow', 'github', 'reddit', 'twitter', 'custom')
                """))
                
            # Check if 'vettingtier' enum exists
            result = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'vettingtier'"))
            if not result.fetchone():
                print(">>> Creating vettingtier enum type...")
                conn.execute(text("""
                    CREATE TYPE vettingtier AS ENUM 
                    ('tier1_manual', 'tier2_review_needed', 'tier3_needs_review', 'tier4_approved')
                """))
                
            # Check if 'tagtype' enum exists
            result = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'tagtype'"))
            if not result.fetchone():
                print(">>> Creating tagtype enum type...")
                conn.execute(text("""
                    CREATE TYPE tagtype AS ENUM 
                    ('concept', 'language', 'framework', 'domain', 'difficulty')
                """))
            
            # Check if 'difficultylevel' enum exists
            result = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'difficultylevel'"))
            if not result.fetchone():
                print(">>> Creating difficultylevel enum type...")
                conn.execute(text("""
                    CREATE TYPE difficultylevel AS ENUM 
                    ('easy', 'medium', 'hard', 'expert')
                """))
                
            # Check if 'problemstatus' enum exists
            result = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'problemstatus'"))
            if not result.fetchone():
                print(">>> Creating problemstatus enum type...")
                conn.execute(text("""
                    CREATE TYPE problemstatus AS ENUM 
                    ('draft', 'review', 'approved', 'published', 'archived')
                """))
            
            # Check if 'processingstatus' enum exists
            result = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'processingstatus'"))
            if not result.fetchone():
                print(">>> Creating processingstatus enum type...")
                conn.execute(text("""
                    CREATE TYPE processingstatus AS ENUM 
                    ('pending', 'processing', 'completed', 'failed')
                """))
            
            # Check if 'deliverychannel' enum exists
            result = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'deliverychannel'"))
            if not result.fetchone():
                print(">>> Creating deliverychannel enum type...")
                conn.execute(text("""
                    CREATE TYPE deliverychannel AS ENUM 
                    ('email', 'sms', 'push', 'in_app')
                """))
                
            # Check if 'deliverystatus' enum exists
            result = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'deliverystatus'"))
            if not result.fetchone():
                print(">>> Creating deliverystatus enum type...")
                conn.execute(text("""
                    CREATE TYPE deliverystatus AS ENUM 
                    ('pending', 'scheduled', 'delivered', 'failed', 'opened', 'completed')
                """))
        
        # Create all tables that don't exist yet
        Base.metadata.create_all(bind=engine)
        
        # Ensure problem_metadata column exists in the problems table for SQLite
        # This is critical for tests that use SQLite
        if str(engine.url).startswith('sqlite'):
            inspector = inspect(engine)
            has_column = False
            
            for column in inspector.get_columns('problems'):
                if column['name'] == 'problem_metadata':
                    has_column = True
                    break
                    
            if not has_column:
                print(">>> Adding problem_metadata column to SQLite test database")
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE problems ADD COLUMN problem_metadata TEXT"))
                print(">>> Added problem_metadata column to SQLite test database")
        
        # Create test users if they don't exist
        with SessionLocal() as session:
            from app.db.models.user import User
            from app.core.security import get_password_hash
            
            # Create admin user
            admin = session.query(User).filter(User.email == "admin@example.com").first()
            if not admin:
                print(">>> Creating test admin user...")
                admin = User(
                    email="admin@example.com",
                    hashed_password=get_password_hash("testpassword123"),
                    is_admin=True,
                    is_active=True,
                    subscription_status="active"
                )
                session.add(admin)
            else:
                # Always update the password to ensure consistency
                print(">>> Updating admin user password...")
                admin.hashed_password = get_password_hash("testpassword123")
                admin.is_admin = True
                admin.is_active = True
                session.add(admin)
            
            # Create regular user
            user = session.query(User).filter(User.email == "user@example.com").first()
            if not user:
                print(">>> Creating test regular user...")
                user = User(
                    email="user@example.com",
                    hashed_password=get_password_hash("testpassword123"),
                    is_admin=False,
                    is_active=True,
                    subscription_status="active"
                )
                session.add(user)
            else:
                # Update password for consistency
                print(">>> Updating regular user password...")
                user.hashed_password = get_password_hash("testpassword123")
                user.is_active = True
                session.add(user)
            
            # Create inactive user
            inactive = session.query(User).filter(User.email == "inactive@example.com").first()
            if not inactive:
                print(">>> Creating test inactive user...")
                inactive = User(
                    email="inactive@example.com",
                    hashed_password=get_password_hash("testpassword123"),
                    is_admin=False,
                    is_active=False,
                    subscription_status="paused"
                )
                session.add(inactive)
            else:
                # Update password for consistency
                print(">>> Updating inactive user password...")
                inactive.hashed_password = get_password_hash("testpassword123")
                inactive.is_active = False
                session.add(inactive)
            
            # Create second admin
            admin2 = session.query(User).filter(User.email == "admin2@example.com").first()
            if not admin2:
                print(">>> Creating second test admin user...")
                admin2 = User(
                    email="admin2@example.com",
                    hashed_password=get_password_hash("testpassword123"),
                    is_admin=True,
                    is_active=True,
                    subscription_status="active"
                )
                session.add(admin2)
            else:
                # Update password for consistency
                print(">>> Updating admin2 user password...")
                admin2.hashed_password = get_password_hash("testpassword123")
                admin2.is_admin = True
                admin2.is_active = True
                session.add(admin2)
            
            session.commit()
            
    except Exception as e:
        print(f"Error setting up test database: {str(e)}")
        raise
    finally:
        # Verify we're still connected to the test database
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database()")).fetchone()
            db_name = result[0]
            print(f">>> Connected to database: {db_name} - Tables preserved")

# ... rest of the code remains the same ...

@pytest.fixture
def db_session():
    """
    Create a fresh database session for a test with transaction rollback.
    
    This fixture ensures complete isolation between tests by creating a transaction
    that is rolled back after the test completes, regardless of whether the test passes or fails.
    This prevents test data from persisting between tests and ensures a clean state for each test.
    """
    # Connect to the database and begin a transaction
    connection = engine.connect()
    transaction = connection.begin()
    
    # Create a session bound to this connection
    session_factory = sessionmaker(bind=connection)
    session = session_factory()
    
    # Start a SAVEPOINT
    session.begin_nested()
    
    # Automatically rollback all changes within the session at the end of each test
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()
    
    # Yield the session
    try:
        yield session
    finally:
        # Close the session and rollback the transaction
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    """
    Create a test client for the FastAPI application with db dependency override.
    
    This fixture provides a FastAPI TestClient configured to use the isolated database session.
    It overrides the database dependency to ensure that all API requests are executed using
    the same isolated transaction as the test itself.
    
    Args:
        db_session: The database session with transaction isolation
        
    Returns:
        TestClient: A configured FastAPI test client
    """
    # Import here to avoid circular imports
    from app.main import app
    from app.db.database import get_db
    from unittest.mock import MagicMock, AsyncMock
    from fastapi import status, Depends
    import functools
    
    # Override the database dependency to use our test session
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Don't close the session here, let the fixture handle it
    
    # Create proper async-compatible mock decorators to replace rate limiting
    def mock_decorator(func):
        @functools.wraps(func)
        def sync_wrapped(*args, **kwargs):
            return func(*args, **kwargs)
        return sync_wrapped
    
    async def mock_async_decorator(func):
        @functools.wraps(func)
        async def async_wrapped(*args, **kwargs):
            return await func(*args, **kwargs)
        return async_wrapped
    
    # Mock the rate_limit function in the app
    from app.core.rate_limiter import rate_limit
    
    # Store the original function
    original_rate_limit = rate_limit
    
    # Replace it with our mock version that doesn't actually rate limit
    def mock_rate_limit(limit_value, key_func=None):
        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                return mock_async_decorator(func)
            return mock_decorator(func)
        return decorator
    
    # Patch the rate limiter
    import asyncio
    with patch('app.core.rate_limiter.rate_limit', mock_rate_limit):
        # Clear any existing rate limit error handlers
        exception_handlers = getattr(app, 'exception_handlers', {})
        if 429 in exception_handlers:
            del exception_handlers[429]
            
        # Override the database dependency
        app.dependency_overrides[get_db] = override_get_db
        
        # Create test client with the app
        with TestClient(app) as test_client:
            yield test_client
        
        # Clear overrides after test
        app.dependency_overrides.clear()


@pytest.fixture
def create_user(db_session):
    """
    Create a user for testing.
    """
    user = User(email="test@example.com", subscription_status="active")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def create_tag(db_session):
    """
    Create a tag for testing.
    """
    from app.db.models.tag import Tag, TagType
    
    tag = Tag(
        name="python", 
        description="Python programming language",
        tag_type=TagType.concept,
        is_featured=True,
        is_private=False
    )
    db_session.add(tag)
    db_session.commit()
    db_session.refresh(tag)
    return tag


@pytest.fixture
def create_content_source(db_session):
    """
    Create a content source for testing.
    """
    content_source = ContentSource(
        source_platform="stackoverflow",
        source_identifier="test-12345",
        raw_data={"url": "https://stackoverflow.com/questions/12345"},
        notes="Test content source"
    )
    db_session.add(content_source)
    db_session.commit()
    db_session.refresh(content_source)
    return content_source


@pytest.fixture
def create_problem(db_session, create_content_source):
    """
    Create a problem for testing.
    """
    problem = Problem(
        title="Test Problem",
        description="This is a test problem description",
        solution="This is the solution",
        vetting_tier="tier1",
        status="pending",
        content_source_id=create_content_source.id
    )
    db_session.add(problem)
    db_session.commit()
    db_session.refresh(problem)
    return problem


@pytest.fixture
def create_delivery_log(db_session, create_user, create_problem):
    """
    Create a delivery log for testing.
    """
    delivery_log = DeliveryLog(
        user_id=create_user.id,
        problem_id=create_problem.id,
        status="delivered"
    )
    db_session.add(delivery_log)
    db_session.commit()
    db_session.refresh(delivery_log)
    return delivery_log


# Test repositories and factory fixtures
@pytest.fixture
def test_user(db_session):
    """
    Create a user for repository-level testing.
    """
    from app.repositories.user import UserRepository
    from app.schemas.user import UserCreate
    
    user_repo = UserRepository(db_session)
    user_data = UserCreate(
        email="test-user@example.com",
        subscription_status="active"
    )
    user = user_repo.create(user_data)
    
    return {"id": user.id, "email": user.email}


@pytest.fixture
def test_tag(db_session):
    """
    Create a test tag for repository-level testing.
    """
    from app.repositories.tag import TagRepository
    from app.schemas.tag import TagCreate
    from app.db.models.tag import TagType
    
    tag_repo = TagRepository(db_session)
    
    # First check if tag already exists
    existing_tag = tag_repo.get_by_name("test-tag")
    if existing_tag:
        return {"id": existing_tag.id, "name": existing_tag.name}
    
    # Create a parent tag
    parent_tag_data = TagCreate(
        name="parent-tag",
        description="Parent tag for testing",
        tag_type=TagType.concept,
        is_featured=True,
        is_private=False
    )
    parent_tag = tag_repo.create(parent_tag_data)
    
    # Create a child tag
    tag_data = TagCreate(
        name="test-tag",
        description="Test tag for testing",
        tag_type=TagType.language,
        is_featured=True,
        is_private=False,
        parent_tag_id=parent_tag.id
    )
    tag = tag_repo.create(tag_data)
    
    return {"id": tag.id, "name": tag.name, "parent_id": parent_tag.id}


@pytest.fixture
def test_content_source(db_session):
    """
    Create a test content source for repository-level testing.
    """
    from app.repositories.content_source import ContentSourceRepository
    from app.schemas.content_source import ContentSourceCreate
    
    cs_repo = ContentSourceRepository(db_session)
    cs_data = ContentSourceCreate(
        source_platform="stackoverflow",
        source_identifier="test-12345",
        raw_data={"url": "https://stackoverflow.com/questions/12345"},
        notes="Test content source for testing"
    )
    
    cs = cs_repo.create(cs_data)
    
    return {"id": cs.id, "source_identifier": cs.source_identifier}


@pytest.fixture
def test_problem(db_session, test_content_source):
    """
    Create a test problem for repository-level testing.
    """
    from app.repositories.problem import ProblemRepository
    from app.schemas.problem import ProblemCreate
    
    problem_repo = ProblemRepository(db_session)
    problem_data = ProblemCreate(
        title="Test Problem",
        description="Test problem description",
        solution="Test solution",
        content_source_id=test_content_source["id"],
        # Add problem_metadata for test compatibility
        problem_metadata={"tag_data": {
            "raw_tags": ["python", "testing"],
            "normalized_tags": ["Python", "Testing"],
            "safe_tags": ["Python", "Testing"],
            "pending_tags": []
        }}
    )
    
    problem = problem_repo.create(problem_data)
    
    return {"id": problem.id, "title": problem.title}


@pytest.fixture
def test_delivery_log(db_session, test_user, test_problem):
    """
    Create a test delivery log for repository-level testing.
    """
    from app.repositories.delivery_log import DeliveryLogRepository
    from app.schemas.delivery_log import DeliveryLogCreate
    from datetime import datetime
    
    dl_repo = DeliveryLogRepository(db_session)
    dl_data = DeliveryLogCreate(
        user_id=test_user["id"],
        problem_id=test_problem["id"],
        delivery_status="delivered",
        delivery_time=datetime.now().isoformat()
    )
    
    dl = dl_repo.create(dl_data)
    
    return {"id": dl.id, "user_id": dl.user_id, "problem_id": dl.problem_id}


@pytest.fixture
def api_client():
    """
    Returns a FastAPI TestClient for API requests.
    """
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)
