import pytest
import uuid
from sqlalchemy import or_
from app.db.models.tag import Tag, TagType
from app.db.models.tag_hierarchy import TagHierarchy
from app.db.models.tag_normalization import TagNormalization, TagReviewStatus, TagSource
from app.schemas.tag import TagCreate, TagUpdate
from app.schemas.tag_normalization import TagNormalizationCreate
from typing import List


def test_get_by_name(db_session, tag_repository, sample_tag):
    """Test retrieving a tag by name."""
    retrieved_tag = tag_repository.get_by_name(name=sample_tag.name)
    assert retrieved_tag is not None
    assert retrieved_tag.id == sample_tag.id
    assert retrieved_tag.name == sample_tag.name
    # Compare value of tag_type to handle both string and enum cases
    if hasattr(retrieved_tag.tag_type, 'value'):
        # If it's an enum, get its value
        assert retrieved_tag.tag_type.value == "concept"
    else:
        # If it's a string, compare directly
        assert retrieved_tag.tag_type == "concept"
    assert retrieved_tag.is_featured == True
    assert retrieved_tag.is_private == False


def test_get_by_name_nonexistent(db_session, tag_repository):
    """Test retrieving a nonexistent tag by name returns None."""
    retrieved_tag = tag_repository.get_by_name(name="nonexistent")
    assert retrieved_tag is None


def test_get_tags_for_user(db_session, tag_repository, sample_user, sample_tag):
    """Test retrieving tags associated with a specific user."""
    # Associate the tag with the user
    sample_user.tags.append(sample_tag)
    db_session.commit()
    
    # Retrieve tags for the user
    user_tags = tag_repository.get_tags_for_user(user_id=sample_user.id)
    assert len(user_tags) == 1
    assert user_tags[0].id == sample_tag.id
    assert user_tags[0].name == sample_tag.name
    # Compare value of tag_type to handle both string and enum cases
    if hasattr(user_tags[0].tag_type, 'value'):
        # If it's an enum, get its value
        assert user_tags[0].tag_type.value == "concept"
    else:
        # If it's a string, compare directly
        assert user_tags[0].tag_type == "concept"
    assert user_tags[0].is_featured == True
    assert user_tags[0].is_private == False


def test_get_tags_for_problem(db_session, tag_repository, sample_problem, sample_tag):
    """Test retrieving tags associated with a specific problem."""
    # Associate the tag with the problem
    sample_problem.tags.append(sample_tag)
    db_session.commit()
    
    # Retrieve tags for the problem
    problem_tags = tag_repository.get_tags_for_problem(problem_id=sample_problem.id)
    assert len(problem_tags) == 1
    assert problem_tags[0].id == sample_tag.id
    assert problem_tags[0].name == sample_tag.name
    # Compare value of tag_type to handle both string and enum cases
    if hasattr(problem_tags[0].tag_type, 'value'):
        # If it's an enum, get its value
        assert problem_tags[0].tag_type.value == "concept"
    else:
        # If it's a string, compare directly
        assert problem_tags[0].tag_type == "concept"
    assert problem_tags[0].is_featured == True
    assert problem_tags[0].is_private == False


def test_get_child_tags(db_session, tag_repository):
    """Test retrieving child tags for a given parent tag using tag_hierarchy table."""
    # Generate unique tag names using UUID
    parent_name = f"programming_{uuid.uuid4().hex[:8]}"
    child1_name = f"python_{uuid.uuid4().hex[:8]}"
    child2_name = f"javascript_{uuid.uuid4().hex[:8]}"
    
    # Create a parent tag
    parent_tag = Tag(
        id=uuid.uuid4(),
        name=parent_name, 
        description="Programming languages",
        tag_type="concept",  # Use string instead of enum
        is_featured=True,
        is_private=False
    )
    db_session.add(parent_tag)
    db_session.commit()
    
    # Create child tags
    child_tags = [
        Tag(
            id=uuid.uuid4(),
            name=child1_name, 
            description="Python programming language",
            tag_type="language",  # Use string instead of enum
            is_featured=True,
            is_private=False
        ),
        Tag(
            id=uuid.uuid4(),
            name=child2_name, 
            description="JavaScript programming language",
            tag_type="language",  # Use string instead of enum
            is_featured=True,
            is_private=False
        )
    ]
    for tag in child_tags:
        db_session.add(tag)
    db_session.commit()
    
    # Create tag hierarchy relationships
    for child_tag in child_tags:
        hierarchy = TagHierarchy(
            parent_tag_id=parent_tag.id,
            child_tag_id=child_tag.id,
            relationship_type="parent_child"
        )
        db_session.add(hierarchy)
    db_session.commit()
    
    # Retrieve child tags
    retrieved_tags = tag_repository.get_child_tags(parent_tag_id=parent_tag.id)
    
    # Verify retrieval
    assert len(retrieved_tags) == 2
    tag_names = [tag.name for tag in retrieved_tags]
    assert child1_name in tag_names
    assert child2_name in tag_names


