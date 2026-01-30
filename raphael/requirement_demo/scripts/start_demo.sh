#!/bin/bash
#
# Start Demo Script
#
# This script starts all components needed for the requirement demo:
# 1. AdminAgent - Manages agent invitations
# 2. CoordinatorAgent - Distributes tasks and handles responses
# 3. Web Service (with BridgeAgent) - HTTP API and WebSocket
#
# Prerequisites:
# - OpenAgents network must be running on localhost:8800
# - Python virtual environment with dependencies installed
#
# Usage:
#   ./scripts/start_demo.sh           # Start all components
#   ./scripts/start_demo.sh --sim     # Start web only (simulation mode)
#

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running in simulation mode
SIM_MODE=false
if [[ "$1" == "--sim" ]]; then
    SIM_MODE=true
    log_info "Running in simulation mode (no real agents)"
fi

# Change to project directory
cd "$PROJECT_DIR"

# Check if virtual environment exists
if [[ ! -d "venv" ]]; then
    log_error "Virtual environment not found. Please create it first:"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Load environment variables if .env exists
if [[ -f ".env" ]]; then
    log_info "Loading environment variables from .env"
    export $(grep -v '^#' .env | xargs)
fi

# Function to cleanup on exit
cleanup() {
    log_info "Shutting down..."

    # Kill all background processes
    if [[ -n "$ADMIN_PID" ]]; then
        log_info "Stopping AdminAgent (PID: $ADMIN_PID)"
        kill $ADMIN_PID 2>/dev/null || true
    fi

    if [[ -n "$COORDINATOR_PID" ]]; then
        log_info "Stopping CoordinatorAgent (PID: $COORDINATOR_PID)"
        kill $COORDINATOR_PID 2>/dev/null || true
    fi

    if [[ -n "$WEB_PID" ]]; then
        log_info "Stopping Web Service (PID: $WEB_PID)"
        kill $WEB_PID 2>/dev/null || true
    fi

    log_info "All components stopped"
}

trap cleanup EXIT INT TERM

if [[ "$SIM_MODE" == "false" ]]; then
    # Start AdminAgent
    log_info "Starting AdminAgent..."
    python -m agents.admin_agent &
    ADMIN_PID=$!
    log_info "AdminAgent started (PID: $ADMIN_PID)"

    # Wait for AdminAgent to connect
    sleep 2

    # Start CoordinatorAgent
    log_info "Starting CoordinatorAgent..."
    python -m agents.coordinator_agent &
    COORDINATOR_PID=$!
    log_info "CoordinatorAgent started (PID: $COORDINATOR_PID)"

    # Wait for CoordinatorAgent to connect
    sleep 2

    # Set environment variable to use real agents
    export USE_REAL_AGENTS=true
else
    export USE_REAL_AGENTS=false
fi

# Start Web Service
log_info "Starting Web Service..."
log_info "USE_REAL_AGENTS=$USE_REAL_AGENTS"

uvicorn web.app:app --host 0.0.0.0 --port 8080 --reload &
WEB_PID=$!
log_info "Web Service started (PID: $WEB_PID)"

log_info ""
log_info "=========================================="
log_info "Demo is running!"
log_info "=========================================="
log_info ""
log_info "Web Service: http://localhost:8080"
log_info "API Docs:    http://localhost:8080/docs"
log_info ""
if [[ "$SIM_MODE" == "false" ]]; then
    log_info "Mode: Real Agents (connected to OpenAgents network)"
else
    log_info "Mode: Simulation (no real agents)"
fi
log_info ""
log_info "Press Ctrl+C to stop all components"
log_info ""

# Wait for any process to exit
wait
