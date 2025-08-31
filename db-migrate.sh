#!/bin/bash
# Database migration script for Daily Challenge
# This script will migrate your dev database to production

# Exit on error
set -e

echo "=== Database Migration for Daily Challenge ==="
echo "This script will export your development database and prepare it for production."
echo "Timestamp: $(date)"

# Variables
DEV_CONTAINER="dcq-db"
BACKUP_FILE="dcq_db_migration_$(date +%Y%m%d%H%M%S).sql"

echo "1. Creating database dump from development..."
docker exec $DEV_CONTAINER pg_dump -U dcq_user dcq_db > $BACKUP_FILE

# Check if backup was successful
if [ ! -s "$BACKUP_FILE" ]; then
  echo "Error: Database backup failed or created an empty file."
  exit 1
fi

echo "Database backup created: $BACKUP_FILE ($(du -h $BACKUP_FILE | cut -f1) in size)"

# Create a transferable archive
echo "2. Compressing backup file..."
gzip -9 $BACKUP_FILE
COMPRESSED_FILE="${BACKUP_FILE}.gz"

echo "=== Migration preparation completed successfully ==="
echo "Next steps:"

echo "3. Transfer the backup file to your production server:"
echo "   scp $COMPRESSED_FILE root@157.180.84.245:/opt/daily-challenge/"

echo "4. On the production server, run:"
echo "   cd /opt/daily-challenge"
echo "   gunzip $COMPRESSED_FILE"
echo "   # Start only the database container"
echo "   docker compose -f docker-compose.production.yml up -d postgres"
echo "   # Wait for database to initialize"
echo "   sleep 10"
echo "   # Restore database"
echo "   cat $BACKUP_FILE | docker exec -i dcq-db psql -U dcq_user dcq_db"
echo "   # Start remaining services"
echo "   docker compose -f docker-compose.production.yml up -d"

echo "5. Verify the migration was successful"