def test_associate_tag_with_user(db_session, tag_repository, sample_user, sample_tag):
    """Test associating a tag with a user."""
    # Clear any existing associations
    sample_user.tags = []
    db_session.commit()
    
    # Associate tag with user
    result = tag_repository.associate_tag_with_user(tag_id=sample_tag.id, user_id=sample_user.id)
    assert result is True
    
    # Verify the association
    db_session.refresh(sample_user)
    assert len(sample_user.tags) == 1
    assert sample_user.tags[0].id == sample_tag.id
    # Compare value of tag_type to handle both string and enum cases
    if hasattr(sample_user.tags[0].tag_type, 'value'):
        # If it's an enum, get its value
        assert sample_user.tags[0].tag_type.value == "concept"
    else:
        # If it's a string, compare directly
        assert sample_user.tags[0].tag_type == "concept"
    assert sample_user.tags[0].is_featured == True
    assert sample_user.tags[0].is_private == False


def test_associate_tag_with_problem(db_session, tag_repository, sample_problem, sample_tag):
    """Test associating a tag with a problem."""
    # Clear any existing associations
    sample_problem.tags = []
    db_session.commit()
    
    # Associate tag with problem
    result = tag_repository.associate_tag_with_problem(tag_id=sample_tag.id, problem_id=sample_problem.id)
    assert result is True
    
    # Verify the association
    db_session.refresh(sample_problem)
    assert len(sample_problem.tags) == 1
    assert sample_problem.tags[0].id == sample_tag.id
    # Compare value of tag_type to handle both string and enum cases
    if hasattr(sample_problem.tags[0].tag_type, 'value'):
        # If it's an enum, get its value
        assert sample_problem.tags[0].tag_type.value == "concept" 
    else:
        # If it's a string, compare directly
        assert sample_problem.tags[0].tag_type == "concept"
    assert sample_problem.tags[0].is_featured == True
    assert sample_problem.tags[0].is_private == False


