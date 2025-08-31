"""
Script to organize tags into proper parent-child hierarchies.

This script:
1. Defines known parent-child relationships for tags
2. Updates existing tags to establish these relationships
3. Ensures that tags are properly categorized for better navigation and filtering
"""
import sys
import os
import logging
from typing import Dict, List, Optional, Set

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import all models explicitly to ensure they're registered with SQLAlchemy
from app.db.session import get_db
from app.db.models.tag import Tag
from app.db.models.problem import Problem
from app.db.models.user import User
from app.db.models.email_queue import EmailQueue
from app.db.models.content_source import ContentSource
from app.db.models.delivery_log import DeliveryLog
from app.db.models.verification_token import VerificationToken
from app.db.models.verification_metrics import VerificationMetrics

from app.repositories.tag import TagRepository
from app.core.logging import get_logger

logger = get_logger()

# Define known parent categories and their children
TAG_HIERARCHY = {
    # Programming Languages
    "Languages": ["Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "PHP", "Ruby", "Swift"],
    
    # Frameworks and Libraries
    "Frameworks": ["React", "Angular", "Vue.js", "Node.js", "Django", "Flask", "FastAPI", "Rails", "Spring"],
    
    # Development Tools
    "Development Tools": ["Git", "Docker", "Kubernetes", "CI/CD", "Jenkins", "GitHub Actions"],
    
    # Code Quality
    "Code Quality": ["Linting", "Testing", "Code Review", "Static Analysis", "Code Coverage"],
    
    # Linting
    "Linting": ["ESLint", "TSLint", "Pylint", "Flake8"],
    
    # Static Analysis
    "Static Analysis": ["AST", "Type Checking", "Code Patterns"],
    
    # Code Organization
    "Code Organization": ["Imports", "Import Statements", "Import Restrictions", "Code Layers", "Architecture", "Patterns"],
    
    # Algorithms
    "Algorithms": ["Sorting", "Searching", "Graph Algorithms", "Dynamic Programming", "Greedy Algorithms", "Recursion"],
    
    # Data Structures
    "Data Structures": ["Arrays", "Linked Lists", "Trees", "Graphs", "Hash Tables", "Stacks", "Queues", "Heaps"],
    
    # Front-end
    "Frontend": ["HTML", "CSS", "JavaScript", "TypeScript", "UI", "UX", "Responsive Design"],
    
    # Back-end
    "Backend": ["API", "REST", "GraphQL", "Authentication", "Authorization", "Database"],
    
    # Databases
    "Databases": ["SQL", "NoSQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch"],
    
    # Security
    "Security": ["Authentication", "Authorization", "Encryption", "HTTPS", "JWT", "OAuth"],
    
    # Deployment
    "Deployment": ["CI/CD", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Heroku"],
    
    # Testing
    "Testing": ["Unit Tests", "Integration Tests", "E2E Tests", "TDD", "BDD", "Mocking"]
}

# Some tags can belong to multiple parent categories
MULTI_PARENT_TAGS = {
    "Recursion": ["Algorithms", "Programming Concepts"],
    "TypeScript": ["Languages", "Frontend"],
    "JavaScript": ["Languages", "Frontend"],
    "Python": ["Languages", "Backend"],
    "Authentication": ["Security", "Backend"],
    "Docker": ["Development Tools", "Deployment"],
    "Kubernetes": ["Development Tools", "Deployment"]
}

def categorize_tags():
    """Update tag parent-child relationships in the database."""
    # Get DB session
    db = next(get_db())
    
    # Initialize repositories
    tag_repo = TagRepository(db)
    
    # Get all tags
    all_tags = db.query(Tag).all()
    logger.info(f"Found {len(all_tags)} tags in the database")
    
    # Create a map of tag name to tag object
    tag_map = {tag.name: tag for tag in all_tags}
    
    # Create parent categories that don't exist yet
    for parent_name in TAG_HIERARCHY.keys():
        if parent_name not in tag_map:
            parent_tag = Tag(name=parent_name)
            db.add(parent_tag)
            logger.info(f"Created new parent category: {parent_name}")
            tag_map[parent_name] = parent_tag
    
    db.flush()  # Ensure all parent tags have IDs
    
    # Count of relationships updated
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    # Update parent-child relationships based on the hierarchy
    for parent_name, children in TAG_HIERARCHY.items():
        parent_tag = tag_map.get(parent_name)
        if not parent_tag:
            logger.warning(f"Parent tag '{parent_name}' not found in database")
            continue
            
        for child_name in children:
            # Normalize case - make sure we look for the child tag with the exact case in the database
            matching_child_name = next((name for name in tag_map.keys() if name.lower() == child_name.lower()), None)
            
            if not matching_child_name:
                # Skip if child tag doesn't exist
                logger.warning(f"Child tag '{child_name}' not found in database")
                continue
                
            child_tag = tag_map[matching_child_name]
            
            # Skip if already has the correct parent
            if child_tag.parent_tag_id == parent_tag.id:
                logger.info(f"Tag '{child_tag.name}' already has parent '{parent_tag.name}'")
                skipped_count += 1
                continue
                
            try:
                # If tag already has a different parent, handle according to the multi-parent list
                if child_tag.parent_tag_id is not None:
                    # Check if this tag should have multiple parents
                    if matching_child_name in MULTI_PARENT_TAGS:
                        # For now, since our model only supports one parent, choose the first one in the list
                        preferred_parents = MULTI_PARENT_TAGS[matching_child_name]
                        if parent_name in preferred_parents:
                            # Update to this parent if it's one of the preferred parents
                            logger.info(f"Changing parent of '{child_tag.name}' from existing parent to '{parent_tag.name}'")
                            child_tag.parent_tag_id = parent_tag.id
                            updated_count += 1
                        else:
                            # Skip if current parent is preferred over this one
                            logger.info(f"Keeping existing parent for '{child_tag.name}' (multi-parent case)")
                            skipped_count += 1
                    else:
                        # If not in multi-parent list, prefer to keep existing parent
                        logger.info(f"Tag '{child_tag.name}' already has a different parent, skipping")
                        skipped_count += 1
                else:
                    # No existing parent, set it
                    child_tag.parent_tag_id = parent_tag.id
                    logger.info(f"Set parent of '{child_tag.name}' to '{parent_tag.name}'")
                    updated_count += 1
                    
            except Exception as e:
                logger.error(f"Error setting parent for tag '{child_tag.name}': {str(e)}")
                error_count += 1
    
    # Commit changes
    try:
        db.commit()
        logger.info(f"Successfully updated {updated_count} tag relationships")
    except Exception as e:
        db.rollback()
        logger.error(f"Error committing tag hierarchy updates: {str(e)}")
        raise
    
    return {
        "total_tags": len(all_tags),
        "updated": updated_count,
        "skipped": skipped_count,
        "errors": error_count
    }

if __name__ == "__main__":
    try:
        results = categorize_tags()
        
        print("\nTag Categorization Results:")
        print("=" * 50)
        print(f"Total tags processed: {results['total_tags']}")
        print(f"Parent-child relationships updated: {results['updated']}")
        print(f"Tags skipped (already correct): {results['skipped']}")
        print(f"Errors: {results['errors']}")
        print("=" * 50)
    except Exception as e:
        logger.error(f"Error running script: {str(e)}")
        print(f"\nError: {str(e)}")
        sys.exit(1)
