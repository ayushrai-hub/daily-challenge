#!/usr/bin/env python3
"""
Test script for API filtering functionality.
Directly tests the filter parameters added to the API endpoints.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta

# API base URL
API_BASE_URL = "http://localhost:8000/api"

# Load test users from the JSON file
try:
    with open("test_users.json", "r") as f:
        TEST_USERS = json.load(f)
    print(f"Loaded {len(TEST_USERS)} test users from test_users.json")
except FileNotFoundError:
    print("Error: test_users.json not found. Run create_test_users_sql.py first.")
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

def test_users_filtering(auth_token):
    """Test filtering functionality on the users API endpoint."""
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    
    # Test cases for user filtering
    test_cases = [
        {
            "name": "All users (no filter)",
            "params": {},
            "expected_count": 5
        },
        {
            "name": "Filter by active status",
            "params": {"is_active": "true"},
            "expected_count": 4  # 4 active users
        },
        {
            "name": "Filter by inactive status",
            "params": {"is_active": "false"},
            "expected_count": 1  # 1 inactive user
        },
        {
            "name": "Filter by admin status",
            "params": {"is_admin": "true"},
            "expected_count": 2  # 2 admin users
        },
        {
            "name": "Filter by non-admin status",
            "params": {"is_admin": "false"},
            "expected_count": 3  # 3 non-admin users
        },
        {
            "name": "Filter by email",
            "params": {"email": "admin@example.com"},
            "expected_count": 1  # 1 user with this exact email
        },
        {
            "name": "Filter by active admin users",
            "params": {"is_active": "true", "is_admin": "true"},
            "expected_count": 2  # 2 active admin users
        }
    ]
    
    # Run the test cases
    for test_case in test_cases:
        print(f"\nRunning test: {test_case['name']}")
        
        # Build query string
        query_params = "&".join([f"{k}={v}" for k, v in test_case["params"].items()])
        query_string = f"?{query_params}" if query_params else ""
        
        url = f"{API_BASE_URL}/users{query_string}"
        print(f"Request URL: {url}")
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            results = response.json()
            count = len(results) if isinstance(results, list) else 0
            print(f"Result count: {count} (Expected: {test_case['expected_count']})")
            
            if count == test_case['expected_count']:
                print("✅ Test passed")
            else:
                print("❌ Test failed")
        else:
            print(f"❌ Test failed: {response.status_code}")
            print(response.text)

def main():
    """Main function to run the filter tests."""
    # Use the admin user for authentication
    admin_user = next((user for user in TEST_USERS if user["email"] == "admin@example.com"), None)
    if not admin_user:
        print("Error: Admin user not found in test_users.json")
        return
    
    auth_token = get_auth_token(admin_user["email"], admin_user["password"])
    if not auth_token:
        print("Failed to authenticate admin user. Cannot proceed with tests.")
        return
    
    print("Successfully authenticated. Starting API filter tests...")
    test_users_filtering(auth_token)

if __name__ == "__main__":
    main()
