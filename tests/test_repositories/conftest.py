import os
import pytest
from sqlalchemy import create_engine, JSON, String
# Update to SQLAlchemy 2.0 compatible imports
from sqlalchemy.orm import sessionmaker, clear_mappers, declarative_base
from sqlalchemy.pool import StaticPool
from datetime import datetime
import uuid
from uuid import UUID

from app.db.models.user import User, SubscriptionStatus
from app.db.models.tag import Tag, TagType
from app.db.models.tag_hierarchy import TagHierarchy
from app.db.models.tag_normalization import TagNormalization, TagReviewStatus, TagSource
from app.db.models.problem import Problem, VettingTier, ProblemStatus, DifficultyLevel
from app.db.models.delivery_log import DeliveryLog, DeliveryStatus, DeliveryChannel
from app.db.models.content_source import SourcePlatform, ProcessingStatus

# Create separate test models for SQLite compatibility
TestBase = declarative_base()

# Import repositories
from app.repositories.user import UserRepository
from app.repositories.tag import TagRepository
from app.repositories.problem import ProblemRepository
from app.repositories.content_source import ContentSourceRepository
from app.repositories.delivery_log import DeliveryLogRepository

# Use counters to ensure unique tag names and emails across tests
tag_counter = 0
user_counter = 0

# Import the actual model definitions but make SQLite-compatible replacements
from sqlalchemy import Column, String, Enum, JSON, Text, ForeignKey, DateTime, Boolean, Table, event, Integer, Float
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta

# Define SQLite-compatible models with proper relationships
# SQLite does not support array, enum or timestamp with timezone

# Association tables for many-to-many relationships
test_user_tags = Table(
    "user_tags", 
    TestBase.metadata,
    Column("user_id", PostgresUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("tag_id", PostgresUUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True)
)

test_problem_tags = Table(
    "problem_tags",
    TestBase.metadata,
    Column("problem_id", PostgresUUID(as_uuid=True), ForeignKey("problems.id"), primary_key=True),
    Column("tag_id", PostgresUUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True)
)

class TestEmailQueue(TestBase):
    __tablename__ = "email_queue"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    email_type = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    html_content = Column(Text, nullable=True)
    text_content = Column(Text, nullable=True)
    template_id = Column(String, nullable=True)
    template_data = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default="pending")
    scheduled_for = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    tracking_id = Column(String, nullable=True)
    
    # Retry and failure tracking fields added in custom_add_retry_fields migration
    retry_count = Column(Integer, default=0, nullable=False)
    last_retry_at = Column(DateTime, nullable=True)
    max_retries = Column(Integer, default=3, nullable=False)
    delivery_data = Column(JSON, nullable=True)
    
    problem_id = Column(PostgresUUID(as_uuid=True), ForeignKey("problems.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # relationships
    user = relationship("TestUser", back_populates="emails")


class TestVerificationToken(TestBase):
    """Model for storing email verification tokens in tests."""
    __tablename__ = "verification_tokens"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, nullable=False, index=True)
    is_used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    token_type = Column(String, nullable=False, default="email_verification")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # relationships
    user = relationship("TestUser", backref="verification_tokens")


class TestVerificationMetrics(TestBase):
    """Model for tracking email verification metrics in tests."""
    __tablename__ = "verification_metrics"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(String, nullable=False, index=True)
    
    # Total counts
    verification_requests_sent = Column(Integer, default=0, nullable=False)
    verification_completed = Column(Integer, default=0, nullable=False)
    verification_expired = Column(Integer, default=0, nullable=False)
    resend_requests = Column(Integer, default=0, nullable=False)
    
    # Time-based metrics (in seconds)
    avg_verification_time = Column(Float, nullable=True)
    median_verification_time = Column(Float, nullable=True)
    min_verification_time = Column(Float, nullable=True)
    max_verification_time = Column(Float, nullable=True)
    
    # Standard timestamps
    date_created = Column(DateTime, nullable=False, server_default=func.now())
    last_updated = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class TestUser(TestBase):
    __tablename__ = "users"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    subscription_status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.active)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # relationships
    tags = relationship("TestTag", secondary=test_user_tags, back_populates="users")
    delivery_logs = relationship("TestDeliveryLog", back_populates="user")
    emails = relationship("TestEmailQueue", back_populates="user")


