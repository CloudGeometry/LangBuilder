# API Surface

> Generated: 2026-02-09 | LangBuilder v1.6.5

## Overview

| Property | Value |
|----------|-------|
| **API Type** | REST |
| **Framework** | FastAPI (Python) |
| **Base Path** | `/api/v1`, `/api/v2` |
| **Auth Method** | JWT Bearer Token / API Key |
| **Total GET** | 68 |
| **Total POST** | 53 |
| **Total DELETE** | 19 |
| **Total PATCH** | 9 |
| **Total PUT** | 2 |
| **Total WEBSOCKET** | 4 |
| **Total HEAD** | 2 |
| **Total Endpoints** | 157 |

## API Structure

```
app (FastAPI)
├── /api
│   ├── /v1 (main API)
│   │   ├── /build/* (chat/flow execution)
│   │   ├── /flows/* (flow CRUD)
│   │   ├── /users/* (user management)
│   │   ├── /projects/* (project management)
│   │   ├── /folders/* (legacy, redirects to projects)
│   │   ├── /store/* (component store)
│   │   ├── /files/* (file management)
│   │   ├── /variables/* (encrypted variables)
│   │   ├── /api_key/* (API key management)
│   │   ├── /monitor/* (builds, messages, transactions)
│   │   ├── /validate/* (code/prompt validation)
│   │   ├── /publish/* (OpenWebUI publishing)
│   │   ├── /starter-projects/* (starter templates)
│   │   ├── /mcp/* (MCP protocol)
│   │   └── /voice/* (voice mode)
│   └── /v2
│       ├── /files/* (enhanced file management)
│       └── /mcp/* (MCP server management)
├── /health, /health_check (health checks)
├── /logs, /logs-stream (log streaming)
└── /v1/models, /v1/chat/completions (OpenAI-compatible)
```

## Endpoints By Router

### Chat / Build Router
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/chat.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v1/build/{flow_id}/vertices` | Bearer | Retrieve vertices order (deprecated) |
| POST | `/api/v1/build/{flow_id}/flow` | Bearer | Build and process a flow |
| GET | `/api/v1/build/{job_id}/events` | Bearer | Get build events (SSE) |
| POST | `/api/v1/build/{job_id}/cancel` | Bearer | Cancel build job |
| POST | `/api/v1/build/{flow_id}/vertices/{vertex_id}` | Bearer | Build specific vertex (deprecated) |
| GET | `/api/v1/build/{flow_id}/{vertex_id}/stream` | Bearer | Stream vertex build (deprecated) |
| POST | `/api/v1/build_public_tmp/{flow_id}/flow` | None | Build public flow without auth |

### Endpoints Router (Base)
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/endpoints.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/all` | Bearer | Get all component types |
| POST | `/api/v1/run/{flow_id_or_name}` | Bearer/APIKey | Run flow (simplified) |
| POST | `/api/v1/webhook/{flow_id_or_name}` | APIKey | Webhook run flow |
| POST | `/api/v1/run/advanced/{flow_id}` | Bearer/APIKey | Advanced flow execution |
| POST | `/api/v1/predict/{flow_id}` | Bearer | Predict (deprecated) |
| POST | `/api/v1/process/{flow_id}` | Bearer | Process (deprecated) |
| GET | `/api/v1/task/{task_id}` | Bearer | Get task (deprecated) |
| POST | `/api/v1/upload/{flow_id}` | Bearer | Upload file (deprecated) |
| GET | `/api/v1/version` | None | Get version |
| POST | `/api/v1/custom_component` | Bearer | Create custom component |
| POST | `/api/v1/custom_component/update` | Bearer | Update custom component |
| GET | `/api/v1/config` | Bearer | Get configuration |

