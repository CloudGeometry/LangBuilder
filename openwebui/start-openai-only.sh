#!/bin/bash

# ActionBridge - OpenAI Only Startup Script

echo "🚀 Starting ActionBridge with OpenAI-only configuration..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📋 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your OpenAI API key and Google OAuth credentials!"
    echo ""
    echo "Required variables to set in .env:"
    echo "  - OPENAI_API_KEY=sk-your-openai-key"
    echo "  - GOOGLE_CLIENT_ID=your-google-client-id"  
    echo "  - GOOGLE_CLIENT_SECRET=your-google-client-secret"
    echo "  - WEBUI_SECRET_KEY=your-random-secret-key"
    echo ""
    read -p "Press Enter after updating .env file..."
fi

# Check if OpenAI API key is set
if ! grep -q "sk-" .env; then
    echo "❌ OpenAI API key not found in .env file!"
    echo "Please set OPENAI_API_KEY=sk-your-actual-key"
    exit 1
fi

# Create secrets directory
mkdir -p secrets

# Check if Google service account exists
if [ ! -f secrets/google-service-account.json ]; then
    echo "⚠️  Google service account key not found at secrets/google-service-account.json"
    echo "This is needed for Google Workspace employee verification."
    echo "You can continue without it, but only manual user approval will work."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Please add your Google service account JSON file to secrets/google-service-account.json"
        exit 1
    fi
fi

# Make sure corporate config exists
if [ ! -f corporate_config.json ]; then
    echo "📋 Creating corporate_config.json..."
    # corporate_config.json should already exist from our setup
fi

echo ""
echo "🐳 Starting ActionBridge with Docker Compose..."
echo ""

# Start with docker-compose
docker-compose up -d

echo ""
echo "✅ ActionBridge is starting!"
echo ""
echo "📍 Access the application:"
echo "   Web UI: http://localhost:3000"
echo "   API: http://localhost:3000/api/v1"
echo ""
echo "🔐 Authentication:"
echo "   - Go to http://localhost:3000/auth"
echo "   - Click 'Sign in with Google'"
echo "   - Use your @actionbridge.com email"
echo ""
echo "📋 To view logs: docker-compose logs -f actionbridge"
echo "🛑 To stop: docker-compose down"
echo ""

# Show logs
echo "📋 Live logs (press Ctrl+C to exit):"
docker-compose logs -f actionbridge