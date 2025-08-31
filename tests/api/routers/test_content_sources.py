import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.api import deps
from app.db.database import SessionLocal
from app.schemas.content_source import ContentSourceCreate, ContentSourceRead
from app.repositories.content_source import ContentSourceRepository

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
def test_content_source(test_db: Session):
    # Make sure we clean up any existing test source first
    content_source_repo = ContentSourceRepository(test_db)
    existing = test_db.query(content_source_repo.model).filter(
        content_source_repo.model.source_identifier == "test_source_fixture",
        content_source_repo.model.source_platform == "custom"
    ).first()
    
    if existing:
        test_db.delete(existing)
        test_db.commit()
    
    # Create a new content source with a unique identifier
    content_source_in = ContentSourceCreate(
        source_identifier="test_source_fixture",
        source_platform="custom",
        notes="Test content for fixture"
    )
    return content_source_repo.create(content_source_in)

def test_create_content_source(client: TestClient):
    # Use a unique identifier with timestamp to avoid collisions
    import time
    unique_id = f"new_source_{int(time.time())}"
    
    response = client.post(
        "/api/content-sources",
        json={
            "source_identifier": unique_id,
            "source_platform": "custom",
            "notes": "New test content"
        }
    )
    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()
    for field in ["id", "source_identifier", "source_platform", "notes", "raw_data", "processed_text", "source_tags", "processing_status", "ingested_at", "processed_at", "problems", "source_title", "source_url", "created_at", "updated_at"]:
        assert field in data
    assert data["source_identifier"] == unique_id

def test_read_content_sources(client: TestClient):
    response = client.get("/api/content-sources")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_read_content_source(client: TestClient, test_content_source: ContentSourceRead):
    response = client.get(f"/api/content-sources/{test_content_source.id}")
    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()
    for field in ["id", "source_identifier", "source_platform", "notes", "raw_data", "processed_text", "source_tags", "processing_status", "ingested_at", "processed_at", "problems", "source_title", "source_url", "created_at", "updated_at"]:
        assert field in data
    
    # Convert UUID to string for comparison
    assert data["id"] == str(test_content_source.id), f"Expected {str(test_content_source.id)}, got {data['id']}"
    assert data["source_identifier"] == test_content_source.source_identifier
