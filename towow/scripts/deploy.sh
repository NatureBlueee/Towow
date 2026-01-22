#!/bin/bash
# ToWow Deployment Script
# Usage: ./scripts/deploy.sh [command]
# Commands: build, up, down, restart, logs, status, init-db, clean

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables if .env exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Default values
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
APP_NAME="towow"

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Build Docker images
build() {
    log_info "Building Docker images..."
    docker compose -f "$COMPOSE_FILE" build --no-cache
    log_info "Build completed!"
}

# Start services
up() {
    log_info "Starting services..."
    docker compose -f "$COMPOSE_FILE" up -d

    log_info "Waiting for services to be healthy..."
    sleep 5

    # Check health
    health_check
}

# Stop services
down() {
    log_info "Stopping services..."
    docker compose -f "$COMPOSE_FILE" down
    log_info "Services stopped!"
}

# Restart services
restart() {
    log_info "Restarting services..."
    down
    up
}

# Show logs
logs() {
    local service="${1:-}"
    if [ -n "$service" ]; then
        docker compose -f "$COMPOSE_FILE" logs -f "$service"
    else
        docker compose -f "$COMPOSE_FILE" logs -f
    fi
}

# Check service status
status() {
    log_info "Service status:"
    docker compose -f "$COMPOSE_FILE" ps
    echo ""
    health_check
}

# Health check
health_check() {
    log_info "Checking service health..."

    # Check database
    if docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U "${POSTGRES_USER:-towow}" > /dev/null 2>&1; then
        echo -e "  Database: ${GREEN}healthy${NC}"
    else
        echo -e "  Database: ${RED}unhealthy${NC}"
    fi

    # Check API
    local api_port="${APP_PORT:-8000}"
    if curl -sf "http://localhost:$api_port/health" > /dev/null 2>&1; then
        echo -e "  API:      ${GREEN}healthy${NC}"
    else
        echo -e "  API:      ${RED}unhealthy${NC}"
    fi
}

# Initialize database
init_db() {
    log_info "Initializing database..."

    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U "${POSTGRES_USER:-towow}" > /dev/null 2>&1; then
            break
        fi
        attempt=$((attempt + 1))
        sleep 1
    done

    if [ $attempt -eq $max_attempts ]; then
        log_error "Database is not ready after $max_attempts seconds"
        exit 1
    fi

    log_info "Running database initialization..."
    docker compose -f "$COMPOSE_FILE" exec -T app python scripts/init_db.py --drop --sample-data

    log_info "Database initialized!"
}

# Clean up everything (including volumes)
clean() {
    log_warn "This will remove all containers, networks, and volumes!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cleaning up..."
        docker compose -f "$COMPOSE_FILE" down -v --rmi local
        log_info "Cleanup completed!"
    else
        log_info "Cleanup cancelled."
    fi
}

# Show help
show_help() {
    cat << EOF
ToWow Deployment Script

Usage: ./scripts/deploy.sh [command]

Commands:
  build       Build Docker images
  up          Start all services
  down        Stop all services
  restart     Restart all services
  logs [svc]  Show logs (optionally for specific service: app, db)
  status      Show service status
  init-db     Initialize database with schema and sample data
  clean       Remove all containers, networks, and volumes
  help        Show this help message

Examples:
  ./scripts/deploy.sh build      # Build images
  ./scripts/deploy.sh up         # Start services
  ./scripts/deploy.sh logs app   # Show app logs
  ./scripts/deploy.sh init-db    # Initialize database

Environment:
  Copy .env.example to .env and configure before deployment.
EOF
}

# Main entry point
main() {
    cd "$PROJECT_ROOT"

    case "${1:-help}" in
        build)
            build
            ;;
        up)
            up
            ;;
        down)
            down
            ;;
        restart)
            restart
            ;;
        logs)
            logs "${2:-}"
            ;;
        status)
            status
            ;;
        init-db)
            init_db
            ;;
        clean)
            clean
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
