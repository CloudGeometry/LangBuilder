#!/bin/bash

# LangBuilder Stack Startup Script
# This script kills any processes on the required ports and starts the stack

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Read ports from .env file with fallback defaults
BACKEND_PORT=$(grep '^LANGBUILDER_BACKEND_PORT=' .env 2>/dev/null | cut -d '=' -f2 || echo 8765)
FRONTEND_PORT=$(grep '^VITE_PORT=' .env 2>/dev/null | cut -d '=' -f2 || echo 8766)
OPENWEBUI_PORT=8767

echo -e "${GREEN}Starting LangBuilder Stack...${NC}"

# Function to kill process on a specific port
kill_port() {
    local port=$1
    local process_name=$2

    echo -e "${YELLOW}Checking for processes on port $port...${NC}"

    # Find PIDs using the port
    pids=$(lsof -ti:$port 2>/dev/null || true)

    if [ -n "$pids" ]; then
        echo -e "${YELLOW}Found processes on port $port: $pids${NC}"
        echo -e "${YELLOW}Killing $process_name processes...${NC}"

        # Kill each PID
        for pid in $pids; do
            kill -9 $pid 2>/dev/null || true
            echo -e "${GREEN}Killed process $pid${NC}"
        done

        # Wait a moment for ports to be released
        sleep 1
    else
        echo -e "${GREEN}No processes found on port $port${NC}"
    fi
}

# Kill processes on backend port
kill_port $BACKEND_PORT "backend"

# Kill processes on frontend port
kill_port $FRONTEND_PORT "frontend"

# Check OpenWebUI Docker container
echo -e "${YELLOW}Checking OpenWebUI container...${NC}"
if docker ps | grep -q "open-webui"; then
    echo -e "${GREEN}OpenWebUI is running on port $OPENWEBUI_PORT${NC}"
else
    echo -e "${YELLOW}OpenWebUI is not running. Start it with:${NC}"
    echo -e "  docker start open-webui"
    echo -e "${YELLOW}Or see PORT_CONFIGURATION.md for full setup${NC}"
fi

echo -e "${GREEN}All ports cleared!${NC}"
echo ""
echo -e "${GREEN}Starting backend on port $BACKEND_PORT...${NC}"
echo -e "${YELLOW}Run 'make backend' in one terminal${NC}"
echo ""
echo -e "${GREEN}Starting frontend on port $FRONTEND_PORT...${NC}"
echo -e "${YELLOW}Run 'make frontend' in another terminal${NC}"
echo ""

# Option 1: Start in background (uncomment if you want automatic startup)
# cd "$(dirname "$0")"
# make backend &
# BACKEND_PID=$!
# make frontend &
# FRONTEND_PID=$!
# echo -e "${GREEN}Backend started with PID: $BACKEND_PID${NC}"
# echo -e "${GREEN}Frontend started with PID: $FRONTEND_PID${NC}"
# echo ""
# echo -e "${YELLOW}To stop the stack, run:${NC}"
# echo -e "  kill $BACKEND_PID $FRONTEND_PID"

# Option 2: Interactive prompt (default)
echo -e "${YELLOW}Do you want to start both services now? (y/n)${NC}"
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    cd "$(dirname "$0")"
    echo -e "${GREEN}Starting backend...${NC}"
    make backend &
    BACKEND_PID=$!

    echo -e "${GREEN}Starting frontend...${NC}"
    make frontend &
    FRONTEND_PID=$!

    echo ""
    echo -e "${GREEN}✓ LangBuilder stack started!${NC}"
    echo -e "  Backend PID: $BACKEND_PID (port $BACKEND_PORT)"
    echo -e "  Frontend PID: $FRONTEND_PID (port $FRONTEND_PORT)"
    echo ""
    echo -e "${GREEN}Access the services at:${NC}"
    echo -e "  LangBuilder Frontend: http://localhost:$FRONTEND_PORT"
    echo -e "  LangBuilder Backend:  http://localhost:$BACKEND_PORT"
    echo -e "  OpenWebUI:            http://localhost:$OPENWEBUI_PORT"
    echo ""
    echo -e "${YELLOW}To stop the stack, press Ctrl+C or run:${NC}"
    echo -e "  kill $BACKEND_PID $FRONTEND_PID"
    echo ""

    # Wait for both processes
    wait
else
    echo -e "${YELLOW}Ports cleared. Start services manually with:${NC}"
    echo -e "  Terminal 1: make backend"
    echo -e "  Terminal 2: make frontend"
fi
