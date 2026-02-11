# Capabilities Matrix - LangBuilder v1.6.5

> Generated: 2026-02-09 | LangBuilder v1.6.5

## Overview

This document maps LangBuilder platform capabilities to the four user roles identified from the codebase authentication and authorization layer. Each capability is annotated with its access level per role, derived from endpoint auth requirements and service-layer access control logic.

**Evidence source:** Roles derived from API endpoint auth annotations, `is_superuser` flag on the User model, API key authentication middleware, and unauthenticated endpoint declarations `[CODE]`.

---

## User Roles

### Role Definitions `[CODE]`

| Role | Auth Mechanism | Description | How Identified in Code |
|------|---------------|-------------|----------------------|
| **Regular User** | JWT Bearer token (`Authorization: Bearer <jwt>`) | Authenticated user with a valid account. Owns flows, API keys, variables, and folders. Can create and execute workflows. | `is_active=True`, `is_superuser=False`; validated via `get_current_active_user` dependency |
| **Superuser** | JWT Bearer token + `is_superuser=True` flag | Administrator with elevated privileges. Bypasses all resource-level access control checks. Can manage all users and system resources. | `is_superuser=True` on User model; validated via superuser-gated route dependencies |
| **API Key User** | API Key (`Authorization: Bearer sk-{uuid}` or `x-api-key` header) | Programmatic access bound to a specific user account. Inherits the permissions of the associated user. Scoped primarily to flow execution and webhook endpoints. | Key format `sk-{uuid}`; resolved to user via hashed key lookup in `ApiKey` table |
| **Public/Anonymous** | None required | Unauthenticated access to a limited set of endpoints: health checks, version info, public flows, profile pictures, auto-login. | Endpoints declared with `Auth: None` in router definitions |

---

## Capabilities by Feature Area

### 1. Authentication & Session Management

| Capability | Regular User | Superuser | API Key | Public |
|------------|:----------:|:---------:|:-------:|:------:|
| Login (email/password) | -- | -- | -- | Yes `[CODE: POST /api/v1/login, Auth: None]` |
| Auto-login (single-user mode) | -- | -- | -- | Yes `[CODE: GET /api/v1/auto_login, Auth: None]` |
| Refresh token | Yes | Yes | No | No |
| Logout | Yes | Yes | No | No |
| OAuth2 login (Google, Microsoft, GitHub) | -- | -- | -- | Yes (initiates flow) `[CODE: OpenWebUI OAuth routes]` |
| LDAP authentication | -- | -- | -- | Yes (initiates flow) `[CODE: OpenWebUI LDAP bind]` |

### 2. Flow Management

| Capability | Regular User | Superuser | API Key | Public |
|------------|:----------:|:---------:|:-------:|:------:|
| Create flow | Yes | Yes | No | No |
| Read own flows | Yes | Yes | No | No |
| Read all users' flows | No | Yes | No | No |
| Read public flow | Yes | Yes | No | Yes `[CODE: GET /api/v1/flows/public_flow/{id}, Auth: None]` |
| Update own flow | Yes | Yes | No | No |
| Delete own flow | Yes | Yes | No | No |
| Batch create flows | Yes | Yes | No | No |
| Upload flows from file | Yes | Yes | No | No |
| Download flows as zip | Yes | Yes | No | No |
| Get basic example flows | Yes | Yes | No | No |
| Delete multiple flows | Yes | Yes | No | No |

**Access Control Note** `[CODE]`: Flows have an `access_type` field (`AccessTypeEnum: PRIVATE | PUBLIC`). PRIVATE flows are accessible only by the owner and superusers. PUBLIC flows are accessible by any authenticated user.

### 3. Flow Execution

