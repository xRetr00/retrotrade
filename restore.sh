#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Please provide backup file path${NC}"
    echo "Usage: ./restore.sh <backup_file.tar.gz>"
    exit 1
fi

BACKUP_FILE=$1
TEMP_DIR="temp_restore"

echo -e "${YELLOW}Starting RetroTrade Restore...${NC}"

# Extract backup
echo "Extracting backup..."
mkdir -p "$TEMP_DIR"
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"
BACKUP_DIR=$(ls "$TEMP_DIR")

# Stop running services
echo "Stopping services..."
docker-compose down

# Restore configuration files
echo "Restoring configuration files..."
cp "$TEMP_DIR/$BACKUP_DIR/.env" .env
cp "$TEMP_DIR/$BACKUP_DIR/docker-compose.yml" docker-compose.yml
cp "$TEMP_DIR/$BACKUP_DIR/prometheus.yml" prometheus.yml

# Start services
echo "Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Restore database
echo "Restoring PostgreSQL database..."
cat "$TEMP_DIR/$BACKUP_DIR/database.sql" | docker-compose exec -T db psql -U postgres retrotrade

# Restore Redis data
echo "Restoring Redis data..."
docker cp "$TEMP_DIR/$BACKUP_DIR/redis-dump.rdb" retrotrade-redis:/data/dump.rdb
docker-compose restart redis

# Restore Grafana dashboards
echo "Restoring Grafana dashboards..."
docker cp "$TEMP_DIR/$BACKUP_DIR/grafana/dashboards" retrotrade-grafana:/var/lib/grafana/
docker-compose restart grafana

# Cleanup
echo "Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

echo -e "${GREEN}Restore completed successfully!${NC}"
echo "Please verify that all services are running correctly:"
echo "Frontend URL: http://localhost"
echo "Grafana URL: http://localhost:3000" 