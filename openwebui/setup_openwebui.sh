#!/bin/bash

# Setup script for Open-WebUI with OpenAI API

echo "================================================"
echo "Open-WebUI Local Installation Script"
echo "================================================"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
REQUIRED_VERSION="3.11"

if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
    echo "✓ Found Python 3.12"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    echo "✓ Found Python 3.11"
else
    echo "❌ Error: Python 3.11 or higher is required"
    echo "Please install Python 3.11+ first:"
    echo "  sudo apt update && sudo apt install python3.11 python3.11-venv"
    exit 1
fi

# Create virtual environment
echo ""
echo "Step 1: Creating Python virtual environment..."
if [ -d ".venv" ]; then
    echo "Virtual environment already exists. Removing old one..."
    rm -rf .venv
fi
$PYTHON_CMD -m venv .venv

# Activate virtual environment
echo "Step 2: Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Step 3: Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install Open-WebUI
echo ""
echo "Step 4: Installing Open-WebUI (this may take 5-10 minutes)..."
echo "Installing core dependencies..."
pip install open-webui

# Create .env file for OpenAI API key
echo ""
echo "Step 5: Setting up configuration..."
if [ -f ".env" ]; then
    echo "Backing up existing .env file to .env.backup"
    cp .env .env.backup
fi

# Prompt for OpenAI API key
read -p "Enter your OpenAI API key (or press Enter to set it later): " OPENAI_KEY

if [ ! -z "$OPENAI_KEY" ]; then
    echo "OPENAI_API_KEY=$OPENAI_KEY" > .env
    echo "✓ OpenAI API key saved to .env file"
else
    echo "# Add your OpenAI API key here:" > .env
    echo "OPENAI_API_KEY=your_api_key_here" >> .env
    echo "⚠️  Remember to add your OpenAI API key to the .env file"
fi

# Add other common environment variables
echo "" >> .env
echo "# Server Configuration" >> .env
echo "HOST=0.0.0.0" >> .env
echo "PORT=8000" >> .env
echo "" >> .env
echo "# Optional: Set data directory" >> .env
echo "DATA_DIR=./data" >> .env

# Create start script
echo ""
echo "Step 6: Creating start script..."
cat > start_openwebui.sh << 'EOF'
#!/bin/bash
echo "Starting Open-WebUI server..."
source .venv/bin/activate

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start the server
open-webui serve --host ${HOST:-0.0.0.0} --port ${PORT:-8000}
EOF

chmod +x start_openwebui.sh

echo ""
echo "================================================"
echo "✓ Installation Complete!"
echo "================================================"
echo ""
echo "To start Open-WebUI:"
echo "  1. Make sure your OpenAI API key is set in .env file"
echo "  2. Run: ./start_openwebui.sh"
echo ""
echo "The server will be available at:"
echo "  - http://localhost:8000"
echo "  - http://0.0.0.0:8000 (accessible from other devices on your network)"
echo ""
echo "To manually start the server:"
echo "  source .venv/bin/activate"
echo "  open-webui serve"
echo ""
echo "For more configuration options, check the .env file"
echo "================================================"