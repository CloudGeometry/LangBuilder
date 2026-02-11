# Service Catalog

> Generated: 2026-02-09 | LangBuilder v1.6.5

> **Terminology Note**: This catalog lists **deployable application units** (services you can run independently).
> Internal service classes (e.g., backend component packages, frontend stores) are counted separately
> in `technology-stack.md` under module counts.

**Summary**: 4 deployable services

## LangBuilder Backend

- **Type**: Backend API
- **Stack**: Python >=3.10, FastAPI >=0.115.2
- **Location**: `langbuilder/src/backend/`
- **Entry Point**: `langbuilder/src/backend/base/langbuilder/main.py`
- **Port**: 7860 (default)
- **API**: REST API (v1, v2) with 157 endpoints
- **Database**: SQLModel ORM, SQLite (dev) / PostgreSQL (prod)
- **README**: Yes

### Key Capabilities
- Flow/workflow execution engine (graph processing)
- 96 pluggable component packages (LLM providers, vector stores, tools)
- Custom component infrastructure with lazy loading
- OpenAI-compatible API endpoint
- MCP (Model Context Protocol) server support
- Voice mode with WebSocket streaming
- File management and document processing
- User management with JWT authentication

---

## LangBuilder Frontend

- **Type**: Frontend SPA
- **Stack**: TypeScript 5.4.5, React 18.3.1
- **Location**: `langbuilder/src/frontend/`
- **Entry Point**: `langbuilder/src/frontend/src/App.tsx`
- **Port**: 3000 (dev)
- **Build Tool**: Vite 5.4.19 with SWC
- **README**: Yes

### Key Capabilities
- Visual flow/graph editor (React Flow)
- Component store browser
- 16 Zustand state management stores
- 135 reusable UI components
- Real-time streaming responses
- Dark mode support
- Keyboard shortcuts system
- File and knowledge base management

---

## OpenWebUI Backend

- **Type**: Backend API
- **Stack**: Python, FastAPI
- **Location**: `openwebui/backend/`
- **Entry Point**: `openwebui/backend/open_webui/main.py`
- **Port**: 8767 (default)
- **Database**: SQLite (default)
- **README**: Yes

### Key Capabilities
- Chat interface backend for published LangBuilder flows
- Corporate authentication (Google Workspace, Zoho OAuth)
- User and session management
- Integration bridge between LangBuilder and chat UI

---

## OpenWebUI Frontend

- **Type**: Frontend SPA
- **Stack**: TypeScript, Svelte
- **Location**: `openwebui/src/`
- **Entry Point**: `openwebui/src/app.html`
- **Port**: 5175 (dev)
- **README**: Yes

### Key Capabilities
- Chat-style interface for interacting with published flows
- User authentication UI
- Session management

---

## Internal Module Counts

> For reference only - these are NOT separate deployable services.

| Application | Module Type | Count |
|-------------|-------------|-------|
| LangBuilder Backend | Component packages | 96 |
| LangBuilder Backend | API routers | 23 |
| LangBuilder Backend | Database models | 10 |
| LangBuilder Frontend | React components | 135+ directories |
| LangBuilder Frontend | Zustand stores | 16 |
| LangBuilder Frontend | Page routes | ~20 |
| LangBuilder Frontend | Modal components | 30 |
| LangBuilder Frontend | Icon components | 139 |
