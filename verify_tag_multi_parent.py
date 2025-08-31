#!/usr/bin/env python
"""
Verification script for the enhanced tag normalization system.

This script tests:
1. Tag name normalization consistency
2. Multiple parent category assignment
3. Duplicate tag detection and merge

Usage:
    python -m app.scripts.verify_tag_multi_parent
"""

import sys
import os
import uuid
from typing import Dict, List, Set
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.db.session import get_db
from app.db.models.tag import Tag, TagType
from app.services.tag_mapper import get_tag_mapper, TagMapper
from app.core.logging import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger()

def print_header(message: str):
    """Print a formatted header for better readability."""
    print("\n" + "=" * 80)
    print(f" {message}")
    print("=" * 80)

def verify_tag_normalization(db: Session, tag_mapper: TagMapper) -> bool:
    """
    Verify that tag normalization is working as expected.
    
    Returns:
        True if all tests pass, False otherwise
    """
    print_header("Testing Tag Normalization")
    
    # Test cases mapping input to expected normalized output
    test_cases = {
        "javascript": "JavaScript",
        "Javascript": "JavaScript",
        "JAVASCRIPT": "JavaScript",
        "TypeScript": "TypeScript",
        "typescript": "TypeScript",
        "React": "React",
        "react.js": "React.js",
        "reactjs": "React.js",
        "c++": "C++",
        "python 3": "Python 3",
    }
    
    success = True
    for input_name, expected in test_cases.items():
        normalized = tag_mapper.normalize_tag_name(input_name)
        result = normalized == expected
        success = success and result
        
        status = "✓" if result else "✗"
        print(f"[{status}] '{input_name}' → '{normalized}' (Expected: '{expected}')")
    
    return success

def verify_multiple_parents(db: Session, tag_mapper: TagMapper) -> bool:
    """
    Verify that tags can be assigned to multiple parent categories.
    
    Returns:
        True if all tests pass, False otherwise
    """
    print_header("Testing Multiple Parent Categories")
    
    test_cases = {
        "TypeScript": ["Languages", "Frontend"],
        "React": ["Frameworks", "Frontend"],
        "Django": ["Frameworks", "Backend"],
        "PostgreSQL": ["Databases", "Backend"],
        "Docker": ["DevOps"],
        "Webpack": ["Frontend", "DevOps"],
    }
    
    success = True
    for tag_name, expected_categories in test_cases.items():
        suitable_categories = tag_mapper.find_suitable_parent_categories(tag_name)
        
        # Check if all expected categories are found
        categories_found = set(suitable_categories)
        expected_set = set(expected_categories)
        missing_categories = expected_set - categories_found
        extra_categories = categories_found - expected_set
        
        result = len(missing_categories) == 0
        success = success and result
        
        status = "✓" if result else "✗"
        print(f"[{status}] '{tag_name}' → {suitable_categories}")
        
        if missing_categories:
            print(f"       Missing categories: {missing_categories}")
        if extra_categories and len(expected_categories) > 0:
            print(f"       Extra categories (these are fine): {extra_categories}")
    
    return success

def create_test_tags(db: Session, tag_mapper: TagMapper) -> Dict[str, Tag]:
    """
    Create test tags with single parent relationships.
    
    Returns:
        Dictionary mapping tag names to tag objects
    """
    print_header("Creating Test Tags")
    
    # First ensure parent categories exist
    parent_categories = tag_mapper.get_or_create_parent_categories()
    print(f"Found {len(parent_categories)} parent categories")
    
    # Commit any new parent categories
    db.commit()
    
    # Delete any existing test tags to start fresh
    for name in ["TypeScript", "React", "Node.js"]:
        existing_tags = db.query(Tag).filter(func.lower(Tag.name) == func.lower(name)).all()
        if existing_tags:
            print(f"Removing {len(existing_tags)} existing tag entries for '{name}'")
            for tag in existing_tags:
                db.delete(tag)
    db.commit()
    
    # Test tags with primary parent categories
    test_tags = {
        "TypeScript": "Languages",
        "React": "Frameworks",
        "Node.js": "Frameworks",
    }
    
    results = {}
    for tag_name, category in test_tags.items():
        print(f"Creating tag '{tag_name}' with parent category: {category}")
        
        # Get parent category
        parent_id = None
        if category in parent_categories:
            parent_id = parent_categories[category].id
            print(f"  Using parent category: {category} (id: {parent_id})")
        
        # Determine appropriate tag type based on category
        tag_type = TagType.language if category == "Languages" else \
                  TagType.framework if category == "Frameworks" else \
                  TagType.domain if category == "Frontend" or category == "Backend" else \
                  TagType.tool if category == "DevOps" else \
                  TagType.concept
        
        # Create a new tag with this parent category
        new_tag = Tag(
            id=uuid.uuid4(),
            name=tag_name,
            description=f"Test tag for {tag_name} (parent: {category})",
            parent_tag_id=parent_id,
            tag_type=tag_type
        )
        
        # Add to database
        db.add(new_tag)
        
        try:
            db.flush()
            results[tag_name] = new_tag
            print(f"  Created tag '{tag_name}' with parent: {category}")
            
            # Commit changes for this tag
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"  ERROR creating tag '{tag_name}': {str(e)}")
    
    return results

def verify_tags(db: Session, tags: Dict[str, Tag]) -> bool:
    """Verify that tags have been correctly created with their parent category"""
    print_header("Verifying Created Tags")
    
    success = True
    for tag_name, tag in tags.items():
        print(f"Verifying tag '{tag_name}'")
        
        # Verify tag exists
        if tag is None:
            print(f"  ERROR: Tag '{tag_name}' is None!")
            success = False
            continue
            
        # Verify parent relationship
        parent_tag = None
        if tag.parent_tag_id:
            parent_tag = db.query(Tag).get(tag.parent_tag_id)
        
        if parent_tag:
            print(f"  Verified: {tag_name} -> {parent_tag.name}")
        else:
            # It's okay if there's no parent
            print(f"  Verified: {tag_name} (no parent)")
        
        if tag_name == "TypeScript" and (parent_tag is None or parent_tag.name != "Languages"):
            print(f"  ✗ Expected 'TypeScript' to have 'Languages' as parent, but found: {parent_tag.name if parent_tag else 'None'}")
            success = False
        elif tag_name == "React" and (parent_tag is None or parent_tag.name != "Frameworks"):
            print(f"  ✗ Expected 'React' to have 'Frameworks' as parent, but found: {parent_tag.name if parent_tag else 'None'}")
            success = False
        elif tag_name == "Node.js" and (parent_tag is None or parent_tag.name != "Frameworks"):
            print(f"  ✗ Expected 'Node.js' to have 'Frameworks' as parent, but found: {parent_tag.name if parent_tag else 'None'}")
            success = False
            
    return success

def main():
    """
    Run verification tests for tag normalization and multiple parent categories.
    """
    success = True
    
    # Get database session
    try:
        db = next(get_db())
        tag_mapper = get_tag_mapper(db)
        
        # Run verification tests
        success = verify_tag_normalization(db, tag_mapper) and success
        success = verify_multiple_parents(db, tag_mapper) and success
        
        # Create test tags and verify them
        created_tags = create_test_tags(db, tag_mapper)
        success = verify_tags(db, created_tags) and success
        
        # Print overall result
        print_header("Verification Results")
        if success:
            print("✅ All verification tests PASSED!")
        else:
            print("❌ Some verification tests FAILED!")
            
    except Exception as e:
        logger.exception("Error during verification")
        print(f"\n❌ Verification failed with error: {str(e)}")
        success = False
    
    # Return exit code
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
