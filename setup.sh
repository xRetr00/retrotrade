#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to print colored messages
print_message() {
    echo -e "${2}${1}${NC}"
}

# Function to show help message
show_help() {
    echo "RetroTrade Initial Setup Script"
    echo "Usage: ./setup.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -d, --docker     Setup using Docker (recommended)"
    echo "  -l, --local      Setup locally (requires system dependencies)"
    echo "  -h, --help       Show this help message"
    echo ""
    echo "Example:"
    echo "  ./setup.sh --docker    # Setup using Docker"
    echo "  ./setup.sh --local     # Setup locally"
    echo ""
    echo "Note: For deployment and updates, use deploy.sh instead"
}

# Function to check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_message "Docker is not installed. Please install Docker first." "$RED"
        print_message "Visit https://docs.docker.com/get-docker/ for installation instructions." "$YELLOW"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_message "Docker daemon is not running. Please start Docker first." "$RED"
        exit 1
    fi
}

# Function to setup using Docker
setup_docker() {
    print_message "Setting up RetroTrade using Docker..." "$BLUE"
    
    # Check Docker installation
    check_docker
    
    # Create directories
    print_message "Creating necessary directories..." "$YELLOW"
    mkdir -p data/postgres data/redis logs models reports
    
    # Setup configuration files
    if [ ! -f "config/config.yaml" ]; then
        cp config/config.example.yaml config/config.yaml
        print_message "Configuration file created" "$GREEN"
    fi

    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        print_message "Creating .env file with secure defaults..." "$YELLOW"
        cat > .env << EOL
DB_PASSWORD=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 32)
API_KEY=$(openssl rand -base64 32)
GRAFANA_PASSWORD=$(openssl rand -base64 32)
EOL
        print_message ".env file created with random secure passwords" "$GREEN"
    fi
    
    print_message "\nInitial setup completed!" "$GREEN"
    print_message "\nNext steps:" "$YELLOW"
    print_message "1. Review and modify config/config.yaml as needed" "$NC"
    print_message "2. Review and modify .env as needed" "$NC"
    print_message "3. Run ./deploy.sh to build and start the services" "$NC"
}

# Function to setup locally
setup_local() {
    print_message "Setting up RetroTrade locally..." "$BLUE"
    
    # Check required commands
    for cmd in python3 pip npm psql redis-cli; do
        if ! command -v $cmd &> /dev/null; then
            print_message "Error: $cmd is not installed. Please install required dependencies first." "$RED"
            exit 1
        fi
    done
    
    # Create virtual environment
    print_message "Setting up Python environment..." "$YELLOW"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Create directories
    mkdir -p logs data models reports
    
    # Setup configuration
    if [ ! -f "config/config.yaml" ]; then
        cp config/config.example.yaml config/config.yaml
        print_message "Configuration file created" "$GREEN"
    fi
    
    # Setup database
    print_message "Setting up database..." "$YELLOW"
    if ! psql -lqt | cut -d \| -f 1 | grep -qw "trading_data"; then
        createdb trading_data
    fi
    python setup_database.py
    
    # Setup frontend
    print_message "Setting up frontend..." "$YELLOW"
    cd web_interface/frontend
    npm install
    npm run build
    cd ../..
    
    print_message "\nInitial setup completed!" "$GREEN"
    print_message "\nTo start the services:" "$YELLOW"
    print_message "1. Start API: uvicorn web_interface.api:app --host 0.0.0.0 --port 8000" "$NC"
    print_message "2. Start frontend: cd web_interface/frontend && npm start" "$NC"
    print_message "3. Start trading bot: python main.py" "$NC"
}

# Main setup process
main() {
    case "$1" in
        -d|--docker)
            setup_docker
            ;;
        -l|--local)
            setup_local
            ;;
        -h|--help)
            show_help
            ;;
        *)
            print_message "Please specify setup method: --docker (recommended) or --local" "$YELLOW"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with command line arguments
main "$@" 