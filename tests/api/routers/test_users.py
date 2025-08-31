import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.api import deps
from app.schemas.user import UserCreate, UserRead
from app.repositories.user import UserRepository
from app.db.models.user import User, SubscriptionStatus
from app.core.security import get_password_hash, create_access_token

@pytest.fixture
def test_user(db_session: Session):
    # Create a unique email for this test run
    unique_id = uuid.uuid4().hex[:8]
    email = f"test-{unique_id}@example.com"
    
    # Create a user directly via model to avoid validation issues
    user = User(
        email=email,
        hashed_password=get_password_hash("Password123!"),
        subscription_status=SubscriptionStatus.active,
        is_active=True,
        is_admin=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

def test_create_user(client, admin_auth_headers):
    # Generate a unique email with timestamp to avoid conflicts
    import time
    unique_id = f"{uuid.uuid4().hex[:8]}_{int(time.time())}"
    email = f"newuser-{unique_id}@example.com"
    
    # First check if the email already exists
    response = client.get(
        f"/api/users/?email={email}",
        headers=admin_auth_headers
    )
    print(f">>> Checking if user {email} exists: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if data and len(data) > 0:
            print(f">>> User with email {email} already exists!")
    
    # Use the raw string value for subscription_status
    payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Test User",
        "is_active": True,
        "is_admin": False,
        "subscription_status": "active"  # Use string instead of enum.value
    }
    print(f"\n>>> Creating user with payload: {payload}")
    
    # Add debugging for auth headers
    print(f">>> Auth headers: {admin_auth_headers}")
    
    response = client.post(
        "/api/users",  # No trailing slash to avoid redirect
        headers=admin_auth_headers,
        json=payload
    )
    print(f">>> Response status: {response.status_code}")
    print(f">>> Response body: {response.text}")
    
    assert response.status_code == 200
    data = response.json()
    for field in ["id", "email", "full_name", "is_active", "is_admin", "subscription_status", "last_login", "tags", "created_at", "updated_at"]:
        assert field in data
    assert data["email"] == email
    assert isinstance(data["tags"], list)
    assert data["subscription_status"] == "active"  # Match string value
    assert data["is_active"] is True
    assert data["is_admin"] is False

def test_read_users(client, admin_auth_headers):
    response = client.get(
        "/api/users/",
        headers=admin_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Check that admin@example.com is present
    assert any(u["email"] == "admin@example.com" for u in data), "admin@example.com not found in users list"
    # Verify field types in the first user
    if data:
        user = data[0]
        # IDs are now UUIDs returned as strings
        assert isinstance(user["id"], str), f"Expected user ID to be a string UUID, got {type(user['id'])}"
        assert isinstance(user["email"], str)
        assert isinstance(user["is_active"], bool)
        assert isinstance(user["is_admin"], bool)
        assert isinstance(user["tags"], list)

def test_read_user(client, admin_auth_headers):
    # Get the admin user info
    response = client.get(
        "/api/users/", headers=admin_auth_headers
    )
    assert response.status_code == 200
    users = response.json()
    admin_user = next(u for u in users if u["email"] == "admin@example.com")
    response = client.get(
        f"/api/users/{admin_user['id']}", headers=admin_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    for field in ["id", "email", "full_name", "is_active", "is_admin", "subscription_status", "last_login", "tags", "created_at", "updated_at"]:
        assert field in data
    assert data["id"] == admin_user["id"]
    assert data["email"] == admin_user["email"]
    assert isinstance(data["is_active"], bool)
    assert isinstance(data["is_admin"], bool)
    assert isinstance(data["tags"], list)
