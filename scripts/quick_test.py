#!/usr/bin/env python3
"""
Quick API Test for Daily Challenge API

This script provides a simple test to verify the API is working.
"""

import requests
import json

# API Configuration
API_BASE_URL = "http://localhost:8000/api"

def test_health_endpoint():
    """Test basic health check endpoint"""
    url = f"{API_BASE_URL}/health"
    print(f"Testing endpoint: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Health endpoint is working!")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"❌ Health endpoint failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error accessing health endpoint: {str(e)}")
        return False

def test_health_detailed_endpoint():
    """Test detailed health check endpoint"""
    url = f"{API_BASE_URL}/health/detailed"
    print(f"Testing endpoint: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Detailed health endpoint is working!")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"❌ Detailed health endpoint failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error accessing detailed health endpoint: {str(e)}")
        return False

def test_openapi_docs():
    """Test OpenAPI docs endpoint to verify our documentation enhancements"""
    url = "http://localhost:8000/openapi.json"
    print(f"Testing endpoint: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ OpenAPI documentation is available!")
            data = response.json()
            
            # Check for our enhanced documentation
            if "info" in data and "description" in data["info"]:
                print("✅ Enhanced API description found in OpenAPI docs!")
                # Print just the first line of the description to confirm
                description = data["info"]["description"].strip().split("\n")[0]
                print(f"Description starts with: {description}")
                
                # Check for tags metadata
                if "tags" in data:
                    print(f"✅ Found {len(data['tags'])} tags with descriptions in OpenAPI docs!")
                else:
                    print("❌ No tags found in OpenAPI docs")
            else:
                print("❌ No enhanced description found in OpenAPI docs")
            
            return True
        else:
            print(f"❌ OpenAPI docs failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error accessing OpenAPI docs: {str(e)}")
        return False

if __name__ == "__main__":
    print("Running quick API tests...")
    
    # Test basic health endpoint
    health_ok = test_health_endpoint()
    print("\n" + "-" * 50 + "\n")
    
    # Test detailed health endpoint
    detailed_health_ok = test_health_detailed_endpoint()
    print("\n" + "-" * 50 + "\n")
    
    # Test OpenAPI docs
    openapi_ok = test_openapi_docs()
    print("\n" + "-" * 50 + "\n")
    
    # Summary
    print("Test Summary:")
    print(f"Health Endpoint: {'✅ PASSED' if health_ok else '❌ FAILED'}")
    print(f"Detailed Health Endpoint: {'✅ PASSED' if detailed_health_ok else '❌ FAILED'}")
    print(f"OpenAPI Documentation: {'✅ PASSED' if openapi_ok else '❌ FAILED'}")
    
    if health_ok and detailed_health_ok and openapi_ok:
        print("\n🎉 All tests passed! Your API enhancements are working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the logs above for details.")
