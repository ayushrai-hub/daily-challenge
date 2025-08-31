import pytest
from app.db.models.problem import Problem, VettingTier, ProblemStatus, DifficultyLevel
from app.schemas.problem import ProblemCreate, ProblemUpdate


def test_get_by_title(db_session, problem_repository, sample_problem):
    """Test retrieving a problem by title."""
    retrieved_problem = problem_repository.get_by_title(title=sample_problem.title)
    assert retrieved_problem is not None
    assert retrieved_problem.id == sample_problem.id
    assert retrieved_problem.title == "Sample problem"


def test_get_by_title_nonexistent(db_session, problem_repository):
    """Test retrieving a nonexistent problem by title returns None."""
    retrieved_problem = problem_repository.get_by_title(title="Nonexistent Problem")
    assert retrieved_problem is None


def test_get_by_vetting_tier(db_session, problem_repository, sample_problem):
    """Test retrieving problems by vetting tier."""
    # Create a second problem with different vetting tier
    second_problem = Problem(
        title="Tier 2 Problem",
        description="This is a tier 2 problem description",
        solution="Tier 2 solution",
        vetting_tier=VettingTier.tier2_ai,
        status=ProblemStatus.draft,
        difficulty_level=DifficultyLevel.medium
    )
    db_session.add(second_problem)
    db_session.commit()
    
    # Test retrieving problems by tier
    tier3_problems = problem_repository.get_by_vetting_tier(tier=VettingTier.tier3_needs_review)
    assert len(tier3_problems) == 1
    assert tier3_problems[0].id == sample_problem.id
    
    tier2_problems = problem_repository.get_by_vetting_tier(tier=VettingTier.tier2_ai)
    assert len(tier2_problems) == 1
    assert tier2_problems[0].id == second_problem.id
    
    tier1_problems = problem_repository.get_by_vetting_tier(tier=VettingTier.tier1_manual)
    assert len(tier1_problems) == 0


def test_get_by_vetting_tier_pagination(db_session, problem_repository):
    """Test pagination when retrieving problems by vetting tier."""
    # Create multiple tier1 problems
    problems = [
        Problem(
            title=f"Problem {i}",
            description=f"Description {i}",
            vetting_tier=VettingTier.tier3_needs_review,
            status=ProblemStatus.draft,
            difficulty_level=DifficultyLevel.medium
        )
        for i in range(5)
    ]
    db_session.add_all(problems)
    db_session.commit()
    
    # Test skip parameter
    retrieved_problems = problem_repository.get_by_vetting_tier(tier=VettingTier.tier3_needs_review, skip=2, limit=2)
    assert len(retrieved_problems) == 2
    assert retrieved_problems[0].title == "Problem 2"
    
    # Test limit parameter
    retrieved_problems = problem_repository.get_by_vetting_tier(tier=VettingTier.tier3_needs_review, limit=3)
    assert len(retrieved_problems) == 3


def test_get_by_status(db_session, problem_repository, sample_problem):
    """Test retrieving problems by status."""
    # Create a second problem with different status
    second_problem = Problem(
        title="Approved Problem",
        description="This is an approved problem description",
        solution="Approved solution",
        vetting_tier=VettingTier.tier3_needs_review,
        status=ProblemStatus.approved,
        difficulty_level=DifficultyLevel.medium
    )
    db_session.add(second_problem)
    db_session.commit()
    
    # Test retrieving problems by status
    draft_problems = problem_repository.get_by_status(status=ProblemStatus.draft)
    assert len(draft_problems) == 1
    assert draft_problems[0].id == sample_problem.id
    
    approved_problems = problem_repository.get_by_status(status=ProblemStatus.approved)
    assert len(approved_problems) == 1
    assert approved_problems[0].id == second_problem.id


def test_get_by_content_source(db_session, problem_repository, sample_problem, sample_content_source):
    """Test retrieving problems by content source ID."""
    # Ensure sample_problem has a content_source_id
    sample_problem.content_source_id = sample_content_source.id
    db_session.commit()
    
    # Test retrieving problems by content source
    problems = problem_repository.get_by_content_source(content_source_id=sample_content_source.id)
    assert len(problems) == 1
    assert problems[0].id == sample_problem.id


def test_get_problems_with_tags(db_session, problem_repository, sample_problem, sample_tag):
    """Test retrieving problems that have specific tags."""
    # Associate the tag with the problem
    sample_problem.tags.append(sample_tag)
    db_session.commit()
    
    # Test retrieving problems with the tag
    problems = problem_repository.get_problems_with_tags(tag_ids=[sample_tag.id])
    assert len(problems) == 1
    assert problems[0].id == sample_problem.id


def test_update_vetting_tier(db_session, problem_repository, sample_problem):
    """Test updating a problem's vetting tier."""
    # Update the vetting tier
    updated_problem = problem_repository.update_vetting_tier(
        problem_id=sample_problem.id,
        new_tier=VettingTier.tier2_ai
    )
    
    assert updated_problem is not None
    assert updated_problem.id == sample_problem.id
    assert updated_problem.vetting_tier == VettingTier.tier2_ai
    
    # Verify it's updated in the database
    db_problem = db_session.query(Problem).filter(Problem.id == sample_problem.id).first()
    assert db_problem.vetting_tier == VettingTier.tier2_ai


def test_update_vetting_tier_nonexistent(db_session, problem_repository):
    """Test updating vetting tier for a nonexistent problem returns None."""
    updated_problem = problem_repository.update_vetting_tier(
        problem_id=9999,
        new_tier=VettingTier.tier2_ai
    )
    
    assert updated_problem is None
