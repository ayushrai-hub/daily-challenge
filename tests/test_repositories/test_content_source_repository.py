import pytest
from app.db.models.content_source import ContentSource, SourcePlatform
from app.schemas.content_source import ContentSourceCreate, ContentSourceUpdate


def test_get_by_source_identifier(db_session, content_source_repository, sample_content_source):
    """Test retrieving a content source by source identifier."""
    retrieved_source = content_source_repository.get_by_source_identifier(
        source_identifier=sample_content_source.source_identifier
    )
    assert retrieved_source is not None
    assert retrieved_source.id == sample_content_source.id
    assert retrieved_source.source_identifier == "12345"


def test_get_by_source_identifier_nonexistent(db_session, content_source_repository):
    """Test retrieving a nonexistent content source by source identifier returns None."""
    retrieved_source = content_source_repository.get_by_source_identifier(
        source_identifier="nonexistent"
    )
    assert retrieved_source is None


def test_get_by_platform(db_session, content_source_repository, sample_content_source):
    """Test retrieving content sources by platform."""
    # Create a second content source with different platform
    second_source = ContentSource(
        source_platform=SourcePlatform.gh_issues,
        source_identifier="github-12345",
        raw_data={"url": "https://github.com/example/repo/issues/1"}
    )
    db_session.add(second_source)
    db_session.commit()
    
    # Test retrieving content sources by platform
    stackoverflow_sources = content_source_repository.get_by_platform(
        platform=SourcePlatform.stackoverflow
    )
    assert len(stackoverflow_sources) == 1
    assert stackoverflow_sources[0].id == sample_content_source.id
    
    github_sources = content_source_repository.get_by_platform(
        platform=SourcePlatform.gh_issues
    )
    assert len(github_sources) == 1
    assert github_sources[0].id == second_source.id


def test_get_by_platform_pagination(db_session, content_source_repository):
    """Test pagination when retrieving content sources by platform."""
    # Create multiple stackoverflow sources
    sources = [
        ContentSource(
            source_platform=SourcePlatform.stackoverflow,
            source_identifier=f"stackoverflow-{i}",
            raw_data={"question_id": i}
        )
        for i in range(5)
    ]
    db_session.add_all(sources)
    db_session.commit()
    
    # Test skip parameter
    retrieved_sources = content_source_repository.get_by_platform(
        platform=SourcePlatform.stackoverflow,
        skip=2,
        limit=2
    )
    assert len(retrieved_sources) == 2
    assert retrieved_sources[0].source_identifier == "stackoverflow-2"
    
    # Test limit parameter
    retrieved_sources = content_source_repository.get_by_platform(
        platform=SourcePlatform.stackoverflow,
        limit=3
    )
    assert len(retrieved_sources) == 3


def test_get_with_problems(db_session, content_source_repository, sample_content_source, sample_problem):
    """Test retrieving content sources that have generated problems."""
    # Ensure sample_problem has a content_source_id
    sample_problem.content_source_id = sample_content_source.id
    db_session.commit()
    
    # Create a second content source without problems
    second_source = ContentSource(
        source_platform=SourcePlatform.gh_issues,
        source_identifier="github-12345",
        raw_data={"url": "https://github.com/example/repo/issues/1"}
    )
    db_session.add(second_source)
    db_session.commit()
    
    # Test retrieving content sources with problems
    sources_with_problems = content_source_repository.get_with_problems()
    assert len(sources_with_problems) == 1
    assert sources_with_problems[0].id == sample_content_source.id


def test_count_by_platform(db_session, content_source_repository):
    """Test counting content sources by platform."""
    # Create content sources with different platforms
    sources = [
        ContentSource(
            source_platform=SourcePlatform.stackoverflow,
            source_identifier="stackoverflow-1",
            raw_data={"question_id": 1}
        ),
        ContentSource(
            source_platform=SourcePlatform.stackoverflow,
            source_identifier="stackoverflow-2",
            raw_data={"question_id": 2}
        ),
        ContentSource(
            source_platform=SourcePlatform.gh_issues,
            source_identifier="github-1",
            raw_data={"issue_id": 1}
        ),
        ContentSource(
            source_platform=SourcePlatform.blog,
            source_identifier="blog-1",
            raw_data={"url": "https://example.com/blog/1"}
        )
    ]
    db_session.add_all(sources)
    db_session.commit()
    
    # Test counting by platform
    counts = content_source_repository.count_by_platform()
    assert counts.get(SourcePlatform.stackoverflow.value) == 2
    assert counts.get(SourcePlatform.gh_issues.value) == 1
    assert counts.get(SourcePlatform.blog.value) == 1
    assert counts.get(SourcePlatform.custom.value) == 0  # Platform not used
