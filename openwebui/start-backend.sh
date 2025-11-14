#!/bin/bash

# OpenWebUI Backend Startup Script
# Configured for OpenAI-only usage with corporate auth bypass

echo "Starting Open WebUI Backend..."
echo "Configuration:"
echo "  - Ollama API: Disabled"
echo "  - Corporate Auth: Bypassed for CloudGeometry"
echo "  - OAuth: Fixed for Google login"
echo ""

cd backend

# Load and process environment variables from parent .env file
if [ -f ../.env ]; then
    # First load the .env to get port definitions
    set -o allexport
    source ../.env
    set +o allexport

    # Now create a processed version with expanded variables using envsubst
    envsubst < ../.env > /tmp/processed_backend.env

    # Load the processed version
    set -o allexport
    source /tmp/processed_backend.env
    set +o allexport

    # Clean up
    rm -f /tmp/processed_backend.env
fi

# Set default port if not specified
BACKEND_PORT=${BACKEND_PORT:-8000}

# Set environment variables
export ENABLE_OLLAMA_API=false
export CORPORATE_AUTH_CONFIG=/home/eugene/proj/CG_OpenChatUI/open-webui/corporate_config.json

# Kill any existing processes on the backend port
echo "Checking for existing processes on port ${BACKEND_PORT}..."
if lsof -Pi :${BACKEND_PORT} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "Killing existing process on port ${BACKEND_PORT}..."
    kill -9 $(lsof -Pi :${BACKEND_PORT} -sTCP:LISTEN -t)
    sleep 2
fi

# Start the backend
echo "Starting backend on http://localhost:${BACKEND_PORT}"
../.venv/bin/python -m uvicorn open_webui.main:app \
    --host 0.0.0.0 \
    --port ${BACKEND_PORT} \
    --forwarded-allow-ips '*' \
    --workers 1
