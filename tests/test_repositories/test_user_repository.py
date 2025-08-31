import pytest
from app.db.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def test_get_by_email(db_session, user_repository, sample_user):
    """Test retrieving a user by email."""
    retrieved_user = user_repository.get_by_email(email=sample_user.email)
    assert retrieved_user is not None
    assert retrieved_user.id == sample_user.id
    assert retrieved_user.email == sample_user.email


def test_get_by_email_nonexistent(db_session, user_repository):
    """Test retrieving a nonexistent user by email returns None."""
    retrieved_user = user_repository.get_by_email(email="nonexistent@example.com")
    assert retrieved_user is None


def test_get_by_subscription_status(db_session, user_repository, sample_user):
    """Test retrieving users by subscription status."""
    # Create users with different statuses
    paused_user = User(email="paused@example.com", subscription_status="paused")
    unsubscribed_user = User(email="unsub@example.com", subscription_status="unsubscribed")
    db_session.add_all([paused_user, unsubscribed_user])
    db_session.commit()
    
    active_users = user_repository.get_by_subscription_status(status="active")
    assert len(active_users) == 1
    assert active_users[0].id == sample_user.id
    
    paused_users = user_repository.get_by_subscription_status(status="paused")
    assert len(paused_users) == 1
    assert paused_users[0].id == paused_user.id


def test_get_by_subscription_status_pagination(db_session, user_repository):
    """Test pagination when retrieving users by subscription status."""
    # Create multiple active users
    users = [
        User(email=f"active{i}@example.com", subscription_status="active")
        for i in range(5)
    ]
    db_session.add_all(users)
    db_session.commit()
    
    # Test skip parameter
    active_users = user_repository.get_by_subscription_status(status="active", skip=2, limit=2)
    assert len(active_users) == 2
    assert active_users[0].email == "active2@example.com"
    
    # Test limit parameter
    active_users = user_repository.get_by_subscription_status(status="active", limit=3)
    assert len(active_users) == 3


def test_get_users_with_tags(db_session, user_repository, sample_user, sample_tag):
    """Test retrieving users who have specific tags."""
    # Create a second user and tag
    second_user = User(email="second@example.com", subscription_status="active")
    db_session.add(second_user)
    db_session.commit()
    
    # Create a distinct second tag
    from app.db.models.tag import Tag, TagType
    second_tag = Tag(name="javascript", description="JavaScript programming language", tag_type=TagType.language)
    db_session.add(second_tag)
    db_session.commit()
    db_session.refresh(second_tag)
    
    # Associate tags with users
    sample_user.tags.append(sample_tag)
    second_user.tags.append(second_tag)
    db_session.add_all([sample_user, second_user])
    db_session.commit()
    
    # Test retrieving users by tag
    python_users = user_repository.get_users_with_tags(tag_ids=[sample_tag.id])
    assert len(python_users) == 1
    assert python_users[0].id == sample_user.id
    
    js_users = user_repository.get_users_with_tags(tag_ids=[second_tag.id])
    assert len(js_users) == 1
    assert js_users[0].id == second_user.id


def test_update_subscription_status(db_session, user_repository, sample_user):
    """Test updating a user's subscription status."""
    updated_user = user_repository.update_subscription_status(
        user_id=sample_user.id,
        new_status="paused"
    )
    
    assert updated_user is not None
    assert updated_user.id == sample_user.id
    assert updated_user.subscription_status.value == "paused"
    
    # Verify it's updated in the database
    db_user = db_session.query(User).filter(User.id == sample_user.id).first()
    assert db_user.subscription_status.value == "paused"


def test_update_subscription_status_nonexistent(db_session, user_repository):
    """Test updating subscription status for a nonexistent user returns None."""
    updated_user = user_repository.update_subscription_status(
        user_id=9999,
        new_status="paused"
    )
    
    assert updated_user is None
