import pytest
import uuid
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.api import deps
from app.db.database import SessionLocal
from app.schemas.delivery_log import DeliveryLogCreate, DeliveryLogRead
from app.repositories.delivery_log import DeliveryLogRepository
from app.db.models.user import User
from app.db.models.problem import Problem, ProblemStatus, DifficultyLevel, VettingTier
from app.db.models.delivery_log import DeliveryChannel, DeliveryStatus
from app.core.security import get_password_hash

@pytest.fixture
def test_db():
    # Initialize test settings
    from app.core.config import init_settings, get_test_settings
    init_settings()
    
    # Create a new database session
    db = SessionLocal()
    try:
        yield db
    finally:
        # Clean up the session
        db.rollback()
        db.close()

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_user_and_problem(test_db):
    """Create test user and problem with proper IDs for testing"""
    # Create a test user with unique email
    unique_id = uuid.uuid4().hex[:8]
    test_password = "TestPassword123!"
    hashed_password = get_password_hash(test_password)
    user = User(
        email=f"test-delivery-{unique_id}@example.com", 
        hashed_password=hashed_password,
        subscription_status="active"
    )
    test_db.add(user)
    test_db.flush()  # Get the ID without committing
    
    # Create a test problem with updated schema fields
    problem = Problem(
        title=f"Test Delivery Problem {unique_id}",
        description="Problem for delivery log testing",
        solution="Test solution",
        vetting_tier=VettingTier.tier1_manual,  # Updated to use enum
        status=ProblemStatus.draft,  # Updated to use enum
        difficulty_level=DifficultyLevel.medium  # Updated to use enum
    )
    test_db.add(problem)
    test_db.flush()  # Get the ID without committing
    
    # Get the IDs and commit
    user_id = user.id
    problem_id = problem.id
    test_db.commit()
    
    return {"user_id": user_id, "problem_id": problem_id}

@pytest.fixture
def test_delivery_log(test_db, test_user_and_problem):
    """
    Create a test delivery log for repository-level testing.
    """
    from app.repositories.delivery_log import DeliveryLogRepository
    from app.schemas.delivery_log import DeliveryLogCreate

    delivery_log_repo = DeliveryLogRepository(test_db)
    delivery_log_in = DeliveryLogCreate(
        user_id=test_user_and_problem["user_id"],
        problem_id=test_user_and_problem["problem_id"],
        status="delivered",
        delivery_channel="email"
    )
    return delivery_log_repo.create(delivery_log_in)

@pytest.fixture
def auth_headers(user_auth_headers):
    """Get authorization headers from the seeded user fixture"""
    return user_auth_headers

def test_create_delivery_log(client, test_user_and_problem, auth_headers):
    """Test creating a delivery log with authentication"""
    payload = {
        "user_id": str(test_user_and_problem["user_id"]),  # Convert UUID to string for JSON
        "problem_id": str(test_user_and_problem["problem_id"]),  # Convert UUID to string for JSON
        "status": "scheduled",
        "delivery_channel": "email"
    }
    response = client.post(
        "/api/delivery-logs",
        headers=auth_headers,
        json=payload
    )
    assert response.status_code == 200
    data = response.json()
    # Check all required fields from DeliveryLogRead
    for field in [
        "id", "user_id", "problem_id", "status", "delivery_channel",
        "scheduled_at", "delivered_at", "opened_at", "completed_at", "meta", "created_at", "updated_at"
    ]:
        assert field in data
    assert data["status"] in ["pending", "scheduled", "delivered", "opened", "completed", "failed"]
    assert data["delivery_channel"] in ["email", "sms", "push", "in_app"]

def test_read_delivery_logs(client, test_delivery_log, auth_headers):
    """Test reading all delivery logs with authentication"""
    response = client.get(
        "/api/delivery-logs",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for entry in data:
        for field in [
            "id", "user_id", "problem_id", "status", "delivery_channel",
            "scheduled_at", "delivered_at", "opened_at", "completed_at", "meta", "created_at", "updated_at"
        ]:
            assert field in entry
        assert entry["status"] in ["pending", "scheduled", "delivered", "opened", "completed", "failed"]
        assert entry["delivery_channel"] in ["email", "sms", "push", "in_app"]

def test_read_delivery_log(client, test_delivery_log, auth_headers):
    """Test reading a specific delivery log with authentication"""
    response = client.get(
        f"/api/delivery-logs/{test_delivery_log.id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_delivery_log.id)  # Compare string with UUID as string
    assert data["user_id"] == str(test_delivery_log.user_id)  # Compare string with UUID as string
    for field in [
        "status", "delivery_channel", "scheduled_at", "delivered_at", "opened_at", "completed_at", "meta", "created_at", "updated_at"
    ]:
        assert field in data
    assert data["status"] in ["pending", "scheduled", "delivered", "opened", "completed", "failed"]
    assert data["delivery_channel"] in ["email", "sms", "push", "in_app"]
