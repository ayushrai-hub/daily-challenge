#!/bin/bash
# Database backup script for Daily Challenge

# Exit on error
set -e

# Set variables
BACKUP_DIR="/opt/backups/daily-challenge"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

echo "=== Creating database backup for Daily Challenge ==="
echo "Timestamp: $(date)"

# Backup database
echo "Creating PostgreSQL dump..."
docker exec dcq-db pg_dump -U dcq_user dcq_db > $BACKUP_DIR/dcq_db_$TIMESTAMP.sql

# Compress backup
echo "Compressing backup file..."
gzip $BACKUP_DIR/dcq_db_$TIMESTAMP.sql

# Create a latest symlink
ln -sf $BACKUP_DIR/dcq_db_$TIMESTAMP.sql.gz $BACKUP_DIR/latest.sql.gz

# Remove backups older than 14 days
echo "Removing backups older than 14 days..."
find $BACKUP_DIR -name "dcq_db_*.sql.gz" -type f -mtime +14 -delete

echo "=== Backup completed successfully ==="
echo "Backup file: $BACKUP_DIR/dcq_db_$TIMESTAMP.sql.gz"
echo "Total backups: $(find $BACKUP_DIR -name "dcq_db_*.sql.gz" | wc -l)"
echo "Disk usage: $(du -sh $BACKUP_DIR)"