class TestTag(TestBase):
    __tablename__ = "tags"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    tag_type = Column(String, nullable=False)  # Use String instead of Enum for SQLite
    is_featured = Column(Boolean, default=False, nullable=False)
    is_private = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # relationships
    users = relationship("TestUser", secondary=test_user_tags, back_populates="tags")
    problems = relationship("TestProblem", secondary=test_problem_tags, back_populates="tags")
    
    # Multi-parent relationship using tag_hierarchy
    parents = relationship(
        "TestTag",
        secondary="tag_hierarchy",
        primaryjoin="TestTagHierarchy.child_tag_id == TestTag.id",
        secondaryjoin="TestTagHierarchy.parent_tag_id == TestTag.id",
        backref="children",
        viewonly=True
    )


class TestTagHierarchy(TestBase):
    __tablename__ = "tag_hierarchy"
    
    parent_tag_id = Column(PostgresUUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    child_tag_id = Column(PostgresUUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    relationship_type = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class TestTagNormalization(TestBase):
    __tablename__ = "tag_normalizations"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    original_name = Column(String, nullable=False, index=True)
    normalized_name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    parent_tag_ids = Column(JSON, nullable=True)  # JSON instead of ARRAY for SQLite
    review_status = Column(String, nullable=False, server_default="pending", index=True)  # String instead of Enum
    admin_notes = Column(Text, nullable=True)
    source = Column(String, nullable=False, server_default="ai_generated", index=True)  # String instead of Enum
    confidence_score = Column(Float, nullable=True)
    reviewed_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    approved_tag_id = Column(PostgresUUID(as_uuid=True), ForeignKey("tags.id"), nullable=True, index=True)
    auto_approved = Column(Boolean, nullable=False, server_default="0")  # Use 0 instead of false for SQLite
    
    # Relationships
    approved_tag = relationship("TestTag", foreign_keys=[approved_tag_id], lazy="joined")


class TestContentSource(TestBase):
    __tablename__ = "content_sources"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_platform = Column(Enum(SourcePlatform), nullable=False)
    source_identifier = Column(String, nullable=False, index=True)
    source_url = Column(String, nullable=True)
    source_title = Column(String, nullable=True)
    raw_data = Column(JSON, nullable=True)
    # Change ARRAY to JSON for SQLite compatibility
    source_tags = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    processing_status = Column(Enum(ProcessingStatus), nullable=False, default=ProcessingStatus.pending)
    processed_text = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    ingested_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # relationships
    problems = relationship("TestProblem", back_populates="content_source")


class TestProblem(TestBase):
    __tablename__ = "problems"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    solution = Column(Text, nullable=True)
    vetting_tier = Column(String, nullable=False, default=VettingTier.tier3_needs_review.value)
    status = Column(String, nullable=False, default=ProblemStatus.draft.value)
    difficulty_level = Column(String, nullable=False)
    content_source_id = Column(PostgresUUID(as_uuid=True), ForeignKey("content_sources.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Add problem_metadata field for SQLite compatibility
    problem_metadata = Column(JSON, nullable=True, default={})
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # relationships
    content_source = relationship("TestContentSource", back_populates="problems")
    tags = relationship("TestTag", secondary=test_problem_tags, back_populates="problems")
    delivery_logs = relationship("TestDeliveryLog", back_populates="problem")


class TestDeliveryLog(TestBase):
    __tablename__ = "delivery_logs"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    problem_id = Column(PostgresUUID(as_uuid=True), ForeignKey("problems.id"), nullable=False)
    status = Column(Enum(DeliveryStatus), nullable=False, default=DeliveryStatus.scheduled)
    delivery_channel = Column(Enum(DeliveryChannel), nullable=False, default=DeliveryChannel.email)
    scheduled_at = Column(DateTime, server_default=func.now(), nullable=False)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # relationships
    user = relationship("TestUser", back_populates="delivery_logs")
    problem = relationship("TestProblem", back_populates="delivery_logs")


@pytest.fixture(scope="function")
def in_memory_db():
    """Creates a fresh in-memory SQLite database for each test function."""
    # Handle UUID conversions for SQLite
    def _uuid_converter(uuid_str):
        if uuid_str is None:
            return None
        return uuid.UUID(uuid_str)
    
    # Create in-memory database with SQLite
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Add UUID support to SQLite
    @event.listens_for(engine, "connect")
    def do_connect(dbapi_connection, connection_record):
        # Register UUID converter
        dbapi_connection.create_function("uuid", 1, lambda x: str(uuid.UUID(x)))
        
        # Enable foreign key support
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # Create all tables for this test
    TestBase.metadata.create_all(engine)
    
    yield engine
    
    # Clean up after the test
    TestBase.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(in_memory_db):
    """Creates a fresh database session for each test."""
    Session = sessionmaker(bind=in_memory_db)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def user_repository(db_session):
    """Returns a UserRepository instance for testing."""
    return UserRepository(db=db_session)


@pytest.fixture(scope="function")
def tag_repository(db_session):
    """Returns a TagRepository instance for testing."""
    return TagRepository(db=db_session)


@pytest.fixture(scope="function")
def problem_repository(db_session):
    """Returns a ProblemRepository instance for testing."""
    return ProblemRepository(db=db_session)


@pytest.fixture(scope="function")
def content_source_repository(db_session):
    """Returns a ContentSourceRepository instance for testing."""
    return ContentSourceRepository(db=db_session)


@pytest.fixture(scope="function")
def delivery_log_repository(db_session):
    """Returns a DeliveryLogRepository instance for testing."""
    return DeliveryLogRepository(db=db_session)


@pytest.fixture(scope="function")
def sample_user(db_session):
    """Creates a sample user for testing."""
    global user_counter
    user_counter += 1
    
    user = TestUser(
        id=uuid.uuid4(),
        email=f"test{user_counter}@example.com",  # Unique email address for each test
        hashed_password="hashed_password",
        subscription_status=SubscriptionStatus.active,
        is_active=True,
        is_email_verified=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def sample_tag(db_session):
    """Creates a sample tag for testing."""
    global tag_counter
    tag_counter += 1
    
    # Create a unique tag name but with a predictable prefix
    tag_name = f"python_{tag_counter}"
    
    tag = TestTag(
        id=uuid.uuid4(),
        name=tag_name,
        description=f"{tag_name} programming language",
        tag_type="concept",  # Use string instead of enum for SQLite compatibility
        is_featured=True,
        is_private=False
    )
    db_session.add(tag)
    db_session.commit()
    db_session.refresh(tag)
    return tag


@pytest.fixture(scope="function")
def sample_content_source(db_session):
    """Creates a sample content source for testing."""
    content_source = TestContentSource(
        id=uuid.uuid4(),
        source_platform=SourcePlatform.stackoverflow,
        source_identifier="12345",
        source_url="https://stackoverflow.com/questions/12345",
        source_title="Sample question",
        raw_data={
            "title": "Sample question", 
            "body": "Sample content"
        },
        # Use JSON list instead of ARRAY for SQLite compatibility
        source_tags=["python", "sqlalchemy"],
        processing_status=ProcessingStatus.pending
    )
    db_session.add(content_source)
    db_session.commit()
    db_session.refresh(content_source)
    return content_source


@pytest.fixture(scope="function")
def sample_problem(db_session, sample_content_source):
    """Creates a sample problem for testing."""
    problem = TestProblem(
        id=uuid.uuid4(),
        title="Sample problem",
        description="This is a sample problem description",
        solution="Sample solution",
        # Use string values instead of enum objects for SQLite compatibility
        vetting_tier=VettingTier.tier3_needs_review.value,
        status=ProblemStatus.draft.value,
        difficulty_level=DifficultyLevel.medium.value,
        content_source_id=sample_content_source.id,
        # Initialize with empty dict for problem_metadata
        problem_metadata={}
    )
    db_session.add(problem)
    db_session.commit()
    db_session.refresh(problem)
    return problem


@pytest.fixture(scope="function")
def sample_delivery_log(db_session, sample_user, sample_problem):
    """Creates a sample delivery log for testing."""
    delivery_log = TestDeliveryLog(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        problem_id=sample_problem.id,
        status=DeliveryStatus.scheduled,  # Changed from delivered to match the actual enum
        delivery_channel=DeliveryChannel.email,
        meta={"channel": "email"},
        scheduled_at=datetime.now(),
        delivered_at=None  # Set to None since it's scheduled, not delivered
    )
    db_session.add(delivery_log)
    db_session.commit()
    db_session.refresh(delivery_log)
    return delivery_log