| Capability | Regular User | Superuser | API Key | Public |
|------------|:----------:|:---------:|:-------:|:------:|
| Build and execute flow (UI) | Yes | Yes | No | No |
| Run flow via API | Yes | Yes | Yes `[CODE: POST /api/v1/run/{id}, Auth: Bearer/APIKey]` | No |
| Run flow via webhook | No | No | Yes `[CODE: POST /api/v1/webhook/{id}, Auth: APIKey]` | No |
| Advanced flow execution | Yes | Yes | Yes `[CODE: POST /api/v1/run/advanced/{id}, Auth: Bearer/APIKey]` | No |
| Build public flow (no auth) | No | No | No | Yes `[CODE: POST /api/v1/build_public_tmp/{id}/flow, Auth: None]` |
| Get build events (SSE) | Yes | Yes | No | No |
| Cancel build job | Yes | Yes | No | No |
| Stream vertex build | Yes | Yes | No | No |

### 4. Project & Folder Organization

| Capability | Regular User | Superuser | API Key | Public |
|------------|:----------:|:---------:|:-------:|:------:|
| Create project/folder | Yes | Yes | No | No |
| Read own projects/folders | Yes | Yes | No | No |
| Update project/folder | Yes | Yes | No | No |
| Delete project/folder | Yes | Yes | No | No |
| Download project flows | Yes | Yes | No | No |
| Upload project from file | Yes | Yes | No | No |

### 5. API Key Management

| Capability | Regular User | Superuser | API Key | Public |
|------------|:----------:|:---------:|:-------:|:------:|
| Create API key | Yes | Yes | No | No |
| List own API keys | Yes | Yes | No | No |
| Delete own API key | Yes | Yes | No | No |
| Save store API key | Yes | Yes | No | No |

### 6. Variable Management (Encrypted Credentials)

| Capability | Regular User | Superuser | API Key | Public |
|------------|:----------:|:---------:|:-------:|:------:|
| Create encrypted variable | Yes | Yes | No | No |
| List own variables (names only) | Yes | Yes | No | No |
| Update variable | Yes | Yes | No | No |
| Delete variable | Yes | Yes | No | No |
| Decrypt variable at runtime | Yes (own flows) | Yes (all flows) | Yes (during flow execution) | No |

**Security Note** `[CODE]`: Variable values are encrypted with AES-GCM at rest. Values are decrypted only in memory during graph execution and are never exposed in API responses or logs.

### 7. User Management

| Capability | Regular User | Superuser | API Key | Public |
|------------|:----------:|:---------:|:-------:|:------:|
| Register new user | -- | -- | -- | Yes `[CODE: POST /api/v1/users/, Auth: None/Bearer]` |
| Get own profile (whoami) | Yes `[CODE: GET /api/v1/users/whoami]` | Yes | No | No |
| List all users | No | Yes `[CODE: GET /api/v1/users/, Auth: Superuser]` | No | No |
| Update any user | No | Yes `[CODE: PATCH /api/v1/users/{id}, Auth: Superuser]` | No | No |
| Reset any user's password | No | Yes `[CODE: PATCH /api/v1/users/{id}/reset-password, Auth: Superuser]` | No | No |
| Delete any user | No | Yes `[CODE: DELETE /api/v1/users/{id}, Auth: Superuser]` | No | No |

### 8. File Management

| Capability | Regular User | Superuser | API Key | Public |
|------------|:----------:|:---------:|:-------:|:------:|
| Upload file (V1, flow-scoped) | Yes | Yes | No | No |
| Download file | Yes | Yes | No | No |
| Download image | Yes | Yes | No | No |
| List files | Yes | Yes | No | No |
| Delete file | Yes | Yes | No | No |
| Upload file (V2, user-scoped) | Yes | Yes | No | No |
| Batch download files (V2) | Yes | Yes | No | No |
| Batch delete files (V2) | Yes | Yes | No | No |
| Edit file name (V2) | Yes | Yes | No | No |
| Delete all own files (V2) | Yes | Yes | No | No |
| View profile pictures | Yes | Yes | Yes | Yes `[CODE: GET /api/v1/files/profile_pictures/*, Auth: None]` |

### 9. Monitoring & Observability

