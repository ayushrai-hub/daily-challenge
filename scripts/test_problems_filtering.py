#!/usr/bin/env python3
"""
Test script for Problems API filtering functionality.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta

# API base URL
API_BASE_URL = "http://localhost:8000/api"

# Load test users and problems from JSON files
try:
    with open("test_users.json", "r") as f:
        TEST_USERS = json.load(f)
    print(f"Loaded {len(TEST_USERS)} test users from test_users.json")
except FileNotFoundError:
    print("Error: test_users.json not found. Run create_test_users_sql.py first.")
    sys.exit(1)

try:
    with open("test_problems.json", "r") as f:
        TEST_PROBLEMS = json.load(f)
    print(f"Loaded {len(TEST_PROBLEMS)} test problems from test_problems.json")
except FileNotFoundError:
    print("Error: test_problems.json not found. Run create_test_problems.py first.")
    sys.exit(1)

def get_auth_token(email, password):
    """Get an auth token for the specified user."""
    url = f"{API_BASE_URL}/auth/login"
    data = {
        "username": email,
        "password": password
    }
    
    response = requests.post(url, data=data)
    if response.status_code != 200:
        print(f"Authentication failed for user {email}: {response.status_code}")
        print(response.text)
        return None
    
    return response.json().get("access_token")

def test_problems_filtering(auth_token):
    """Test filtering functionality on the problems API endpoint."""
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    
    # Test cases for problem filtering
    test_cases = [
        {
            "name": "All problems (no filter)",
            "params": {},
            "expected_min_count": 5  # At least our 5 test problems
        },
        {
            "name": "Filter by 'easy' difficulty",
            "params": {"difficulty": "easy"},
            "expected_count": 2  # 2 easy problems
        },
        {
            "name": "Filter by 'medium' difficulty",
            "params": {"difficulty": "medium"},
            "expected_count": 2  # 2 medium problems
        },
        {
            "name": "Filter by 'hard' difficulty",
            "params": {"difficulty": "hard"},
            "expected_count": 1  # 1 hard problem
        },
        {
            "name": "Filter by 'approved' status",
            "params": {"status": "approved"},
            "expected_count": 3  # 3 approved problems
        },
        {
            "name": "Filter by 'draft' status",
            "params": {"status": "draft"},
            "expected_count": 1  # 1 draft problem
        },
        {
            "name": "Filter by 'archived' status",
            "params": {"status": "archived"},
            "expected_count": 1  # 1 archived problem
        },
        {
            "name": "Filter by title substring",
            "params": {"title": "Test Problem 1"},
            "expected_count": 1  # 1 problem with this title
        },
        {
            "name": "Filter by difficulty AND status",
            "params": {"difficulty": "easy", "status": "approved"},
            "expected_count": 2  # 2 easy approved problems
        }
    ]
    
    # Run the test cases
    for test_case in test_cases:
        print(f"\nRunning test: {test_case['name']}")
        
        # Build query string
        query_params = "&".join([f"{k}={v}" for k, v in test_case["params"].items()])
        query_string = f"?{query_params}" if query_params else ""
        
        url = f"{API_BASE_URL}/problems{query_string}"
        print(f"Request URL: {url}")
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            results = response.json()
            count = len(results) if isinstance(results, list) else 0
            
            if "expected_min_count" in test_case:
                expected = test_case["expected_min_count"]
                print(f"Result count: {count} (Expected minimum: {expected})")
                if count >= expected:
                    print("✅ Test passed")
                else:
                    print("❌ Test failed")
            else:
                expected = test_case["expected_count"]
                print(f"Result count: {count} (Expected: {expected})")
                if count == expected:
                    print("✅ Test passed")
                else:
                    print("❌ Test failed")
        else:
            print(f"❌ Test failed with status code: {response.status_code}")
            print(response.text)

def main():
    """Main function to run the filter tests."""
    # Use the admin user for authentication
    admin_user = next((user for user in TEST_USERS if user["is_admin"]), None)
    if not admin_user:
        print("Error: Admin user not found in test_users.json")
        return
    
    auth_token = get_auth_token(admin_user["email"], admin_user["password"])
    if not auth_token:
        print("Failed to authenticate admin user. Cannot proceed with tests.")
        return
    
    print("Successfully authenticated. Starting Problems API filter tests...")
    test_problems_filtering(auth_token)

if __name__ == "__main__":
    main()