def test_tag_hierarchy_multi_parent(db_session, tag_repository):
    """Test hierarchical tag relationships using the tag_hierarchy junction table with multi-parent support."""
    # Create tags for our hierarchy
    programming = Tag(
        name="programming", 
        description="Programming languages",
        tag_type="concept",
        is_featured=True,
        is_private=False
    )
    
    languages = Tag(
        name="languages",
        description="Programming languages category",
        tag_type="concept",
        is_featured=True,
        is_private=False
    )
    
    web = Tag(
        name="web", 
        description="Web development",
        tag_type="concept",
        is_featured=True,
        is_private=False
    )
    
    frontend = Tag(
        name="frontend", 
        description="Frontend technologies",
        tag_type="topic",
        is_featured=False,
        is_private=False
    )
    
    typescript = Tag(
        name="typescript",
        description="TypeScript programming language",
        tag_type="language",
        is_featured=True,
        is_private=False
    )
    
    for tag in [programming, languages, web, frontend, typescript]:
        db_session.add(tag)
    db_session.commit()
    
    # Create hierarchy relationships
    # TypeScript has multiple parents: languages and frontend
    hierarchies = [
        TagHierarchy(parent_tag_id=programming.id, child_tag_id=web.id),
        TagHierarchy(parent_tag_id=web.id, child_tag_id=frontend.id),
        TagHierarchy(parent_tag_id=languages.id, child_tag_id=typescript.id),
        TagHierarchy(parent_tag_id=frontend.id, child_tag_id=typescript.id)
    ]
    
    for hierarchy in hierarchies:
        db_session.add(hierarchy)
    db_session.commit()
    
    # Test 1: Verify child tags can be retrieved correctly
    children = tag_repository.get_child_tags(parent_tag_id=programming.id)
    assert len(children) == 1
    assert children[0].name == "web"
    
    children = tag_repository.get_child_tags(parent_tag_id=web.id)
    assert len(children) == 1
    assert children[0].name == "frontend"
    
    # Test 2: TypeScript should have two parents
    parents = tag_repository.get_parent_tags(child_tag_id=typescript.id)
    assert len(parents) == 2
    parent_names = {tag.name for tag in parents}
    assert "languages" in parent_names
    assert "frontend" in parent_names
    
    # Test 3: Test get_all_ancestors to retrieve all ancestors of typescript
    ancestors = tag_repository.get_all_ancestors(tag_id=typescript.id)
    assert len(ancestors) == 4  # languages, frontend, web, programming
    ancestor_names = {tag.name for tag in ancestors}
    assert "languages" in ancestor_names
    assert "frontend" in ancestor_names
    assert "web" in ancestor_names
    assert "programming" in ancestor_names
    
    # Test 4: Test adding a parent relationship
    # Add programming as a direct parent of typescript
    tag_repository.add_parent_child_relationship(parent_id=programming.id, child_id=typescript.id)
    
    # Verify the new relationship
    parents = tag_repository.get_parent_tags(child_tag_id=typescript.id)
    assert len(parents) == 3
    parent_names = {tag.name for tag in parents}
    assert "languages" in parent_names
    assert "frontend" in parent_names
    assert "programming" in parent_names
    
    # Test 5: Test removing a parent relationship
    tag_repository.remove_parent_child_relationship(parent_id=languages.id, child_id=typescript.id)
    
    # Verify the relationship was removed
    parents = tag_repository.get_parent_tags(child_tag_id=typescript.id)
    assert len(parents) == 2
    parent_names = {tag.name for tag in parents}
    assert "languages" not in parent_names
    assert "frontend" in parent_names
    assert "programming" in parent_names


def test_cycle_detection(db_session, tag_repository):
    """Test cycle detection in tag hierarchies."""
    # Create tags for a potential cycle
    a = Tag(name="tag_a", description="Tag A", tag_type="concept")
    b = Tag(name="tag_b", description="Tag B", tag_type="concept")
    c = Tag(name="tag_c", description="Tag C", tag_type="concept")
    d = Tag(name="tag_d", description="Tag D", tag_type="concept")
    
    for tag in [a, b, c, d]:
        db_session.add(tag)
    db_session.commit()
    
    # Create a hierarchy: A -> B -> C
    tag_repository.add_parent_child_relationship(parent_id=a.id, child_id=b.id)
    tag_repository.add_parent_child_relationship(parent_id=b.id, child_id=c.id)
    
    # Verify the hierarchy
    assert len(tag_repository.get_child_tags(parent_tag_id=a.id)) == 1
    assert len(tag_repository.get_child_tags(parent_tag_id=b.id)) == 1
    assert len(tag_repository.get_parent_tags(child_tag_id=c.id)) == 1
    
    # Attempt to create a cycle: C -> A (should fail)
    # This would create a cycle: A -> B -> C -> A
    with pytest.raises(ValueError, match="would create a cycle"):
        tag_repository.add_parent_child_relationship(parent_id=c.id, child_id=a.id)
    
    # Verify the hierarchy remains unchanged
    assert len(tag_repository.get_parent_tags(child_tag_id=a.id)) == 0
    
    # Add a valid relationship C -> D
    tag_repository.add_parent_child_relationship(parent_id=c.id, child_id=d.id)
    assert len(tag_repository.get_child_tags(parent_tag_id=c.id)) == 1
    
    # Attempt to create a longer cycle: D -> A (should fail)
    # This would create a cycle: A -> B -> C -> D -> A
    with pytest.raises(ValueError, match="would create a cycle"):
        tag_repository.add_parent_child_relationship(parent_id=d.id, child_id=a.id)


