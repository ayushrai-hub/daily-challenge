import pytest
import uuid
from uuid import UUID
from pydantic import ValidationError
from datetime import datetime

from app.schemas.user import UserCreate, UserRead
from app.schemas.tag import TagCreate, TagRead
from app.schemas.problem import ProblemCreate, ProblemRead
from app.schemas.content_source import ContentSourceCreate, ContentSourceRead
from app.schemas.delivery_log import DeliveryLogCreate, DeliveryLogRead

from app.db.models.user import SubscriptionStatus, User as UserModel
from app.db.models.tag import Tag as TagModel, TagType
from app.db.models.problem import VettingTier, ProblemStatus, DifficultyLevel, Problem as ProblemModel
from app.db.models.content_source import SourcePlatform, ProcessingStatus, ContentSource as ContentSourceModel
from app.db.models.delivery_log import DeliveryStatus, DeliveryChannel, DeliveryLog as DeliveryLogModel

# User schemas tests
def test_user_create_validation():
    with pytest.raises(ValidationError):
        UserCreate()
    user = UserCreate(email="test@example.com", password="TestPassword123!")
    assert user.email == "test@example.com"
    assert user.subscription_status == SubscriptionStatus.active

def test_user_read_from_orm():
    now = datetime.utcnow()
    test_uuid = uuid.uuid4()
    u = UserModel(
        email="u@x.com", 
        hashed_password="hashed", 
        is_active=True, 
        is_admin=False,
        subscription_status=SubscriptionStatus.paused
    )
    u.id = test_uuid
    u.created_at = now
    u.updated_at = now
    # Use model_validate instead of from_orm (Pydantic v2)
    ur = UserRead.model_validate(u, from_attributes=True)
    assert ur.id == test_uuid
    assert ur.email == "u@x.com"
    assert ur.subscription_status == SubscriptionStatus.paused
    assert ur.created_at == now
    assert ur.updated_at == now
    assert ur.is_active is True
    assert ur.is_admin is False

# Tag schemas tests
def test_tag_create_validation():
    with pytest.raises(ValidationError):
        TagCreate()
    t = TagCreate(
        name="tag1", 
        description="Test tag",
        tag_type="concept",
        is_featured=True,
        is_private=False
    )
    assert t.name == "tag1"
    assert t.tag_type == TagType.concept
    assert t.is_featured is True
    assert t.is_private is False

def test_tag_read_from_orm(db_session):
    # Create a test tag without setting children directly
    t = TagModel(
        name="t1", 
        description="Test tag",
        tag_type=TagType.concept,
        is_featured=True,
        is_private=False
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    
    # Now validate with the model using the standard Pydantic approach
    # This uses our improved from_orm method in the schema
    tr = TagRead.model_validate(t, from_attributes=True)
    
    # Assertions
    assert tr.id == t.id
    assert tr.name == "t1"
    assert tr.tag_type == TagType.concept
    assert tr.is_featured is True
    assert tr.is_private is False
    # Children should be an empty list
    assert tr.children == []

# Problem schemas tests
def test_problem_create_validation():
    with pytest.raises(ValidationError):
        ProblemCreate()
    p = ProblemCreate(
        title="Problem 1",
        description="Problem content",
        vetting_tier=VettingTier.tier3_needs_review,
        status=ProblemStatus.draft,
        difficulty_level=DifficultyLevel.medium
    )
    assert p.title == "Problem 1"
    assert p.description == "Problem content"
    assert p.vetting_tier == VettingTier.tier3_needs_review
    assert p.status == ProblemStatus.draft
    assert p.difficulty_level == DifficultyLevel.medium

def test_problem_read_from_orm():
    test_uuid = uuid.uuid4()
    p = ProblemModel(
        title="p1", 
        description="content", 
        vetting_tier=VettingTier.tier1_manual,
        status=ProblemStatus.draft,
        difficulty_level=DifficultyLevel.medium
    )
    p.id = test_uuid
    # Use model_validate instead of from_orm (Pydantic v2)
    pr = ProblemRead.model_validate(p, from_attributes=True)
    assert pr.id == test_uuid
    assert pr.title == "p1"
    assert pr.description == "content"
    assert pr.vetting_tier == VettingTier.tier1_manual
    assert pr.status == ProblemStatus.draft
    assert pr.difficulty_level == DifficultyLevel.medium

# ContentSource schemas tests
def test_content_source_create_validation():
    with pytest.raises(ValidationError):
        ContentSourceCreate()
    cs = ContentSourceCreate(
        source_identifier="example-id",
        source_platform=SourcePlatform.gh_issues,
        processing_status=ProcessingStatus.pending
    )
    assert cs.source_identifier == "example-id"
    assert cs.source_platform == SourcePlatform.gh_issues
    assert cs.processing_status == ProcessingStatus.pending

def test_content_source_read_from_orm():
    test_uuid = uuid.uuid4()
    cs = ContentSourceModel(
        source_identifier="test-id",
        source_platform=SourcePlatform.gh_issues,
        processing_status=ProcessingStatus.pending
    )
    cs.id = test_uuid
    # Use model_validate instead of from_orm (Pydantic v2)
    cr = ContentSourceRead.model_validate(cs, from_attributes=True)
    assert cr.id == test_uuid
    assert cr.source_identifier == "test-id"
    assert cr.source_platform == SourcePlatform.gh_issues
    assert cr.processing_status == ProcessingStatus.pending

# DeliveryLog schemas tests
def test_delivery_log_create_validation():
    with pytest.raises(ValidationError):
        DeliveryLogCreate()
    
    # Generate UUIDs for foreign keys
    user_uuid = uuid.uuid4()
    problem_uuid = uuid.uuid4()
    
    dl = DeliveryLogCreate(
        user_id=user_uuid,
        problem_id=problem_uuid,
        status=DeliveryStatus.delivered,
        delivery_channel=DeliveryChannel.email
    )
    assert dl.user_id == user_uuid
    assert dl.problem_id == problem_uuid
    assert dl.status == DeliveryStatus.delivered
    assert dl.delivery_channel == DeliveryChannel.email

def test_delivery_log_read_from_orm():
    now = datetime.utcnow()
    # Generate UUIDs for IDs
    log_uuid = uuid.uuid4()
    user_uuid = uuid.uuid4()
    problem_uuid = uuid.uuid4()
    
    dlm = DeliveryLogModel(
        user_id=user_uuid,
        problem_id=problem_uuid,
        status=DeliveryStatus.delivered,
        delivery_channel=DeliveryChannel.email,
        scheduled_at=now
    )
    dlm.id = log_uuid
    dlm.created_at = now
    dlm.updated_at = now
    # Use model_validate instead of from_orm (Pydantic v2)
    dlr = DeliveryLogRead.model_validate(dlm, from_attributes=True)
    assert dlr.id == log_uuid
    assert dlr.user_id == user_uuid
    assert dlr.problem_id == problem_uuid
    assert dlr.status == DeliveryStatus.delivered
    assert dlr.delivery_channel == DeliveryChannel.email
    assert dlr.scheduled_at == now
    assert dlr.created_at == now
    assert dlr.updated_at == now
