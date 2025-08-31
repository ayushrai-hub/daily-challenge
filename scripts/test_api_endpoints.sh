#!/bin/bash

# API Test Script
# This script tests all API endpoints in the Daily Challenge application

API_BASE_URL="http://localhost:8000/api"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Daily Challenge API Test Suite ===${NC}"
echo "Testing API at $API_BASE_URL"
echo

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to test an API endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local payload=$3
    local description=$4
    local expected_status=${5:-200}  # Default to expecting 200 OK
    
    TOTAL_TESTS=$((TOTAL_TESTS+1))
    
    echo -e "\n${YELLOW}Test: $description${NC}"
    echo "Endpoint: $method $endpoint"
    
    # Create a temp file for response
    RESP_FILE=$(mktemp)
    
    if [ -n "$payload" ]; then
        echo "Payload: $payload"
        status_code=$(curl -s -X $method "$API_BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$payload" \
            -w "%{http_code}" \
            -o $RESP_FILE)
    else
        status_code=$(curl -s -X $method "$API_BASE_URL$endpoint" \
            -w "%{http_code}" \
            -o $RESP_FILE)
    fi
    
    response_body=$(cat $RESP_FILE)
    
    if [ "$status_code" == "$expected_status" ]; then
        echo -e "${GREEN}✓ Success: Status code $status_code${NC}"
        PASSED_TESTS=$((PASSED_TESTS+1))
    else
        echo -e "${RED}✗ Failed: Expected status $expected_status, got $status_code${NC}"
        FAILED_TESTS=$((FAILED_TESTS+1))
    fi
    
    if [ ${#response_body} -gt 500 ]; then
        echo "Response: ${response_body:0:500}... (truncated)"
    else
        echo "Response: $response_body"
    fi
    
    # Return ID for resources created (if available)
    if [ "$status_code" == "200" ] || [ "$status_code" == "201" ]; then
        # Use jq to extract id if installed, otherwise use grep
        if command -v jq &> /dev/null; then
            resource_id=$(echo "$response_body" | jq -r '.id // empty')
        else
            resource_id=$(echo "$response_body" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
        fi
        echo "$resource_id"
    else
        echo ""
    fi
    
    # Clean up temp file
    rm $RESP_FILE
}

echo -e "\n${YELLOW}=== Health Check Tests ===${NC}"
test_endpoint "GET" "/health" "" "Basic Health Check"
test_endpoint "GET" "/health/detailed" "" "Detailed Health Check"

echo -e "\n${YELLOW}=== User Tests ===${NC}"
# Create a user
user_payload='{
  "email": "test-user-'$(date +%s)'@example.com",
  "subscription_status": "active"
}'
echo "Creating test user..."
user_id=$(test_endpoint "POST" "/users" "$user_payload" "Create user")

if [ -n "$user_id" ]; then
    echo "Created user with ID: $user_id"
    # Get all users
    test_endpoint "GET" "/users" "" "Get all users"
    
    # Get specific user
    test_endpoint "GET" "/users/$user_id" "" "Get specific user by ID"
else
    echo -e "${RED}Failed to create user, skipping related tests${NC}"
fi

echo -e "\n${YELLOW}=== Tag Tests ===${NC}"
# Create a tag
tag_payload='{
  "name": "python-'$(date +%s)'",
  "description": "Python programming language"
}'
echo "Creating test tag..."
tag_id=$(test_endpoint "POST" "/tags" "$tag_payload" "Create new tag")

if [ -n "$tag_id" ]; then
    echo "Created tag with ID: $tag_id"
    # Get all tags
    test_endpoint "GET" "/tags" "" "Get all tags"
    
    # Get specific tag
    test_endpoint "GET" "/tags/$tag_id" "" "Get specific tag by ID"
else
    echo -e "${RED}Failed to create tag, skipping related tests${NC}"
fi

