"""
Quick script to update the parent-child relationships for existing web development tags.
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

def update_web_tag_parents():
    """Update parent-child relationships for web development tags directly in the database."""
    db = next(get_db())
    
    # Define the parent-child relationships
    mappings = {
        "Frontend": ["Web", "Portal", "UI", "Interface", "Layout", "Design", "Client", "Browser", "HTML", "CSS"],
        "Backend": ["Controllers", "Http Routes", "Routes", "Server", "API", "Endpoint", "Service", "Handler"],
        "Business": ["Invoicing", "Accounting", "Billing", "Payment", "CRM", "ERP"]
    }
    
    # Create parent categories if they don't exist
    for parent_name, child_tags in mappings.items():
        parent = db.query(Tag).filter(Tag.name == parent_name).first()
        
        if not parent:
            parent = Tag(
                name=parent_name,
                description=f"{parent_name} category for related technologies",
                tag_type=TagType.topic,
                is_featured=True
            )
            db.add(parent)
            db.flush()
            logger.info(f"Created parent category: {parent.name}")
        else:
            logger.info(f"Found existing parent category: {parent.name} (ID: {parent.id})")
        
        # For each child tag, set the parent relationship
        for child_name in child_tags:
            child = db.query(Tag).filter(Tag.name == child_name).first()
            
            if child:
                if child.parent_tag_id == parent.id:
                    logger.info(f"Tag '{child.name}' already has correct parent '{parent.name}'")
                else:
                    old_parent = "None"
                    if child.parent_tag_id:
                        old_parent_tag = db.query(Tag).filter(Tag.id == child.parent_tag_id).first()
                        old_parent = old_parent_tag.name if old_parent_tag else "Unknown"
                    
                    child.parent_tag_id = parent.id
                    logger.info(f"Updated parent for tag '{child.name}' from '{old_parent}' to '{parent.name}'")
            else:
                logger.info(f"Tag '{child_name}' not found in database, skipping")
    
    # Commit the changes
    db.commit()
    logger.info("All web development tag parent relationships updated")
    
    # Print the tag hierarchy for verification
    print("\nTag Hierarchy After Update:")
    print("=" * 60)
    for parent_name in mappings.keys():
        parent = db.query(Tag).filter(Tag.name == parent_name).first()
        if parent:
            children = db.query(Tag).filter(Tag.parent_tag_id == parent.id).all()
            child_names = [child.name for child in children]
            print(f"{parent.name} ({len(child_names)} children):")
            for child_name in sorted(child_names):
                print(f"  - {child_name}")
        else:
            print(f"{parent_name}: Not found")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    update_web_tag_parents()
