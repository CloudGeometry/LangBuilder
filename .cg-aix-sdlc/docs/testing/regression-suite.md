# Regression Test Suite - LangBuilder v1.6.5

## Document Information

**Version**: 1.6.5
**Last Updated**: 2026-02-09
**Owner**: QA Team
**Related Documents**:
- [Test Inventory](./test-inventory.md)
- [Feature Catalog](../product/feature-catalog.md)
- [API Surface](../inventory/api-surface.md)

---

## 1. Regression Suite Overview

### 1.1 Purpose and Scope

This document defines the critical regression test suite that MUST pass before any LangBuilder release. The regression suite ensures:

- **Core Functionality Integrity**: Essential user workflows remain functional after code changes
- **Data Persistence Stability**: Critical data operations preserve integrity across deployments
- **API Contract Compliance**: Backend endpoints maintain expected behavior and response formats
- **Performance Baselines**: System performance does not degrade below acceptable thresholds
- **Security Controls**: Authentication, authorization, and data isolation remain intact

The regression suite focuses on **end-user critical paths** rather than comprehensive feature coverage. These tests represent the minimum viable functionality required for production deployment.

### 1.2 When to Execute

| Trigger Event | Scope | Required Pass Rate |
|---------------|-------|-------------------|
| **Pre-Release** | Full suite (P0 + P1 + P2) | 100% P0, 95% P1, 90% P2 |
| **Post-Deployment** | Critical path (P0 only) | 100% P0 |
| **After Major Changes** | Relevant subsections | 100% affected P0 tests |
| **Nightly CI/CD** | Full suite | 100% P0, 90% P1 |
| **Database Migration** | Data integrity tests (REG-030 series) | 100% |

### 1.3 Execution Time Targets

| Suite Level | Target Duration | Actual Average | Status |
|-------------|----------------|----------------|--------|
| P0 Critical Path | ≤ 10 minutes | ~8 minutes | ✅ On target |
| P0 + P1 Combined | ≤ 25 minutes | ~22 minutes | ✅ On target |
| Full Suite (P0+P1+P2) | ≤ 45 minutes | ~38 minutes | ✅ On target |
| Performance Tests Only | ≤ 15 minutes | ~12 minutes | ✅ On target |

### 1.4 Test Environment Requirements

- **Python**: 3.10-3.13
- **Node.js**: 18.x or 20.x
- **Database**: SQLite (dev) or PostgreSQL (staging/prod)
- **Dependencies**: All packages from `pyproject.toml` and `package.json`
- **Test Data**: Fresh database with seeded test users and sample flows
- **External Services**: Mock OpenAI API (or test API key with rate limits)

---

## 2. Critical Path Tests (P0 - Must Pass)

These tests represent the absolute minimum functionality required for LangBuilder to be usable. **All P0 tests MUST pass before any production release.**

### REG-001: User Login and Authentication Flow

**Priority**: P0
**Automated**: Yes
**Test Type**: Integration (API + UI)
**Estimated Duration**: 90 seconds

**Description**: Verify that users can successfully authenticate using JWT-based login and maintain session state across requests.

**Test Steps**:
1. Send POST request to `/api/v1/login` with valid credentials
2. Verify 200 OK response with JWT access token
3. Extract `access_token` from response body
4. Send GET request to `/api/v1/auto_login` with token in Authorization header
5. Verify 200 OK response with user profile data
6. Attempt protected endpoint access without token
7. Verify 401 Unauthorized response
8. Attempt access with expired token
9. Verify 401 Unauthorized response

**Expected Result**:
- Valid credentials return JWT token with 24-hour expiration
- Token authenticates subsequent requests to protected endpoints
- Requests without valid token are rejected with 401 status
- User profile includes `id`, `username`, `is_active`, `is_superuser`

**Test Coverage**:
- `POST /api/v1/login` (authentication)
- `GET /api/v1/auto_login` (token validation)
- JWT token generation and validation logic
- User session management

---

### REG-002: Create New Flow and Save

**Priority**: P0
**Automated**: Yes
**Test Type**: Integration (API + UI)
**Estimated Duration**: 60 seconds

**Description**: Verify that authenticated users can create a new flow, add initial data, and persist it to the database.

**Test Steps**:
1. Authenticate as test user and obtain JWT token
2. Send POST request to `/api/v1/flows/` with flow metadata:
   ```json
   {
     "name": "Test Regression Flow",
     "description": "Automated regression test flow",
     "data": {"nodes": [], "edges": []},
     "folder_id": null
   }
   ```
3. Verify 201 Created response with generated `flow_id`
4. Extract `flow_id` from response
5. Send GET request to `/api/v1/flows/{flow_id}`
6. Verify response contains matching name, description, and empty canvas data
7. Verify `user_id` matches authenticated user
8. Verify `created_at` and `updated_at` timestamps are set

**Expected Result**:
- Flow is created with unique UUID identifier
- Flow data is persisted to database
- Flow is associated with correct user
- Empty canvas state is valid JSON: `{"nodes": [], "edges": []}`

**Test Coverage**:
- `POST /api/v1/flows/` (create flow)
- `GET /api/v1/flows/{flow_id}` (retrieve flow)
- Database flow insertion and retrieval
- User-flow ownership association

---

### REG-003: Add Nodes to Canvas and Connect Them

