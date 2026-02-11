# Feature Quick Reference - LangBuilder v1.6.5

Quick-lookup table of all 59 cataloged features with category, required user role, primary API surface, and maturity status.

**Version**: 1.6.5 | **Generated**: 2026-02-09

**Status Legend**: **S** = Stable | **B** = Beta | **V** = Verify
**Role Legend**: All = Any authenticated user | Dev = Developer | Admin = Superuser/Admin | Public = No auth required | Ops = Operator/DevOps

---

| # | Feature | Category | User Role | API | Status |
|--:|---------|----------|-----------|-----|:------:|
| 1 | Node-Based Canvas | Visual Workflow Builder | All | `GET/PATCH /api/v1/flows/{id}` | S |
| 2 | Drag-and-Drop Component Placement | Visual Workflow Builder | All | `GET /api/v1/endpoints/custom_component` | S |
| 3 | Edge Connections and Data Flow | Visual Workflow Builder | All | `POST /api/v1/validate/code` | S |
| 4 | Node Configuration Editor | Visual Workflow Builder | All | `POST /api/v1/validate/prompt` | S |
| 5 | Canvas Interaction Controls | Visual Workflow Builder | All | N/A (client-side) | S |
| 6 | DAG Build Execution | Flow Execution Engine | All | `POST /api/v1/build/{id}/flow` | S |
| 7 | Individual Vertex Build | Flow Execution Engine | All | `POST /api/v1/build/{id}/vertices` | S |
| 8 | Server-Sent Events Streaming | Flow Execution Engine | All | `GET /api/v1/build/{id}/events` | S |
| 9 | Build Cancellation | Flow Execution Engine | All | `POST /api/v1/build/{id}/cancel` | S |
| 10 | Public Flow Execution | Flow Execution Engine | Public | `POST /api/v1/build/public/{id}/flow` | S |
| 11 | Multi-Provider LLM Access (28 providers) | AI Model Integration | All | `GET /api/v1/endpoints/custom_component` | S |
| 12 | OpenAI-Compatible API Gateway | AI Model Integration | Dev | `GET /api/v1/openai/models`, `POST /api/v1/openai/chat/completions` | S |
| 13 | Model Parameter Management | AI Model Integration | All | N/A (flow config) | S |
| 14 | Embedding Model Support | AI Model Integration | All | `POST /api/v1/build/{id}/flow` | S |
| 15 | Multi-Backend Vector Storage (13+ backends) | Vector Database Support | All | `POST /api/v1/build/{id}/flow` | S |
| 16 | Document Ingestion and Chunking | Vector Database Support | All | `POST /api/v1/build/{id}/flow` | S |
| 17 | Similarity and Hybrid Search | Vector Database Support | All | `POST /api/v1/build/{id}/flow` | S |
| 18 | Component Registry (96 packages, 12 categories) | Component System | All | `GET /api/v1/endpoints/custom_component` | S |
| 19 | Custom Component Development | Component System | Dev | `POST /api/v1/endpoints/custom_component` | S |
| 20 | Component Store | Component System | All | `GET/POST /api/v1/store/` | S |
| 21 | Code Validation | Component System | All | `POST /api/v1/validate/code`, `POST /api/v1/validate/prompt` | S |
| 22 | Flow CRUD Operations | Project and Flow Management | All | `POST/GET/PATCH/DELETE /api/v1/flows/` | S |
| 23 | Batch Flow Operations | Project and Flow Management | All | `POST /api/v1/flows/batch/` | S |
| 24 | Flow Import and Export | Project and Flow Management | All | `POST /api/v1/flows/upload/`, `GET /api/v1/flows/{id}/download/` | S |
| 25 | Project Organization | Project and Flow Management | All | `POST/GET/PATCH/DELETE /api/v1/projects/` | S |
| 26 | Legacy Folder Support | Project and Flow Management | All | `GET/POST/PATCH/DELETE /api/v1/folders/` | S |
| 27 | Starter Project Templates | Project and Flow Management | All | `GET /api/v1/starter-projects/` | S |
| 28 | Flow Example Library | Project and Flow Management | All | `GET /api/v1/flows/examples/` | S |
| 29 | JWT Authentication | Authentication and Authorization | All | `POST /api/v1/login/`, `POST /api/v1/login/refresh`, `POST /api/v1/login/logout` | S |
| 30 | Auto-Login Mode | Authentication and Authorization | All | `GET /api/v1/login/auto_login` | S |
| 31 | API Key Authentication | Authentication and Authorization | Dev | `POST/GET/DELETE /api/v1/api_key/` | S |
| 32 | OAuth2 Integration (Google, Zoho) | Authentication and Authorization | All | Login router OAuth callbacks | S |
| 33 | LDAP Authentication | Authentication and Authorization | All | `POST /api/v1/login/` (LDAP path) | V |
| 34 | Superuser Administration | Authentication and Authorization | Admin | All admin-scoped endpoints | S |
| 35 | File Upload and Storage (V1) | File Management | All | `POST /api/v1/files/upload` | S |
| 36 | File Download and Retrieval (V1) | File Management | All | `GET /api/v1/files/{id}/download`, `GET /api/v1/files/` | S |
| 37 | Image and Profile Picture Management (V1) | File Management | All | `POST /api/v1/files/images`, `GET /api/v1/files/profile_image/{id}` | S |
| 38 | Enhanced File Operations (V2) | File Management | All | `POST/GET/DELETE /api/v2/files/`, `POST /api/v2/files/batch/` | S |
| 39 | Build Monitoring | Monitoring and Observability | All | `GET /api/v1/monitor/builds` | S |
| 40 | Message History | Monitoring and Observability | All | `GET /api/v1/monitor/messages` | S |
| 41 | Transaction Tracking | Monitoring and Observability | All | `GET /api/v1/monitor/transactions` | S |
| 42 | Session Management | Monitoring and Observability | All | `GET /api/v1/monitor/sessions` | S |
| 43 | Log Streaming | Monitoring and Observability | Admin | `GET /api/v1/logs/stream`, `GET /api/v1/logs/` | B |
| 44 | Third-Party Observability Integration (6 platforms) | Monitoring and Observability | Ops | N/A (env config) | S |
| 45 | MCP Server (V1) | MCP Protocol Support | All | `GET /api/v1/mcp/sse`, `POST /api/v1/mcp/messages` | S |
| 46 | MCP Project Management | MCP Protocol Support | Dev | `GET/POST/PUT /api/v1/mcp/projects/` | S |
| 47 | MCP Server Management (V2) | MCP Protocol Support | Dev | `5 endpoints under /api/v2/mcp/` | B |
| 48 | Voice Mode WebSocket Flows | Voice Interaction | All | `WS /api/v1/voice/ws/{id}`, `GET /api/v1/voice/flows` | B |
| 49 | Voice ID Management | Voice Interaction | All | `GET /api/v1/voice/voices` | B |
| 50 | Voice Flow Configuration | Voice Interaction | Dev | `PUT /api/v1/voice/flows/{id}/config` | B |
| 51 | OpenWebUI Publishing | Publishing and Distribution | Dev | `POST /api/v1/publish/`, `GET /api/v1/publish/status/{id}` | S |
| 52 | Component Store Sharing | Publishing and Distribution | Dev | `POST /api/v1/store/components/`, `GET /api/v1/store/` | S |
| 53 | API Endpoint Exposure | Publishing and Distribution | Dev | `POST /api/v1/endpoints/run/{id}`, `POST /api/v1/endpoints/webhook/{id}` | S |
| 54 | Encrypted Variable Storage | Variable Management | All | `POST/GET/PATCH/DELETE /api/v1/variables/` | S |
| 55 | Environment Variable Fallback | Variable Management | Ops | N/A (runtime resolution) | S |
| 56 | Health Check Endpoints | Configuration and Administration | Ops | `GET /health`, `GET /api/v1/health/` | S |
| 57 | User Administration | Configuration and Administration | Admin | `POST/GET/PATCH/DELETE /api/v1/users/` | S |
| 58 | System Configuration | Configuration and Administration | Ops | N/A (env vars) | S |
| 59 | Database Backend Support (SQLite/PostgreSQL) | Configuration and Administration | Ops | N/A (DATABASE_URL env var) | S |

