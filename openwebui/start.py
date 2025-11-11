#!/usr/bin/env python3
"""
Start OpenWebUI backend with proper environment loading
"""
import os
import sys
import subprocess
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_dir))

# Change to the backend directory
os.chdir(backend_dir)

# Load environment variables using python-dotenv
from dotenv import load_dotenv
# Load .env from parent directory
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Verify critical variables
google_client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
if google_client_id:
    print(f"✅ Google OAuth configured: {google_client_id[:30]}...")
else:
    print("⚠️  Google OAuth not configured")

print("\n" + "="*60)
print("Starting OpenWebUI Backend...")
print(f"Working directory: {os.getcwd()}")
print(f"Database path: {os.path.join(os.getcwd(), 'data/webui.db')}")
print("Backend API: http://localhost:8000")
print("Frontend UI: http://localhost:5173")
print("="*60 + "\n")

# Start uvicorn
try:
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "open_webui.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
    ])
except KeyboardInterrupt:
    print("\n✅ Backend stopped")
    sys.exit(0)