#!/usr/bin/env python
"""
Verification script for multi-parent tag normalization.

This script tests the tag normalization process with multi-parent relationships:
1. Creates test tags with multi-parent relationships
2. Tests normalization of tags with multi-parent support
3. Verifies correct parent-child relationships are established
4. Ensures case-insensitive matching works with multi-parent tags
"""
import sys
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Set

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.session import get_db
from app.db.models.tag import Tag, TagType
from app.db.models.tag_hierarchy import TagHierarchy
from app.repositories.tag import TagRepository
from app.services.tag_normalizer import TagNormalizer
from app.schemas.tag import TagCreate
from app.core.logging import get_logger

logger = get_logger()

def setup_test_tags(db, tag_repo) -> Dict[str, uuid.UUID]:
    """
    Create a set of test tags for verification with multi-parent relationships.
    
    Returns:
        Dictionary mapping tag names to their UUIDs
    """
    print("\nSetting up test tags with multi-parent relationships...")
    
    # Create parent category tags
    categories = {
        "Languages": TagCreate(name="Languages", tag_type=TagType.language),
        "Frameworks": TagCreate(name="Frameworks", tag_type=TagType.framework),
        "Tools": TagCreate(name="Tools", tag_type=TagType.tool),
        "Frontend": TagCreate(name="Frontend", tag_type=TagType.domain),
        "Backend": TagCreate(name="Backend", tag_type=TagType.domain)
    }
    
    tag_ids = {}
    
    # Create or reuse the category tags
    for name, tag_data in categories.items():
        existing = tag_repo.get_by_name(name)
        if existing:
            tag = existing
            print(f"Reusing existing category tag: {name} ({tag.id})")
        else:
            tag = tag_repo.create(tag_data)
            print(f"Created category tag: {name} ({tag.id})")
        tag_ids[name] = tag.id
    
    # Create test tags with multi-parent relationships
    test_tags = [
        # JavaScript belongs to Languages (primary) and Frontend
        {
            "name": "JavaScript", 
            "tag_type": TagType.language,
            "parent_ids": [tag_ids["Languages"], tag_ids["Frontend"]]
        },
        # React belongs to Frameworks (primary) and Frontend
        {
            "name": "React", 
            "tag_type": TagType.framework,
            "parent_ids": [tag_ids["Frameworks"], tag_ids["Frontend"]]
        },
        # Node.js belongs to Languages, Tools, and Backend (multiple parents)
        {
            "name": "Node.js", 
            "tag_type": TagType.language,
            "parent_ids": [tag_ids["Languages"], tag_ids["Tools"], tag_ids["Backend"]]
        }
    ]
    
    for tag_data in test_tags:
        # Strip parent_ids from tag_data before creating tag (will add hierarchy separately)
        parent_ids = tag_data.pop("parent_ids")
        
        # Create or get the tag without parent relationships
        tag_create = TagCreate(**tag_data)
        existing = tag_repo.get_by_name(tag_data["name"])
        if existing:
            tag = existing
            print(f"Reusing existing test tag: {tag_data['name']} ({tag.id})")
        else:
            tag = tag_repo.create(tag_create)
            print(f"Created test tag: {tag_data['name']} ({tag.id})")
        
        tag_ids[tag_data["name"]] = tag.id
        
        # Clear existing parent relationships for this tag
        db.query(TagHierarchy).filter(TagHierarchy.child_tag_id == tag.id).delete()
        
        # Create the parent-child relationships explicitly in tag_hierarchy table
        for parent_id in parent_ids:
            # Check if relationship already exists
            existing_rel = db.query(TagHierarchy).filter(
                TagHierarchy.parent_tag_id == parent_id,
                TagHierarchy.child_tag_id == tag.id
            ).first()
            
            if not existing_rel:
                # Skip if this would create a cycle
                if not tag_repo.would_create_cycle(parent_id, tag.id):
                    hierarchy = TagHierarchy(
                        parent_tag_id=parent_id,
                        child_tag_id=tag.id
                    )
                    db.add(hierarchy)
                    print(f"  Added parent relationship: {parent_id} -> {tag.id}")
        
        # Restore parent_ids for verification later
        tag_data["parent_ids"] = parent_ids
    
    # Make sure all changes are flushed to database
    db.flush()
    
    # Verify the hierarchies were created
    for name, tag_id in tag_ids.items():
        if name not in categories:
            parents = tag_repo.get_parent_tags(tag_id)
            parent_names = [p.name for p in parents]
            print(f"Tag '{name}' has parents: {parent_names}")
    
    return tag_ids

