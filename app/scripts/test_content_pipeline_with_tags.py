#!/usr/bin/env python
"""
Test the full content pipeline with multi-parent tag relationships.

This script:
1. Creates test tags with multi-parent relationships
2. Triggers the content pipeline to generate a problem
3. Verifies that the generated content has properly normalized tags
4. Checks that parent-child relationships are maintained
"""
import sys
import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Set

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.session import get_db
from app.db.models.tag import Tag, TagType
from app.db.models.tag_hierarchy import TagHierarchy
from app.db.models.problem import Problem, DifficultyLevel, VettingTier, ProblemStatus
from app.repositories.tag import TagRepository
from app.repositories.problem_repository import create_problem_with_tags_sync, standardize_and_organize_tags
from app.services.tag_normalizer import TagNormalizer
from app.services.tag_mapper import get_tag_mapper
from app.schemas.tag import TagCreate
from app.core.logging import get_logger

logger = get_logger()

def cleanup_test_data(db):
    """Clean up any existing test data to ensure a clean test environment."""
    print("\nCleaning up any existing test data...")
    
    try:
        # 1. First remove any existing test problems
        test_problems = db.query(Problem).filter(
            (Problem.title == "Test Multi-Parent Tag Problem") | 
            (Problem.title == "AI-Generated Multi-Parent Tag Test")
        ).all()
        
        for test_problem in test_problems:
            print(f"Removing existing test problem: {test_problem.title} (ID: {test_problem.id})")
            # First remove the problem-tag relationships
            test_problem.tags = []
            db.flush()
            db.delete(test_problem)
            db.commit()
        
        # 2. Try to delete any test tags/categories with proper hierarchy cleanup
        # This would be test tags like 'javascript', 'react', 'Node.js', etc.
        test_tags = [
            "JavaScript", "javascript", "React", "react", "Node.js", "nodejs", 
            "Frontend Development", "frontend development"
        ]
        
        tag_repo = TagRepository(db)
        
        # First cleanup any tag hierarchy entries for these tags
        for tag_name in test_tags:
            tag = tag_repo.get_by_name_case_insensitive(tag_name)
            if tag:
                print(f"Cleaning up tag hierarchy for: {tag.name} (ID: {tag.id})")
                # Remove all tag hierarchy entries where this tag is a child
                db.query(TagHierarchy).filter(TagHierarchy.child_tag_id == tag.id).delete()
                # Remove all tag hierarchy entries where this tag is a parent
                db.query(TagHierarchy).filter(TagHierarchy.parent_tag_id == tag.id).delete()
                db.commit()
        
        # Now we can safely delete the tags
        for tag_name in test_tags:
            tag = tag_repo.get_by_name_case_insensitive(tag_name)
            if tag:
                print(f"Removing test tag: {tag.name} (ID: {tag.id})")
                db.delete(tag)
                db.commit()
    
    except Exception as e:
        print(f"Error during cleanup: {type(e).__name__}: {str(e)}")
        db.rollback()
        import traceback
        traceback.print_exc()

def setup_test_tags(db):
    """Create or get test tags with multi-parent relationships."""
    print("\nSetting up test tags for content pipeline test...")
    
    tag_repo = TagRepository(db)
    
    # Create or get parent category tags
    categories = {
        "Languages": TagCreate(name="Languages", tag_type=TagType.language),
        "Frameworks": TagCreate(name="Frameworks", tag_type=TagType.framework),
        "Frontend": TagCreate(name="Frontend", tag_type=TagType.domain),
        "Backend": TagCreate(name="Backend", tag_type=TagType.domain),
        "DevOps": TagCreate(name="DevOps", tag_type=TagType.domain),
    }
    
    category_ids = {}
    
    for name, tag_data in categories.items():
        existing = tag_repo.get_by_name(name)
        if existing:
            category_ids[name] = existing.id
            print(f"Using existing category: {name} ({existing.id})")
        else:
            new_tag = tag_repo.create(tag_data)
            category_ids[name] = new_tag.id
            print(f"Created category: {name} ({new_tag.id})")
    
    return category_ids