### Validate Router
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/validate.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v1/validate/code` | Bearer | Validate code |
| POST | `/api/v1/validate/prompt` | Bearer | Validate prompt |

### Store Router
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/store.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/store/check/` | Bearer | Check if store is enabled |
| GET | `/api/v1/store/check/api_key` | Bearer | Check API key |
| POST | `/api/v1/store/components/` | Bearer | Share component |
| PATCH | `/api/v1/store/components/{component_id}` | Bearer | Update shared component |
| GET | `/api/v1/store/components/` | Bearer | Get components list |
| GET | `/api/v1/store/components/{component_id}` | Bearer | Download component |
| GET | `/api/v1/store/tags` | Bearer | Get tags |
| GET | `/api/v1/store/users/likes` | Bearer | Get user likes |
| POST | `/api/v1/store/users/likes/{component_id}` | Bearer | Like component |

### Flows Router
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/flows.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v1/flows/` | Bearer | Create flow |
| GET | `/api/v1/flows/` | Bearer | Read flows (paginated) |
| GET | `/api/v1/flows/{flow_id}` | Bearer | Read single flow |
| GET | `/api/v1/flows/public_flow/{flow_id}` | None | Read public flow |
| PATCH | `/api/v1/flows/{flow_id}` | Bearer | Update flow |
| DELETE | `/api/v1/flows/{flow_id}` | Bearer | Delete flow |
| POST | `/api/v1/flows/batch/` | Bearer | Create multiple flows |
| POST | `/api/v1/flows/upload/` | Bearer | Upload flows from file |
| DELETE | `/api/v1/flows/` | Bearer | Delete multiple flows |
| POST | `/api/v1/flows/download/` | Bearer | Download flows as zip |
| GET | `/api/v1/flows/basic_examples/` | Bearer | Get basic example flows |

### Users Router
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/users.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v1/users/` | None/Bearer | Add user |
| GET | `/api/v1/users/whoami` | Bearer | Get current user |
| GET | `/api/v1/users/` | Superuser | Get all users |
| PATCH | `/api/v1/users/{user_id}` | Superuser | Update user |
| PATCH | `/api/v1/users/{user_id}/reset-password` | Superuser | Reset password |
| DELETE | `/api/v1/users/{user_id}` | Superuser | Delete user |

### API Key Router
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/api_key.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/api_key/` | Bearer | Get API keys |
| POST | `/api/v1/api_key/` | Bearer | Create API key |
| DELETE | `/api/v1/api_key/{api_key_id}` | Bearer | Delete API key |
| POST | `/api/v1/api_key/store` | Bearer | Save store API key |

### Login Router
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/login.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v1/login` | None | Login (get access token) |
| GET | `/api/v1/auto_login` | None | Auto login |
| POST | `/api/v1/refresh` | Bearer | Refresh token |
| POST | `/api/v1/logout` | Bearer | Logout |

### Variables Router
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/variable.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v1/variables/` | Bearer | Create variable |
| GET | `/api/v1/variables/` | Bearer | Read all variables |
| PATCH | `/api/v1/variables/{variable_id}` | Bearer | Update variable |
| DELETE | `/api/v1/variables/{variable_id}` | Bearer | Delete variable |

### Files Router (V1)
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/files.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v1/files/upload/{flow_id}` | Bearer | Upload file |
| GET | `/api/v1/files/download/{flow_id}/{file_name}` | Bearer | Download file |
| GET | `/api/v1/files/images/{flow_id}/{file_name}` | Bearer | Download image |
| GET | `/api/v1/files/profile_pictures/{folder}/{file}` | None | Download profile picture |
| GET | `/api/v1/files/profile_pictures/list` | None | List profile pictures |
| GET | `/api/v1/files/list/{flow_id}` | Bearer | List files |
| DELETE | `/api/v1/files/delete/{flow_id}/{file_name}` | Bearer | Delete file |