---

## Summary by Category

| Category | Features | S | B | V |
|----------|:--------:|:-:|:-:|:-:|
| Visual Workflow Builder | 5 | 5 | 0 | 0 |
| Flow Execution Engine | 5 | 5 | 0 | 0 |
| AI Model Integration | 4 | 4 | 0 | 0 |
| Vector Database Support | 3 | 3 | 0 | 0 |
| Component System | 4 | 4 | 0 | 0 |
| Project and Flow Management | 7 | 7 | 0 | 0 |
| Authentication and Authorization | 6 | 5 | 0 | 1 |
| File Management | 4 | 4 | 0 | 0 |
| Monitoring and Observability | 6 | 5 | 1 | 0 |
| MCP Protocol Support | 3 | 2 | 1 | 0 |
| Voice Interaction | 3 | 0 | 3 | 0 |
| Publishing and Distribution | 3 | 3 | 0 | 0 |
| Variable Management | 2 | 2 | 0 | 0 |
| Configuration and Administration | 4 | 4 | 0 | 0 |
| **Total** | **59** | **53** | **5** | **1** |

## Summary by Status

| Status | Count | % |
|--------|:-----:|:-:|
| Stable | 53 | 89.8% |
| Beta | 5 | 8.5% |
| Verify | 1 | 1.7% |

## Summary by User Role

| Role | Primary Features |
|------|:----------------:|
| All (any authenticated) | 38 |
| Dev (developer) | 12 |
| Admin (superuser) | 3 |
| Ops (operator/devops) | 4 |
| Public (no auth) | 1 |
| **Total** | **59** |

---

*Generated: 2026-02-09*
*Source: LangBuilder v1.6.5 codebase inventory analysis*
*Generated by CloudGeometry AIx SDLC - Product Analysis*