**Priority**: P0
**Automated**: Partial (API automated, UI manual)
**Test Type**: Integration (API + UI)
**Estimated Duration**: 120 seconds

**Description**: Verify that users can add component nodes to the canvas, configure them, and create valid edge connections representing data flow.

**Test Steps**:
1. Create a test flow using REG-002 process
2. Update flow data with two nodes (ChatInput and ChatOutput):
   ```json
   {
     "nodes": [
       {
         "id": "ChatInput-001",
         "type": "genericNode",
         "position": {"x": 100, "y": 100},
         "data": {
           "type": "ChatInput",
           "node": {"display_name": "Chat Input"}
         }
       },
       {
         "id": "ChatOutput-001",
         "type": "genericNode",
         "position": {"x": 400, "y": 100},
         "data": {
           "type": "ChatOutput",
           "node": {"display_name": "Chat Output"}
         }
       }
     ],
     "edges": [
       {
         "id": "edge-001",
         "source": "ChatInput-001",
         "target": "ChatOutput-001",
         "sourceHandle": "message_response",
         "targetHandle": "message"
       }
     ]
   }
   ```
3. Send PATCH request to `/api/v1/flows/{flow_id}` with updated data
4. Verify 200 OK response
5. Send GET request to `/api/v1/flows/{flow_id}`
6. Verify nodes and edges are persisted correctly
7. Send POST request to `/api/v1/validate/code` with flow_id
8. Verify validation returns success (no errors)

**Expected Result**:
- Canvas data with 2 nodes and 1 edge is saved
- Node positions, types, and configurations are preserved
- Edge connection between compatible handles is valid
- Flow validation confirms graph integrity

**Test Coverage**:
- `PATCH /api/v1/flows/{flow_id}` (update flow)
- `POST /api/v1/validate/code` (validate flow graph)
- Canvas state serialization/deserialization
- Edge type compatibility validation

---

### REG-004: Execute a Simple Flow (Build + Run)

**Priority**: P0
**Automated**: Yes
**Test Type**: Integration (Full Stack)
**Estimated Duration**: 180 seconds

**Description**: Verify that a valid flow can be executed end-to-end with DAG build and successful output generation.

**Test Steps**:
1. Create a simple flow with ChatInput → ChatOutput (from REG-003)
2. Send POST request to `/api/v1/build/{flow_id}/flow` with input data:
   ```json
   {
     "inputs": {
       "ChatInput-001": {
         "message": "Hello, this is a regression test."
       }
     }
   }
   ```
3. Monitor SSE event stream at `/api/v1/build/{flow_id}/events`
4. Verify events received in order:
   - `build_started`
   - `vertex_build_started` (for each node)
   - `vertex_build_completed` (for each node)
   - `build_completed`
5. Verify final event contains output data from ChatOutput node
6. Verify execution completes within 30 seconds
7. Verify no error events are emitted

**Expected Result**:
- Flow builds successfully without errors
- All vertices execute in dependency order
- ChatOutput receives and returns the input message
- SSE events provide real-time progress updates
- Final output matches expected structure

**Test Coverage**:
- `POST /api/v1/build/{flow_id}/flow` (trigger build)
- `GET /api/v1/build/{flow_id}/events` (SSE streaming)
- DAG dependency resolution
- Vertex execution engine
- Real-time event streaming

---

### REG-005: Chat Interface with Streaming Response

**Priority**: P0
**Automated**: Yes
**Test Type**: Integration (API + WebSocket)
**Estimated Duration**: 150 seconds

**Description**: Verify that the chat interface can execute a flow with LLM streaming and deliver token-by-token responses.

**Test Steps**:
1. Create a flow: ChatInput → OpenAI LLM → ChatOutput
2. Configure OpenAI node with valid API key or mock
3. Send POST request to `/api/v1/build/{flow_id}/flow` with chat message:
   ```json
   {
     "inputs": {
       "ChatInput-001": {
         "message": "Say 'Hello World' and nothing else."
       }
     },
     "stream": true
   }
   ```
4. Connect to SSE stream at `/api/v1/build/{flow_id}/events`
5. Verify streaming events include:
   - `token` events with partial response chunks
   - `chunk` events with accumulated text
6. Verify final message contains "Hello World"
7. Verify total execution time < 10 seconds
8. Verify stream closes cleanly after completion

**Expected Result**:
- LLM node streams tokens progressively
- SSE delivers real-time token chunks to client
- Full response is assembled correctly
- Stream terminates properly after completion

**Test Coverage**:
- LLM component streaming execution
- SSE token streaming to frontend
- Chat interface flow pattern
- Stream lifecycle management

---

### REG-006: OpenAI-Compatible Endpoint Works

**Priority**: P0
**Automated**: Yes
**Test Type**: Integration (API)
**Estimated Duration**: 90 seconds

**Description**: Verify that the OpenAI-compatible chat completion endpoint can execute flows using the standard OpenAI API format.

**Test Steps**:
1. Create a flow configured as a chat endpoint (with endpoint_name set)
2. Send POST request to `/v1/chat/completions` with OpenAI-format payload:
   ```json
   {
     "model": "flow/{flow_id}",
     "messages": [
       {"role": "user", "content": "Test message for regression"}
     ],
     "stream": false
   }
   ```