| Capability | Regular User | Superuser | API Key | Public |
|------------|:----------:|:---------:|:-------:|:------:|
| Get vertex builds | Yes | Yes | No | No |
| Delete vertex builds | Yes | Yes | No | No |
| Get message sessions | Yes | Yes | No | No |
| Get messages | Yes | Yes | No | No |
| Update message | Yes | Yes | No | No |
| Delete messages | Yes | Yes | No | No |
| Update session ID | Yes | Yes | No | No |
| Get transactions | Yes | Yes | No | No |
| Stream logs | Yes | Yes | No | No |
| Get logs | Yes | Yes | No | No |

### 10. Publishing (OpenWebUI Integration)

| Capability | Regular User | Superuser | API Key | Public |
|------------|:----------:|:---------:|:-------:|:------:|
| List published flows | Yes | Yes | No | No |
| Publish flow to OpenWebUI | Yes | Yes | No | No |
| Unpublish flow from OpenWebUI | Yes | Yes | No | No |
| Check publish status | Yes | Yes | No | No |

### 11. Component Store

| Capability | Regular User | Superuser | API Key | Public |
|------------|:----------:|:---------:|:-------:|:------:|
| Check store status | Yes | Yes | No | No |
| Check store API key | Yes | Yes | No | No |
| Share component | Yes | Yes | No | No |
| Update shared component | Yes | Yes | No | No |
| Browse components | Yes | Yes | No | No |
| Download component | Yes | Yes | No | No |
| Get store tags | Yes | Yes | No | No |
| Like/unlike component | Yes | Yes | No | No |

### 12. MCP (Model Context Protocol)

| Capability | Regular User | Superuser | API Key | Public |
|------------|:----------:|:---------:|:-------:|:------:|
| SSE connection (V1) | Yes | Yes | No | No |
| Send MCP messages (V1) | Yes | Yes | No | No |
| List project tools | Yes | Yes | No | No |
| Project SSE connection | Yes | Yes | No | No |
| Send project MCP messages | Yes | Yes | No | No |
| Update project MCP settings | Yes | Yes | No | No |
| Install MCP config | Yes | Yes | No | No |
| Check installed MCP servers | Yes | Yes | No | No |
| Manage MCP servers (V2) | Yes | Yes | No | No |

### 13. OpenAI-Compatible API

| Capability | Regular User | Superuser | API Key | Public |
|------------|:----------:|:---------:|:-------:|:------:|
| List models (`/v1/models`) | Yes | Yes | Yes `[CODE: Auth: Bearer/APIKey]` | No |
| Chat completions (`/v1/chat/completions`) | Yes | Yes | Yes `[CODE: Auth: Bearer/APIKey]` | No |

### 14. Voice Mode

| Capability | Regular User | Superuser | API Key | Public |
|------------|:----------:|:---------:|:-------:|:------:|
| Get ElevenLabs voice IDs | Yes | Yes | No | No |
| Voice flow as tool (WebSocket) | Yes | Yes | No | No |
| Voice flow TTS (WebSocket) | Yes | Yes | No | No |

### 15. System & Infrastructure

| Capability | Regular User | Superuser | API Key | Public |
|------------|:----------:|:---------:|:-------:|:------:|
| Health check | Yes | Yes | Yes | Yes `[CODE: GET /health, Auth: None]` |
| Detailed health check | Yes | Yes | Yes | Yes `[CODE: GET /health_check, Auth: None]` |
| Get version | Yes | Yes | Yes | Yes `[CODE: GET /api/v1/version, Auth: None]` |
| Get all component types | Yes | Yes | No | No |
| Get configuration | Yes | Yes | No | No |
| Get starter projects | Yes | Yes | No | No |
| Validate code | Yes | Yes | No | No |
| Validate prompt | Yes | Yes | No | No |
| Create custom component | Yes | Yes | No | No |
| Update custom component | Yes | Yes | No | No |

---

## Permission Model `[CODE]`

### Authorization Logic

The LangBuilder authorization model is flag-based, implemented through boolean fields on the `User` model rather than a formal RBAC system:

