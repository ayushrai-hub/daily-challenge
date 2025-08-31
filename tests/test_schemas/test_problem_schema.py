"""
Tests for Problem schema validation.

This tests the Pydantic schemas for Problem models, including:
- Field validation
- Default values
- Custom validators
"""

import pytest
import uuid
from pydantic import ValidationError
from uuid import UUID

from app.schemas.problem import ProblemCreate, ProblemRead
from app.db.models.problem import VettingTier, DifficultyLevel, ProblemStatus


def ensure_uuid_string(value):
    """Helper function to ensure UUID can be compared as string"""
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    return value


class TestProblemCreateSchema:
    """Tests for the ProblemCreate schema."""
    
    def test_valid_problem_create(self):
        """Test that a valid problem can be created."""
        data = {
            "title": "Test Problem",
            "description": "This is a test problem",
            "solution": "This is the solution",
            "vetting_tier": VettingTier.tier1_manual,
            "status": ProblemStatus.draft,
            "difficulty_level": DifficultyLevel.medium,
            "content_source_id": str(uuid.uuid4())
        }
        
        problem = ProblemCreate(**data)
        assert problem.title == data["title"]
        assert problem.description == data["description"]
        assert problem.solution == data["solution"]
        assert problem.vetting_tier == data["vetting_tier"]
        assert problem.status == data["status"]
        assert problem.difficulty_level == data["difficulty_level"]
        assert ensure_uuid_string(problem.content_source_id) == ensure_uuid_string(data["content_source_id"])
    
    def test_minimal_problem_create(self):
        """Test that a problem can be created with only required fields."""
        data = {
            "title": "Test Problem",
            "description": "This is a test problem",
        }
        
        problem = ProblemCreate(**data)
        assert problem.title == data["title"]
        assert problem.description == data["description"]
        assert problem.solution is None
        assert problem.vetting_tier == VettingTier.tier3_needs_review
        assert problem.status == ProblemStatus.draft
        assert problem.difficulty_level == DifficultyLevel.medium
        assert problem.content_source_id is None
    
    def test_invalid_title(self):
        """Test that title validation works."""
        # Test empty title
        with pytest.raises(ValidationError) as exc_info:
            ProblemCreate(title="", description="Test description")
        
        assert "title" in str(exc_info.value)
        assert "string_too_short" in str(exc_info.value)
    
    def test_content_source_validator(self):
        """Test the content_source_id validator."""
        # Test with invalid content_source_id (None)
        data = {
            "title": "Test Problem",
            "description": "This is a test problem",
            "content_source_id": None
        }
        
        problem = ProblemCreate(**data)
        assert problem.content_source_id is None
        
        # Test with content_source_id = 1
        test_uuid = str(uuid.uuid4())
        data["content_source_id"] = test_uuid
        problem = ProblemCreate(**data)
        assert ensure_uuid_string(problem.content_source_id) == ensure_uuid_string(test_uuid)


class TestProblemReadSchema:
    """Tests for the ProblemRead schema."""
    
    def test_problem_read_schema(self):
        """Test that a ProblemRead schema can be created."""
        data = {
            "id": str(uuid.uuid4()),
            "title": "Test Problem",
            "description": "This is a test problem",
            "solution": "This is the solution",
            "vetting_tier": VettingTier.tier1_manual,
            "status": ProblemStatus.draft,
            "difficulty_level": DifficultyLevel.medium,
            "content_source_id": str(uuid.uuid4()),
            "approved_at": None,
            "last_updated_at": "2025-05-02T10:00:00",
            "tags": [],
            "created_at": "2025-05-02T10:00:00",
            "updated_at": "2025-05-02T10:00:00"
        }
        
        problem = ProblemRead(**data)
        assert ensure_uuid_string(problem.id) == ensure_uuid_string(data["id"])
        assert problem.title == data["title"]
        assert problem.description == data["description"]
        assert problem.solution == data["solution"]
        assert problem.vetting_tier == data["vetting_tier"]
        assert problem.status == data["status"]
        assert problem.difficulty_level == data["difficulty_level"]
        assert problem.tags == []
        assert problem.approved_at is None
