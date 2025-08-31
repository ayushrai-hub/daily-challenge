import pytest
from sqlalchemy.orm import Session
import time
from app.repositories.base import BaseRepository
from app.db.models.user import User, SubscriptionStatus
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash


def test_base_repository_initialization(db_session, user_repository):
    """Test that a BaseRepository can be properly initialized."""
    assert isinstance(user_repository, BaseRepository)
    assert user_repository.model == User
    assert isinstance(user_repository.db, Session)


def test_get_by_id(db_session, user_repository, sample_user):
    """Test retrieving a record by ID."""
    retrieved_user = user_repository.get(sample_user.id)
    assert retrieved_user is not None
    assert retrieved_user.id == sample_user.id
    assert retrieved_user.email == sample_user.email


def test_get_nonexistent_id(db_session, user_repository):
    """Test retrieving a nonexistent record returns None."""
    nonexistent_id = 9999
    retrieved_user = user_repository.get(nonexistent_id)
    assert retrieved_user is None


def test_get_multi(db_session, user_repository, sample_user):
    """Test retrieving multiple records with pagination."""
    # Create a second user
    second_user = User(email="second@example.com", subscription_status=SubscriptionStatus.active)
    db_session.add(second_user)
    db_session.commit()
    
    # Test default pagination (should return both users)
    users = user_repository.get_multi()
    assert len(users) == 2
    
    # Test skip parameter
    users = user_repository.get_multi(skip=1)
    assert len(users) == 1
    assert users[0].id == second_user.id
    
    # Test limit parameter
    users = user_repository.get_multi(limit=1)
    assert len(users) == 1
    assert users[0].id == sample_user.id


@pytest.mark.parametrize("test_model_type", ["run_with_user_model"])
def test_get_multi_with_filters(db_session, user_repository, test_model_type):
    """
    Test retrieving multiple records with filters.
    """
    if test_model_type == "skip_test_if_filter_issue":
        pytest.skip("Skipping filter test due to known test environment limitations")
        
    # Use the actual User model that the repository is configured with
    from app.db.models.user import User
    
    # First, clear any existing users to start with a clean state
    # But don't delete the admin user that might be needed for other tests
    existing_users = db_session.query(User).filter(User.email != "admin@example.com").all()
    for user in existing_users:
        db_session.delete(user)
    db_session.commit()
    
    # Now create our test users with a unique attribute we can query
    import uuid
    unique_guid = str(uuid.uuid4())
    test_email_prefix = f"test_{unique_guid}"
    
    # Create exactly 3 test users with our unique email prefix
    users_to_create = []
    for i in range(3):
        users_to_create.append(User(
            email=f"{test_email_prefix}_{i}@example.com",
            hashed_password="testpwd",
            is_active=True,
            is_admin=False,
            subscription_status="active"
        ))
    
    # Add all users at once and commit
    db_session.add_all(users_to_create)
    db_session.commit()
    
    try:
        # Verify our setup by directly querying the database with User model
        direct_query_users = db_session.query(User).filter(
            User.email.like(f"{test_email_prefix}%")
        ).all()
        
        # We should have exactly 3 users that match our prefix
        assert len(direct_query_users) == 3, f"Expected 3 test users, got {len(direct_query_users)}"
        
        # Debug: Print all users in the database
        all_users = db_session.query(User).all()
        print("\n=== All users in database ===")
        for u in all_users:
            print(f"ID: {u.id}, Email: {u.email}, Is Admin: {getattr(u, 'is_admin', False)}")
        
        # Now test the actual repository filter using the email field
        filter_email = f"{test_email_prefix}_1@example.com"
        print(f"\n=== Filtering for email: {filter_email} ===")
        
        # Debug: Check what the repository returns
        # Pass filters as keyword arguments instead of a dictionary
        filtered_users = user_repository.get_multi(
            email=filter_email
        )
        
        print(f"\n=== Filtered users ===")
        for i, user in enumerate(filtered_users, 1):
            print(f"{i}. ID: {user.id}, Email: {user.email}")
        
        # We should get exactly 1 user with this specific email
        assert len(filtered_users) == 1, f"Expected 1 filtered user, got {len(filtered_users)}"
        assert filtered_users[0].email == filter_email, f"Expected email {filter_email}, got {filtered_users[0].email if filtered_users else 'None'}"
        
        # Also test with a different filter field
        filtered_active_users = user_repository.get_multi(
            is_active=True
        )
        # Should get all our test users plus any admin users
        assert len(filtered_active_users) >= 3
        
    finally:
        # Clean up our test users
        for user in users_to_create:
            # Make sure the user still exists before trying to delete
            user_in_db = db_session.query(User).filter(User.id == user.id).first()
            if user_in_db:
                db_session.delete(user_in_db)
        db_session.commit()


def test_create(db_session, user_repository):
    """Test creating a new record."""
    user_create_data = {
        "email": "new@example.com",
        "hashed_password": get_password_hash("testpassword123"),  
        "is_active": True,
        "subscription_status": SubscriptionStatus.active
    }
    
    new_user = user_repository.create(obj_in=user_create_data)
    
    assert new_user.id is not None
    assert new_user.email == "new@example.com"
    assert new_user.subscription_status == SubscriptionStatus.active
    
    # Verify it's in the database
    db_user = db_session.query(User).filter(User.id == new_user.id).first()
    assert db_user is not None
    assert db_user.email == "new@example.com"


def test_update(db_session, user_repository, sample_user):
    """Test updating an existing record."""
    from app.db.models.user import SubscriptionStatus  # Import the enum
    
    # Use dictionary with specific fields rather than schema
    # Use string values instead of enum objects for SQLite compatibility
    user_update = {
        "email": "updated@example.com",
        "is_active": True,
        "subscription_status": SubscriptionStatus.active.value  # Use string value instead of enum
    }
    
    updated_user = user_repository.update(db_obj=sample_user, obj_in=user_update)
    
    assert updated_user.id == sample_user.id
    assert updated_user.email == "updated@example.com"
    assert updated_user.is_active == True
    # For the comparison, handle both string and enum cases
    if hasattr(updated_user.subscription_status, 'value'):
        assert updated_user.subscription_status.value == "active"
    else:
        assert updated_user.subscription_status == "active"
    
    # Verify it's updated in the database
    db_user = db_session.query(User).filter(User.id == sample_user.id).first()
    assert db_user.email == "updated@example.com"


def test_update_with_dict(db_session, user_repository, sample_user):
    """Test updating an existing record using a dict."""
    update_dict = {"email": "dict-updated@example.com"}
    updated_user = user_repository.update(db_obj=sample_user, obj_in=update_dict)
    
    assert updated_user.id == sample_user.id
    assert updated_user.email == "dict-updated@example.com"


def test_delete(db_session, user_repository, sample_user):
    """Test deleting a record."""
    user_id = sample_user.id
    deleted_user = user_repository.delete(id=user_id)
    
    assert deleted_user.id == user_id
    
    # Verify it's deleted from the database
    db_user = db_session.query(User).filter(User.id == user_id).first()
    assert db_user is None


def test_count(db_session, user_repository, sample_user):
    """Test counting records."""
    # Create a second user
    second_user = User(email="second@example.com", subscription_status=SubscriptionStatus.active)
    db_session.add(second_user)
    db_session.commit()
    
    # Test count without filters
    count = user_repository.count()
    assert count == 2
    
    # Test count with filters
    count = user_repository.count(filters={"email": sample_user.email})
    assert count == 1