```
1. Check is_active flag
   - if is_active = False → DENY ALL ACCESS (account disabled)

2. Check authentication method
   - JWT Bearer token → resolve to User record via token claims
   - API Key (sk-{uuid}) → resolve to User record via hashed key lookup
   - No auth → only public endpoints accessible

3. Check is_superuser flag
   - if is_superuser = True → ALLOW ALL OPERATIONS (bypass access control)

4. Apply resource-level access control
   - Flow access_type = PRIVATE → only owner can access
   - Flow access_type = PUBLIC → any authenticated user can access
   - User-scoped resources (API keys, variables, folders) → only owner can access
```

### Flow Access Control Matrix `[CODE]`

| Flow Access Type | Owner | Other Regular User | Superuser | API Key (owner's) | Public |
|-----------------|:-----:|:-----------------:|:---------:|:-----------------:|:------:|
| `PRIVATE` | Full | No access | Full | Execute only | No access |
| `PUBLIC` | Full | Read + Execute | Full | Execute only | Read only (via public endpoint) |

### Unique Constraints Affecting Permissions `[CODE]`

| Constraint | Models | Business Impact |
|-----------|--------|----------------|
| `UNIQUE(user_id, name)` | Flow, Folder | Users cannot have duplicate flow or folder names within their workspace |
| `UNIQUE(user_id, endpoint_name)` | Flow | Each user's flow endpoints must have unique names |
| `UNIQUE(flow_id, platform, platform_url, status)` | PublishRecord | Prevents duplicate active publications of the same flow |

---

## Permission Examples `[CODE]`

### Example 1: Regular User Creates and Executes a Flow

```
1. POST /api/v1/flows/ (Auth: Bearer JWT)
   → Creates flow with user_id = current_user.id
   → access_type defaults to PRIVATE
   → Constraint: name must be unique for this user

2. POST /api/v1/build/{flow_id}/flow (Auth: Bearer JWT)
   → Service layer checks: flow.user_id == current_user.id (PRIVATE flow)
   → Builds and executes the flow
   → Creates VertexBuild records and TransactionTable entries
```

### Example 2: API Key User Runs a Flow via Webhook

```
1. POST /api/v1/webhook/{flow_id_or_name} (Auth: APIKey)
   → API key resolved to user via hashed lookup in ApiKey table
   → total_uses incremented, last_used_at updated
   → Flow execution proceeds with the key owner's permissions
   → Response returned synchronously
```

### Example 3: Superuser Manages Another User's Resources

```
1. GET /api/v1/users/ (Auth: Bearer JWT, is_superuser=True)
   → Returns list of all users (gated by superuser check)

2. PATCH /api/v1/users/{user_id}/reset-password (Auth: Superuser)
   → Resets target user's password (superuser-only endpoint)

3. GET /api/v1/flows/ (Auth: Bearer JWT, is_superuser=True)
   → Superuser bypasses access_type checks
   → Can view and manage all flows regardless of ownership
```

### Example 4: Public/Anonymous Access

```
1. GET /health (Auth: None)
   → Returns system health status, no credentials required

2. GET /api/v1/version (Auth: None)
   → Returns application version

3. GET /api/v1/flows/public_flow/{flow_id} (Auth: None)
   → Returns flow data only if flow.access_type == PUBLIC
   → No user context available

4. POST /api/v1/build_public_tmp/{flow_id}/flow (Auth: None)
   → Executes a public flow without authentication
   → Limited to flows explicitly marked as PUBLIC
```

---

## Summary: Endpoint Count by Auth Method `[CODE]`

| Auth Method | Endpoint Count | Percentage |
|------------|:--------------:|:----------:|
| Bearer (JWT) only | 131 | 83.4% |
| Bearer or API Key | 6 | 3.8% |
| API Key only | 1 | 0.6% |
| Superuser (Bearer + flag) | 4 | 2.5% |
| None (public) | 11 | 7.0% |
| WebSocket (Bearer) | 4 | 2.5% |
| **Total** | **157** | **100%** |

---

*Generated by CloudGeometry AIx SDLC - Product Analysis*
