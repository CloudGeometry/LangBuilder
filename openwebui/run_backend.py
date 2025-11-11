#!/usr/bin/env python3
"""
Backend starter with automatic .env loading
"""
import os
import sys
import subprocess
from pathlib import Path

# Change to the correct directory
os.chdir(Path(__file__).parent)

# Load .env file
env_file = Path('.env')
if env_file.exists():
    print("Loading environment variables from .env file...")
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip("'\"")
                    os.environ[key] = value
                    if key == 'GOOGLE_CLIENT_ID':
                        print(f"✓ Google OAuth configured: {value[:30]}...")

# Verify critical variables
if os.environ.get('GOOGLE_CLIENT_ID'):
    print("✅ Google OAuth is configured and ready!")
else:
    print("⚠️  Google OAuth not configured (GOOGLE_CLIENT_ID not set)")

print("\n" + "="*50)
print("Starting OpenWebUI Backend...")
print("Backend API: http://localhost:8000")
print("Frontend UI: http://localhost:5173")
print("="*50 + "\n")

# Start uvicorn
subprocess.run([
    sys.executable, "-m", "uvicorn",
    "open_webui.main:app",
    "--reload",
    "--host", "0.0.0.0",
    "--port", "8000"
])