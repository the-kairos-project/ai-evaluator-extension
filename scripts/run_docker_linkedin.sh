#!/bin/bash

# Docker LinkedIn Integration Script
# This script helps manage the Docker setup for LinkedIn integration testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
check_env() {
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from example.env..."
        if [ -f example.env ]; then
            cp example.env .env
            print_status "Please edit .env file and add your LINKEDIN_COOKIE"
        else
            print_error "example.env file not found!"
            exit 1
        fi
    fi
    
    # Source the .env file
    set -a
    source .env
    set +a
    
    # Check for LinkedIn cookie
    if [ -z "$LINKEDIN_COOKIE" ]; then
        print_warning "LINKEDIN_COOKIE not set in .env file"
        print_status "LinkedIn functionality will be limited without a valid cookie"
    else
        print_success "LinkedIn cookie found"
    fi
}

# Build and start services
start_services() {
    print_status "Building and starting Docker services..."
    
    # Build the services
    docker-compose build --no-cache
    
    # Start the services
    docker-compose up -d
    
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    check_services
}

# Check service health
check_services() {
    print_status "Checking service health..."
    
    # Check MCP Server
    if curl -s http://localhost:8000/health > /dev/null; then
        print_success "MCP Server is healthy"
    else
        print_error "MCP Server is not responding"
        return 1
    fi
    
    # Check LinkedIn MCP Server
    if curl -s http://localhost:8081/health > /dev/null; then
        print_success "LinkedIn MCP Server is healthy"
    else
        print_error "LinkedIn MCP Server is not responding"
        return 1
    fi
}

# Run tests
run_tests() {
    print_status "Running integration tests..."
    
    # Install test dependencies
    pip install aiohttp
    
    # Run the test script
    python test_docker_linkedin.py
}

# View logs
view_logs() {
    service=${1:-"all"}
    
    case $service in
        "mcp")
            docker-compose logs -f mcp-server
            ;;
        "linkedin")
            docker-compose logs -f linkedin-mcp
            ;;
        "all"|*)
            docker-compose logs -f
            ;;
    esac
}

# Stop services
stop_services() {
    print_status "Stopping Docker services..."
    docker-compose down
    print_success "Services stopped"
}

# Clean up (remove containers and volumes)
cleanup() {
    print_status "Cleaning up Docker resources..."
    docker-compose down -v --remove-orphans
    docker system prune -f
    print_success "Cleanup complete"
}

# Show usage
usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     - Build and start all services"
    echo "  stop      - Stop all services"
    echo "  restart   - Restart all services"
    echo "  test      - Run integration tests"
    echo "  logs      - View logs (options: mcp, linkedin, all)"
    echo "  status    - Check service health"
    echo "  cleanup   - Stop services and clean up resources"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start              # Start all services"
    echo "  $0 test               # Run tests"
    echo "  $0 logs linkedin      # View LinkedIn service logs"
    echo "  $0 cleanup            # Clean up everything"
}

# Main script logic
main() {
    case ${1:-help} in
        "start")
            check_env
            start_services
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            stop_services
            check_env
            start_services
            ;;
        "test")
            check_env
            run_tests
            ;;
        "logs")
            view_logs $2
            ;;
        "status")
            check_services
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|*)
            usage
            ;;
    esac
}

# Run main function with all arguments
main "$@" 