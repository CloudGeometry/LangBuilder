#!/bin/bash

# Navigate to the OpenWebUI directory
cd /home/eugene/proj/CG_OpenChatUI/open-webui

echo "🎨 Starting OpenWebUI Frontend..."
echo "================================="

# Load and process environment variables (safer method for JSON values)
if [ -f .env ]; then
    # First load the .env to get port definitions
    set -a && source .env && set +a

    # Now create a processed version with expanded variables using envsubst
    envsubst < .env > /tmp/processed_frontend.env

    # Load the processed version
    set -a && source /tmp/processed_frontend.env && set +a

    # Clean up
    rm -f /tmp/processed_frontend.env
fi

# Set default ports if not specified
FRONTEND_PORT=${FRONTEND_PORT:-5173}
BACKEND_PORT=${BACKEND_PORT:-8000}

echo "Frontend will be available at: http://localhost:${FRONTEND_PORT}"
echo "Make sure the backend is running on: http://localhost:${BACKEND_PORT}"
echo ""

# Start the frontend with optimized Pyodide caching
npm run dev -- --port ${FRONTEND_PORT}