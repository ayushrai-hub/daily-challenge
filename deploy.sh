#!/bin/bash
# Deployment script for Daily Challenge

# Exit on error
set -e

echo "=== Starting deployment for Daily Challenge ==="
echo "Timestamp: $(date)"

# Pull latest changes
echo "Pulling latest code changes..."
cd /opt/daily-challenge
git pull

# Build and start services
echo "Building and starting containers..."
docker compose -f docker-compose.production.yml up -d --build

# Run database migrations if needed
echo "Running database migrations..."
docker exec dcq-api alembic upgrade head

# Create backup after deployment
echo "Creating deployment backup..."
/opt/daily-challenge/backup.sh

echo "=== Deployment completed successfully ==="
echo "Services running:"
docker ps -a | grep dcq

# Check API health
echo "Checking API health..."
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health || echo "API health check failed"

echo "=== Deployment completed at $(date) ==="
