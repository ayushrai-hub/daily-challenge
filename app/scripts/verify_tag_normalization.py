"""
Simple verification script for tag normalization.

This script:
1. Uses the TagNormalizer service directly to test normalization
2. Verifies that it correctly handles case differences
3. Uses a direct SQL query to check ESLint tag mapping
"""
import sys
import os
import uuid
from datetime import datetime
from typing import List, Dict

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import only what we need for minimal testing
from app.core.logging import get_logger
logger = get_logger()

from app.db.session import get_db
from app.services.tag_normalizer import TagNormalizer

def test_normalizer_service():
    """Test the TagNormalizer service directly."""
    # Create an instance of TagNormalizer
    normalizer = TagNormalizer()
    
    # Test cases to verify normalization
    test_cases = [
        {"input": "eslint", "expected": "ESLint"},
        {"input": "javascript", "expected": "JavaScript"},
        {"input": "typescript", "expected": "TypeScript"},
        {"input": "react", "expected": "React"},
        {"input": "CODE QUALITY", "expected": "Code Quality"},
        {"input": "fastapi", "expected": "FastAPI"},
    ]
    
    results = []
    
    for case in test_cases:
        input_tag = case["input"]
        expected_tag = case["expected"]
        
        # Normalize the tag name
        normalized = normalizer._normalize_known_technology(input_tag)
        
        # Check if it matches expectation
        success = normalized == expected_tag
        results.append({
            "input": input_tag,
            "expected": expected_tag,
            "actual": normalized,
            "success": success
        })
    
    return results

def verify_eslint_in_db():
    """Verify ESLint tag in database using direct SQL."""
    db = next(get_db())
    
    try:
        # Use raw SQL to avoid model loading issues
        query = "SELECT id, name FROM tags WHERE LOWER(name) = 'eslint'"
        results = db.execute(query).fetchall()
        
        # Count how many variants of 'eslint' exist
        eslint_variants = []
        for row in results:
            eslint_variants.append({"id": row[0], "name": row[1]})
        
        if len(eslint_variants) == 0:
            return {"success": False, "message": "No ESLint tag found in database"}
        elif len(eslint_variants) == 1:
            eslint = eslint_variants[0]
            return {
                "success": True, 
                "message": f"Found single ESLint tag: {eslint['name']} ({eslint['id']})",
                "proper_case": eslint["name"] == "ESLint"
            }
        else:
            return {
                "success": False,
                "message": f"Multiple ESLint tags found: {', '.join(v['name'] for v in eslint_variants)}",
                "variants": eslint_variants
            }
        
    except Exception as e:
        logger.error(f"Error verifying ESLint in database: {str(e)}")
        return {"success": False, "message": str(e)}

if __name__ == "__main__":
    print("\nTag Normalization Verification")
    print("=" * 50)
    
    # Test 1: TagNormalizer Service
    print("\n1. Testing TagNormalizer Service:")
    results = test_normalizer_service()
    
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} '{result['input']}' → '{result['actual']}' (Expected: '{result['expected']}')")
    
    # Count successes
    successes = sum(1 for r in results if r["success"])
    print(f"\nNormalizer Test Results: {successes}/{len(results)} tests passed")
    
    # Test 2: Database Verification
    print("\n2. Verifying ESLint Tag in Database:")
    db_result = verify_eslint_in_db()
    
    if db_result["success"]:
        status = "✅" if db_result.get("proper_case", False) else "⚠️"
        print(f"{status} {db_result['message']}")
    else:
        print(f"❌ {db_result['message']}")
        if "variants" in db_result:
            print(f"   Found {len(db_result['variants'])} variants:")
            for v in db_result['variants']:
                print(f"   - {v['name']} ({v['id']})")
    
    print("\nVerification Complete")
    print("=" * 50)