def verify_tag_hierarchy(db, tag_repo, tag_ids):
    """Verify that the tag hierarchies were created correctly."""
    print("\nVerifying tag hierarchies...")
    
    # Check each test tag's parents
    test_tags = ["JavaScript", "React", "Node.js"]
    
    all_correct = True
    for tag_name in test_tags:
        tag_id = tag_ids.get(tag_name)
        if not tag_id:
            print(f"❌ Failed to find tag: {tag_name}")
            all_correct = False
            continue
        
        # Get parents
        parents = tag_repo.get_parent_tags(tag_id)
        parent_names = {p.name for p in parents}
        
        # Expected parents
        expected_parents = set()
        if tag_name == "JavaScript":
            expected_parents = {"Languages", "Frontend"}
        elif tag_name == "React":
            expected_parents = {"Frameworks", "Frontend"}
        elif tag_name == "Node.js":
            expected_parents = {"Languages", "Tools", "Backend"}
        
        # Check if parents match expectations
        if parent_names == expected_parents:
            print(f"✅ {tag_name} has correct parents: {parent_names}")
        else:
            print(f"❌ {tag_name} has incorrect parents: {parent_names} (expected {expected_parents})")
            all_correct = False
    
    return all_correct

def test_tag_normalization(db, tag_repo, tag_ids):
    """Test the tag normalizer with multi-parent tags."""
    print("\nTesting tag normalization with multi-parent support...")
    
    # Create normalizer
    normalizer = TagNormalizer(tag_repo)
    
    # Test normalizing a tag with multiple parents using lowercase versions
    test_cases = [
        {"input": "javascript", "expected": "JavaScript"},
        {"input": "react", "expected": "React"},
        {"input": "node.js", "expected": "Node.js"},
        {"input": "nodejs", "expected": "Node.js"},  # Alias handling
    ]
    
    success_count = 0
    for case in test_cases:
        # Normalize the tag name
        normalized = normalizer.normalize_tag_names([case["input"]])
        if not normalized:
            print(f"❌ Normalization failed for {case['input']}")
            continue
        
        # Check if normalization is correct
        normalized_name = normalized[0]
        if normalized_name == case["expected"]:
            print(f"✅ Normalized '{case['input']}' correctly to '{normalized_name}'")
            success_count += 1
        else:
            print(f"❌ Normalization incorrect: '{case['input']}' → '{normalized_name}' (expected '{case['expected']}')")
    
    # Test mapping to existing tags
    mapping_success_count = 0
    for case in test_cases:
        # Map to existing tags
        mapped = normalizer.map_to_existing_tags([case["input"]])
        if not mapped:
            print(f"❌ Tag mapping failed for {case['input']}")
            continue
        
        # Check if mapping is correct
        mapped_name = mapped[0]
        if mapped_name == case["expected"]:
            print(f"✅ Mapped '{case['input']}' correctly to existing tag '{mapped_name}'")
            mapping_success_count += 1
        else:
            print(f"❌ Mapping incorrect: '{case['input']}' → '{mapped_name}' (expected '{case['expected']}')")
    
    print(f"\nNormalization success: {success_count}/{len(test_cases)} cases passed")
    print(f"Mapping success: {mapping_success_count}/{len(test_cases)} cases passed")
    
    return success_count == len(test_cases) and mapping_success_count == len(test_cases)

