#!/usr/bin/env python3
"""
Test script for Content Sources API filtering functionality.
This script tests various filtering scenarios to ensure that the API correctly filters content sources
based on different parameters.
"""

import json
import requests
import sys
from datetime import datetime, timedelta

# API Base URL
BASE_URL = "http://localhost:8000/api"

def get_auth_token():
    """Get authentication token for API access"""
    try:
        with open("test_users.json", "r") as f:
            users = json.load(f)
            print(f"Loaded {len(users)} test users from test_users.json")
            
            # Use the first user (admin) for authentication
            admin_user = users[0]
            login_data = {
                "username": admin_user["email"],
                "password": "testpassword123"  # Correct password from create_test_users.py
            }
            
            response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
            response.raise_for_status()
            return response.json()["access_token"]
            
    except FileNotFoundError:
        print("Error: test_users.json not found. Please run create_test_users.py first.")
        sys.exit(1)
    except Exception as e:
        print(f"Error getting auth token: {str(e)}")
        sys.exit(1)

def load_content_sources():
    """Load test content sources data from JSON file"""
    try:
        with open("test_content_sources.json", "r") as f:
            content_sources = json.load(f)
            print(f"Loaded {len(content_sources)} test content sources from test_content_sources.json")
            return content_sources
    except FileNotFoundError:
        print("Error: test_content_sources.json not found. Please run create_test_content_sources.py first.")
        sys.exit(1)

def test_filter(description, url, expected_count=None, expected_min_count=None):
    """Test a specific filter scenario"""
    print(f"\nRunning test: {description}")
    print(f"Request URL: {url}")
    
    response = requests.get(
        url, 
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code != 200:
        print(f"❌ Test failed with status code {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    results = response.json()
    count = len(results)
    print(f"Result count: {count}", end="")
    
    if expected_count is not None:
        print(f" (Expected: {expected_count})")
        if count == expected_count:
            print("✅ Test passed")
            return True
        else:
            print("❌ Test failed - count mismatch")
            return False
    elif expected_min_count is not None:
        print(f" (Expected minimum: {expected_min_count})")
        if count >= expected_min_count:
            print("✅ Test passed")
            return True
        else:
            print("❌ Test failed - count below minimum")
            return False
    else:
        print(" (No expected count specified)")
        return True

def run_tests():
    """Run all content source filtering tests"""
    content_sources = load_content_sources()
    
    # Calculate some test values based on our content sources
    source_platforms = set(src["source_platform"] for src in content_sources)
    processed_sources = [src for src in content_sources if src["processing_status"] == "processed"]
    pending_sources = [src for src in content_sources if src["processing_status"] == "pending"]
    failed_sources = [src for src in content_sources if src["processing_status"] == "failed"]
    
    # Count sources with "Algorithm" in the title
    algorithm_sources = [src for src in content_sources if "Algorithm" in src["source_title"]]
    
    # Run tests
    tests = [
        # Basic tests without filters
        {
            "description": "All content sources (no filter)",
            "url": f"{BASE_URL}/content-sources",
            "expected_min_count": len(content_sources)
        },
        
        # Single field filters
        {
            "description": "Filter by source platform 'stackoverflow'",
            "url": f"{BASE_URL}/content-sources?source_platform=stackoverflow",
            "expected_count": len([src for src in content_sources if src["source_platform"] == "stackoverflow"])
        },
        {
            "description": "Filter by source platform 'blog'",
            "url": f"{BASE_URL}/content-sources?source_platform=blog",
            "expected_count": len([src for src in content_sources if src["source_platform"] == "blog"])
        },
        {
            "description": "Filter by processing status 'processed'",
            "url": f"{BASE_URL}/content-sources?processing_status=processed",
            "expected_count": len(processed_sources)
        },
        {
            "description": "Filter by processing status 'pending'",
            "url": f"{BASE_URL}/content-sources?processing_status=pending",
            "expected_count": len(pending_sources)
        },
        {
            "description": "Filter by processing status 'failed'",
            "url": f"{BASE_URL}/content-sources?processing_status=failed",
            "expected_count": len(failed_sources)
        },
        
        # Partial text matching
        {
            "description": "Filter by source title substring 'Algorithm'",
            "url": f"{BASE_URL}/content-sources?source_title=Algorithm",
            "expected_count": len(algorithm_sources)  # Dynamic count based on actual data
        },
        {
            "description": "Filter by source URL substring 'github'",
            "url": f"{BASE_URL}/content-sources?source_url=github",
            "expected_count": 1
        },
        
        # Combined filters
        {
            "description": "Filter by platform AND status",
            "url": f"{BASE_URL}/content-sources?source_platform=stackoverflow&processing_status=processed",
            "expected_count": len([src for src in content_sources 
                                if src["source_platform"] == "stackoverflow" and 
                                src["processing_status"] == "processed"])
        },
        
        # Date range filters
        {
            "description": "Filter by ingested within last week",
            "url": f"{BASE_URL}/content-sources?ingested_at_after={datetime.now() - timedelta(days=7):%Y-%m-%dT%H:%M:%S}",
            "expected_min_count": 1
        }
    ]
    
    # Execute all tests
    passed = 0
    for test in tests:
        if test_filter(**test):
            passed += 1
    
    print(f"\nTests completed: {passed}/{len(tests)} passed")
    return passed == len(tests)

if __name__ == "__main__":
    print("Starting Content Sources API filter tests...")
    token = get_auth_token()
    
    if token:
        print("Successfully authenticated. Starting Content Sources API filter tests...")
        success = run_tests()
        if success:
            print("\nAll Content Sources API filter tests passed!")
            sys.exit(0)
        else:
            print("\nSome Content Sources API filter tests failed.")
            sys.exit(1)
    else:
        print("Failed to authenticate. Cannot run tests.")
        sys.exit(1)