def test_tag_normalization(db_session, tag_repository):
    """Test tag normalization workflow."""
    # Create a normalization entry
    normalization_data = TagNormalizationCreate(
        original_name="javascript",
        normalized_name="JavaScript",
        source="ai_generated",  # Use string instead of enum for SQLite compatibility
        confidence_score=0.95,
        description="JavaScript is a programming language"
    )
    
    # Add the normalization
    norm = tag_repository.create_tag_normalization(normalization_data)
    assert norm is not None
    assert norm.original_name == "javascript"
    assert norm.normalized_name == "JavaScript"
    assert norm.source == TagSource.ai_generated
    assert norm.confidence_score == 0.95
    assert norm.description == "JavaScript is a programming language"
    assert norm.review_status == TagReviewStatus.pending
    
    # Get normalization by ID
    retrieved_norm = tag_repository.get_tag_normalization(norm.id)
    assert retrieved_norm is not None
    assert retrieved_norm.id == norm.id
    
    # List all pending normalizations
    pending_norms = tag_repository.get_pending_normalizations()
    assert len(pending_norms) >= 1
    assert any(n.id == norm.id for n in pending_norms)
    
    # Approve tag normalization
    approved_result = tag_repository.approve_tag_normalization(norm.id)
    assert approved_result is not None
    assert isinstance(approved_result, tuple)
    norm_obj, tag_obj = approved_result
    
    # Verify the status changed
    retrieved_norm = tag_repository.get_tag_normalization(norm.id)
    assert retrieved_norm.review_status == TagReviewStatus.approved
    
    # Create another normalization for rejection testing
    reject_norm = tag_repository.create_tag_normalization(
        TagNormalizationCreate(
            original_name="react",
            normalized_name="React.js",
            source="ai_generated",  # Use string instead of enum for SQLite compatibility
            confidence_score=0.85,
            description="React is a JavaScript library for building user interfaces"
        )
    )
    
    # Reject normalization
    rejected_result = tag_repository.reject_tag_normalization(reject_norm.id, "Prefer React without .js")
    assert rejected_result is not None
    
    # Verify the status changed
    retrieved_reject_norm = tag_repository.get_tag_normalization(reject_norm.id)
    assert retrieved_reject_norm.review_status == TagReviewStatus.rejected
    assert retrieved_reject_norm.admin_notes == "Prefer React without .js"


def test_remove_parent_child_relationship(db_session, tag_repository):
    """Test removing a parent-child relationship from the tag hierarchy."""
    # Create parent and child tags
    parent_name = f"parent_tag_{uuid.uuid4().hex[:8]}"
    child_name = f"child_tag_{uuid.uuid4().hex[:8]}"
    
    parent_tag = Tag(
        id=uuid.uuid4(),
        name=parent_name,
        description="Parent tag",
        tag_type="concept",
        is_featured=False,
        is_private=False
    )
    
    child_tag = Tag(
        id=uuid.uuid4(),
        name=child_name,
        description="Child tag",
        tag_type="concept",
        is_featured=False,
        is_private=False
    )
    
    db_session.add_all([parent_tag, child_tag])
    db_session.commit()
    
    # Add parent-child relationship
    result = tag_repository.add_parent_child_relationship(
        parent_id=parent_tag.id,
        child_id=child_tag.id
    )
    assert result is True
    
    # Verify relationship exists
    children = tag_repository.get_child_tags(parent_tag.id)
    assert len(children) == 1
    assert children[0].id == child_tag.id
    
    # Remove relationship
    removed = tag_repository.remove_parent_child_relationship(
        parent_id=parent_tag.id,
        child_id=child_tag.id
    )
    assert removed is True
    
    # Verify relationship no longer exists
    children_after = tag_repository.get_child_tags(parent_tag.id)
    assert len(children_after) == 0


