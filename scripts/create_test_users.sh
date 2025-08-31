#!/bin/bash
# Script to create test users for authentication testing
# This file stores test user credentials and includes curl commands to create them

# Set base URL for API
API_URL='http://localhost:8000/api'

# Default to development database settings
POSTGRES_CONTAINER="dcq-db"
POSTGRES_USER="dcq_user"
POSTGRES_PASS="dcq_pass"
POSTGRES_DB="dcq_db"
POSTGRES_PORT="5433"

# Allow overriding with test database settings via environment variable
if [ "$USE_TEST_DB" = "true" ]; then
  POSTGRES_CONTAINER="dcq-test-db"
  POSTGRES_USER="dcq_test_user"
  POSTGRES_PASS="dcq_test_pass"
  POSTGRES_DB="dcq_test_db"
  POSTGRES_PORT="5434"
  echo "Using TEST database settings"
else
  echo "Using DEVELOPMENT database settings"
fi

echo "Creating test users for authentication testing..."
echo "================================================="
echo ""
echo "Test User Credentials:"
echo "--------------------"
echo "1. Admin User"
echo "   Email: admin@example.com"
echo "   Password: Admin123!"
echo ""
echo "2. Regular Active User"
echo "   Email: user@example.com"
echo "   Password: User123!"
echo ""
echo "3. Paused User"
echo "   Email: paused@example.com"
echo "   Password: Paused123!"
echo ""
echo "4. Unsubscribed User"
echo "   Email: unsubscribed@example.com"
echo "   Password: Unsub123!"
echo ""
echo "================================================="

# Create Admin User
echo "Creating admin user..."
curl -X 'POST' \
  "${API_URL}/auth/register" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "admin@example.com",
  "password": "Admin123!",
  "full_name": "Admin User"
}'
echo ""

# Make the user an admin (this needs to be done directly in the database since API likely doesn't expose this)
echo "Setting admin privileges..."
docker exec ${POSTGRES_CONTAINER} psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "UPDATE users SET is_admin = true WHERE email = 'admin@example.com';"

# Create Regular User
echo "Creating regular user..."
curl -X 'POST' \
  "${API_URL}/auth/register" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "user@example.com",
  "password": "User123!",
  "full_name": "Regular User"
}'
echo ""

# Create Paused User
echo "Creating paused subscription user..."
curl -X 'POST' \
  "${API_URL}/auth/register" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "paused@example.com",
  "password": "Paused123!",
  "full_name": "Paused User"
}'
echo ""

# Set subscription status to paused
echo "Setting paused subscription status..."
docker exec ${POSTGRES_CONTAINER} psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "UPDATE users SET subscription_status = 'paused' WHERE email = 'paused@example.com';"

# Create Unsubscribed User
echo "Creating unsubscribed user..."
curl -X 'POST' \
  "${API_URL}/auth/register" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "unsubscribed@example.com",
  "password": "Unsub123!",
  "full_name": "Unsubscribed User"
}'
echo ""

# Set subscription status to unsubscribed
echo "Setting unsubscribed status..."
docker exec ${POSTGRES_CONTAINER} psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "UPDATE users SET subscription_status = 'unsubscribed' WHERE email = 'unsubscribed@example.com';"

echo ""
echo "All test users have been created!"
echo ""
echo "To login as admin and get a token:"
echo "curl -X 'POST' \\
  '${API_URL}/auth/login' \\
  -H 'accept: application/json' \\
  -H 'Content-Type: application/x-www-form-urlencoded' \\
  -d 'username=admin@example.com&password=Admin123!'"
echo ""
echo "To login as regular user and get a token:"
echo "curl -X 'POST' \\
  '${API_URL}/auth/login' \\
  -H 'accept: application/json' \\
  -H 'Content-Type: application/x-www-form-urlencoded' \\
  -d 'username=user@example.com&password=User123!'"
echo ""
echo "To access protected endpoints with token:"
echo "curl -X 'GET' \\
  '${API_URL}/auth/me' \\
  -H 'accept: application/json' \\
  -H 'Authorization: Bearer YOUR_TOKEN_HERE'"
