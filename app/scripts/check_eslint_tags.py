"""
Direct database check for ESLint tag normalization.

This script:
1. Directly queries the database to verify that ESLint tags are properly normalized
2. Checks that only one version of ESLint exists in the database
3. Verifies the TagNormalizer service handles lowercase eslint correctly
"""
import sys
import os
from sqlalchemy import func, text

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.logging import get_logger
logger = get_logger()

# Import only the minimum necessary to avoid model registration issues
from app.db.session import get_db
from app.services.tag_normalizer import TagNormalizer
from app.repositories.tag import TagRepository

def check_eslint_tags():
    """Directly check ESLint tags in the database."""
    db = next(get_db())
    
    # Check if we have any eslint tags (case insensitive)
    query = text("SELECT id, name FROM tags WHERE LOWER(name) = 'eslint'")
    results = db.execute(query).fetchall()
    
    eslint_tags = []
    for row in results:
        eslint_tags.append({"id": row[0], "name": row[1]})
    
    print(f"Found {len(eslint_tags)} ESLint tags in database")
    for tag in eslint_tags:
        print(f"  - {tag['name']} (ID: {tag['id']})")
    
    # Initialize tag repository and normalizer
    tag_repo = TagRepository(db)
    normalizer = TagNormalizer(tag_repo)
    
    # Verify tag normalizer handles eslint correctly
    test_cases = [
        {"input": "eslint", "expected": "ESLint"},
        {"input": "EsLiNt", "expected": "ESLint"},
        {"input": "ESLINT", "expected": "ESLint"}
    ]
    
    print("\nTesting TagNormalizer with ESLint variations:")
    for case in test_cases:
        result = normalizer._normalize_known_technology(case["input"])
        success = result == case["expected"]
        status = "✅" if success else "❌"
        print(f"{status} '{case['input']}' → '{result}' (Expected: '{case['expected']}')")
    
    return {
        "success": len(eslint_tags) == 1 and eslint_tags[0]["name"] == "ESLint",
        "count": len(eslint_tags),
        "tags": eslint_tags
    }

if __name__ == "__main__":
    print("\nESLint Tag Verification")
    print("=" * 50)
    
    result = check_eslint_tags()
    
    print("\nVerification Result:")
    if result["success"]:
        print("✅ SUCCESS: ESLint tag normalization is working correctly!")
        print(f"- Only one ESLint tag exists: {result['tags'][0]['name']}")
    else:
        if result["count"] == 0:
            print("❌ FAILURE: No ESLint tag found in the database")
        elif result["count"] > 1:
            print("❌ FAILURE: Multiple ESLint tags exist in the database")
            for tag in result["tags"]:
                print(f"  - {tag['name']} (ID: {tag['id']})")
        else:
            print(f"❌ FAILURE: ESLint tag has incorrect capitalization: {result['tags'][0]['name']}")
    
    print("=" * 50)
