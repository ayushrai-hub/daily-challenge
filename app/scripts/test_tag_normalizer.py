"""
Test script to verify that the TagNormalizer correctly handles case-insensitive matching.
"""
import sys
from app.db.session import get_db
from app.repositories.tag import TagRepository
from app.services.tag_normalizer import TagNormalizer

# Import all models to ensure SQLAlchemy can resolve them
from app.db.models.user import User
from app.db.models.tag import Tag
from app.db.models.problem import Problem
from app.db.models.email_queue import EmailQueue
from app.db.models.content_source import ContentSource
from app.db.models.delivery_log import DeliveryLog

def test_tag_normalization():
    """Test case-insensitive tag matching and normalization"""
    print("Testing tag normalization service...")
    
    # Get DB session
    db = next(get_db())
    
    # Create repository and normalizer
    tag_repo = TagRepository(db)
    normalizer = TagNormalizer(tag_repo)
    
    # Test cases to verify (lowercase -> expected proper case)
    test_cases = [
        # Format: lowercase input -> expected normalized output
        ("typescript", "TypeScript"),
        ("javascript", "JavaScript"),
        ("python", "Python"),
        ("arrays", "Arrays"),
        ("algorithms", "Algorithms"),
        ("eslint", "ESLint"),
        # Add more cases as needed
    ]
    
    for input_tag, expected in test_cases:
        # Test normalization (case standardization)
        normalized = normalizer.normalize_tag_names([input_tag])
        if not normalized or normalized[0] != expected:
            print(f"❌ Normalization failed: '{input_tag}' -> '{normalized[0] if normalized else None}' (expected '{expected}')")
        else:
            print(f"✅ Normalization success: '{input_tag}' -> '{normalized[0]}'")
        
        # Check if it maps to an existing tag with proper case
        mapped = normalizer.map_to_existing_tags([input_tag])
        existing_tag = tag_repo.get_by_name_case_insensitive(input_tag)
        
        if existing_tag:
            print(f"   Found existing tag: '{existing_tag.name}'")
            if mapped and mapped[0] == existing_tag.name:
                print(f"✅ Mapping success: '{input_tag}' -> '{mapped[0]}'")
            else:
                print(f"❌ Mapping failed: '{input_tag}' -> '{mapped[0] if mapped else None}' (expected '{existing_tag.name}')")
        else:
            print(f"   No existing tag found for '{input_tag}'")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_tag_normalization()
