import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.main import app
from app.api import deps
from app.db.database import SessionLocal
from app.schemas.problem import ProblemCreate, ProblemRead
from app.repositories.problem import ProblemRepository
from app.db.models.problem import Problem, DifficultyLevel, ProblemStatus, VettingTier
from app.repositories.user import UserRepository
from app.core.security import get_password_hash, create_access_token

@pytest.fixture
def test_problem(db_session: Session):
    problem_repo = ProblemRepository(db_session)
    problem_in = ProblemCreate(
        title="Test Problem",
        description="This is a test problem",
        solution="Test solution", 
        vetting_tier=VettingTier.tier1_manual,  
        status=ProblemStatus.draft,            
        difficulty_level=DifficultyLevel.medium,     
        approved_at=None
    )
    return problem_repo.create(problem_in)

def test_create_problem(client, admin_auth_headers):
    unique_id = uuid.uuid4().hex[:8]
    response = client.post(
        "/api/problems",
        headers=admin_auth_headers,
        json={
            "title": f"New Problem {unique_id}",
            "description": "This is a new problem",
            "solution": "Solution for the problem",
            "vetting_tier": "tier1_manual",
            "status": "draft",
            "difficulty_level": "medium",
            "approved_at": None
        }
    )
    assert response.status_code == 200
    data = response.json()
    for field in [
        "id", "title", "description", "solution", "vetting_tier", "status", "difficulty_level", "content_source_id", "approved_at", "updated_at", "tags"
    ]:
        assert field in data
    assert data["title"].startswith("New Problem")
    assert data["status"] == "draft"
    assert data["difficulty_level"] == "medium"
    # Check enums and nullable fields
    assert data["vetting_tier"] in ["tier1_manual", "tier2_manual", "tier3_manual", "tier1", "tier2", "tier3"]
    assert data["content_source_id"] is None or isinstance(data["content_source_id"], str)  # UUID represented as string in JSON
    assert data["tags"] is not None

def test_read_problems(client, admin_auth_headers):
    response = client.get(
        "/api/problems",
        headers=admin_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_read_problem(client, admin_auth_headers):
    # Create a problem first
    unique_id = uuid.uuid4().hex[:8]
    create_resp = client.post(
        "/api/problems",
        headers=admin_auth_headers,
        json={
            "title": f"Read Problem {unique_id}",
            "description": "Test read problem",
            "solution": "Test solution",
            "vetting_tier": "tier1_manual",
            "status": "draft",
            "difficulty_level": "medium",
            "approved_at": None
        }
    )
    assert create_resp.status_code == 200
    problem = create_resp.json()
    problem_id = problem["id"]
    response = client.get(
        f"/api/problems/{problem_id}",
        headers=admin_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    for field in [
        "id", "title", "description", "solution", "vetting_tier", "status", "difficulty_level", "content_source_id", "approved_at", "updated_at", "tags"
    ]:
        assert field in data
    assert data["id"] == problem_id
    assert data["title"].startswith("Read Problem")
    assert data["vetting_tier"] in ["tier1_manual", "tier2_manual", "tier3_manual", "tier1", "tier2", "tier3"]
    assert data["content_source_id"] is None or isinstance(data["content_source_id"], str)  # UUID represented as string in JSON
    assert data["tags"] is not None