3. Verify 200 OK response
4. Verify response format matches OpenAI schema:
   ```json
   {
     "id": "chatcmpl-xxx",
     "object": "chat.completion",
     "created": 1234567890,
     "model": "flow/{flow_id}",
     "choices": [
       {
         "index": 0,
         "message": {
           "role": "assistant",
           "content": "..."
         },
         "finish_reason": "stop"
       }
     ]
   }
   ```
5. Test with `stream: true` and verify SSE format
6. Verify flow execution triggered correctly

**Expected Result**:
- Endpoint accepts OpenAI-compatible request format
- Response conforms to OpenAI schema
- Flow executes with correct input mapping
- Streaming mode returns SSE-formatted chunks

**Test Coverage**:
- `POST /v1/chat/completions` (OpenAI compatibility)
- Flow execution via endpoint routing
- Request/response format translation
- Streaming and non-streaming modes

---

### REG-007: Project CRUD Operations

**Priority**: P0
**Automated**: Yes
**Test Type**: Integration (API)
**Estimated Duration**: 120 seconds

**Description**: Verify that projects (folders) can be created, listed, updated, and deleted with proper flow association.

**Test Steps**:
1. Send POST request to `/api/v1/projects/` to create project:
   ```json
   {
     "name": "Regression Test Project",
     "description": "Automated test project"
   }
   ```
2. Verify 201 Created with generated `project_id`
3. Send GET request to `/api/v1/projects/` to list all projects
4. Verify new project appears in list
5. Create a flow and associate it with the project:
   - POST to `/api/v1/flows/` with `folder_id: project_id`
6. Send GET request to `/api/v1/projects/{project_id}`
7. Verify project details include associated flow
8. Send PATCH request to update project name
9. Verify update succeeds
10. Send DELETE request to `/api/v1/projects/{project_id}`
11. Verify 200 OK response
12. Verify project no longer appears in list
13. Verify associated flow's `folder_id` is set to null

**Expected Result**:
- Projects can be created with unique IDs
- Project list returns all user's projects
- Flows can be associated with projects
- Project updates persist correctly
- Project deletion handles flow associations gracefully

**Test Coverage**:
- `POST /api/v1/projects/` (create)
- `GET /api/v1/projects/` (list)
- `GET /api/v1/projects/{id}` (retrieve)
- `PATCH /api/v1/projects/{id}` (update)
- `DELETE /api/v1/projects/{id}` (delete)
- Project-flow relationships

---

### REG-008: Database Migration Integrity

**Priority**: P0
**Automated**: Yes
**Test Type**: Integration (Database)
**Estimated Duration**: 180 seconds

**Description**: Verify that Alembic migrations can be applied cleanly to a fresh database and that schema matches expected structure.

**Test Steps**:
1. Drop existing test database
2. Create fresh empty database
3. Run `alembic upgrade head` to apply all migrations
4. Verify migration completes without errors
5. Inspect database schema:
   - Verify all 10 expected tables exist: `user`, `flow`, `folder`, `apikey`, `message`, `variable`, `file`, `credential`, `vertexbuild`, `transaction`
6. Verify primary keys and foreign keys are correct
7. Verify indexes exist on frequently queried columns
8. Create test data: 1 user, 1 project, 1 flow
9. Verify data insertion succeeds
10. Run `alembic downgrade -1` (rollback one version)
11. Verify rollback succeeds
12. Run `alembic upgrade +1` (re-apply)
13. Verify test data still exists

**Expected Result**:
- All migrations apply cleanly to empty database
- Schema matches expected structure from SQLModel definitions
- Foreign key constraints are enforced
- Rollback and re-migration preserve data integrity

**Test Coverage**:
- Alembic migration system
- Database schema generation
- Data model integrity
- Migration reversibility

---

## 3. High Priority Tests (P1 - Should Pass)

These tests cover important features that most users rely on daily. **95% of P1 tests should pass** before release.

### REG-010: Component Discovery and Loading

**Priority**: P1
**Automated**: Yes
**Test Type**: Integration (API)
**Estimated Duration**: 60 seconds

**Description**: Verify that the backend can discover and load all 96 component packages across 12 categories.

**Test Steps**:
1. Send GET request to `/api/v1/endpoints/custom_component`
2. Verify response contains component list
3. Verify component count ≥ 96 packages
4. Verify all 12 categories present:
   - agents, embeddings, helpers, inputs, llms, memories, outputs, prompts, retrievers, text_splitters, tools, vector_stores
5. Verify each component has required fields:
   - `display_name`, `description`, `template`, `input_types`, `output_types`
6. Pick 5 random components and verify their templates are valid JSON
7. Verify component icons/logos load correctly

**Expected Result**:
- All component packages are discovered
- Component metadata is complete and valid
- Templates contain correct schema definitions
- Categories are properly assigned

**Test Coverage**:
- Component discovery system
- Component metadata generation
- Template schema validation
- Category organization

---

### REG-011: Custom Component Upload and Use

**Priority**: P1
**Automated**: Partial
**Test Type**: Integration (API + Execution)
**Estimated Duration**: 180 seconds

**Description**: Verify that users can upload custom Python components and use them in flows.

