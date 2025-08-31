#!/usr/bin/env python
"""
Script to test the tag handling in the content pipeline.
Specifically checks if case-insensitive tag handling works properly.
"""
import os
import sys
import traceback
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.logging import setup_logging, get_logger
from app.tasks.content_processing.pipeline.ai_processing import complete_content_pipeline
from app.db.session import SessionLocal
from app.repositories.tag import TagRepository
from app.repositories.problem_repository import create_problem_with_tags_sync
from app.db.models.problem import DifficultyLevel, ProblemStatus, VettingTier

# Setup logging
setup_logging()
logger = get_logger()

def test_tag_handling():
    """Test the tag handling with case variations."""
    logger.info("=== Testing Tag Handling ===")
    
    # Create some test case variations for tags
    tag_variations = [
        # Original tag | Variant with different case
        ("Python", "python"),
        ("JavaScript", "javascript"),
        ("React", "REACT"),
        ("TypeScript", "Typescript"),
        ("NodeJS", "nodejs"),
    ]
    
    db = SessionLocal()
    try:
        tag_repo = TagRepository(db)
        
        # First, make sure we start with a clean state for our test tags
        for orig_tag, variant_tag in tag_variations:
            # Check if any of these tags already exist
            existing_tag = tag_repo.get_by_name_case_insensitive(orig_tag)
            if existing_tag:
                logger.info(f"Tag already exists: {existing_tag.name} (ID: {existing_tag.id})")
            else:
                logger.info(f"Tag does not exist yet: {orig_tag}")
        
        # Test 1: Create problems with original tag versions
        logger.info("\n=== Test 1: Creating problems with original tags ===")
        for i, (orig_tag, _) in enumerate(tag_variations):
            problem_data = {
                "title": f"Test Problem {i+1} with {orig_tag}",
                "description": f"This is a test problem for {orig_tag}",
                "solution": f"The solution involves using {orig_tag}",
                "difficulty_level": DifficultyLevel.easy,
                "status": ProblemStatus.draft,
                "vetting_tier": VettingTier.tier3_needs_review,
                "tags": [orig_tag]
            }
            
            logger.info(f"Creating problem with tag: {orig_tag}")
            problem_id = create_problem_with_tags_sync(db, problem_data)
            logger.info(f"Created problem with ID: {problem_id}")
        
        # Test 2: Create problems with variant tag versions (should reuse existing tags)
        logger.info("\n=== Test 2: Creating problems with variant tags (should reuse existing) ===")
        for i, (_, variant_tag) in enumerate(tag_variations):
            problem_data = {
                "title": f"Variant Test Problem {i+1} with {variant_tag}",
                "description": f"This is a test problem for {variant_tag}",
                "solution": f"The solution involves using {variant_tag}",
                "difficulty_level": DifficultyLevel.easy,
                "status": ProblemStatus.draft,
                "vetting_tier": VettingTier.tier3_needs_review,
                "tags": [variant_tag]
            }
            
            logger.info(f"Creating problem with variant tag: {variant_tag}")
            problem_id = create_problem_with_tags_sync(db, problem_data)
            logger.info(f"Created problem with ID: {problem_id}")
        
        # Test 3: Check tag counts to verify de-duplication worked
        logger.info("\n=== Test 3: Checking tag counts ===")
        for orig_tag, variant_tag in tag_variations:
            # This should return exactly one tag regardless of case
            orig_tag_count = db.query(tag_repo.model).filter(tag_repo.model.name.ilike(f"{orig_tag}")).count()
            variant_tag_count = db.query(tag_repo.model).filter(tag_repo.model.name.ilike(f"{variant_tag}")).count()
            
            logger.info(f"Tag '{orig_tag}' count: {orig_tag_count}")
            logger.info(f"Tag '{variant_tag}' count: {variant_tag_count}")
            
            if orig_tag_count == 1 and variant_tag_count == 1 and orig_tag.lower() == variant_tag.lower():
                logger.info(f"✅ SUCCESS: Case-insensitive tag handling works for '{orig_tag}'")
            else:
                logger.error(f"❌ FAILURE: Case-insensitive tag handling failed for '{orig_tag}'")
        
        logger.info("\n=== Testing Complete ===")
        
    except Exception as e:
        logger.error(f"Error testing tag handling: {str(e)}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_tag_handling()
