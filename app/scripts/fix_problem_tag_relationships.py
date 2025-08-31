"""
Fix and verify the relationships between tags and their parents.

This script provides a direct approach to:
1. Verify tag parent relationships are properly set in the database
2. Update any tags that don't have the correct parent relationship
3. Validate that the relationships are working correctly
"""
import sys
import os
from pprint import pprint

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.logging import get_logger
logger = get_logger()

from app.db.session import get_db
from app.db.models.tag import Tag, TagType

def fix_tag_parent_relationships():
    """
    Verify and fix the relationships between tags and their parents directly in the database.
    """
    db = next(get_db())
    
    # Define the expected parent-child relationships
    tag_categories = {
        "Frontend": ["Web", "Portal", "UI", "Interface", "Layout", "Design", "Client", "Browser", "HTML", "CSS"],
        "Backend": ["Controllers", "Http Routes", "Routes", "Server", "API", "Endpoint", "Service", "Handler"],
        "Business": ["Invoicing", "Accounting", "Billing", "Payment", "CRM", "ERP"],
        "Languages": ["Python", "JavaScript", "TypeScript", "Java", "C++", "Go", "Rust"],
        "Frameworks": ["React", "Angular", "Vue", "Django", "Flask", "Express", "Spring", "Next.js", "Gatsby"],
        "Databases": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "SQLite", "DynamoDB"],
        "DevOps": ["Docker", "Kubernetes", "AWS", "Azure", "GCP", "CI/CD", "Jenkins", "GitHub Actions"]
    }
    
    # Create or verify parent categories exist
    for category, child_tags in tag_categories.items():
        parent_tag = db.query(Tag).filter(Tag.name == category).first()
        
        if not parent_tag:
            # Create the parent category
            parent_tag = Tag(
                name=category,
                description=f"{category} category for related technologies",
                tag_type=TagType.topic,
                is_featured=True
            )
            db.add(parent_tag)
            db.commit()
            logger.info(f"Created parent category: {category}")
        else:
            logger.info(f"Parent category exists: {category} (ID: {parent_tag.id})")
    
    # Find all existing tags and update their parent relationships
    updated_count = 0
    for category, child_tags in tag_categories.items():
        parent_tag = db.query(Tag).filter(Tag.name == category).first()
        
        if not parent_tag:
            logger.error(f"Parent category {category} not found, skipping children")
            continue
        
        # Find all tags that should belong to this category
        for child_name in child_tags:
            # Find the child tag (case-insensitive)
            child_tag = db.query(Tag).filter(Tag.name.ilike(f"%{child_name}%")).first()
            
            if child_tag:
                # If parent relationship is missing or incorrect, update it
                if not child_tag.parent_tag_id or child_tag.parent_tag_id != parent_tag.id:
                    old_parent_id = child_tag.parent_tag_id
                    old_parent = "None"
                    if old_parent_id:
                        old_parent_tag = db.query(Tag).filter(Tag.id == old_parent_id).first()
                        if old_parent_tag:
                            old_parent = old_parent_tag.name
                    
                    # Update the parent relationship
                    child_tag.parent_tag_id = parent_tag.id
                    logger.info(f"Updated {child_tag.name}: Parent changed from '{old_parent}' to '{parent_tag.name}'")
                    updated_count += 1
                else:
                    logger.info(f"Tag {child_tag.name} already has correct parent: {parent_tag.name}")
            else:
                # Child tag doesn't exist yet, can be created as needed
                pass
    
    # Commit all changes
    db.commit()
    logger.info(f"Updated {updated_count} tag parent relationships")
    
    # Verify the changes
    print("\nVerified Tag Relationships:")
    print("=" * 60)
    for category in tag_categories.keys():
        parent_tag = db.query(Tag).filter(Tag.name == category).first()
        if parent_tag:
            # Force a new query to get the latest data with children
            children = db.query(Tag).filter(Tag.parent_tag_id == parent_tag.id).all()
            child_names = [child.name for child in children]
            print(f"{parent_tag.name} ({len(child_names)} children):")
            for child_name in sorted(child_names):
                print(f"  - {child_name}")
        else:
            print(f"{category}: Not found")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    fix_tag_parent_relationships()