**Test Steps**:
1. Prepare a custom component Python file:
   ```python
   from langbuilder.base_component import Component

   class CustomRegressTest(Component):
       display_name = "Custom Regression Test"
       description = "A test custom component"

       def build(self, text: str) -> str:
           return f"Processed: {text}"
   ```
2. Send POST request to `/api/v1/custom_component/upload` with file
3. Verify 201 Created response with component_id
4. Send GET request to `/api/v1/custom_component/` to list components
5. Verify new component appears in list
6. Create a flow using the custom component
7. Execute the flow with test input
8. Verify custom component executes correctly
9. Verify output matches expected format: "Processed: {input}"

**Expected Result**:
- Custom component uploads successfully
- Component is validated for security
- Component appears in component library
- Component can be used in flows
- Component executes correctly

**Test Coverage**:
- `POST /api/v1/custom_component/upload` (upload)
- `GET /api/v1/custom_component/` (list)
- Custom component validation
- Custom component execution
- Security checks for uploaded code

---

### REG-012: Flow Import/Export

**Priority**: P1
**Automated**: Yes
**Test Type**: Integration (API)
**Estimated Duration**: 90 seconds

**Description**: Verify that flows can be exported as JSON and re-imported without data loss.

**Test Steps**:
1. Create a complex flow with 5+ nodes and connections
2. Send GET request to `/api/v1/flows/{flow_id}/download` or export via UI
3. Verify response contains complete flow JSON with:
   - Flow metadata (name, description)
   - Canvas data (nodes, edges)
   - Component configurations
4. Save exported JSON to file
5. Delete the original flow
6. Send POST request to `/api/v1/flows/upload` with exported JSON
7. Verify new flow is created with different flow_id
8. Compare imported flow data with original export
9. Verify all nodes, edges, and configurations match
10. Verify imported flow is executable

**Expected Result**:
- Export captures complete flow state
- Import recreates flow accurately
- Component configurations are preserved
- Imported flow executes identically to original

**Test Coverage**:
- Flow export/serialization
- Flow import/deserialization
- Data integrity across export/import
- Flow portability

---

### REG-013: API Key Management (Create/Revoke)

**Priority**: P1
**Automated**: Yes
**Test Type**: Integration (API)
**Estimated Duration**: 90 seconds

**Description**: Verify that users can create API keys for programmatic access and revoke them to invalidate access.

**Test Steps**:
1. Send POST request to `/api/v1/api_key/` to create new API key:
   ```json
   {
     "name": "Regression Test Key"
   }
   ```
2. Verify 201 Created with API key in response
3. Extract API key value (only shown once)
4. Attempt authenticated request using API key in header:
   - `x-api-key: {api_key_value}`
5. Verify request succeeds with 200 OK
6. Send GET request to `/api/v1/api_key/` to list keys
7. Verify test key appears in list (hashed)
8. Send DELETE request to `/api/v1/api_key/{key_id}` to revoke
9. Verify 200 OK response
10. Attempt authenticated request with revoked key
11. Verify request fails with 401 Unauthorized
12. Verify key no longer appears in list

**Expected Result**:
- API keys can be created with unique identifiers
- Keys authenticate requests correctly
- Key list shows metadata (name, created_at) but not raw key
- Revoked keys immediately cease to function
- Revoked keys are removed from database

**Test Coverage**:
- `POST /api/v1/api_key/` (create)
- `GET /api/v1/api_key/` (list)
- `DELETE /api/v1/api_key/{id}` (revoke)
- API key authentication middleware
- Key hashing and validation

---

### REG-014: File Upload and Reference in Flow

**Priority**: P1
**Automated**: Yes
**Test Type**: Integration (API + Execution)
**Estimated Duration**: 120 seconds

**Description**: Verify that users can upload files and reference them in flow components (e.g., for RAG or document processing).

**Test Steps**:
1. Prepare a test text file (1KB sample document)
2. Send POST request to `/api/v1/files/upload` with file:
   - Content-Type: multipart/form-data
   - Field: `file`
3. Verify 201 Created response with `file_id`
4. Send GET request to `/api/v1/files/` to list files
5. Verify uploaded file appears with correct:
   - Filename, file size, MIME type, uploaded_at timestamp
6. Create a flow with a File component referencing the uploaded file
7. Execute the flow
8. Verify component can read file contents correctly
9. Send DELETE request to `/api/v1/files/{file_id}` to remove
10. Verify file is deleted from storage and database
11. Verify file no longer appears in list

**Expected Result**:
- Files upload successfully to backend storage
- File metadata is tracked in database
- Files can be referenced in flow components
- Components can read file contents during execution
- File deletion removes both database record and storage file

**Test Coverage**:
- `POST /api/v1/files/upload` (upload)
- `GET /api/v1/files/` (list)
- `DELETE /api/v1/files/{id}` (delete)
- File storage system
- File reference resolution in components

---

### REG-015: Multi-User Isolation

**Priority**: P1
**Automated**: Yes
**Test Type**: Integration (Security)
**Estimated Duration**: 120 seconds

**Description**: Verify that users can only access their own flows, projects, and resources (no cross-user data leakage).

**Test Steps**:
1. Create User A and User B (separate accounts)
2. Authenticate as User A and create:
   - Flow A1 with name "User A Private Flow"
   - Project A1 with name "User A Project"