def test_get_all_ancestors_complex_hierarchy(db_session, tag_repository):
    """Test retrieving all ancestors in a complex multi-level hierarchy."""
    # Create a multi-level hierarchy
    # grandparent → parent1 → child
    #             ↘ parent2 ↗
    
    # Create tags
    tags = {
        "grandparent": Tag(id=uuid.uuid4(), name=f"grandparent_{uuid.uuid4().hex[:8]}", tag_type="concept"),
        "parent1": Tag(id=uuid.uuid4(), name=f"parent1_{uuid.uuid4().hex[:8]}", tag_type="concept"),
        "parent2": Tag(id=uuid.uuid4(), name=f"parent2_{uuid.uuid4().hex[:8]}", tag_type="concept"),
        "child": Tag(id=uuid.uuid4(), name=f"child_{uuid.uuid4().hex[:8]}", tag_type="concept")
    }
    
    db_session.add_all(tags.values())
    db_session.commit()
    
    # Create relationships
    tag_repository.add_parent_child_relationship(tags["grandparent"].id, tags["parent1"].id)
    tag_repository.add_parent_child_relationship(tags["grandparent"].id, tags["parent2"].id)
    tag_repository.add_parent_child_relationship(tags["parent1"].id, tags["child"].id)
    tag_repository.add_parent_child_relationship(tags["parent2"].id, tags["child"].id)
    
    # Get all ancestors of child
    ancestors = tag_repository.get_all_ancestors(tags["child"].id)
    
    # Verify all ancestors are found (3 total: parent1, parent2, grandparent)
    assert len(ancestors) == 3
    ancestor_ids = {a.id for a in ancestors}
    assert tags["parent1"].id in ancestor_ids
    assert tags["parent2"].id in ancestor_ids
    assert tags["grandparent"].id in ancestor_ids


def test_update_tag(db_session, tag_repository):
    """Test updating tag metadata."""
    # Create a tag
    tag = Tag(
        id=uuid.uuid4(),
        name=f"update_test_{uuid.uuid4().hex[:8]}",
        description="Original description",
        tag_type="concept",
        is_featured=False,
        is_private=False
    )
    
    db_session.add(tag)
    db_session.commit()
    
    # Update tag
    updated = tag_repository.update_tag(
        id=tag.id,
        update_data={
            "description": "Updated description",
            "is_featured": True,
            "tag_type": "language"
        }
    )
    
    assert updated is not None
    assert updated.description == "Updated description"
    assert updated.is_featured is True
    
    # Check tag_type - handle both enum and string versions
    # The actual value could be either a TagType enum or a string depending on environment
    if hasattr(updated.tag_type, 'value'):
        # It's an enum
        assert updated.tag_type.value == 'language'
    else:
        # It's a string
        assert updated.tag_type == 'language'
    
    # Verify persistence
    retrieved = tag_repository.get(tag.id)
    assert retrieved.description == "Updated description"
    assert retrieved.is_featured is True
    
    # Check retrieved tag_type - handle both enum and string versions
    if hasattr(retrieved.tag_type, 'value'):
        # It's an enum
        assert retrieved.tag_type.value == 'language'
    else:
        # It's a string
        assert retrieved.tag_type == 'language'
    

def test_delete_tag_with_hierarchy(db_session, tag_repository):
    """Test deleting a tag and its impact on tag hierarchy."""
    # Create parent and child tags
    parent_name = f"parent_del_{uuid.uuid4().hex[:8]}"
    child_name = f"child_del_{uuid.uuid4().hex[:8]}"
    
    parent_tag = Tag(
        id=uuid.uuid4(),
        name=parent_name,
        description="Parent tag",
        tag_type="concept"
    )
    
    child_tag = Tag(
        id=uuid.uuid4(),
        name=child_name,
        description="Child tag",
        tag_type="concept"
    )
    
    db_session.add_all([parent_tag, child_tag])
    db_session.commit()
    
    # Add parent-child relationship
    tag_repository.add_parent_child_relationship(
        parent_id=parent_tag.id,
        child_id=child_tag.id
    )
    
    # Delete parent tag
    deleted = tag_repository.delete(parent_tag.id)
    assert deleted is True
    
    # Verify parent is deleted
    retrieved_parent = tag_repository.get(parent_tag.id)
    assert retrieved_parent is None
    
    # Verify child still exists but relationship is removed
    retrieved_child = tag_repository.get(child_tag.id)
    assert retrieved_child is not None
    
    # Check hierarchy - should not contain the deleted tag
    hierarchy_exists = db_session.query(TagHierarchy).filter(
        or_(
            TagHierarchy.parent_tag_id == parent_tag.id,
            TagHierarchy.child_tag_id == parent_tag.id
        )
    ).first()
    
    assert hierarchy_exists is None
