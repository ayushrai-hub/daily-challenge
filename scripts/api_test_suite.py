#!/usr/bin/env python3
"""
API Test Suite for Daily Challenge API

This script provides a comprehensive test suite for the Daily Challenge API endpoints.
It uses pytest to ensure all API endpoints are working correctly.
"""

import os
import json
import pytest
import requests
import datetime
from typing import Dict, Any, List, Optional, Union

# API Configuration
API_BASE_URL = "http://localhost:8000/api"
test_data = {}  # Store test data across tests

# Helper Functions
def call_api(
    method: str, 
    endpoint: str, 
    payload: Optional[Dict[str, Any]] = None,
    expected_status: int = 200
) -> Dict[str, Any]:
    """
    Call API endpoint and return response.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        endpoint: API endpoint path
        payload: Request payload (for POST/PUT)
        expected_status: Expected HTTP status code
        
    Returns:
        Response JSON data
    """
    url = f"{API_BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, json=payload, headers=headers)
    elif method == "PUT":
        response = requests.put(url, json=payload, headers=headers)
    elif method == "DELETE":
        response = requests.delete(url, headers=headers)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
    
    # Check status code
    assert response.status_code == expected_status, \
        f"Expected status {expected_status}, got {response.status_code}: {response.text}"
    
    # Return response data if JSON, otherwise empty dict
    try:
        return response.json() if response.text else {}
    except json.JSONDecodeError:
        return {}

# Test Classes
class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_basic_health(self):
        """Test basic health check endpoint"""
        data = call_api("GET", "/health")
        assert data["status"] == "ok"
    
    def test_detailed_health(self):
        """Test detailed health check endpoint"""
        data = call_api("GET", "/health/detailed")
        assert data["status"] == "ok"
        assert "version" in data
        assert "environment" in data
        assert "database" in data

class TestUserEndpoints:
    """Test user-related endpoints"""
    
    def test_create_user(self):
        """Test user creation"""
        # Generate unique email using timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        email = f"test-user-{timestamp}@example.com"
        
        payload = {
            "email": email,
            "subscription_status": "active"
        }
        
        data = call_api("POST", "/users", payload)
        assert data["email"] == email
        assert "id" in data
        
        # Store user ID for future tests
        test_data["user_id"] = data["id"]
    
    def test_get_users(self):
        """Test getting all users"""
        data = call_api("GET", "/users")
        assert isinstance(data, list)
        # At least one user should exist (the one we created)
        assert len(data) > 0
    
    def test_get_user_by_id(self):
        """Test getting a specific user by ID"""
        user_id = test_data.get("user_id")
        if not user_id:
            pytest.skip("No user ID available for testing")
        
        data = call_api("GET", f"/users/{user_id}")
        assert data["id"] == user_id

class TestTagEndpoints:
    """Test tag-related endpoints"""
    
    def test_create_tag(self):
        """Test tag creation"""
        # Generate unique tag using timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        tag_name = f"test-tag-{timestamp}"
        
        payload = {
            "name": tag_name,
            "description": "Test tag for API testing"
        }
        
        data = call_api("POST", "/tags", payload)
        assert data["name"] == tag_name
        assert "id" in data
        
        # Store tag ID for future tests
        test_data["tag_id"] = data["id"]
    
    def test_get_tags(self):
        """Test getting all tags"""
        data = call_api("GET", "/tags")
        assert isinstance(data, list)
        # At least one tag should exist (the one we created)
        assert len(data) > 0
    
    def test_get_tag_by_id(self):
        """Test getting a specific tag by ID"""
        tag_id = test_data.get("tag_id")
        if not tag_id:
            pytest.skip("No tag ID available for testing")
        
        data = call_api("GET", f"/tags/{tag_id}")
        assert data["id"] == tag_id