3. Note flow_id (A1_flow_id) and project_id (A1_project_id)
4. Authenticate as User B
5. Attempt to access User A's flow:
   - GET `/api/v1/flows/{A1_flow_id}`
6. Verify 403 Forbidden or 404 Not Found response
7. Attempt to list all flows for User B:
   - GET `/api/v1/flows/`
8. Verify User A's flow does NOT appear in list
9. Attempt to update User A's flow:
   - PATCH `/api/v1/flows/{A1_flow_id}`
10. Verify 403 Forbidden response
11. Repeat tests for project access
12. Verify User B cannot see or modify User A's projects

**Expected Result**:
- User B cannot read User A's flows
- User B cannot modify User A's flows
- User B cannot list User A's flows
- User B cannot access User A's projects
- All resource queries filter by user_id correctly

**Test Coverage**:
- User-based resource isolation
- Authorization checks on all endpoints
- Query filtering by authenticated user
- Security boundary enforcement

---

### REG-016: WebSocket Connection Stability

**Priority**: P1
**Automated**: Partial
**Test Type**: Integration (WebSocket)
**Estimated Duration**: 180 seconds

**Description**: Verify that WebSocket connections for real-time updates remain stable during flow execution.

**Test Steps**:
1. Establish WebSocket connection to backend
2. Authenticate connection with JWT token
3. Subscribe to flow execution events
4. Execute a long-running flow (15+ seconds)
5. Verify WebSocket delivers all events:
   - Connection confirmation
   - Build progress updates
   - Vertex execution status
   - Output delivery
6. Verify connection remains open throughout execution
7. Verify no message loss or duplication
8. Intentionally close connection and reconnect
9. Verify reconnection succeeds within 5 seconds
10. Verify event delivery resumes after reconnection

**Expected Result**:
- WebSocket connection establishes successfully
- Connection remains stable during long operations
- All events are delivered in order
- No messages are lost
- Reconnection is seamless

**Test Coverage**:
- WebSocket connection lifecycle
- Event streaming infrastructure
- Connection resilience
- Message ordering and delivery guarantees

---

### REG-017: Variable Management

**Priority**: P1
**Automated**: Yes
**Test Type**: Integration (API)
**Estimated Duration**: 90 seconds

**Description**: Verify that users can create, update, list, and delete variables for use in flows (e.g., API keys, environment configs).

**Test Steps**:
1. Send POST request to `/api/v1/variables/` to create variable:
   ```json
   {
     "name": "TEST_API_KEY",
     "value": "sk-test-regression-key-12345",
     "type": "credential"
   }
   ```
2. Verify 201 Created with variable_id
3. Send GET request to `/api/v1/variables/` to list variables
4. Verify new variable appears in list
5. Verify sensitive values are masked (e.g., "sk-test-...12345")
6. Reference variable in a flow component configuration
7. Execute flow and verify component receives correct variable value
8. Send PATCH request to update variable value
9. Verify update succeeds
10. Execute flow again and verify new value is used
11. Send DELETE request to `/api/v1/variables/{variable_id}`
12. Verify variable is deleted
13. Verify deleted variable no longer available in flows

**Expected Result**:
- Variables can be created with name-value pairs
- Variables are scoped to user
- Sensitive values are masked in list responses
- Variables can be referenced in component configurations
- Variable updates take effect immediately
- Deleted variables are removed from system

**Test Coverage**:
- `POST /api/v1/variables/` (create)
- `GET /api/v1/variables/` (list)
- `PATCH /api/v1/variables/{id}` (update)
- `DELETE /api/v1/variables/{id}` (delete)
- Variable resolution in flow execution
- Credential masking

---

## 4. Medium Priority Tests (P2 - Nice to Pass)

These tests cover advanced features and edge cases. **90% of P2 tests should pass** before release, but blockers here may be acceptable if documented.

### REG-020: Store/Marketplace Browse

**Priority**: P2
**Automated**: Partial
**Test Type**: Integration (API)
**Estimated Duration**: 60 seconds

**Description**: Verify that users can browse the store/marketplace for flow templates and components.

**Test Steps**:
1. Send GET request to `/api/v1/store/` to list available items
2. Verify response contains store items
3. Verify each item has: name, description, preview image, category
4. Filter store items by category
5. Search store items by keyword
6. Verify search returns relevant results
7. Select a store item to view details
8. Verify detailed view includes full description and screenshots

**Expected Result**:
- Store endpoint returns browsable catalog
- Items are categorized appropriately
- Search functionality works correctly
- Item details are complete

**Test Coverage**:
- `GET /api/v1/store/` (list store items)
- Store catalog management
- Search and filtering
- Store item metadata

---

### REG-021: Flow Sharing

**Priority**: P2
**Automated**: Partial
**Test Type**: Integration (API)
**Estimated Duration**: 90 seconds

**Description**: Verify that users can share flows with other users or generate public links.

**Test Steps**:
1. Create a flow as User A
2. Generate share link for the flow
3. Verify share link is created with unique token
4. Authenticate as User B
5. Access flow via share link
6. Verify User B can view flow (read-only)
7. Verify User B cannot modify shared flow
8. Revoke share link as User A
9. Verify User B can no longer access via link

**Expected Result**:
- Share links can be generated
- Shared flows are accessible to recipients
- Share permissions are enforced (read-only)
- Revoked links immediately stop working

