#!/bin/bash
# Script to update the test database with the current schema

echo "Updating test database schema..."

# Set the database URL for the test database
export DATABASE_URL="postgresql://dcq_test_user:dcq_test_pass@localhost:5434/dcq_test_db"

# Drop and recreate the test database
echo "Dropping and recreating test database..."
docker exec dcq-test-db psql -U dcq_test_user -c "DROP DATABASE IF EXISTS dcq_test_db;"
docker exec dcq-test-db psql -U dcq_test_user -c "CREATE DATABASE dcq_test_db;"

# Create enum types in the test database
echo "Creating enum types..."
docker exec dcq-test-db psql -U dcq_test_user -d dcq_test_db -c "
CREATE TYPE IF NOT EXISTS sourceplatform AS ENUM ('stackoverflow', 'gh_issues', 'blog', 'custom');
CREATE TYPE IF NOT EXISTS vettingtier AS ENUM ('tier1', 'tier2', 'tier3');
CREATE TYPE IF NOT EXISTS tagtype AS ENUM ('language', 'framework', 'library', 'concept', 'tool', 'platform', 'other');
CREATE TYPE IF NOT EXISTS difficultylevel AS ENUM ('beginner', 'intermediate', 'advanced', 'expert');
CREATE TYPE IF NOT EXISTS problemstatus AS ENUM ('draft', 'pending', 'approved', 'rejected', 'retired');
CREATE TYPE IF NOT EXISTS processingstatus AS ENUM ('pending', 'processing', 'completed', 'failed');
CREATE TYPE IF NOT EXISTS deliverychannel AS ENUM ('email', 'sms', 'push', 'in_app');
CREATE TYPE IF NOT EXISTS deliverystatus AS ENUM ('pending', 'delivered', 'failed', 'opened', 'completed');
"

# Run alembic migrations on the test database
echo "Running alembic migrations..."
alembic upgrade head

echo "Test database schema updated successfully!"
