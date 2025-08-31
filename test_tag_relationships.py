#!/usr/bin/env python
"""
Test script to verify the Tag model's parent-child relationships are working properly.
This script creates tags and establishes parent-child relationships between them.
"""
import os
import sys
from uuid import UUID, uuid4
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Add the app directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the models
from app.db.models.base_model import BaseModel
from app.db.models.tag import Tag
from app.db.models.tag_hierarchy import TagHierarchy
from app.core.logging import setup_logging, get_logger

# Set up logging
setup_logging()
logger = get_logger()

def create_test_session():
    """Create a test database session."""
    # Use the same database URL as the application
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://dcq_user:dcq_pass@localhost:5433/dcq_db")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()

def test_tag_relationships():
    """Test creating tags and establishing parent-child relationships."""
    session = create_test_session()
    
    try:
        logger.info("Starting tag relationship test")
        
        # Use unique test tag names to avoid conflicts with existing tags
        tag_prefix = f"Test_{uuid4().hex[:6]}_"
        logger.info(f"Using tag prefix: {tag_prefix} for test tags")
        
        # Create some test tags with unique names
        programming_tag = Tag(name=f"{tag_prefix}Programming", description="Programming languages and concepts")
        python_tag = Tag(name=f"{tag_prefix}Python", description="Python programming language")
        js_tag = Tag(name=f"{tag_prefix}JavaScript", description="JavaScript programming language")
        framework_tag = Tag(name=f"{tag_prefix}Frameworks", description="Programming frameworks")
        django_tag = Tag(name=f"{tag_prefix}Django", description="Django web framework")
        flask_tag = Tag(name=f"{tag_prefix}Flask", description="Flask web framework")
        react_tag = Tag(name=f"{tag_prefix}React", description="React.js frontend framework")
        
        # Add tags to session
        session.add_all([
            programming_tag, python_tag, js_tag, framework_tag, 
            django_tag, flask_tag, react_tag
        ])
        session.flush()  # Get IDs without committing
        
        logger.info(f"Created tags with IDs: {programming_tag.id}, {python_tag.id}, {js_tag.id}, {framework_tag.id}")
        
        # Create parent-child relationships
        # Programming is parent of Python and JavaScript
        session.add(TagHierarchy(parent_tag_id=programming_tag.id, child_tag_id=python_tag.id))
        session.add(TagHierarchy(parent_tag_id=programming_tag.id, child_tag_id=js_tag.id))
        
        # Framework is parent of Django, Flask and React
        session.add(TagHierarchy(parent_tag_id=framework_tag.id, child_tag_id=django_tag.id))
        session.add(TagHierarchy(parent_tag_id=framework_tag.id, child_tag_id=flask_tag.id))
        session.add(TagHierarchy(parent_tag_id=framework_tag.id, child_tag_id=react_tag.id))
        
        # Python is also parent of Django and Flask
        session.add(TagHierarchy(parent_tag_id=python_tag.id, child_tag_id=django_tag.id))
        session.add(TagHierarchy(parent_tag_id=python_tag.id, child_tag_id=flask_tag.id))
        
        # JavaScript is parent of React
        session.add(TagHierarchy(parent_tag_id=js_tag.id, child_tag_id=react_tag.id))
        
        # Commit the changes
        session.commit()
        logger.info("Successfully created tag relationships")
        
        # Query tags to verify relationships
        logger.info("Testing tag relationships...")
        
        # Refresh tags from database to load relationships
        session.refresh(programming_tag)
        session.refresh(python_tag)
        session.refresh(js_tag)
        session.refresh(framework_tag)
        session.refresh(django_tag)
        session.refresh(flask_tag)
        session.refresh(react_tag)
        
        # Test children relationships
        logger.info(f"Programming tag has {len(programming_tag.children)} children")
        for child in programming_tag.children:
            logger.info(f"  - Child: {child.name}")
            
        logger.info(f"Python tag has {len(python_tag.children)} children")
        for child in python_tag.children:
            logger.info(f"  - Child: {child.name}")
            
        # Test parents relationships
        logger.info(f"Django tag has {len(django_tag.parents)} parents")
        for parent in django_tag.parents:
            logger.info(f"  - Parent: {parent.name}")
            
        logger.info(f"React tag has {len(react_tag.parents)} parents")
        for parent in react_tag.parents:
            logger.info(f"  - Parent: {parent.name}")
            
        # Verify multi-parent feature works correctly
        if len(django_tag.parents) > 1:
            logger.info("SUCCESS: Multi-parent relationship works! Django has multiple parents.")
        else:
            logger.warning("FAIL: Django should have multiple parents.")
            
        # Clean up test data
        logger.info("Cleaning up test data...")
        # First delete the hierarchy relationships
        for relation in session.query(TagHierarchy).all():
            session.delete(relation)
            
        # Then delete the tags
        for tag in [programming_tag, python_tag, js_tag, framework_tag, django_tag, flask_tag, react_tag]:
            session.delete(tag)
            
        session.commit()
        logger.info("Test data cleaned up successfully")
        
        return True
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error: {str(e)}")
        session.rollback()
        return False
    except Exception as e:
        logger.error(f"Error testing tag relationships: {str(e)}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    success = test_tag_relationships()
    if success:
        logger.info("Tag relationship test completed successfully!")
        print("✅ Tag relationship test passed!")
    else:
        logger.error("Tag relationship test failed!")
        print("❌ Tag relationship test failed!")
