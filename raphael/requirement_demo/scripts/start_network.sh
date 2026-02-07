#!/bin/bash
#
# Start OpenAgents Network with local mods
#
# This script starts the OpenAgents network with the local mods directory
# in the Python path, allowing custom mods like requirement_network to be loaded.
#
# Usage:
#   ./scripts/start_network.sh
#

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# Change to project directory
cd "$PROJECT_DIR"

# Check if virtual environment exists
if [[ ! -d "venv" ]]; then
    echo "Virtual environment not found. Please create it first:"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Add mods directory to Python path
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)/mods"

log_info "Starting OpenAgents network..."
log_info "PYTHONPATH includes: $(pwd)/mods"
log_info ""
log_info "Network will be available at:"
log_info "  HTTP: http://localhost:8800"
log_info "  gRPC: localhost:8801"
log_info "  Studio: http://localhost:8800/studio"
log_info ""
log_info "Press Ctrl+C to stop the network"
log_info ""

# Start the network
openagents network start .
