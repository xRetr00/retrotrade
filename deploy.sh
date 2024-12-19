#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Starting RetroTrade Deployment...${NC}"

# Enable BuildKit for better performance and caching
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Creating .env file..."
    cat > .env << EOL
DB_PASSWORD=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 32)
API_KEY=$(openssl rand -base64 32)
GRAFANA_PASSWORD=$(openssl rand -base64 32)
EOL
    echo -e "${GREEN}.env file created with random secure passwords${NC}"
fi

# Load environment variables
source .env

# Check Docker and Docker Compose installation
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Enable BuildKit globally if not already enabled
if [ ! -f "/etc/docker/daemon.json" ] || ! grep -q "buildkit" "/etc/docker/daemon.json"; then
    echo -e "${YELLOW}Enabling Docker BuildKit globally...${NC}"
    sudo mkdir -p /etc/docker
    echo '{
    "features": {
        "buildkit": true
    }
}' | sudo tee /etc/docker/daemon.json > /dev/null
    # Restart Docker daemon to apply changes
    if command -v systemctl &> /dev/null; then
        sudo systemctl restart docker
    else
        sudo service docker restart
    fi
fi

# Stop any running containers
echo "Stopping existing containers..."
docker-compose down

# Pull latest changes
echo "Pulling latest changes..."
git pull

# Build and start containers with BuildKit enabled
echo "Building and starting containers with optimized caching..."
DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 docker-compose up -d --build

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Check service health
check_service() {
    if docker-compose ps | grep -q "$1.*running"; then
        echo -e "${GREEN}✓ $1 is running${NC}"
    else
        echo -e "${RED}✗ $1 failed to start${NC}"
        exit 1
    fi
}

check_service "retrotrade-backend"
check_service "retrotrade-frontend"
check_service "retrotrade-db"
check_service "retrotrade-redis"
check_service "retrotrade-prometheus"
check_service "retrotrade-grafana"

# Initialize database
echo "Initializing database..."
docker-compose exec backend python setup_database.py

# Setup monitoring
echo "Setting up monitoring..."
docker-compose exec grafana grafana-cli plugins install grafana-piechart-panel

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "Frontend URL: http://localhost"
echo -e "Grafana URL: http://localhost:3000"
echo -e "Default Grafana credentials:"
echo -e "Username: admin"
echo -e "Password: ${GRAFANA_PASSWORD}"

echo -e "\n${YELLOW}Useful commands:${NC}"
echo -e "- View logs: docker-compose logs -f"
echo -e "- Stop services: docker-compose down"
echo -e "- Restart services: docker-compose restart"
echo -e "- Rebuild with cache: DOCKER_BUILDKIT=1 docker-compose build"
echo -e "- Clean build cache: docker builder prune" 