class TestContentSourceEndpoints:
    """Test content source-related endpoints"""
    
    def test_create_content_source(self):
        """Test content source creation"""
        # Generate unique identifier using timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        source_identifier = f"stackoverflow-{timestamp}"
        
        payload = {
            "source_platform": "stackoverflow",
            "source_identifier": source_identifier,
            "raw_data": {"url": "https://stackoverflow.com/questions/12345"},
            "notes": "Test content source for API testing"
        }
        
        data = call_api("POST", "/content-sources", payload)
        assert data["source_identifier"] == source_identifier
        assert "id" in data
        
        # Store content source ID for future tests
        test_data["content_source_id"] = data["id"]
    
    def test_get_content_sources(self):
        """Test getting all content sources"""
        data = call_api("GET", "/content-sources")
        assert isinstance(data, list)
        # At least one content source should exist (the one we created)
        assert len(data) > 0
    
    def test_get_content_source_by_id(self):
        """Test getting a specific content source by ID"""
        content_source_id = test_data.get("content_source_id")
        if not content_source_id:
            pytest.skip("No content source ID available for testing")
        
        data = call_api("GET", f"/content-sources/{content_source_id}")
        assert data["id"] == content_source_id

class TestProblemEndpoints:
    """Test problem-related endpoints"""
    
    def test_create_problem_with_content_source(self):
        """Test problem creation with content source"""
        content_source_id = test_data.get("content_source_id")
        if not content_source_id:
            pytest.skip("No content source ID available for testing")
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        title = f"Test Problem {timestamp}"
        
        payload = {
            "title": title,
            "description": "Test problem description",
            "solution": "Test problem solution",
            "content_source_id": content_source_id
        }
        
        data = call_api("POST", "/problems", payload)
        assert data["title"] == title
        assert data["content_source_id"] == content_source_id
        assert "id" in data
        
        # Store problem ID for future tests
        test_data["problem_id"] = data["id"]
    
    def test_create_problem_without_content_source(self):
        """Test problem creation without content source"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        title = f"Test Problem No Source {timestamp}"
        
        payload = {
            "title": title,
            "description": "Test problem description without source",
            "solution": "Test problem solution",
            "content_source_id": 0  # Should be converted to None in the backend
        }
        
        data = call_api("POST", "/problems", payload)
        assert data["title"] == title
        assert data["content_source_id"] is None
        assert "id" in data
        
        # Store problem ID for future tests
        test_data["problem_without_source_id"] = data["id"]
    
    def test_get_problems(self):
        """Test getting all problems"""
        data = call_api("GET", "/problems")
        assert isinstance(data, list)
        # At least one problem should exist (the ones we created)
        assert len(data) > 0
    
    def test_get_problem_by_id(self):
        """Test getting a specific problem by ID"""
        problem_id = test_data.get("problem_id")
        if not problem_id:
            pytest.skip("No problem ID available for testing")
        
        data = call_api("GET", f"/problems/{problem_id}")
        assert data["id"] == problem_id

class TestDeliveryLogEndpoints:
    """Test delivery log-related endpoints"""
    
    def test_create_delivery_log(self):
        """Test delivery log creation"""
        user_id = test_data.get("user_id")
        problem_id = test_data.get("problem_id")
        
        if not user_id or not problem_id:
            pytest.skip("No user ID or problem ID available for testing")
        
        payload = {
            "user_id": user_id,
            "problem_id": problem_id,
            "delivery_status": "delivered",
            "delivery_time": datetime.datetime.now().isoformat()
        }
        
        data = call_api("POST", "/delivery-logs", payload)
        assert data["user_id"] == user_id
        assert data["problem_id"] == problem_id
        assert "id" in data
        
        # Store delivery log ID for future tests
        test_data["delivery_log_id"] = data["id"]
    
    def test_get_delivery_logs(self):
        """Test getting all delivery logs"""
        data = call_api("GET", "/delivery-logs")
        assert isinstance(data, list)
    
    def test_get_delivery_log_by_id(self):
        """Test getting a specific delivery log by ID"""
        delivery_log_id = test_data.get("delivery_log_id")
        if not delivery_log_id:
            pytest.skip("No delivery log ID available for testing")
        
        data = call_api("GET", f"/delivery-logs/{delivery_log_id}")
        assert data["id"] == delivery_log_id

# Main execution
if __name__ == "__main__":
    print("Running Daily Challenge API tests...")
    pytest.main(["-v", __file__])
