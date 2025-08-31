"""
Tests for tag hierarchy relationships with complex multi-parent structures.

These tests verify that the tag hierarchy system correctly handles complex relationships
including multiple parents per tag, deep ancestor chains, and cycle detection.
"""
import pytest
import uuid
from datetime import datetime, timedelta
import time

from app.db.models.tag import Tag
from app.db.models.tag_hierarchy import TagHierarchy
from app.schemas.tag import TagCreate
from app.repositories.tag import TagRepository


class TestComplexTagHierarchy:
    """Tests for complex tag hierarchies with multiple parents per tag."""

    def test_create_tag_with_multiple_parents(self, db_session):
        """Test creating a tag with multiple parents."""
        # Create repository
        tag_repo = TagRepository(db_session)
        
        # Create three parent tags
        parent1 = tag_repo.create(TagCreate(name="Parent1", description="First parent"))
        parent2 = tag_repo.create(TagCreate(name="Parent2", description="Second parent"))
        parent3 = tag_repo.create(TagCreate(name="Parent3", description="Third parent"))
        
        # Create a child tag with multiple parents
        child = tag_repo.create(TagCreate(
            name="MultiParentChild",
            description="Child with multiple parents",
            parent_ids=[parent1.id, parent2.id, parent3.id]
        ))
        
        # Verify that the child has all three parents
        parents = tag_repo.get_parent_tags(child.id)
        parent_ids = [p.id for p in parents]
        
        assert len(parents) == 3
        assert parent1.id in parent_ids
        assert parent2.id in parent_ids
        assert parent3.id in parent_ids
        
        # Verify each parent has the child
        children1 = tag_repo.get_child_tags(parent1.id)
        children2 = tag_repo.get_child_tags(parent2.id)
        children3 = tag_repo.get_child_tags(parent3.id)
        
        assert child.id in [c.id for c in children1]
        assert child.id in [c.id for c in children2]
        assert child.id in [c.id for c in children3]
    
    def test_deep_ancestry_with_multiple_paths(self, db_session):
        """Test ancestor tracking with multiple paths to same ancestors."""
        # Create repository
        tag_repo = TagRepository(db_session)
        
        # Create a diamond-shaped hierarchy:
        # A
        # ├─→ B ──┐
        # └─→ C ──┘
        #      └─→ D
        
        tag_a = tag_repo.create(TagCreate(name="A", description="Top ancestor"))
        tag_b = tag_repo.create(TagCreate(name="B", description="Middle left", parent_ids=[tag_a.id]))
        tag_c = tag_repo.create(TagCreate(name="C", description="Middle right", parent_ids=[tag_a.id]))
        tag_d = tag_repo.create(TagCreate(name="D", description="Bottom", parent_ids=[tag_b.id, tag_c.id]))
        
        # Get all ancestors of D
        ancestors = tag_repo.get_all_ancestors(tag_d.id)
        ancestor_ids = [a.id for a in ancestors]
        
        # D should have 3 ancestors: A, B, and C (with no duplicates)
        assert len(ancestors) == 3
        assert tag_a.id in ancestor_ids
        assert tag_b.id in ancestor_ids
        assert tag_c.id in ancestor_ids
        
        # Check that each tag's parent count is correct
        assert len(tag_repo.get_parent_tags(tag_a.id)) == 0
        assert len(tag_repo.get_parent_tags(tag_b.id)) == 1
        assert len(tag_repo.get_parent_tags(tag_c.id)) == 1
        assert len(tag_repo.get_parent_tags(tag_d.id)) == 2
        
    def test_cycle_detection(self, db_session):
        """Test that cycle detection prevents circular tag relationships."""
        # Create repository
        tag_repo = TagRepository(db_session)
        
        # Create some tags in a legal hierarchy
        tag_a = tag_repo.create(TagCreate(name="CycleA", description="Top"))
        tag_b = tag_repo.create(TagCreate(name="CycleB", description="Middle", parent_ids=[tag_a.id]))
        tag_c = tag_repo.create(TagCreate(name="CycleC", description="Bottom", parent_ids=[tag_b.id]))
        
        # Try to create a cycle by making A a child of C
        # This should fail because it would create A → B → C → A
        with pytest.raises(ValueError) as excinfo:
            tag_repo.add_parent_child_relationship(tag_c.id, tag_a.id)
        
        # Check error message mentions cycle detection
        assert "cycle" in str(excinfo.value).lower()
        
        # Verify no relationship was created
        assert tag_c.id not in [p.id for p in tag_repo.get_parent_tags(tag_a.id)]
    
    def test_remove_parent_relationship(self, db_session):
        """Test removing one parent from a multi-parent tag."""
        # Create repository
        tag_repo = TagRepository(db_session)
        
        # Create parents and child
        parent1 = tag_repo.create(TagCreate(name="RemoveParent1", description="First parent"))
        parent2 = tag_repo.create(TagCreate(name="RemoveParent2", description="Second parent"))
        parent3 = tag_repo.create(TagCreate(name="RemoveParent3", description="Third parent"))
        
        child = tag_repo.create(TagCreate(
            name="RemoveParentChild",
            description="Child with multiple parents", 
            parent_ids=[parent1.id, parent2.id, parent3.id]
        ))
        
        # Remove one parent relationship
        result = tag_repo.remove_parent_child_relationship(parent2.id, child.id)
        assert result is True
        
        # Child should now have only two parents
        parents = tag_repo.get_parent_tags(child.id)
        parent_ids = [p.id for p in parents]
        
        assert len(parents) == 2
        assert parent1.id in parent_ids
        assert parent2.id not in parent_ids
        assert parent3.id in parent_ids

    def test_complex_hierarchy_performance(self, db_session):
        """Benchmark the performance of tag hierarchy operations in complex scenarios."""
        # Create repository
        tag_repo = TagRepository(db_session)
        
        # Create a 3-level hierarchy with branching
        #       Root
        #      /    \
        #   Mid1    Mid2
        #  /   \    /   \
        # L1  L2  L3    L4
        
        # First level (single root)
        root = tag_repo.create(TagCreate(name="PerfRoot", description="Root tag"))
        
        # Second level (two mid-level tags)
        mid_tags = []
        for i in range(2):
            mid = tag_repo.create(TagCreate(
                name=f"PerfMid{i+1}",
                description=f"Mid-level tag {i+1}",
                parent_ids=[root.id]
            ))
            mid_tags.append(mid)
        
        # Third level (each mid-level tag has two children)
        leaf_tags = []
        for i, mid in enumerate(mid_tags):
            for j in range(2):
                leaf = tag_repo.create(TagCreate(
                    name=f"PerfLeaf{i*2+j+1}",
                    description=f"Leaf tag {i*2+j+1}",
                    parent_ids=[mid.id]
                ))
                leaf_tags.append(leaf)
        
        # Benchmark getting ancestors for a leaf tag
        start_time = time.time()
        for _ in range(100):  # Run 100 times to get meaningful measurements
            ancestors = tag_repo.get_all_ancestors(leaf_tags[0].id)
        ancestor_time = (time.time() - start_time) / 100
        
        # Benchmark getting all tags (a common operation)
        start_time = time.time()
        for _ in range(100):
            all_tags = tag_repo.get_multi(limit=100)
        get_all_time = (time.time() - start_time) / 100
        
        # Log performance results
        print(f"Average time to get all ancestors: {ancestor_time * 1000:.2f}ms")
        print(f"Average time to get all tags: {get_all_time * 1000:.2f}ms")
        
        # Make sure the performance is reasonable (adjust thresholds as needed)
        assert ancestor_time < 0.01  # Less than 10ms
        assert get_all_time < 0.05   # Less than 50ms

    def test_very_large_hierarchy(self, db_session):
        """Test performance with a large number of parent-child relationships."""
        # Skip this test in normal runs unless specifically requested
        pytest.skip("Long-running benchmark test - run with explicit marker")
        
        # Create repository
        tag_repo = TagRepository(db_session)
        
        # Create a root tag
        root = tag_repo.create(TagCreate(name="LargeRoot", description="Root for large hierarchy"))
        
        # Create 50 direct children of the root
        children = []
        for i in range(50):
            child = tag_repo.create(TagCreate(
                name=f"LargeChild{i}",
                description=f"Child {i}",
                parent_ids=[root.id]
            ))
            children.append(child)
        
        # Create 200 grandchildren with multiple parents (creating many-to-many relationships)
        grandchildren = []
        for i in range(200):
            # Each grandchild has 2-3 parents from the children list
            # This creates a dense network of relationships
            parent_count = min(3, (i % 3) + 2)
            parent_indices = [(i + j) % len(children) for j in range(parent_count)]
            parent_ids = [children[idx].id for idx in parent_indices]
            
            grandchild = tag_repo.create(TagCreate(
                name=f"LargeGrandchild{i}",
                description=f"Grandchild {i}",
                parent_ids=parent_ids
            ))
            grandchildren.append(grandchild)
        
        # Benchmark time to get all ancestors for a grandchild
        # This tests traversing multiple paths in the hierarchy
        start_time = time.time()
        ancestors = tag_repo.get_all_ancestors(grandchildren[100].id)
        ancestor_time = time.time() - start_time
        
        # Benchmark time to check for cycles when adding a new relationship
        # This is one of the most intensive operations
        start_time = time.time()
        cycle_check = tag_repo.would_create_cycle(grandchildren[50].id, grandchildren[150].id)
        cycle_time = time.time() - start_time
        
        # Benchmark retrieving all relationships for a specific tag
        start_time = time.time()
        parents = tag_repo.get_parent_tags(grandchildren[75].id)
        children = tag_repo.get_child_tags(children[25].id)
        relationship_time = time.time() - start_time
        
        # Log performance metrics
        print(f"Time to get ancestors in large hierarchy: {ancestor_time * 1000:.2f}ms")
        print(f"Time to check for cycles: {cycle_time * 1000:.2f}ms")
        print(f"Time to get relationships: {relationship_time * 1000:.2f}ms")
        
        # Verify the structure is as expected
        assert len(ancestors) <= 51  # 1 root + up to 50 children (could be less due to shared parents)
        assert len(parents) >= 2     # Each grandchild has at least 2 parents
        assert len(children) > 0     # Each child has at least one grandchild