**Test Coverage**:
- Flow sharing system
- Share link generation and validation
- Permission enforcement on shared resources
- Share revocation

---

### REG-022: Admin User Management

**Priority**: P2
**Automated**: Yes
**Test Type**: Integration (API)
**Estimated Duration**: 90 seconds

**Description**: Verify that superuser admins can manage other users (create, disable, delete).

**Test Steps**:
1. Authenticate as superuser admin
2. Send POST request to `/api/v1/users/` to create new user:
   ```json
   {
     "username": "testuser_regression",
     "password": "SecurePass123!",
     "is_active": true,
     "is_superuser": false
   }
   ```
3. Verify user is created
4. Send GET request to `/api/v1/users/` to list all users
5. Verify new user appears in list
6. Send PATCH request to disable user (is_active: false)
7. Verify user can no longer authenticate
8. Send DELETE request to remove user
9. Verify user is deleted
10. Attempt same operations as non-admin user
11. Verify all operations fail with 403 Forbidden

**Expected Result**:
- Admins can create users
- Admins can list all users
- Admins can disable/enable users
- Admins can delete users
- Non-admins cannot perform admin operations

**Test Coverage**:
- `POST /api/v1/users/` (create user - admin)
- `GET /api/v1/users/` (list users - admin)
- `PATCH /api/v1/users/{id}` (update user - admin)
- `DELETE /api/v1/users/{id}` (delete user - admin)
- Superuser authorization checks

---

### REG-023: OAuth Login Flows

**Priority**: P2
**Automated**: No (requires external OAuth providers)
**Test Type**: Integration (Auth)
**Estimated Duration**: 120 seconds (manual)

**Description**: Verify that OAuth2 authentication works for supported providers (Google, GitHub, etc.).

**Test Steps**:
1. Navigate to login page
2. Click "Login with Google" button
3. Complete OAuth flow in browser
4. Verify redirect back to LangBuilder with valid session
5. Verify user profile is populated from OAuth provider
6. Verify JWT token is issued
7. Logout and repeat with GitHub OAuth
8. Verify same account links if email matches

**Expected Result**:
- OAuth providers redirect correctly
- User authentication succeeds
- Profile data is imported from provider
- Subsequent logins use existing account
- Account linking works for matching emails

**Test Coverage**:
- OAuth2 integration
- Provider callback handling
- User account creation/linking
- Session management via OAuth

---

### REG-024: Bulk Operations

**Priority**: P2
**Automated**: Yes
**Test Type**: Integration (API)
**Estimated Duration**: 120 seconds

**Description**: Verify that users can perform bulk operations on flows and projects (delete multiple, move to folder, etc.).

**Test Steps**:
1. Create 10 test flows
2. Send bulk delete request with array of flow_ids:
   ```json
   {
     "flow_ids": ["flow1", "flow2", "flow3"]
   }
   ```
3. Verify all specified flows are deleted
4. Create 5 more test flows
5. Send bulk move request to move flows to a project
6. Verify all flows have updated folder_id
7. Verify bulk operations are atomic (all succeed or all fail)

**Expected Result**:
- Bulk delete removes all specified flows
- Bulk move updates all specified flows
- Operations are transactional
- Invalid flow_ids in batch are handled gracefully

**Test Coverage**:
- Bulk flow operations
- Transaction management
- Error handling in bulk operations
- Performance with multiple items

---

## 5. Data Integrity Tests

These tests ensure critical data remains consistent and recoverable across system events.

### REG-030: Flow Data Persistence After Restart

**Priority**: P1
**Automated**: Yes
**Test Type**: Integration (Database + Service)
**Estimated Duration**: 120 seconds

**Description**: Verify that flow data persists correctly across backend restarts (no in-memory data loss).

**Test Steps**:
1. Create a complex flow with 5+ nodes
2. Execute the flow and verify success
3. Record flow_id and final state
4. Gracefully stop the backend service
5. Restart the backend service
6. Wait for service to be ready (health check)
7. Send GET request to `/api/v1/flows/{flow_id}`
8. Verify flow data matches pre-restart state
9. Execute the flow again
10. Verify execution succeeds identically to pre-restart

**Expected Result**:
- Flow data is fully persisted to database
- No in-memory caching causes data loss
- Flow remains executable after restart
- All nodes, edges, and configurations intact

**Test Coverage**:
- Database persistence layer
- Service restart resilience
- Data recovery from persistent storage
- Stateless service design validation

---

### REG-031: Database Migration Rollback

**Priority**: P1
**Automated**: Yes
**Test Type**: Integration (Database)
**Estimated Duration**: 180 seconds

**Description**: Verify that database migrations can be rolled back without data loss for reversible changes.

**Test Steps**:
1. Create test data in current schema: 2 users, 3 flows, 2 projects
2. Record all test data IDs and content
3. Apply a new migration: `alembic upgrade +1`
4. Verify migration applies successfully
5. Verify test data still accessible and intact
6. Roll back the migration: `alembic downgrade -1`
7. Verify rollback succeeds
8. Verify test data still accessible and intact
9. Re-apply migration: `alembic upgrade +1`
10. Verify test data remains consistent

**Expected Result**:
- Migration applies without errors
- Rollback succeeds without errors
- Test data survives migration and rollback
- Data integrity is maintained throughout