def verify_parent_preservation(db, tag_repo, tag_ids):
    """Verify that parents are preserved when normalizing tags."""
    print("\nVerifying parent preservation during normalization...")
    
    # This test ensures that when we look up a tag by name and normalize it,
    # all parent relationships are preserved
    
    # Get each test tag
    test_tags = ["JavaScript", "React", "Node.js"]
    success = True
    
    for tag_name in test_tags:
        # Get original tag and its parents
        original_tag = tag_repo.get_by_name(tag_name)
        if not original_tag:
            print(f"❌ Could not find tag: {tag_name}")
            success = False
            continue
            
        original_parents = tag_repo.get_parent_tags(original_tag.id)
        original_parent_names = {p.name for p in original_parents}
        
        # Now get the same tag using lowercase name
        lowercase_tag = tag_repo.get_by_name_case_insensitive(tag_name.lower())
        if not lowercase_tag:
            print(f"❌ Case-insensitive lookup failed for: {tag_name.lower()}")
            success = False
            continue
            
        lowercase_parents = tag_repo.get_parent_tags(lowercase_tag.id)
        lowercase_parent_names = {p.name for p in lowercase_parents}
        
        # Compare parent sets
        if original_parent_names == lowercase_parent_names:
            print(f"✅ Parents preserved for {tag_name}: {lowercase_parent_names}")
        else:
            print(f"❌ Parents not preserved for {tag_name}. Original: {original_parent_names}, Lookup: {lowercase_parent_names}")
            success = False
    
    return success

def cleanup_test_tags(db, tag_ids):
    """Clean up the test tags created for this verification."""
    print("\nCleaning up test tags...")
    
    try:
        # First delete all hierarchy relationships
        db.query(TagHierarchy).filter(
            (TagHierarchy.parent_tag_id.in_(tag_ids.values())) | 
            (TagHierarchy.child_tag_id.in_(tag_ids.values()))
        ).delete(synchronize_session=False)
        
        # Then delete the tags
        db.query(Tag).filter(Tag.id.in_(tag_ids.values())).delete(synchronize_session=False)
        db.commit()
        print(f"✅ Successfully deleted {len(tag_ids)} test tags and their relationships")
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ Error cleaning up test tags: {str(e)}")
        return False

if __name__ == "__main__":
    print("\nMulti-Parent Tag Normalization Verification")
    print("=" * 60)
    
    # Get DB session
    db = next(get_db())
    
    try:
        # Create tag repository
        tag_repo = TagRepository(db)
        
        # Setup test tags
        tag_ids = setup_test_tags(db, tag_repo)
        
        # Verify tag hierarchy
        hierarchy_success = verify_tag_hierarchy(db, tag_repo, tag_ids)
        
        # Test normalization
        normalization_success = test_tag_normalization(db, tag_repo, tag_ids)
        
        # Test parent preservation
        preservation_success = verify_parent_preservation(db, tag_repo, tag_ids)
        
        # Display overall results
        print("\nOverall Test Results:")
        print("=" * 60)
        print(f"Tag Hierarchy Setup: {'✅ PASS' if hierarchy_success else '❌ FAIL'}")
        print(f"Tag Normalization: {'✅ PASS' if normalization_success else '❌ FAIL'}")
        print(f"Parent Preservation: {'✅ PASS' if preservation_success else '❌ FAIL'}")
        
        overall_success = hierarchy_success and normalization_success and preservation_success
        
        print("\nOverall: " + ("✅ PASS" if overall_success else "❌ FAIL"))
        
        # Cleanup test data
        cleanup_success = cleanup_test_tags(db, tag_ids)
        print(f"Test Data Cleanup: {'✅ Success' if cleanup_success else '❌ Error'}")
            
    except Exception as e:
        logger.error(f"Error during verification: {str(e)}")
        print(f"❌ ERROR: {str(e)}")
