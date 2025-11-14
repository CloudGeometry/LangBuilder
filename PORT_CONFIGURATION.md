# Port Configuration Guide

## Sequential Port Assignment: 8765-8766-8767

All services now use sequential ports that are easy to remember and avoid common defaults (3000, 8000, 8080, etc.).

## Port Assignments

| Service | Port | Configuration Location | Status |
|---------|------|----------------------|--------|
| **LangBuilder Backend** | **8765** | `.env` → `LANGBUILDER_BACKEND_PORT`<br>`Makefile` line 16 | ✅ Configured |
| **LangBuilder Frontend** | **8766** | `.env` → `VITE_PORT`<br>`Makefile.frontend` lines 53-58 | ✅ Configured |
| **OpenWebUI** | **8767** | Docker run command `-p 8767:8080` | ✅ Configured |

---

## Configuration Files Updated

### 1. `.env` File
```bash
# Port Configuration - Sequential ports 8765, 8766, 8767
LANGBUILDER_BACKEND_PORT=8765
LANGBUILDER_FRONTEND_PORT=8766
BACKEND_URL=http://localhost:8765

# Vite Frontend Configuration
VITE_PORT=8766
VITE_PROXY_TARGET=http://localhost:8765
```

### 2. `Makefile`
- **Line 16**: Now reads port from `.env` with fallback to 8765
- **Line 239**: Kill command uses dynamic `$(port)` variable

### 3. `Makefile.frontend`
- **Lines 53-58**: `run_frontend` target updated to:
  - Read `VITE_PORT` from `.env` with fallback to 8766
  - Kill processes on configured port and legacy port 3000
  - Export `VITE_PORT` environment variable before calling npm
  - Display which port is starting

---

## OpenWebUI Port Update (Manual Step Required)

OpenWebUI is currently running on **5839** and needs to be restarted on **8767**.

### Stop Current Container
```bash
docker stop open-webui
docker rm open-webui
```

### Start with New Port (8767)
**IMPORTANT:** Use the correct volume name to preserve your data!

```bash
docker run -d \
  --name open-webui \
  -p 8767:8080 \
  -v openwebui_open-webui:/app/backend/data \
  --add-host=host.docker.internal:host-gateway \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

**Note:** The volume name `openwebui_open-webui` preserves your existing data (admin account, settings, chats). Using a different volume name will create a fresh database.

### Start Ollama (if needed)
```bash
docker run -d \
  --name ollama \
  -p 11434:11434 \
  -v ollama:/root/.ollama \
  --restart always \
  ollama/ollama
```

---

## Verification After Restart

### Check All Ports
```bash
# Check what's listening on our ports
lsof -i -P | grep LISTEN | grep -E "8765|8766|8767"
```

**Expected output:**
```
uvicorn   <pid>  user  <fd>  IPv4  <addr>  TCP *:8765 (LISTEN)
node      <pid>  user  <fd>  IPv4  <addr>  TCP localhost:8766 (LISTEN)
```

### Test Services
```bash
# Backend
curl http://localhost:8765/health
# Should return: {"status":"ok"}

# Frontend
open http://localhost:8766

# OpenWebUI
open http://localhost:8767
```

---

## Starting Services with New Ports

### Option 1: Use Makefile
```bash
# Terminal 1: Start backend (will use port 8765 from .env)
make backend

# Terminal 2: Start frontend (will use port 8766 from .env)
make frontend
```

### Option 2: Manual Start
```bash
# Backend on 8765
cd /path/to/langbuilder
uv run uvicorn --factory langbuilder.main:create_app \
  --host 0.0.0.0 \
  --port 8765 \
  --reload

# Frontend on 8766
cd src/frontend
VITE_PORT=8766 npm run dev
```

---

## Updating Published Flows

After changing the backend port from 7860 to 8765, you need to update the Pipe function Valves in OpenWebUI:

### 1. Access OpenWebUI Admin Panel
- Go to http://localhost:8767
- Settings → Functions → LangBuilder Flow Execution Pipe

### 2. Update Valves
Change:
```json
{
  "LANGBUILDER_URL": "http://host.docker.internal:7860"
}
```

To:
```json
{
  "LANGBUILDER_URL": "http://host.docker.internal:8765"
}
```

### 3. Restart OpenWebUI
```bash
docker restart open-webui
```

---

## Troubleshooting

### Port Already in Use
If you get "Address already in use" errors:

```bash
# Find what's using the port
lsof -i :8765
lsof -i :8766
lsof -i :8767

# Kill the process
kill -9 <PID>

# Or use the Makefile (kills 8765 automatically)
make backend
```

### Frontend Not Starting on 8766
Vite might fall back to 3000. Check:
```bash
# Verify .env is being read
grep VITE_PORT .env

# Start with explicit port
cd src/frontend
VITE_PORT=8766 npm run dev
```

### OpenWebUI Can't Connect to LangBuilder
1. Verify backend is running: `curl http://localhost:8765/health`
2. Check Valves in OpenWebUI point to correct port (8765)
3. Ensure `host.docker.internal` works from Docker:
   ```bash
   docker exec open-webui curl http://host.docker.internal:8765/health
   ```

---

## Quick Reference Card

```
┌─────────────────────────────────────┐
│  LangBuilder Stack Ports            │
├─────────────────────────────────────┤
│  Backend:   http://localhost:8765   │
│  Frontend:  http://localhost:8766   │
│  OpenWebUI:  http://localhost:8767  │
└─────────────────────────────────────┘

Easy to remember: 8765-8766-8767
No conflicts with: 3000, 8000, 8080, 5000
```

---

## Configuration Files Reference

| File | What It Controls | Key Settings |
|------|-----------------|--------------|
| `.env` | Backend & Frontend ports | `LANGBUILDER_BACKEND_PORT=8765`<br>`VITE_PORT=8766` |
| `Makefile` | Backend startup | Reads port from `.env` (line 16) |
| `Makefile.frontend` | Frontend startup | Reads and exports `VITE_PORT` (lines 53-58) |
| `vite.config.mts` | Frontend server | Reads `VITE_PORT` env var |
| Docker run command | OpenWebUI port | `-p 8767:8080` |

---

## After Reboot Checklist

- [ ] Start LangBuilder Backend: `make backend` (port 8765)
- [ ] Start LangBuilder Frontend: `make frontend` (port 8766)
- [ ] Start OpenWebUI: Docker auto-starts or manual `docker start open-webui` (port 8767)
- [ ] Verify ports: `lsof -i -P | grep LISTEN | grep -E "8765|8766|8767"`
- [ ] Test each service with curl/browser

**All ports are now static and will persist across reboots!** ✅