### Monitor Router
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/monitor.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/monitor/builds` | Bearer | Get vertex builds |
| DELETE | `/api/v1/monitor/builds` | Bearer | Delete vertex builds |
| GET | `/api/v1/monitor/messages/sessions` | Bearer | Get message sessions |
| GET | `/api/v1/monitor/messages` | Bearer | Get messages |
| DELETE | `/api/v1/monitor/messages` | Bearer | Delete messages |
| PUT | `/api/v1/monitor/messages/{message_id}` | Bearer | Update message |
| PATCH | `/api/v1/monitor/messages/session/{old_session_id}` | Bearer | Update session ID |
| DELETE | `/api/v1/monitor/messages/session/{session_id}` | Bearer | Delete session messages |
| GET | `/api/v1/monitor/transactions` | Bearer | Get transactions |

### Folders Router (Legacy)
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/folders.py`
> All routes redirect to `/api/v1/projects` endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v1/folders/` | Bearer | Create folder (redirect) |
| GET | `/api/v1/folders/` | Bearer | Read folders (redirect) |
| GET | `/api/v1/folders/{folder_id}` | Bearer | Read folder (redirect) |
| PATCH | `/api/v1/folders/{folder_id}` | Bearer | Update folder (redirect) |
| DELETE | `/api/v1/folders/{folder_id}` | Bearer | Delete folder (redirect) |
| GET | `/api/v1/folders/download/{folder_id}` | Bearer | Download folder (redirect) |
| POST | `/api/v1/folders/upload/` | Bearer | Upload folder (redirect) |

### Projects Router
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/projects.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v1/projects/` | Bearer | Create project |
| GET | `/api/v1/projects/` | Bearer | Read projects |
| GET | `/api/v1/projects/{project_id}` | Bearer | Read project |
| PATCH | `/api/v1/projects/{project_id}` | Bearer | Update project |
| DELETE | `/api/v1/projects/{project_id}` | Bearer | Delete project |
| GET | `/api/v1/projects/download/{project_id}` | Bearer | Download project flows |
| POST | `/api/v1/projects/upload/` | Bearer | Upload project from file |

### Publish Router
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/publish.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/publish/flows` | Bearer | Get published flows |
| POST | `/api/v1/publish/openwebui` | Bearer | Publish to OpenWebUI |
| DELETE | `/api/v1/publish/openwebui` | Bearer | Unpublish from OpenWebUI |
| GET | `/api/v1/publish/status/{flow_id}` | Bearer | Get publish status |

### Starter Projects Router
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/starter_projects.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/starter-projects/` | Bearer | Get starter projects |

### MCP Router (V1)
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/mcp.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| HEAD | `/api/v1/mcp/sse` | Bearer | SSE health check |
| GET | `/api/v1/mcp/sse` | Bearer | Handle SSE connection |
| POST | `/api/v1/mcp/` | Bearer | Handle MCP messages |

