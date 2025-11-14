#!/bin/bash

# Navigate to the OpenWebUI directory
cd /home/eugene/proj/CG_OpenChatUI/open-webui

echo "🚀 Starting OpenWebUI with Google OAuth..."
echo "======================================"

# Activate virtual environment
source .venv/bin/activate

# Load environment variables (safer method for JSON values)
set -a && source .env && set +a

echo "✓ Google OAuth Client ID: ${GOOGLE_CLIENT_ID:0:30}..."
echo ""

echo "Starting Backend (API Server)..."
echo "Backend will be available at: http://localhost:8000"
echo "API documentation at: http://localhost:8000/docs"
echo ""

# Start the backend
cd backend && ./start-with-oauth.sh