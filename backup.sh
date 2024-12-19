#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Create backup directory
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo -e "${YELLOW}Starting RetroTrade Backup...${NC}"

# Backup database
echo "Backing up PostgreSQL database..."
docker-compose exec -T db pg_dump -U postgres retrotrade > "$BACKUP_DIR/database.sql"

# Backup Redis data
echo "Backing up Redis data..."
docker-compose exec -T redis redis-cli SAVE
docker cp retrotrade-redis:/data/dump.rdb "$BACKUP_DIR/redis-dump.rdb"

# Backup configuration files
echo "Backing up configuration files..."
cp .env "$BACKUP_DIR/.env"
cp docker-compose.yml "$BACKUP_DIR/docker-compose.yml"
cp prometheus.yml "$BACKUP_DIR/prometheus.yml"

# Backup Grafana dashboards
echo "Backing up Grafana dashboards..."
mkdir -p "$BACKUP_DIR/grafana"
docker cp retrotrade-grafana:/var/lib/grafana/dashboards "$BACKUP_DIR/grafana/"

# Create archive
echo "Creating backup archive..."
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"

# Cleanup old backups (keep last 7 days)
find backups/ -type f -name "*.tar.gz" -mtime +7 -delete

echo -e "${GREEN}Backup completed successfully!${NC}"
echo "Backup saved to: $BACKUP_DIR.tar.gz"

# Optional: Upload to remote storage
if [ ! -z "$BACKUP_REMOTE_PATH" ]; then
    echo "Uploading backup to remote storage..."
    rsync -avz "$BACKUP_DIR.tar.gz" "$BACKUP_REMOTE_PATH"
    echo -e "${GREEN}Backup uploaded to remote storage${NC}"
fi 