### MCP Projects Router
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/mcp_projects.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/mcp/project/{project_id}` | Bearer | List project tools |
| HEAD | `/api/v1/mcp/project/{project_id}/sse` | Bearer | SSE health check |
| GET | `/api/v1/mcp/project/{project_id}/sse` | Bearer | Handle project SSE |
| POST | `/api/v1/mcp/project/{project_id}` | Bearer | Handle project messages |
| PATCH | `/api/v1/mcp/project/{project_id}` | Bearer | Update project MCP settings |
| POST | `/api/v1/mcp/project/{project_id}/install` | Bearer | Install MCP config |
| GET | `/api/v1/mcp/project/{project_id}/installed` | Bearer | Check installed MCP servers |

### Voice Mode Router
**File**: `langbuilder/src/backend/base/langbuilder/api/v1/voice_mode.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/voice/elevenlabs/voice_ids` | Bearer | Get ElevenLabs voice IDs |
| WEBSOCKET | `/api/v1/voice/ws/flow_as_tool/{flow_id}` | Bearer | Voice flow as tool |
| WEBSOCKET | `/api/v1/voice/ws/flow_as_tool/{flow_id}/{session_id}` | Bearer | Voice flow as tool (session) |
| WEBSOCKET | `/api/v1/voice/ws/flow_tts/{flow_id}` | Bearer | Voice flow TTS |
| WEBSOCKET | `/api/v1/voice/ws/flow_tts/{flow_id}/{session_id}` | Bearer | Voice flow TTS (session) |

### Files Router (V2)
**File**: `langbuilder/src/backend/base/langbuilder/api/v2/files.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v2/files` | Bearer | Upload user file |
| GET | `/api/v2/files` | Bearer | List files |
| DELETE | `/api/v2/files/batch/` | Bearer | Delete multiple files |
| POST | `/api/v2/files/batch/` | Bearer | Download files as zip |
| GET | `/api/v2/files/{file_id}` | Bearer | Download file |
| PUT | `/api/v2/files/{file_id}` | Bearer | Edit file name |
| DELETE | `/api/v2/files/{file_id}` | Bearer | Delete file |
| DELETE | `/api/v2/files` | Bearer | Delete all files |

### MCP Router (V2)
**File**: `langbuilder/src/backend/base/langbuilder/api/v2/mcp.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v2/mcp/servers` | Bearer | Get MCP servers list |
| GET | `/api/v2/mcp/servers/{server_name}` | Bearer | Get specific server |
| POST | `/api/v2/mcp/servers/{server_name}` | Bearer | Add server |
| PATCH | `/api/v2/mcp/servers/{server_name}` | Bearer | Update server |
| DELETE | `/api/v2/mcp/servers/{server_name}` | Bearer | Delete server |

### Health Check Router
**File**: `langbuilder/src/backend/base/langbuilder/api/health_check_router.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/health` | None | Basic health check |
| GET | `/health_check` | None | Detailed health check |

### Log Router
**File**: `langbuilder/src/backend/base/langbuilder/api/log_router.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/logs-stream` | Bearer | Stream logs (SSE) |
| GET | `/logs` | Bearer | Get logs |

### OpenAI Compatible Router
**File**: `langbuilder/src/backend/base/langbuilder/api/openai_compat_router.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/v1/models` | Bearer/APIKey | List models (OpenAI-compatible) |
| POST | `/v1/chat/completions` | Bearer/APIKey | Chat completions (OpenAI-compatible) |

## Summary By Router

| Router | GET | POST | DELETE | PATCH | PUT | WS | HEAD | Total |
|--------|-----|------|--------|-------|-----|----|------|-------|
| Chat/Build | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 7 |
| Endpoints | 4 | 8 | 0 | 0 | 0 | 0 | 0 | 12 |
| Validate | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 |
| Store | 5 | 2 | 0 | 1 | 0 | 0 | 0 | 9 |
| Flows | 4 | 4 | 2 | 1 | 0 | 0 | 0 | 11 |
| Users | 2 | 1 | 1 | 2 | 0 | 0 | 0 | 6 |
| API Keys | 1 | 2 | 1 | 0 | 0 | 0 | 0 | 4 |
| Login | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 4 |
| Variables | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 4 |
| Files (V1) | 5 | 1 | 1 | 0 | 0 | 0 | 0 | 7 |
| Monitor | 4 | 0 | 3 | 1 | 1 | 0 | 0 | 9 |
| Folders | 3 | 2 | 1 | 1 | 0 | 0 | 0 | 7 |
| Projects | 3 | 2 | 1 | 1 | 0 | 0 | 0 | 7 |
| Publish | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 4 |
| Starter Projects | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| MCP (V1) | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 3 |
| MCP Projects | 3 | 2 | 0 | 1 | 0 | 0 | 1 | 8 |
| Voice Mode | 1 | 0 | 0 | 0 | 0 | 4 | 0 | 5 |
| Files (V2) | 2 | 2 | 3 | 0 | 1 | 0 | 0 | 11 |
| MCP (V2) | 2 | 1 | 1 | 1 | 0 | 0 | 0 | 5 |
| Health | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| Logs | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| OpenAI Compat | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 |
| **Total** | **68** | **53** | **19** | **9** | **2** | **4** | **2** | **157** |

## Authentication Methods

| Method | Description | Usage |
|--------|-------------|-------|
| JWT Bearer Token | OAuth2 password flow | Primary auth for most endpoints |
| API Key | Header-based API key | Programmatic access (run, webhook) |
| Superuser | Bearer token + superuser flag | Admin-only operations |
| None | No authentication required | Health, version, public flows |