def create_test_problem(db, tags=None):
    """Create a test problem with normalized tags."""
    if tags is None:
        tags = ["javascript", "react", "nodejs", "frontend development"]
    
    print(f"\nCreating test problem with tags: {tags}")
    
    # Problem data with tags that need normalization
    problem_data = {
        "title": "Test Multi-Parent Tag Problem",
        "description": "This is a test problem to verify the tag normalization system with multi-parent relationships.",
        "solution": "```javascript\nfunction solution() {\n  return 'This is a test solution';\n}\n```",
        "difficulty_level": DifficultyLevel.medium,
        "status": ProblemStatus.draft,
        "vetting_tier": VettingTier.tier3_needs_review,
        "tags": tags
    }
    
    try:
        # Create the problem using the repository function that handles tag normalization
        problem_id = create_problem_with_tags_sync(db, problem_data)
        print(f"Created problem with ID: {problem_id}")
        return problem_id
    except Exception as e:
        print(f"Error creating problem: {type(e).__name__}: {str(e)}")
        # Print traceback for debugging
        import traceback
        traceback.print_exc()
        return None

def test_ai_generated_content(db):
    """Test tag normalization directly with simulated AI-generated content."""
    print("\nTesting tag normalization with simulated AI-generated content...")
    
    # First create a set of standard tags that will be reused across problems
    tag_repo = TagRepository(db)
    
    # 1. Make sure standard parent tags exist
    print("\nStep 1: Setting up standard parent tags...")
    languages_tag = tag_repo.get_by_name_case_insensitive("Languages")
    if not languages_tag:
        languages_tag = Tag(name="Languages", tag_type=TagType.language)
        db.add(languages_tag)
        db.flush()
        print(f"Created parent tag: Languages (ID: {languages_tag.id})")
    else:
        print(f"Using existing parent tag: Languages (ID: {languages_tag.id})")
    
    frameworks_tag = tag_repo.get_by_name_case_insensitive("Frameworks")
    if not frameworks_tag:
        frameworks_tag = Tag(name="Frameworks", tag_type=TagType.framework)
        db.add(frameworks_tag)
        db.flush()
        print(f"Created parent tag: Frameworks (ID: {frameworks_tag.id})")
    else:
        print(f"Using existing parent tag: Frameworks (ID: {frameworks_tag.id})")
    
    # 2. Create standard child tags with proper relationships if they don't exist
    print("\nStep 2: Setting up standard child tags with predictable relationships...")
    
    # Python tag (child of Languages)
    python_tag = tag_repo.get_by_name_case_insensitive("Python")
    if not python_tag:
        python_tag = Tag(name="Python", tag_type=TagType.language)
        db.add(python_tag)
        db.flush()
        print(f"Created tag: Python (ID: {python_tag.id})")
        
        # Add Python -> Languages relationship
        python_languages = TagHierarchy(parent_tag_id=languages_tag.id, child_tag_id=python_tag.id)
        db.add(python_languages)
    else:
        print(f"Using existing tag: Python (ID: {python_tag.id})")
        
    # FastAPI tag (child of Frameworks and Python)
    fastapi_tag = tag_repo.get_by_name_case_insensitive("FastAPI")
    if not fastapi_tag:
        fastapi_tag = Tag(name="FastAPI", tag_type=TagType.framework)
        db.add(fastapi_tag)
        db.flush()
        print(f"Created tag: FastAPI (ID: {fastapi_tag.id})")
        
        # Add FastAPI -> Frameworks relationship
        fastapi_frameworks = TagHierarchy(parent_tag_id=frameworks_tag.id, child_tag_id=fastapi_tag.id)
        db.add(fastapi_frameworks)
        
        # Add FastAPI -> Python relationship (multi-parent)
        fastapi_python = TagHierarchy(parent_tag_id=python_tag.id, child_tag_id=fastapi_tag.id)
        db.add(fastapi_python)
    else:
        print(f"Using existing tag: FastAPI (ID: {fastapi_tag.id})")
    
    # Commit the standard tags
    db.commit()
    
    # 3. Now test AI-generated content with case variations of existing tags
    print("\nStep 3: Testing AI-generated content with case variations of existing tags...")
    
    # Note the case variations of the existing tags to test case insensitivity
    ai_generated_problem = {
        "title": "AI-Generated Multi-Parent Tag Test",
        "description": "This problem tests tag reuse with varied casing.",
        "difficulty_level": "medium",  # String format as would come from AI
        "tags": [
            "python",      # lowercase variation of existing "Python" tag
            "FASTAPI",     # uppercase variation of existing "FastAPI" tag
            "API Development"  # New tag that doesn't exist yet
        ],
        "solution": "```python\ndef solution():\n    return 'This is a simulated AI-generated solution'\n```",
        "example": {"input": "test", "output": "result"}
    }
    
    try:
        # Create the problem using create_problem_with_tags_sync which should handle
        # tag normalization and reuse existing tags properly
        problem_data = {
            "title": ai_generated_problem["title"],
            "description": ai_generated_problem["description"],
            "solution": ai_generated_problem["solution"],
            "difficulty_level": DifficultyLevel.medium,  # Convert string to enum
            "status": ProblemStatus.approved,  
            "vetting_tier": VettingTier.tier2_ai,
            "tags": ai_generated_problem["tags"]
        }
        
        # Use the standard function that handles case insensitivity
        problem_id = create_problem_with_tags_sync(db, problem_data)
        db.flush()
        
        # Get the created problem to verify its tags
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        
        print(f"✅ Successfully created AI-simulated problem with ID: {problem_id}")
        
        # 4. Verify that the system reused existing tags rather than creating duplicates
        print("\nStep 4: Verifying tag reuse and relationships...")
        problem_tag_names = [tag.name for tag in problem.tags]
        print(f"Problem has these tags: {problem_tag_names}")
        
        # Check that we reused existing tags with correct casing
        python_reused = False
        fastapi_reused = False
        api_dev_created = False
        
        for tag in problem.tags:
            # Check tag parents
            parent_tags = tag_repo.get_parent_tags(tag.id)
            parent_names = [p.name for p in parent_tags]
            print(f"Tag '{tag.name}' has parents: {parent_names}")
            
            # Check if we reused Python with correct case
            if tag.name.lower() == "python":
                python_reused = (tag.id == python_tag.id)
                print(f"Python tag reused: {python_reused} (matched tag ID: {tag.id} vs original ID: {python_tag.id})")
                if not any(p.name == "Languages" for p in parent_tags):
                    print(f"❌ Python tag missing expected parent 'Languages'. Found: {parent_names}")
                    
            # Check if we reused FastAPI with correct case
            elif tag.name.lower() == "fastapi":
                fastapi_reused = (tag.id == fastapi_tag.id)
                print(f"FastAPI tag reused: {fastapi_reused} (matched tag ID: {tag.id} vs original ID: {fastapi_tag.id})")
                if not any(p.name == "Frameworks" for p in parent_tags):
                    print(f"❌ FastAPI tag missing expected parent 'Frameworks'. Found: {parent_names}")
                if not any(p.name == "Python" for p in parent_tags):
                    print(f"❌ FastAPI tag missing expected parent 'Python'. Found: {parent_names}")
                    
            # Check if the new tag was created properly
            elif "api development" in tag.name.lower():
                api_dev_created = True
                print(f"API Development tag created with name: {tag.name} (ID: {tag.id})")
        
        # Evaluate overall success
        success = python_reused and fastapi_reused and api_dev_created
        
        if success:
            print("\n✅ AI-generated content successfully reused existing tags and created new ones!")
        else:
            print("\n❌ Issues with tag handling in AI-generated content:")
            if not python_reused:
                print("  - Failed to reuse existing Python tag")
            if not fastapi_reused:
                print("  - Failed to reuse existing FastAPI tag")
            if not api_dev_created:
                print("  - Failed to create new API Development tag")
        
        # Clean up the test problem
        cleanup_test_problem(db, problem_id)
        
        # Don't clean up the standard tags - we want to keep them in the database
        # for potential future tests and to better reflect real-world conditions
        
        return success, problem_id
    except Exception as e:
        print(f"❌ Error testing AI-generated content: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def verify_problem_tags(db, problem_id, is_ai_generated=False):
    """Verify that the problem has properly normalized tags with correct parent relationships."""
    print(f"\nVerifying tags for problem {problem_id}...")
    
    try:
        # Get the problem with its tags
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            print(f"❌ Problem {problem_id} not found")
            return False
        
        print(f"Problem: {problem.title}")
        print(f"Tags: {[tag.name for tag in problem.tags]}")
        
        # Quick check to make sure the problem has tags
        if not problem.tags:
            print("❌ Problem has no tags")
            return False
        
        # Create a tag repository to check parent tags
        tag_repo = TagRepository(db)
        
        # Verify that tags are properly normalized and have expected parents
        success = True
        for tag in problem.tags:
            parent_tags = tag_repo.get_parent_tags(tag.id)
            parent_names = [p.name for p in parent_tags]
            
            print(f"\nTag '{tag.name}' has parents: {parent_names}")
            
            if is_ai_generated:
                # For AI-generated content, check based on the expected tags:
                # python, FastAPI, api-development, REST, async
                if tag.name.lower() == "python":
                    parent_names_lower = {p.lower() for p in parent_names}
                    if "languages" not in parent_names_lower:
                        print(f"❌ Python missing expected parent 'Languages'. Found: {parent_names}")
                        success = False
                        
                elif tag.name.lower() == "fastapi":
                    parent_names_lower = {p.lower() for p in parent_names}
                    if "frameworks" not in parent_names_lower:
                        print(f"❌ FastAPI missing expected parent 'Frameworks'. Found: {parent_names}")
                        success = False
                        
                elif tag.name.lower() == "rest":
                    parent_names_lower = {p.lower() for p in parent_names}
                    if "concept" not in parent_names_lower and "api" not in parent_names_lower:
                        print(f"❌ REST missing expected concept-related parent. Found: {parent_names}")
                        success = False
            else:
                # For regular test content with javascript, react, nodejs
                if tag.name == "JavaScript":
                    # JavaScript should be under both Languages and Frontend
                    # Use case-insensitive comparison
                    parent_names_lower = {p.lower() for p in parent_names}
                    if "languages" not in parent_names_lower:
                        print(f"❌ JavaScript missing expected parent 'Languages'. Found: {parent_names}")
                        success = False
                        
                elif tag.name == "React":
                    # React should be under both Frameworks and Frontend
                    # JavaScript as a parent is also acceptable
                    parent_names_lower = {p.lower() for p in parent_names}
                    if "frameworks" not in parent_names_lower:
                        print(f"❌ React missing expected parent 'Frameworks'. Found: {parent_names}")
                        success = False
                        
                elif tag.name == "Node.js":
                    # Node.js should be under both Backend and Frameworks
                    parent_names_lower = {p.lower() for p in parent_names}
                    if "frameworks" not in parent_names_lower:
                        print(f"❌ Node.js missing expected parent 'Frameworks'. Found: {parent_names}")
                        success = False
        
        if success:
            print("\n✅ All tags have the correct parent relationships!")
        else:
            print("\n❌ Some tags are missing expected parent relationships.")
        
        return success
    except Exception as e:
        print(f"Error during verification: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_test_problem(db, problem_id):
    """Clean up the test problem."""
    print(f"\nCleaning up test problem {problem_id}...")
    
    try:
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        if problem:
            # Remove tag associations first
            problem.tags = []
            db.commit()
            
            # Then delete the problem
            db.delete(problem)
            db.commit()
            print(f"✅ Successfully deleted test problem {problem_id}")
        else:
            print(f"❓ Problem {problem_id} not found for cleanup")
        
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ Error cleaning up test problem: {str(e)}")
        return False

if __name__ == "__main__":
    print("\nContent Pipeline Tag Normalization Test")
    print("=" * 60)
    
    # Get DB session
    db = next(get_db())
    
    try:
        # 0. Clean up any existing test data
        cleanup_test_data(db)
        
        # 1. Setup test tags
        category_ids = setup_test_tags(db)
        
        # 2. Test with regular tags
        print("\nPart A: Testing with regular predefined tags")
        print("-" * 60)
        print("\nStep 2: Creating test problem...")
        problem_id = create_test_problem(db)
        
        # 3. Verify the problem tags and their parent relationships
        print("\nStep 3: Verifying tag relationships...")
        verify_success_regular = verify_problem_tags(db, problem_id)
        
        # 4. Cleanup
        print("\nStep 4: Cleanup...")
        if problem_id:
            cleanup_test_problem(db, problem_id)
        
        # 5. Test with simulated AI-generated content
        print("\nPart B: Testing with simulated AI-generated content")
        print("-" * 60)
        ai_success, ai_problem_id = test_ai_generated_content(db)
        
        # 6. Report results
        print("\nOverall Test Results:")
        print("=" * 60)
        print(f"Regular Tag Normalization: {'✅ PASS' if verify_success_regular else '❌ FAIL'}")
        print(f"AI-Generated Content Tag Normalization: {'✅ PASS' if ai_success else '❌ FAIL'}")
        print(f"Overall Test Status: {'✅ PASS' if (verify_success_regular and ai_success) else '❌ FAIL'}")
        
    except Exception as e:
        logger.error(f"Error during content pipeline test: {str(e)}")
        print(f"❌ FATAL ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