**Test Coverage**:
- Alembic migration system
- Rollback functionality
- Data preservation during schema changes
- Migration reversibility

---

### REG-032: Concurrent Flow Editing

**Priority**: P2
**Automated**: Partial
**Test Type**: Integration (Concurrency)
**Estimated Duration**: 150 seconds

**Description**: Verify that concurrent edits to the same flow by multiple sessions handle conflicts appropriately.

**Test Steps**:
1. Create a test flow
2. Open two authenticated sessions (User A, Session 1 and Session 2)
3. Both sessions GET the same flow simultaneously
4. Session 1 updates flow data (add node 1)
5. Session 2 updates flow data (add node 2) - slightly delayed
6. Both sessions PATCH the flow concurrently
7. Verify one update succeeds
8. Verify second update either:
   - Succeeds if non-conflicting (both nodes added)
   - Fails with 409 Conflict if conflicting
9. Verify final flow state is consistent
10. Verify no data corruption or lost nodes

**Expected Result**:
- Concurrent updates are handled gracefully
- Optimistic locking or last-write-wins is enforced
- No data corruption occurs
- User receives clear feedback on conflicts

**Test Coverage**:
- Concurrent request handling
- Optimistic locking (if implemented)
- Conflict detection and resolution
- Data consistency under concurrency

---

## 6. Performance Regression

These tests ensure system performance remains within acceptable bounds across releases.

### REG-040: API Response Time Baselines

**Priority**: P1
**Automated**: Yes
**Test Type**: Performance (API)
**Estimated Duration**: 300 seconds

**Description**: Verify that critical API endpoints meet response time SLAs under normal load.

**Performance Baselines**:

| Endpoint | Metric | Baseline | Threshold |
|----------|--------|----------|-----------|
| `POST /api/v1/login` | p95 latency | 150ms | 250ms |
| `GET /api/v1/flows/` | p95 latency | 200ms | 400ms |
| `GET /api/v1/flows/{id}` | p95 latency | 100ms | 200ms |
| `POST /api/v1/flows/` | p95 latency | 250ms | 500ms |
| `PATCH /api/v1/flows/{id}` | p95 latency | 300ms | 600ms |
| `POST /api/v1/build/{id}/flow` | p95 latency | 5000ms | 10000ms |
| `GET /api/v1/endpoints/custom_component` | p95 latency | 500ms | 1000ms |

**Test Steps**:
1. Run 100 requests to each endpoint with 10 concurrent users
2. Measure response times for each request
3. Calculate p50, p95, p99 latencies
4. Compare against baseline thresholds
5. Flag any endpoint exceeding threshold by >10%
6. Generate performance report with latency distributions

**Expected Result**:
- All endpoints meet p95 thresholds
- No endpoint shows >20% regression from baseline
- p99 latencies remain reasonable (< 2x threshold)

**Test Coverage**:
- API endpoint latency
- Database query performance
- Response time consistency
- Performance regression detection

---

### REG-041: Canvas Rendering Performance

**Priority**: P2
**Automated**: Partial (requires browser testing)
**Test Type**: Performance (UI)
**Estimated Duration**: 180 seconds

**Description**: Verify that React Flow canvas renders and responds smoothly with large flows (50+ nodes).

**Performance Baselines**:

| Operation | Metric | Baseline | Threshold |
|-----------|--------|----------|-----------|
| Initial canvas load (50 nodes) | Time to interactive | 800ms | 1500ms |
| Add node to canvas | Render time | 50ms | 100ms |
| Drag node | Frame rate | 60fps | 30fps |
| Zoom in/out | Frame rate | 60fps | 30fps |
| Pan canvas | Frame rate | 60fps | 30fps |

**Test Steps**:
1. Create a flow with 50 nodes and 60 edges
2. Load the flow in the UI
3. Measure time from request to full canvas render
4. Perform 20 node drag operations
5. Monitor frame rate during dragging
6. Perform 10 zoom operations (in and out)
7. Monitor frame rate during zoom
8. Perform canvas panning
9. Monitor frame rate during pan
10. Generate performance report

**Expected Result**:
- Canvas loads within 1.5 seconds
- Interactions maintain 30+ fps
- No UI freezing or jank
- Smooth user experience with large flows

**Test Coverage**:
- React Flow rendering performance
- Canvas interaction responsiveness
- Large graph handling
- Frontend performance optimization

---

### REG-042: Flow Execution Latency

**Priority**: P1
**Automated**: Yes
**Test Type**: Performance (Execution)
**Estimated Duration**: 300 seconds

**Description**: Verify that flow execution latency remains within acceptable bounds for various flow complexities.

**Performance Baselines**:

| Flow Type | Nodes | Metric | Baseline | Threshold |
|-----------|-------|--------|----------|-----------|
| Simple (ChatInput → ChatOutput) | 2 | Total execution | 500ms | 1000ms |
| Medium (Input → LLM → Output) | 3 | Total execution | 3000ms | 6000ms |
| Complex (Multi-branch RAG) | 10 | Total execution | 8000ms | 15000ms |
| Large DAG | 25 | Total execution | 20000ms | 40000ms |