echo -e "\n${YELLOW}=== Content Source Tests ===${NC}"
# Create a content source
content_source_payload='{
  "source_platform": "stackoverflow",
  "source_identifier": "stackoverflow-'$(date +%s)'",
  "raw_data": {"url": "https://stackoverflow.com/questions/12345"},
  "notes": "Interesting discussion about Python performance"
}'
echo "Creating test content source..."
content_source_id=$(test_endpoint "POST" "/content-sources" "$content_source_payload" "Create content source")

if [ -n "$content_source_id" ]; then
    echo "Created content source with ID: $content_source_id"
    # Get all content sources
    test_endpoint "GET" "/content-sources" "" "Get all content sources"
    
    # Get specific content source
    test_endpoint "GET" "/content-sources/$content_source_id" "" "Get specific content source by ID"
else
    echo -e "${RED}Failed to create content source, skipping related tests${NC}"
fi

echo -e "\n${YELLOW}=== Problem Tests ===${NC}"
# Create a problem with content source
if [ -n "$content_source_id" ]; then
    problem_with_source_payload='{
      "title": "Optimize Python Loop Performance",
      "description": "How to optimize the performance of nested loops in Python?",
      "solution": "Use list comprehensions or numpy vectorization instead of nested loops",
      "content_source_id": '"$content_source_id"'
    }'
    echo "Creating test problem with content source..."
    problem_id=$(test_endpoint "POST" "/problems" "$problem_with_source_payload" "Create problem with content source")
    
    if [ -n "$problem_id" ]; then
        echo "Created problem with ID: $problem_id"
    fi
fi

# Create a problem without content source
problem_without_source_payload='{
  "title": "Understanding Python Decorators",
  "description": "Explain how decorators work in Python and provide examples",
  "solution": "Decorators are functions that modify the behavior of other functions",
  "content_source_id": 0
}'
echo "Creating test problem without content source..."
problem_without_source_id=$(test_endpoint "POST" "/problems" "$problem_without_source_payload" "Create problem without content source")

if [ -n "$problem_without_source_id" ]; then
    echo "Created problem without source, ID: $problem_without_source_id"
fi

# Get all problems
test_endpoint "GET" "/problems" "" "Get all problems"

# Get specific problem (prefer problem with source if available)
test_problem_id="${problem_id:-$problem_without_source_id}"
if [ -n "$test_problem_id" ]; then
    test_endpoint "GET" "/problems/$test_problem_id" "" "Get specific problem by ID"
else
    echo -e "${RED}No problems created, skipping problem detail test${NC}"
fi

echo -e "\n${YELLOW}=== Delivery Log Tests ===${NC}"
# Create a delivery log
if [ -n "$problem_id" ] && [ -n "$user_id" ]; then
    delivery_log_payload='{
      "user_id": '"$user_id"',
      "problem_id": '"$problem_id"',
      "delivery_status": "delivered",
      "delivery_time": "2025-05-02T10:00:00Z"
    }'
    echo "Creating test delivery log..."
    delivery_log_id=$(test_endpoint "POST" "/delivery-logs" "$delivery_log_payload" "Create delivery log")
    
    if [ -n "$delivery_log_id" ]; then
        echo "Created delivery log with ID: $delivery_log_id"
    fi
fi

# Get all delivery logs
test_endpoint "GET" "/delivery-logs" "" "Get all delivery logs"

# Get specific delivery log
if [ -n "$delivery_log_id" ]; then
    test_endpoint "GET" "/delivery-logs/$delivery_log_id" "" "Get specific delivery log by ID"
else
    echo -e "${RED}Failed to create delivery log or missing dependencies, skipping detail test${NC}"
fi

echo -e "\n${YELLOW}=== Test Summary ===${NC}"
echo "Total tests run: $TOTAL_TESTS"
echo -e "${GREEN}Tests passed: $PASSED_TESTS${NC}"
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "${RED}Tests failed: $FAILED_TESTS${NC}"
else
    echo -e "${GREEN}All tests passed!${NC}"
fi
