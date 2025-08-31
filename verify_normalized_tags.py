#!/usr/bin/env python3
"""
Verify Tag Normalization Implementation

This script tests whether the tag normalization implementations are working correctly.
It verifies:
1. API-level normalization in the create_tag endpoint
2. Proper parent category assignment
3. Tag deduplication

Run this script after implementing tag normalization to verify everything is working.
"""

import sys
import os
import asyncio
from pydantic import BaseModel
from typing import Optional, List

# Add project root to path for module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.db.session import get_db
from app.schemas.tag import TagCreate, TagRead
from app.api.routers.tags import create_tag
from app.db.models.tag import Tag
from app.core.logging import get_logger

# Use the standardized logging system
logger = get_logger()

# Model for test case
class TestCase(BaseModel):
    input_name: str
    expected_name: str
    expected_parent_type: Optional[str] = None
    

async def test_tag_normalization():
    """Test the tag normalization in the create_tag endpoint"""
    
    # Test cases with expected normalized results
    test_cases = [
        TestCase(input_name="javascript", expected_name="JavaScript", expected_parent_type="Languages"),
        TestCase(input_name="typescript", expected_name="TypeScript", expected_parent_type="Languages"),
        TestCase(input_name="next.js", expected_name="Next.js", expected_parent_type="Frameworks"),
        TestCase(input_name="redux", expected_name="Redux", expected_parent_type="Frameworks"),
        TestCase(input_name="software architecture", expected_name="Software Architecture"),
        TestCase(input_name="code quality", expected_name="Code Quality")
    ]
    
    # Get database session
    db = next(get_db())
    created_tags = []
    
    print("\nTag Normalization Test Results:")
    print("=" * 60)
    
    successes = 0
    failures = 0
    
    try:
        for test_case in test_cases:
            # Create a tag with the input name
            tag_in = TagCreate(name=test_case.input_name)
            result = await create_tag(tag_in, db)
            
            # Store ID for cleanup
            created_tags.append(result.id)
            
            # Check normalization
            name_match = result.name == test_case.expected_name
            
            # Check parent category if expected
            parent_match = True
            if test_case.expected_parent_type:
                # Fetch the full tag to get parent info
                full_tag = db.query(Tag).filter(Tag.id == result.id).first()
                if full_tag and full_tag.parent_tag_id:
                    parent_tag = db.query(Tag).filter(Tag.id == full_tag.parent_tag_id).first()
                    parent_match = parent_tag and parent_tag.name == test_case.expected_parent_type
                else:
                    parent_match = False
            
            # Display test results
            print(f"Input: '{test_case.input_name}'")
            print(f"Expected: '{test_case.expected_name}'")
            print(f"Actual: '{result.name}'")
            
            if test_case.expected_parent_type:
                parent_name = "None"
                if full_tag and full_tag.parent_tag_id:
                    parent = db.query(Tag).filter(Tag.id == full_tag.parent_tag_id).first()
                    parent_name = parent.name if parent else "Unknown"
                print(f"Parent Category: '{parent_name}' (Expected: '{test_case.expected_parent_type}')")
            
            if name_match and parent_match:
                print(f"✅ PASS")
                successes += 1
            else:
                print(f"❌ FAIL - {'Name mismatch' if not name_match else 'Parent category mismatch'}")
                failures += 1
            
            print("-" * 40)
            
        # Try creating a duplicate to check deduplication
        print("\nDEDUPLICATION TEST:")
        tag_in = TagCreate(name="JavaScript")  # Trying to create again
        result = await create_tag(tag_in, db)
        
        # We should get the same ID as the first JavaScript tag
        is_deduplicated = str(result.id) == str(created_tags[0])
        print(f"Deduplication test: {'✅ PASS' if is_deduplicated else '❌ FAIL'}")
        
        if is_deduplicated:
            successes += 1
        else:
            failures += 1
            
    except Exception as e:
        print(f"Error during test: {str(e)}")
        db.rollback()
    finally:
        # Clean up created tags - comment this out if you want to keep them
        if db:
            try:
                # Uncomment to delete test tags
                # for tag_id in created_tags:
                #     tag = db.query(Tag).filter(Tag.id == tag_id).first()
                #     if tag:
                #         db.delete(tag)
                # db.commit()
                pass
            except Exception as e:
                print(f"Error cleaning up: {str(e)}")
                db.rollback()
            finally:
                db.close()
    
    print("=" * 60)
    print(f"SUMMARY: {successes} passed, {failures} failed")
    print("=" * 60)
    
    return successes > 0 and failures == 0

if __name__ == "__main__":
    asyncio.run(test_tag_normalization())