**Test Steps**:
1. Execute each flow type 50 times
2. Measure end-to-end execution time
3. Calculate p50, p95, p99 latencies
4. Measure per-vertex execution times
5. Identify slowest vertices
6. Compare against baseline thresholds
7. Flag any flow exceeding threshold by >15%
8. Generate execution performance report

**Expected Result**:
- All flow types complete within thresholds
- No >20% regression from baseline
- Vertex execution times are consistent
- Parallel vertex execution provides speedup

**Test Coverage**:
- DAG execution performance
- Vertex execution latency
- Parallel execution efficiency
- Flow execution optimization

---

## 7. Regression Test Execution Guide

### 7.1 Running the Full Suite

```bash
# Set up test environment
export TEST_ENV=regression
export DATABASE_URL=sqlite:///./test_regression.db

# Run backend regression tests
cd langbuilder/src/backend
pytest tests/ -m regression --verbose --html=regression-report.html

# Run frontend E2E regression tests
cd ../../frontend
npm run test:e2e:regression

# Run performance tests
pytest tests/performance/ --benchmark-only
```

### 7.2 Pre-Release Checklist

- [ ] All P0 tests pass (100%)
- [ ] 95%+ P1 tests pass
- [ ] 90%+ P2 tests pass
- [ ] All performance baselines met
- [ ] No security test failures
- [ ] Migration tests pass
- [ ] Regression report reviewed by QA lead
- [ ] Known failures documented with tickets
- [ ] Deployment runbook updated

### 7.3 Test Result Interpretation

**Test Status Codes**:
- ✅ **PASS**: Test passed, no issues
- ⚠️ **WARN**: Test passed but close to threshold (within 10%)
- ❌ **FAIL**: Test failed, blocking issue
- ⏭️ **SKIP**: Test skipped (e.g., missing dependency)
- 🔄 **FLAKY**: Test passed but has intermittent failures

**Failure Response**:
1. **P0 Failure**: Immediate investigation, blocks release
2. **P1 Failure**: Investigate within 24 hours, blocks release if critical path
3. **P2 Failure**: Document as known issue, fix in next sprint
4. **Performance Regression**: Investigate, acceptable if <20% and documented

### 7.4 Continuous Integration

Regression tests run automatically on:
- Every PR to main branch (P0 tests only)
- Nightly builds (full suite)
- Weekly scheduled runs (full suite + performance)
- Before every release candidate build

CI job must complete within **45 minutes** or timeout.

---

## 8. Test Maintenance

### 8.1 Updating Baselines

Performance baselines should be reviewed quarterly or after major architectural changes. To update:

1. Run full performance suite 5 times on stable main branch
2. Calculate median p95 latencies across runs
3. Set new baseline to median value
4. Set threshold to baseline + 50% (or stricter if warranted)
5. Update this document with new baselines
6. Commit changes with justification

### 8.2 Adding New Regression Tests

When adding critical features, consider adding P0/P1 regression tests. New test should:
- Cover a critical user path or data integrity concern
- Be automated (or have automation plan)
- Execute in <3 minutes (individual test)
- Be deterministic (no flaky tests)
- Include clear expected results

Submit new tests via PR with updates to this document.

### 8.3 Test Ownership

| Test Category | Owner | Review Cadence |
|---------------|-------|----------------|
| Authentication (REG-001) | Security Team | Monthly |
| Flow Operations (REG-002-004) | Backend Team | Quarterly |
| Execution Engine (REG-005-006) | Backend Team | Quarterly |
| Project Management (REG-007) | Product Team | Quarterly |
| Database (REG-008, REG-030-032) | Infrastructure Team | Monthly |
| Components (REG-010-011) | Backend Team | Quarterly |
| API Operations (REG-012-014) | Backend Team | Quarterly |
| Security (REG-015) | Security Team | Monthly |
| Real-time (REG-016) | Infrastructure Team | Monthly |
| Performance (REG-040-042) | Performance Team | Weekly |

---

## 9. Appendix

### 9.1 Test Data Requirements

The regression suite requires the following test data:

**Users**:
- `testuser_a@example.com` / `Password123!` (regular user)
- `testuser_b@example.com` / `Password123!` (regular user)
- `admin@example.com` / `AdminPass123!` (superuser)

**Flows**:
- `Simple Chat Flow` (ChatInput → ChatOutput)
- `LLM Flow` (ChatInput → OpenAI → ChatOutput)
- `RAG Flow` (10 nodes, complex DAG)

**Files**:
- `test_document.txt` (1KB text file)
- `test_data.json` (sample JSON data)

### 9.2 Known Limitations

- REG-023 (OAuth) requires manual testing with real OAuth providers
- REG-041 (Canvas performance) requires browser automation (Playwright/Cypress)
- REG-016 (WebSocket) has intermittent failures under high load (investigating)
- Performance tests may vary by ±10% depending on hardware

### 9.3 Related Resources

- [Test Inventory](./test-inventory.md) - Complete test catalog
- [Feature Catalog](../product/feature-catalog.md) - Full feature list
- [API Surface](../inventory/api-surface.md) - API endpoint documentation
- [Architecture](../architecture/system-architecture.md) - System architecture
- CI/CD Pipeline Configuration: `.github/workflows/regression.yml`

---

**Document Version**: 1.0
**Last Updated**: 2026-02-09
**Next Review**: 2026-03-09
