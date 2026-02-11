# Manual Test Scenarios - LangBuilder v1.6.5

> **Generated:** 2026-02-09
> **Version:** 1.6.5
> **Purpose:** Comprehensive manual testing checklists for LangBuilder features organized by functional area

## Overview

This document provides detailed manual test scenarios for validating LangBuilder functionality across all major feature areas. Each scenario includes a unique ID, description, preconditions, step-by-step instructions, expected results, and priority classification.

**Priority Levels:**
- **Critical** - Core functionality; must pass before release
- **High** - Important features used in primary workflows
- **Medium** - Secondary features; affects user experience
- **Low** - Nice-to-have features; edge cases

**Test Coverage:**
- 10 functional areas
- 100+ test scenarios
- End-to-end user journeys
- Integration points
- Edge cases and error handling

---

## Table of Contents

1. [User Authentication & Authorization](#1-user-authentication--authorization)
2. [Flow Builder Canvas](#2-flow-builder-canvas)
3. [Component Management](#3-component-management)
4. [Flow Execution](#4-flow-execution)
5. [Project Management](#5-project-management)
6. [API Endpoints](#6-api-endpoints)
7. [File Management](#7-file-management)
8. [Store/Marketplace](#8-storemarketplace)
9. [Settings & Configuration](#9-settings--configuration)
10. [Integration Testing](#10-integration-testing)

---

## 1. User Authentication & Authorization

### MAN-001: User Registration

| Field | Details |
|-------|---------|
| **Description** | Verify new user can successfully register an account |
| **Priority** | Critical |
| **Preconditions** | - Application is running<br>- No existing user with test email/username |
| **Test Data** | Email: `testuser@example.com`<br>Username: `testuser`<br>Password: `SecurePass123!` |

**Steps:**
1. Navigate to LangBuilder homepage
2. Click "Register" or "Sign Up" link
3. Enter unique email address in email field
4. Enter unique username in username field
5. Enter password meeting minimum requirements (8+ characters)
6. Confirm password in confirmation field
7. Click "Register" button

**Expected Results:**
- User account is created successfully
- User is automatically logged in with JWT token
- User is redirected to main dashboard/canvas
- Success message is displayed
- User appears in database with bcrypt-hashed password
- API endpoint: `POST /api/v1/users/` returns 201 status

---

### MAN-002: User Login with Valid Credentials

| Field | Details |
|-------|---------|
| **Description** | Verify registered user can log in with correct credentials |
| **Priority** | Critical |
| **Preconditions** | - User account exists in database<br>- User is logged out |
| **Test Data** | Username: `testuser`<br>Password: `SecurePass123!` |

**Steps:**
1. Navigate to login page
2. Enter registered username in username field
3. Enter correct password in password field
4. Click "Login" button

**Expected Results:**
- User is authenticated successfully
- JWT access token and refresh token are issued
- User is redirected to dashboard
- User session is maintained in browser
- API endpoint: `POST /api/v1/login` returns 200 with tokens

---

### MAN-003: User Login with Invalid Credentials

| Field | Details |
|-------|---------|
| **Description** | Verify system rejects login attempts with incorrect password |
| **Priority** | Critical |
| **Preconditions** | - User account exists<br>- User is logged out |
| **Test Data** | Username: `testuser`<br>Password: `WrongPassword123!` |

**Steps:**
1. Navigate to login page
2. Enter valid username
3. Enter incorrect password
4. Click "Login" button

**Expected Results:**
- Login is rejected
- Error message displayed: "Invalid credentials" or similar
- User remains on login page
- No tokens are issued
- API endpoint: `POST /api/v1/login` returns 401 Unauthorized

---

### MAN-004: JWT Token Refresh

| Field | Details |
|-------|---------|
| **Description** | Verify access token can be refreshed using refresh token |
| **Priority** | High |
| **Preconditions** | - User is logged in<br>- Valid refresh token exists |

**Steps:**
1. Log in and capture initial access token
2. Wait for access token to expire (or manually expire it)
3. Make an authenticated API request
4. System should automatically use refresh token to get new access token

**Expected Results:**
- New access token is issued automatically
- User session continues without interruption
- User is not logged out
- API endpoint: `POST /api/v1/refresh` returns new tokens

---

### MAN-005: API Key Creation

| Field | Details |
|-------|---------|
| **Description** | Verify user can create API key for programmatic access |
| **Priority** | High |
| **Preconditions** | - User is logged in<br>- User has appropriate permissions |

**Steps:**
1. Navigate to Settings or API Keys section
2. Click "Create New API Key" button
3. Enter API key name/description
4. Set expiration date (optional)
5. Click "Generate" button

**Expected Results:**
- New API key is generated
- API key is displayed to user (one-time only)
- API key is stored securely in database (hashed)
- User can copy API key to clipboard
- API endpoint: `POST /api/v1/api_key/{user_id}/api_keys` returns 201

---

### MAN-006: API Key Authentication

| Field | Details |
|-------|---------|
| **Description** | Verify API key can be used for programmatic authentication |
| **Priority** | High |
| **Preconditions** | - Valid API key exists for user |
| **Test Data** | API Key: `sk-xxx...xxx` |

**Steps:**
1. Make API request to authenticated endpoint
2. Include API key in Authorization header: `Bearer <api_key>`
3. Request should be processed as authenticated user

**Expected Results:**
- Request is authenticated successfully
- API responds with requested data
- Request is attributed to correct user
- Rate limiting applies based on user tier

---

### MAN-007: API Key Revocation

| Field | Details |
|-------|---------|
| **Description** | Verify user can revoke/delete API keys |
| **Priority** | High |
| **Preconditions** | - User is logged in<br>- At least one API key exists |

**Steps:**
1. Navigate to API Keys management page
2. Locate API key to revoke
3. Click "Delete" or "Revoke" button
4. Confirm deletion
5. Attempt to use revoked API key

**Expected Results:**
- API key is removed from database
- Confirmation message is displayed
- Subsequent requests with revoked key return 401 Unauthorized
- API endpoint: `DELETE /api/v1/api_key/{user_id}/api_keys/{api_key_id}` returns 200

---

### MAN-008: Superuser Access Control

| Field | Details |
|-------|---------|
| **Description** | Verify superuser can access all flows and admin features |
| **Priority** | High |
| **Preconditions** | - Superuser account exists<br>- Test flows exist with PRIVATE access |

**Steps:**
1. Log in as superuser
2. Navigate to flows list
3. Attempt to access flows owned by other users
4. Attempt to access admin-only endpoints

**Expected Results:**
- Superuser can view/edit all flows regardless of owner
- Superuser can access admin endpoints
- Superuser permissions are enforced at API level
- Regular users cannot access other users' private flows

---

### MAN-009: Password Reset Flow

| Field | Details |
|-------|---------|
| **Description** | Verify user can reset forgotten password |
| **Priority** | Medium |
| **Preconditions** | - User account exists<br>- Email service is configured |

**Steps:**
1. Navigate to login page
2. Click "Forgot Password" link
3. Enter registered email address
4. Submit password reset request
5. Check email for reset link
6. Click reset link
7. Enter new password
8. Submit new password
9. Log in with new password

**Expected Results:**
- Password reset email is sent
- Reset link is valid for limited time
- Password is updated in database
- Old password no longer works
- User can log in with new password

---

### MAN-010: Session Timeout

| Field | Details |
|-------|---------|
| **Description** | Verify user session expires after period of inactivity |
| **Priority** | Medium |
| **Preconditions** | - User is logged in<br>- Session timeout is configured |

**Steps:**
1. Log in to application
2. Leave browser idle for duration exceeding session timeout
3. Attempt to perform an action (e.g., save flow)

**Expected Results:**
- Session expires after timeout period
- User is redirected to login page
- Unsaved work is either auto-saved or warning is displayed
- User must re-authenticate to continue

---

## 2. Flow Builder Canvas

### MAN-011: Create New Blank Flow

| Field | Details |
|-------|---------|
| **Description** | Verify user can create a new empty flow |
| **Priority** | Critical |
| **Preconditions** | - User is logged in |

**Steps:**
1. Click "New Flow" button from dashboard
2. Optionally enter flow name and description
3. Click "Create" button

**Expected Results:**
- New flow is created in database
- Empty canvas is displayed
- Flow appears in user's flows list
- Flow ID is generated
- API endpoint: `POST /api/v1/flows/` returns 201 with flow data

---

### MAN-012: Drag and Drop Component from Sidebar

| Field | Details |
|-------|---------|
| **Description** | Verify user can add component to canvas via drag-and-drop |
| **Priority** | Critical |
| **Preconditions** | - Flow is open in canvas<br>- Component sidebar is visible |

**Steps:**
1. Open component sidebar
2. Browse or search for desired component (e.g., "OpenAI")
3. Click and drag component onto canvas
4. Release mouse button to drop component

**Expected Results:**
- Component node appears on canvas at drop location
- Node is selectable and movable
- Node displays component name and icon
- Node has appropriate input/output handles based on component type
- Node is added to frontend state (Zustand)

---

### MAN-013: Connect Two Nodes with Edge

| Field | Details |
|-------|---------|
| **Description** | Verify user can create edge connection between compatible nodes |
| **Priority** | Critical |
| **Preconditions** | - Flow is open<br>- Two compatible nodes are on canvas |

**Steps:**
1. Hover over output handle of source node
2. Click and drag from output handle
3. Drag to compatible input handle of target node
4. Release to create edge connection

**Expected Results:**
- Visual edge line connects the two nodes
- Edge is rendered with directional arrow
- Connection is validated for type compatibility
- Edge appears in flow definition
- Data will flow from source to target during execution

---

### MAN-014: Prevent Invalid Edge Connection

| Field | Details |
|-------|---------|
| **Description** | Verify system prevents incompatible node connections |
| **Priority** | High |
| **Preconditions** | - Flow is open<br>- Two incompatible nodes exist on canvas |

**Steps:**
1. Attempt to connect output of type "String" to input requiring "Integer"
2. Drag from incompatible output handle to incompatible input handle
3. Attempt to release connection

**Expected Results:**
- Connection is rejected
- Visual indicator shows connection is invalid (red/error state)
- Error message explains type mismatch
- No edge is created
- Frontend validates type compatibility

---

### MAN-015: Configure Node Parameters

| Field | Details |
|-------|---------|
| **Description** | Verify user can open and configure node settings |
| **Priority** | Critical |
| **Preconditions** | - Flow is open<br>- Node exists on canvas |

**Steps:**
1. Click on a node (e.g., OpenAI LLM node)
2. Configuration panel/modal opens
3. Modify parameters (e.g., model: "gpt-4", temperature: 0.7)
4. Add API key reference from global variables
5. Click "Save" or close panel

**Expected Results:**
- Configuration panel displays all available parameters
- Parameters are organized by category (basic/advanced)
- Changes are saved to node configuration
- Node state updates in frontend
- Configuration persists when flow is saved

---

### MAN-016: Delete Node from Canvas

| Field | Details |
|-------|---------|
| **Description** | Verify user can remove node from flow |
| **Priority** | High |
| **Preconditions** | - Flow is open<br>- Node exists on canvas |

**Steps:**
1. Select node by clicking on it
2. Press Delete key or click delete button
3. Confirm deletion if prompted

**Expected Results:**
- Node is removed from canvas
- All connected edges are also removed
- Node is removed from flow definition
- Action can be undone with Ctrl+Z

---

### MAN-017: Delete Edge Connection

| Field | Details |
|-------|---------|
| **Description** | Verify user can remove edge between nodes |
| **Priority** | High |
| **Preconditions** | - Flow is open<br>- Edge connection exists |

**Steps:**
1. Click on edge to select it
2. Press Delete key or click delete button
3. Confirm deletion if prompted

**Expected Results:**
- Edge is removed from canvas
- Nodes remain on canvas
- Data flow between nodes is broken
- Action can be undone

---

### MAN-018: Canvas Zoom and Pan

| Field | Details |
|-------|---------|
| **Description** | Verify canvas navigation controls work correctly |
| **Priority** | High |
| **Preconditions** | - Flow is open with multiple nodes |

**Steps:**
1. Use mouse wheel to zoom in and out
2. Click and drag on empty canvas area to pan
3. Use zoom controls (+/- buttons) if available
4. Test zoom limits (max zoom in/out)

**Expected Results:**
- Canvas zooms smoothly in/out
- Zoom centers on mouse position
- Pan allows navigation across entire canvas
- Zoom level is maintained when saving/loading
- Minimap updates to reflect viewport position

---

### MAN-019: Minimap Navigation

| Field | Details |
|-------|---------|
| **Description** | Verify minimap provides overview and navigation |
| **Priority** | Medium |
| **Preconditions** | - Flow is open<br>- Minimap is visible |

**Steps:**
1. Locate minimap (typically bottom-right corner)
2. Observe node positions in minimap
3. Click on minimap to navigate
4. Drag viewport indicator in minimap

**Expected Results:**
- Minimap shows all nodes in flow
- Current viewport is highlighted in minimap
- Clicking minimap navigates to that area
- Minimap updates as nodes are added/moved

---

### MAN-020: Copy and Paste Nodes

| Field | Details |
|-------|---------|
| **Description** | Verify user can duplicate nodes via copy/paste |
| **Priority** | Medium |
| **Preconditions** | - Flow is open<br>- Node exists on canvas |

**Steps:**
1. Select node(s) to copy
2. Press Ctrl+C (Cmd+C on Mac) to copy
3. Press Ctrl+V (Cmd+V on Mac) to paste
4. Observe duplicated node(s)

**Expected Results:**
- Selected node(s) are duplicated
- Duplicates appear offset from originals
- Node configurations are copied
- New unique IDs are assigned
- Edges are not copied (only nodes)

---

### MAN-021: Undo/Redo Actions

| Field | Details |
|-------|---------|
| **Description** | Verify undo/redo functionality for canvas operations |
| **Priority** | High |
| **Preconditions** | - Flow is open |

**Steps:**
1. Perform action (add node, delete edge, move node)
2. Press Ctrl+Z (Cmd+Z on Mac) to undo
3. Verify action is reversed
4. Press Ctrl+Shift+Z (Cmd+Shift+Z on Mac) to redo
5. Verify action is reapplied

**Expected Results:**
- Undo reverses last action
- Multiple undo steps work correctly
- Redo reapplies undone actions
- Undo history is maintained during session
- Undo/redo works for all canvas operations

---

### MAN-022: Auto-Layout Flow Nodes

| Field | Details |
|-------|---------|
| **Description** | Verify auto-layout feature arranges nodes optimally |
| **Priority** | Low |
| **Preconditions** | - Flow is open with multiple nodes |

**Steps:**
1. Create flow with nodes in random positions
2. Click "Auto Layout" or similar button
3. Observe node rearrangement

**Expected Results:**
- Nodes are arranged in logical flow order
- Connected nodes are positioned near each other
- Layout follows left-to-right or top-to-bottom pattern
- Edges don't overlap excessively
- Layout is visually clean and readable

---

### MAN-023: Save Flow

| Field | Details |
|-------|---------|
| **Description** | Verify flow can be saved with all changes persisted |
| **Priority** | Critical |
| **Preconditions** | - Flow is open<br>- Changes have been made |

**Steps:**
1. Make changes to flow (add/modify nodes)
2. Click "Save" button or use Ctrl+S
3. Observe save confirmation
4. Close and reopen flow

**Expected Results:**
- Save operation completes successfully
- Confirmation message displayed
- All changes are persisted to database
- Reopened flow shows all saved changes
- API endpoint: `PATCH /api/v1/flows/{flow_id}` returns 200

---

### MAN-024: Auto-Save Flow

| Field | Details |
|-------|---------|
| **Description** | Verify auto-save periodically saves changes |
| **Priority** | High |
| **Preconditions** | - Flow is open<br>- Auto-save is enabled |

**Steps:**
1. Make changes to flow
2. Wait for auto-save interval (typically 30-60 seconds)
3. Observe auto-save indicator
4. Make additional changes
5. Close browser without manual save
6. Reopen flow

**Expected Results:**
- Auto-save triggers at regular intervals
- Visual indicator shows "Saving..." then "Saved"
- Changes are persisted without manual save
- No data loss on unexpected close
- Last auto-save timestamp is visible

---

### MAN-025: Search Component Library

| Field | Details |
|-------|---------|
| **Description** | Verify component search functionality in sidebar |
| **Priority** | Medium |
| **Preconditions** | - Flow is open<br>- Component sidebar is visible |

**Steps:**
1. Click on component search box
2. Type search term (e.g., "openai")
3. Observe filtered results
4. Clear search and verify all components return

**Expected Results:**
- Search filters components in real-time
- Results match search term in name/description
- Components are highlighted or filtered
- No results message shown when no matches
- Search is case-insensitive

---

## 3. Component Management

### MAN-026: Browse Component Categories

| Field | Details |
|-------|---------|
| **Description** | Verify component library is organized by categories |
| **Priority** | High |
| **Preconditions** | - User is logged in<br>- Component sidebar is visible |

**Steps:**
1. Open component sidebar
2. Observe category organization (12 categories)
3. Expand each category to view components
4. Verify categories: LLMs, Vector Stores, Agents, Tools, Prompts, Text Processing, Data Loaders, Embeddings, Memory, Chains, Utilities, Custom

**Expected Results:**
- Components are organized into 12 categories
- Each category is expandable/collapsible
- Category shows count of components
- Components display name, icon, and description
- API endpoint: `GET /api/v1/all` returns categorized components

---

### MAN-027: View Component Details

| Field | Details |
|-------|---------|
| **Description** | Verify component details can be viewed before adding to canvas |
| **Priority** | Medium |
| **Preconditions** | - Component sidebar is open |

**Steps:**
1. Hover over or click component in sidebar
2. View component tooltip or detail panel
3. Review inputs, outputs, and parameters

**Expected Results:**
- Component description is displayed
- Input/output types are shown
- Required vs optional parameters are indicated
- Provider information is shown (for LLM/vector store components)
- Documentation link is available (if applicable)

---

### MAN-028: Upload Custom Component

| Field | Details |
|-------|---------|
| **Description** | Verify user can upload custom component package |
| **Priority** | High |
| **Preconditions** | - User is logged in<br>- Valid custom component file exists |

**Steps:**
1. Navigate to Custom Components section
2. Click "Upload Component" button
3. Select valid component file (Python package)
4. Confirm upload
5. Wait for component validation and loading

**Expected Results:**
- Component file is uploaded successfully
- Component is validated for correctness
- Component appears in Custom category
- Component is available for use in flows
- API endpoint: `POST /api/v1/custom_component/upload/{flow_id}` returns 201

---

### MAN-029: Update Custom Component

| Field | Details |
|-------|---------|
| **Description** | Verify custom component can be updated with new version |
| **Priority** | Medium |
| **Preconditions** | - Custom component exists<br>- Updated component file available |

**Steps:**
1. Locate existing custom component
2. Click "Update" or "Replace" button
3. Upload new version of component file
4. Confirm update
5. Verify flows using component still work

**Expected Results:**
- Component is updated to new version
- Existing flows using component are migrated
- Breaking changes are highlighted
- Component version is tracked
- API endpoint: `PATCH /api/v1/custom_component/update/{flow_id}` returns 200

---

### MAN-030: Delete Custom Component

| Field | Details |
|-------|---------|
| **Description** | Verify custom component can be removed |
| **Priority** | Medium |
| **Preconditions** | - Custom component exists<br>- Component is not used in any flows |

**Steps:**
1. Navigate to Custom Components list
2. Select component to delete
3. Click "Delete" button
4. Confirm deletion
5. Verify component is removed from library

**Expected Results:**
- Component is deleted from system
- Component no longer appears in sidebar
- Confirmation message is shown
- If component is in use, warning is displayed
- API endpoint: `DELETE /api/v1/custom_component/{flow_id}` returns 200

---

### MAN-031: List Available LLM Providers

| Field | Details |
|-------|---------|
| **Description** | Verify all supported LLM providers are available |
| **Priority** | High |
| **Preconditions** | - User is logged in |

**Steps:**
1. Open component sidebar
2. Expand "LLMs" category
3. Count available LLM provider components
4. Verify major providers present: OpenAI, Anthropic, Google AI, Azure OpenAI, AWS Bedrock, Groq, Mistral, Cohere, Ollama, HuggingFace

**Expected Results:**
- 24+ LLM provider components are available
- Each provider has appropriate configuration options
- Providers include both cloud and local options
- Component descriptions are accurate
- Icons/branding are correct

---

### MAN-032: List Available Vector Stores

| Field | Details |
|-------|---------|
| **Description** | Verify all supported vector databases are available |
| **Priority** | High |
| **Preconditions** | - User is logged in |

**Steps:**
1. Open component sidebar
2. Expand "Vector Stores" category
3. Count available vector store components
4. Verify major stores present: ChromaDB, Pinecone, Qdrant, Weaviate, Milvus, FAISS, PGVector

**Expected Results:**
- 19+ vector store components are available
- Each store has connection configuration options
- Both cloud and self-hosted options available
- Component descriptions include use cases
- Configuration includes authentication options

---

### MAN-033: Configure Component Default Settings

| Field | Details |
|-------|---------|
| **Description** | Verify default settings can be configured for component types |
| **Priority** | Low |
| **Preconditions** | - User is logged in<br>- User is on settings page |

**Steps:**
1. Navigate to Settings > Component Defaults
2. Select component type (e.g., OpenAI LLM)
3. Set default values (e.g., model: gpt-4, temperature: 0.7)
4. Save defaults
5. Add new instance of component to canvas
6. Verify defaults are applied

**Expected Results:**
- Default settings are saved
- New component instances use defaults
- Defaults can be overridden per instance
- Defaults are user-specific
- Defaults persist across sessions

---

### MAN-034: Component Version Compatibility

| Field | Details |
|-------|---------|
| **Description** | Verify system handles component version changes gracefully |
| **Priority** | Medium |
| **Preconditions** | - Flow uses specific component version<br>- Component has new version available |

**Steps:**
1. Open flow using older component version
2. System detects newer version available
3. Review version change notes
4. Choose to upgrade or keep current version

**Expected Results:**
- Version mismatch is detected
- User is notified of available updates
- Breaking changes are highlighted
- User can choose to upgrade or stay
- Flow continues to work with old version

---

### MAN-035: Component Error Handling

| Field | Details |
|-------|---------|
| **Description** | Verify graceful handling of component loading failures |
| **Priority** | Medium |
| **Preconditions** | - Corrupt or invalid component exists |

**Steps:**
1. Attempt to load flow with invalid component
2. Observe error handling
3. View error details

**Expected Results:**
- Error message is displayed clearly
- Specific component causing issue is identified
- Flow continues to load other components
- User can remove problematic component
- Detailed error log is available

---

## 4. Flow Execution

### MAN-036: Execute Complete Flow

| Field | Details |
|-------|---------|
| **Description** | Verify full flow execution with all nodes |
| **Priority** | Critical |
| **Preconditions** | - Valid flow with connected nodes exists<br>- All required credentials configured |

**Steps:**
1. Open flow in canvas
2. Verify all nodes are properly configured
3. Click "Run" or "Execute" button
4. Provide any required inputs (e.g., chat message)
5. Observe execution progress

**Expected Results:**
- Flow execution begins immediately
- Progress indicator shows execution status
- Nodes execute in correct dependency order
- Final output is displayed
- API endpoint: `POST /api/v1/build/{flow_id}/flow` returns 200

---

### MAN-037: Execute Single Node (Vertex Build)

| Field | Details |
|-------|---------|
| **Description** | Verify individual node can be executed in isolation |
| **Priority** | High |
| **Preconditions** | - Flow is open<br>- Node has all required inputs |

**Steps:**
1. Right-click on specific node
2. Select "Run Node" or "Build Vertex" option
3. Provide any required test inputs
4. Observe node execution

**Expected Results:**
- Only selected node executes
- Node dependencies are built first
- Node output is displayed
- Rest of flow does not execute
- API endpoint: `POST /api/v1/build/{flow_id}/vertices` returns 200

---

### MAN-038: Stream LLM Response

| Field | Details |
|-------|---------|
| **Description** | Verify LLM responses stream in real-time via SSE |
| **Priority** | High |
| **Preconditions** | - Flow contains LLM node<br>- Flow is ready to execute |

**Steps:**
1. Execute flow with LLM component
2. Observe output panel
3. Watch for token-by-token streaming
4. Verify complete response matches streamed content

**Expected Results:**
- Response appears token by token
- Streaming is smooth without significant delays
- Complete response matches streamed tokens
- SSE connection is stable
- API endpoint: `GET /api/v1/build/{flow_id}/events` streams SSE events

---

### MAN-039: Cancel Running Flow

| Field | Details |
|-------|---------|
| **Description** | Verify flow execution can be cancelled mid-run |
| **Priority** | High |
| **Preconditions** | - Flow is currently executing |

**Steps:**
1. Start flow execution
2. While execution is in progress, click "Cancel" button
3. Observe cancellation handling

**Expected Results:**
- Execution stops immediately or gracefully
- In-progress nodes are terminated
- Resources are cleaned up
- Cancellation confirmation is displayed
- Partial results may be shown
- API endpoint: `POST /api/v1/build/{flow_id}/cancel` returns 200

---

### MAN-040: Handle Execution Error

| Field | Details |
|-------|---------|
| **Description** | Verify graceful error handling during flow execution |
| **Priority** | High |
| **Preconditions** | - Flow contains node that will fail (e.g., invalid API key) |

**Steps:**
1. Configure node with invalid credentials or parameters
2. Execute flow
3. Observe error handling when node fails

**Expected Results:**
- Error is caught and displayed clearly
- Error message includes node name and specific issue
- Execution stops at failed node
- User can view detailed error log
- Flow state is preserved for debugging
- Other valid nodes' results are retained

---

### MAN-041: View Execution History

| Field | Details |
|-------|---------|
| **Description** | Verify past flow executions can be reviewed |
| **Priority** | Medium |
| **Preconditions** | - Flow has been executed multiple times |

**Steps:**
1. Open flow
2. Navigate to "History" or "Executions" tab
3. View list of past executions
4. Click on specific execution to view details

**Expected Results:**
- List shows execution timestamp, status, duration
- Each execution can be inspected individually
- Inputs and outputs are preserved
- Error details are available for failed runs
- Execution logs are accessible

---

### MAN-042: Execute Flow with Chat Interface

| Field | Details |
|-------|---------|
| **Description** | Verify chat-style interaction with conversational flows |
| **Priority** | High |
| **Preconditions** | - Flow configured for chat interaction<br>- Flow contains chat-compatible components |

**Steps:**
1. Open flow with chat interface
2. Enter message in chat input box
3. Press Enter or click Send
4. Observe streaming response
5. Send follow-up message
6. Verify conversation context is maintained

**Expected Results:**
- Messages appear in chat history
- Responses stream in real-time
- Conversation context is preserved
- Chat history shows full conversation
- API endpoint: `POST /api/v1/chat` handles chat messages

---

### MAN-043: Execute Public Flow (Unauthenticated)

| Field | Details |
|-------|---------|
| **Description** | Verify public flows can be executed without authentication |
| **Priority** | High |
| **Preconditions** | - Flow exists with access type set to PUBLIC<br>- User is logged out |

**Steps:**
1. Obtain public flow URL or ID
2. Navigate to flow execution endpoint without authentication
3. Provide required inputs
4. Execute flow

**Expected Results:**
- Flow executes without requiring login
- Public flows are read-only (cannot be edited)
- Execution works identically to authenticated execution
- Rate limiting may apply to public executions
- API endpoint: `POST /api/v1/build/public/{flow_id}/flow` returns results

---

### MAN-044: Parallel Node Execution

| Field | Details |
|-------|---------|
| **Description** | Verify independent nodes execute in parallel |
| **Priority** | Medium |
| **Preconditions** | - Flow has parallel branches (nodes with no dependencies on each other) |

**Steps:**
1. Create flow with parallel branches (e.g., multiple LLM calls to different providers)
2. Execute flow
3. Observe execution timing and progress
4. Verify parallel nodes execute simultaneously

**Expected Results:**
- Independent nodes execute concurrently
- Execution time is reduced compared to sequential
- Progress indicators show parallel execution
- Results are combined correctly after parallel execution
- DAG executor handles parallel scheduling

---

### MAN-045: Flow with File Upload Input

| Field | Details |
|-------|---------|
| **Description** | Verify flow can accept file uploads as input |
| **Priority** | Medium |
| **Preconditions** | - Flow configured to accept file input |

**Steps:**
1. Open flow execution interface
2. Locate file upload button/area
3. Select file from local system
4. Confirm file upload
5. Execute flow with uploaded file

**Expected Results:**
- File is uploaded successfully
- File is processed by flow components
- File content is accessible to nodes
- Supported file types are validated
- Error handling for unsupported files

---

### MAN-046: Flow with Global Variables

| Field | Details |
|-------|---------|
| **Description** | Verify global variables are resolved during execution |
| **Priority** | High |
| **Preconditions** | - Global variables are configured<br>- Flow references global variables |

**Steps:**
1. Create global variables (e.g., API_KEY, MODEL_NAME)
2. Configure flow nodes to use variables (e.g., `{API_KEY}`)
3. Execute flow
4. Verify variables are resolved correctly

**Expected Results:**
- Variable placeholders are replaced with actual values
- Encrypted variables (credentials) are decrypted
- Missing variables cause clear error messages
- Variable scope is respected (user vs global)
- API endpoint: `GET /api/v1/variables/` lists variables

---

### MAN-047: Flow Execution Monitoring

| Field | Details |
|-------|---------|
| **Description** | Verify real-time execution monitoring and progress tracking |
| **Priority** | Medium |
| **Preconditions** | - Flow is executing |

**Steps:**
1. Start flow execution
2. Observe execution monitoring interface
3. View node-by-node progress
4. Monitor execution time
5. View intermediate outputs

**Expected Results:**
- Each node shows status (pending/running/complete/error)
- Visual indicators on canvas show active nodes
- Execution timeline is displayed
- Intermediate outputs are shown as available
- Performance metrics (time per node) are tracked

---

### MAN-048: Retry Failed Execution

| Field | Details |
|-------|---------|
| **Description** | Verify failed flow can be retried |
| **Priority** | Medium |
| **Preconditions** | - Flow execution has failed |

**Steps:**
1. Execute flow that fails (e.g., due to network issue)
2. Fix the issue causing failure
3. Click "Retry" button
4. Observe re-execution

**Expected Results:**
- Flow re-executes from beginning or from failed node
- Previous error is cleared
- New execution attempt is tracked separately
- Success after retry is indicated clearly

---

## 5. Project Management

### MAN-049: Create New Project

| Field | Details |
|-------|---------|
| **Description** | Verify user can create project to organize flows |
| **Priority** | High |
| **Preconditions** | - User is logged in |

**Steps:**
1. Navigate to Projects section
2. Click "New Project" button
3. Enter project name and description
4. Optionally set project icon/color
5. Click "Create" button

**Expected Results:**
- Project is created successfully
- Project appears in projects list
- Project has unique ID
- User is owner of project
- API endpoint: `POST /api/v1/projects/` returns 201

---

### MAN-050: Rename Project

| Field | Details |
|-------|---------|
| **Description** | Verify project can be renamed |
| **Priority** | Medium |
| **Preconditions** | - User owns a project |

**Steps:**
1. Locate project in list
2. Click edit/rename button
3. Enter new project name
4. Save changes

**Expected Results:**
- Project name is updated
- Change is reflected immediately in UI
- Associated flows remain unchanged
- API endpoint: `PATCH /api/v1/projects/{project_id}` returns 200

---

### MAN-051: Delete Project

| Field | Details |
|-------|---------|
| **Description** | Verify project can be deleted |
| **Priority** | High |
| **Preconditions** | - User owns a project<br>- Project contains flows (or is empty) |

**Steps:**
1. Locate project in list
2. Click "Delete" button
3. Review warning about flows in project
4. Confirm deletion

**Expected Results:**
- Confirmation dialog explains impact
- If project has flows, user chooses to delete flows or move them
- Project is removed from database
- Flows are either deleted or moved to default location
- API endpoint: `DELETE /api/v1/projects/{project_id}` returns 200

---

### MAN-052: Move Flow to Project

| Field | Details |
|-------|---------|
| **Description** | Verify flow can be organized into project |
| **Priority** | High |
| **Preconditions** | - User has flows and projects |

**Steps:**
1. Open flow or select from list
2. Click "Move to Project" option
3. Select destination project from dropdown
4. Confirm move

**Expected Results:**
- Flow is associated with selected project
- Flow appears under project in navigation
- Flow is removed from previous location
- API endpoint: `PATCH /api/v1/flows/{flow_id}` updates project association

---

### MAN-053: Create Folder Structure

| Field | Details |
|-------|---------|
| **Description** | Verify nested folder organization for flows |
| **Priority** | Medium |
| **Preconditions** | - User is logged in |

**Steps:**
1. Navigate to folders section
2. Click "New Folder" button
3. Enter folder name
4. Optionally create sub-folders
5. Move flows into folders

**Expected Results:**
- Folders are created successfully
- Nested folder structure is supported
- Flows can be moved into folders
- Folder tree is displayed in navigation
- API endpoint: `POST /api/v1/folders/` returns 201

---

### MAN-054: Search Flows by Name

| Field | Details |
|-------|---------|
| **Description** | Verify flow search functionality |
| **Priority** | Medium |
| **Preconditions** | - User has multiple flows |

**Steps:**
1. Navigate to flows list
2. Enter search term in search box
3. Observe filtered results
4. Clear search to show all flows

**Expected Results:**
- Search filters flows in real-time
- Results match flow names and descriptions
- Search is case-insensitive
- No results message when no matches
- Search works across all projects/folders

---

### MAN-055: Filter Flows by Project

| Field | Details |
|-------|---------|
| **Description** | Verify flows can be filtered by project |
| **Priority** | Medium |
| **Preconditions** | - User has flows in multiple projects |

**Steps:**
1. Navigate to flows list
2. Select project from filter dropdown
3. Observe filtered results showing only flows in selected project
4. Clear filter to show all flows

**Expected Results:**
- Filter shows only flows in selected project
- Filter updates immediately
- Flow count is displayed
- "All Projects" option shows all flows

---

### MAN-056: Duplicate Flow

| Field | Details |
|-------|---------|
| **Description** | Verify flow can be cloned/duplicated |
| **Priority** | High |
| **Preconditions** | - Flow exists |

**Steps:**
1. Locate flow in list
2. Click "Duplicate" or "Clone" option
3. Optionally rename duplicate
4. Confirm duplication

**Expected Results:**
- Exact copy of flow is created
- Duplicate has new unique ID
- All nodes and configurations are copied
- Duplicate is named "(Copy)" or similar
- User can edit duplicate independently
- API endpoint: Likely uses `POST /api/v1/flows/` with existing flow data

---

### MAN-057: Export Flow

| Field | Details |
|-------|---------|
| **Description** | Verify flow can be exported as file |
| **Priority** | High |
| **Preconditions** | - Flow exists |

**Steps:**
1. Open flow or select from list
2. Click "Export" button
3. Choose export format (JSON)
4. Save file to local system

**Expected Results:**
- Flow is exported as JSON file
- Export includes all nodes, edges, configurations
- Exported file can be imported later
- File is named appropriately (flow-name.json)
- API endpoint: `GET /api/v1/flows/{flow_id}` provides flow data

---

### MAN-058: Import Flow

| Field | Details |
|-------|---------|
| **Description** | Verify flow can be imported from file |
| **Priority** | High |
| **Preconditions** | - Valid flow export file exists |

**Steps:**
1. Navigate to flows section
2. Click "Import" button
3. Select flow JSON file
4. Confirm import
5. Review imported flow

**Expected Results:**
- Flow is imported successfully
- All nodes and configurations are restored
- New flow ID is assigned
- Import validation catches invalid files
- User can edit imported flow
- API endpoint: `POST /api/v1/flows/` creates flow from import

---

### MAN-059: Set Flow Access Level

| Field | Details |
|-------|---------|
| **Description** | Verify flow access can be set to PRIVATE/PUBLIC |
| **Priority** | High |
| **Preconditions** | - User owns a flow |

**Steps:**
1. Open flow settings
2. Locate "Access" or "Visibility" setting
3. Select access level: PRIVATE or PUBLIC
4. Save changes
5. Test access based on setting

**Expected Results:**
- PRIVATE: Only owner and superusers can access
- PUBLIC: Flow can be executed without authentication
- Access change is immediate
- Public flows have shareable URL
- API endpoint: `PATCH /api/v1/flows/{flow_id}` updates access field

---

### MAN-060: View Project Statistics

| Field | Details |
|-------|---------|
| **Description** | Verify project shows statistics (flow count, executions, etc.) |
| **Priority** | Low |
| **Preconditions** | - Project exists with flows and executions |

**Steps:**
1. Navigate to project details page
2. View project statistics section
3. Observe metrics displayed

**Expected Results:**
- Flow count is accurate
- Total executions count is shown
- Last activity timestamp is displayed
- Storage usage may be shown
- Success/failure rate may be shown

---

## 6. API Endpoints

### MAN-061: OpenAI-Compatible Chat Completions

| Field | Details |
|-------|---------|
| **Description** | Verify OpenAI-compatible API endpoint works with OpenAI SDK |
| **Priority** | Critical |
| **Preconditions** | - Flow configured for chat<br>- API key generated |

**Steps:**
1. Get API endpoint URL: `/api/v1/openai/chat/completions`
2. Configure OpenAI SDK with LangBuilder URL and API key
3. Send chat completion request
4. Verify response format matches OpenAI spec

**Expected Results:**
- Request is accepted and processed
- Response follows OpenAI format
- Streaming works if requested
- SDK client works without modification
- API endpoint: `POST /api/v1/openai/chat/completions` returns OpenAI-format response

---

### MAN-062: List Available Models (OpenAI Format)

| Field | Details |
|-------|---------|
| **Description** | Verify models endpoint lists flows as models |
| **Priority** | High |
| **Preconditions** | - Flows exist and are marked as endpoints |

**Steps:**
1. Send GET request to `/api/v1/openai/models`
2. Review list of returned models
3. Verify flows appear as models

**Expected Results:**
- Endpoint returns list of flow-models
- Response follows OpenAI models format
- Each flow has model ID, name, capabilities
- Only appropriate flows are exposed
- API endpoint: `GET /api/v1/openai/models` returns model list

---

### MAN-063: Execute Flow via REST API

| Field | Details |
|-------|---------|
| **Description** | Verify flow can be executed via direct API call |
| **Priority** | Critical |
| **Preconditions** | - Flow exists<br>- API authentication configured |

**Steps:**
1. Get flow ID
2. Send POST request to `/api/v1/build/{flow_id}/flow` with inputs
3. Include authentication header
4. Verify response contains outputs

**Expected Results:**
- Flow executes successfully
- Response includes execution results
- Status codes are appropriate (200, 400, 401, 500)
- Response time is reasonable
- API endpoint: `POST /api/v1/build/{flow_id}/flow` returns outputs

---

### MAN-064: Stream Flow Results via SSE

| Field | Details |
|-------|---------|
| **Description** | Verify SSE streaming for real-time results |
| **Priority** | High |
| **Preconditions** | - Flow is executing |

**Steps:**
1. Execute flow via API
2. Connect to SSE endpoint: `/api/v1/build/{flow_id}/events`
3. Listen for server-sent events
4. Parse events as they arrive

**Expected Results:**
- SSE connection is established
- Events stream in real-time
- Event types include: build_start, vertex_start, vertex_complete, token_stream, build_complete
- Connection closes gracefully on completion
- API endpoint: `GET /api/v1/build/{flow_id}/events` streams events

---

### MAN-065: Health Check Endpoint

| Field | Details |
|-------|---------|
| **Description** | Verify health check endpoint reports service status |
| **Priority** | Medium |
| **Preconditions** | - Service is running |

**Steps:**
1. Send GET request to `/health` or `/api/health`
2. Review response

**Expected Results:**
- Returns 200 OK if healthy
- Returns service status information
- Response includes version number
- Response is fast (< 100ms)
- Can be used for monitoring/alerting

---

### MAN-066: API Rate Limiting

| Field | Details |
|-------|---------|
| **Description** | Verify API rate limits are enforced |
| **Priority** | Medium |
| **Preconditions** | - Rate limiting is configured |

**Steps:**
1. Send multiple rapid requests to API
2. Exceed configured rate limit
3. Observe rate limit response

**Expected Results:**
- Requests within limit are processed
- Requests exceeding limit return 429 Too Many Requests
- Response headers include rate limit info
- Rate limit resets after time window
- Different limits for authenticated vs public

---

### MAN-067: Validate Flow Code

| Field | Details |
|-------|---------|
| **Description** | Verify flow validation endpoint checks flow integrity |
| **Priority** | Medium |
| **Preconditions** | - Flow exists (valid or invalid) |

**Steps:**
1. Send POST request to `/api/v1/validate/code` with flow data
2. Review validation response

**Expected Results:**
- Valid flows return success
- Invalid flows return specific error details
- Validation checks: syntax, type compatibility, required fields
- Response includes error locations
- API endpoint: `POST /api/v1/validate/code` returns validation result

---

### MAN-068: API Error Handling

| Field | Details |
|-------|---------|
| **Description** | Verify API returns appropriate error responses |
| **Priority** | High |
| **Preconditions** | - API is running |

**Steps:**
1. Send requests with various error conditions:
   - Missing authentication (401)
   - Insufficient permissions (403)
   - Resource not found (404)
   - Invalid input (400)
   - Server error (500)
2. Verify error responses

**Expected Results:**
- HTTP status codes are correct
- Error messages are descriptive
- Error format is consistent (JSON)
- Sensitive info is not exposed
- Error IDs for tracking/debugging

---

### MAN-069: List All Flows via API

| Field | Details |
|-------|---------|
| **Description** | Verify API endpoint lists user's flows |
| **Priority** | Medium |
| **Preconditions** | - User is authenticated<br>- User has flows |

**Steps:**
1. Send GET request to `/api/v1/flows/`
2. Include authentication
3. Review returned flows list

**Expected Results:**
- User's flows are returned
- Response includes flow metadata
- Pagination works if many flows
- Filters work (by project, date, etc.)
- API endpoint: `GET /api/v1/flows/` returns flow list

---

### MAN-070: Get Flow Details via API

| Field | Details |
|-------|---------|
| **Description** | Verify API returns complete flow definition |
| **Priority** | High |
| **Preconditions** | - Flow exists<br>- User has access |

**Steps:**
1. Send GET request to `/api/v1/flows/{flow_id}`
2. Include authentication
3. Review returned flow data

**Expected Results:**
- Complete flow definition is returned
- Includes nodes, edges, configurations
- Includes metadata (name, description, timestamps)
- Credentials are not exposed in response
- API endpoint: `GET /api/v1/flows/{flow_id}` returns flow

---

## 7. File Management

### MAN-071: Upload File

| Field | Details |
|-------|---------|
| **Description** | Verify user can upload files to LangBuilder |
| **Priority** | High |
| **Preconditions** | - User is logged in |

**Steps:**
1. Navigate to Files section or file upload area
2. Click "Upload" button
3. Select file from local system
4. Confirm upload
5. Wait for upload completion

**Expected Results:**
- File is uploaded successfully
- Progress indicator shows upload status
- File appears in files list
- File metadata is stored (name, size, type, timestamp)
- API endpoint: `POST /api/v1/files/upload/{flow_id}` returns 201

---

### MAN-072: Download File

| Field | Details |
|-------|---------|
| **Description** | Verify user can download previously uploaded files |
| **Priority** | High |
| **Preconditions** | - File exists in system |

**Steps:**
1. Navigate to Files list
2. Locate file to download
3. Click download button
4. Save file to local system

**Expected Results:**
- File downloads successfully
- Downloaded file matches uploaded file (hash verification)
- Filename is preserved
- API endpoint: `GET /api/v1/files/download/{file_id}` returns file

---

### MAN-073: Delete File

| Field | Details |
|-------|---------|
| **Description** | Verify user can delete uploaded files |
| **Priority** | Medium |
| **Preconditions** | - File exists<br>- User owns file |

**Steps:**
1. Navigate to Files list
2. Select file to delete
3. Click "Delete" button
4. Confirm deletion

**Expected Results:**
- File is removed from system
- File no longer appears in list
- Storage is freed
- Warning if file is used in flows
- API endpoint: `DELETE /api/v1/files/{file_id}` returns 200

---

### MAN-074: List Uploaded Files

| Field | Details |
|-------|---------|
| **Description** | Verify files list shows all user's uploads |
| **Priority** | Medium |
| **Preconditions** | - User has uploaded files |

**Steps:**
1. Navigate to Files section
2. View files list
3. Verify files are displayed with metadata

**Expected Results:**
- All user's files are listed
- Metadata shown: name, size, type, upload date
- List is sortable and searchable
- Pagination for many files
- API endpoint: `GET /api/v1/files/` returns files list

---

### MAN-075: Use File in Flow

| Field | Details |
|-------|---------|
| **Description** | Verify uploaded file can be referenced in flow |
| **Priority** | High |
| **Preconditions** | - File is uploaded<br>- Flow is open |

**Steps:**
1. Add file loader component to flow
2. Configure component to reference uploaded file
3. Select file from files list
4. Execute flow using file

**Expected Results:**
- File can be selected from dropdown/picker
- File content is loaded by component
- File path is correctly resolved
- File is processed according to component logic

---

### MAN-076: File Type Validation

| Field | Details |
|-------|---------|
| **Description** | Verify system validates file types on upload |
| **Priority** | Medium |
| **Preconditions** | - User attempts to upload various file types |

**Steps:**
1. Attempt to upload supported file types (PDF, TXT, CSV, etc.)
2. Attempt to upload unsupported/restricted file types (EXE, etc.)
3. Observe validation behavior

**Expected Results:**
- Supported file types upload successfully
- Unsupported file types are rejected
- Clear error message explains restriction
- File type is validated by extension and MIME type
- Security restrictions are enforced

---

### MAN-077: File Size Limits

| Field | Details |
|-------|---------|
| **Description** | Verify file size limits are enforced |
| **Priority** | Medium |
| **Preconditions** | - File size limit is configured (e.g., 100MB) |

**Steps:**
1. Attempt to upload file within size limit
2. Attempt to upload file exceeding size limit
3. Observe validation

**Expected Results:**
- Files within limit upload successfully
- Files exceeding limit are rejected
- Error message indicates size limit
- Upload does not consume resources before validation
- Limit is enforced on client and server side

---

### MAN-078: File Upload Progress

| Field | Details |
|-------|---------|
| **Description** | Verify upload progress is displayed for large files |
| **Priority** | Low |
| **Preconditions** | - Large file to upload |

**Steps:**
1. Begin uploading large file
2. Observe progress indicator
3. Monitor upload until completion

**Expected Results:**
- Progress bar shows upload percentage
- Upload can be cancelled mid-process
- Upload speed may be displayed
- Upload completion is clearly indicated

---

### MAN-079: File Preview

| Field | Details |
|-------|---------|
| **Description** | Verify supported file types can be previewed |
| **Priority** | Low |
| **Preconditions** | - Text or image file is uploaded |

**Steps:**
1. Navigate to Files list
2. Click on file to preview
3. View file preview

**Expected Results:**
- Text files show content preview
- Images display thumbnail or full image
- PDFs show page preview
- Unsupported types show metadata only

---

### MAN-080: File Search

| Field | Details |
|-------|---------|
| **Description** | Verify files can be searched by name |
| **Priority** | Low |
| **Preconditions** | - Multiple files uploaded |

**Steps:**
1. Navigate to Files list
2. Enter search term in search box
3. Observe filtered results

**Expected Results:**
- Files are filtered by name
- Search is case-insensitive
- Search updates in real-time
- Clear search to show all files

---

## 8. Store/Marketplace

### MAN-081: Browse Store Flows

| Field | Details |
|-------|---------|
| **Description** | Verify user can browse community/shared flows in store |
| **Priority** | High |
| **Preconditions** | - User is logged in<br>- Store has published flows |

**Steps:**
1. Navigate to Store or Marketplace section
2. Browse available flows
3. View flow categories/tags
4. Read flow descriptions and ratings

**Expected Results:**
- Store displays published flows
- Flows are organized by category
- Each flow shows: name, description, author, rating, download count
- Flows can be filtered/sorted
- API endpoint: `GET /api/v1/store/` returns store flows

---

### MAN-082: Search Store Flows

| Field | Details |
|-------|---------|
| **Description** | Verify store flows can be searched |
| **Priority** | Medium |
| **Preconditions** | - Store has published flows |

**Steps:**
1. Navigate to Store
2. Enter search term in store search box
3. Observe filtered results
4. Try different search terms

**Expected Results:**
- Search filters flows by name, description, tags
- Results are relevant to search term
- Search is case-insensitive
- No results message when no matches

---

### MAN-083: Download/Import Flow from Store

| Field | Details |
|-------|---------|
| **Description** | Verify flow can be downloaded from store and added to user's flows |
| **Priority** | Critical |
| **Preconditions** | - Store flow exists |

**Steps:**
1. Browse store and select flow
2. View flow details
3. Click "Download" or "Add to My Flows" button
4. Confirm action
5. Navigate to user's flows list

**Expected Results:**
- Flow is copied to user's account
- User can edit their copy
- Original store flow remains unchanged
- Flow appears in user's flows list
- API endpoint: Likely `POST /api/v1/store/flows/{flow_id}/download` or similar

---

### MAN-084: Publish Flow to Store

| Field | Details |
|-------|---------|
| **Description** | Verify user can publish their flow to store |
| **Priority** | High |
| **Preconditions** | - User owns a flow<br>- User has publish permissions |

**Steps:**
1. Open flow
2. Click "Publish to Store" option
3. Fill in store listing details (description, tags, category)
4. Set visibility (public)
5. Confirm publication

**Expected Results:**
- Flow is published to store
- Flow appears in store listings
- Other users can view and download
- Publisher retains ownership of original
- API endpoint: `POST /api/v1/publish/` publishes flow

---

### MAN-085: Unpublish Flow from Store

| Field | Details |
|-------|---------|
| **Description** | Verify user can remove their flow from store |
| **Priority** | Medium |
| **Preconditions** | - User has published flow in store |

**Steps:**
1. Navigate to user's published flows
2. Select flow to unpublish
3. Click "Unpublish" or "Remove from Store" button
4. Confirm action

**Expected Results:**
- Flow is removed from store listings
- Flow is no longer visible to other users
- User retains original flow
- Previously downloaded copies remain with other users

---

### MAN-086: Rate and Review Store Flow

| Field | Details |
|-------|---------|
| **Description** | Verify user can rate and review store flows |
| **Priority** | Low |
| **Preconditions** | - User has downloaded a store flow |

**Steps:**
1. Open store flow details
2. Click "Rate" or "Review" button
3. Provide star rating (1-5)
4. Optionally write review text
5. Submit rating/review

**Expected Results:**
- Rating is recorded
- Average rating is updated
- Review text is published (if provided)
- User can edit their rating later
- One rating per user per flow

---

### MAN-087: View Flow Statistics in Store

| Field | Details |
|-------|---------|
| **Description** | Verify store flows display usage statistics |
| **Priority** | Low |
| **Preconditions** | - Store flow has been downloaded and used |

**Steps:**
1. Open store flow details
2. View statistics section
3. Observe displayed metrics

**Expected Results:**
- Download count is shown
- View count is displayed
- Average rating is visible
- Recent activity may be shown
- Publisher can view detailed analytics

---

### MAN-088: Filter Store Flows by Category

| Field | Details |
|-------|---------|
| **Description** | Verify store flows can be filtered by category/tags |
| **Priority** | Medium |
| **Preconditions** | - Store has flows in multiple categories |

**Steps:**
1. Navigate to Store
2. Select category filter (e.g., "RAG", "Chatbots", "Data Processing")
3. Observe filtered results
4. Try multiple filters

**Expected Results:**
- Flows are filtered by selected category
- Multiple filters can be applied
- Filter count shows number of flows
- Clear filters to show all

---

### MAN-089: View Starter Projects

| Field | Details |
|-------|---------|
| **Description** | Verify starter/example projects are available |
| **Priority** | High |
| **Preconditions** | - Starter projects are configured |

**Steps:**
1. Navigate to Starter Projects or Examples section
2. Browse available starter projects
3. View project descriptions
4. Select a starter project to use

**Expected Results:**
- Multiple starter projects are available
- Each has clear description and use case
- Projects cover common scenarios (RAG, chat, agents)
- Projects can be opened directly
- API endpoint: `GET /api/v1/starter-projects/` returns starters

---

### MAN-090: Clone Starter Project

| Field | Details |
|-------|---------|
| **Description** | Verify starter project can be cloned to user's account |
| **Priority** | High |
| **Preconditions** | - Starter project exists |

**Steps:**
1. Select starter project
2. Click "Use This Template" or "Clone" button
3. Optionally rename
4. Confirm creation
5. View cloned flow in user's flows

**Expected Results:**
- Starter project is cloned
- User can edit their copy
- Original starter remains available
- Clone is fully functional
- All components are properly configured

---

## 9. Settings & Configuration

### MAN-091: Create Global Variable

| Field | Details |
|-------|---------|
| **Description** | Verify user can create global variables for reuse |
| **Priority** | High |
| **Preconditions** | - User is logged in |

**Steps:**
1. Navigate to Settings > Variables
2. Click "Add Variable" button
3. Enter variable name (e.g., "OPENAI_API_KEY")
4. Enter variable value
5. Select variable type (string/credential)
6. Save variable

**Expected Results:**
- Variable is created successfully
- Variable appears in variables list
- Credentials are encrypted at rest
- Variable can be referenced in flows using `{VARIABLE_NAME}`
- API endpoint: `POST /api/v1/variables/` returns 201

---

### MAN-092: Update Global Variable

| Field | Details |
|-------|---------|
| **Description** | Verify global variable can be modified |
| **Priority** | High |
| **Preconditions** | - Global variable exists |

**Steps:**
1. Navigate to Variables list
2. Select variable to edit
3. Modify value
4. Save changes
5. Verify flows using variable receive updated value

**Expected Results:**
- Variable value is updated
- Change takes effect immediately
- Flows using variable get new value on next execution
- Update history may be tracked
- API endpoint: `PATCH /api/v1/variables/{variable_id}` returns 200

---

### MAN-093: Delete Global Variable

| Field | Details |
|-------|---------|
| **Description** | Verify global variable can be removed |
| **Priority** | Medium |
| **Preconditions** | - Global variable exists |

**Steps:**
1. Navigate to Variables list
2. Select variable to delete
3. Click "Delete" button
4. Review warning about flows using variable
5. Confirm deletion

**Expected Results:**
- Warning shows which flows use variable
- Variable is deleted from system
- Flows referencing variable will error if executed
- User must update flows or create new variable
- API endpoint: `DELETE /api/v1/variables/{variable_id}` returns 200

---

### MAN-094: Configure User Profile

| Field | Details |
|-------|---------|
| **Description** | Verify user can update profile information |
| **Priority** | Medium |
| **Preconditions** | - User is logged in |

**Steps:**
1. Navigate to Settings > Profile
2. Update profile fields (name, email, bio)
3. Upload profile picture (if supported)
4. Save changes

**Expected Results:**
- Profile information is updated
- Changes reflect in UI
- Email change may require verification
- Profile picture is resized/optimized
- API endpoint: `PATCH /api/v1/users/{user_id}` returns 200

---

### MAN-095: Change Password

| Field | Details |
|-------|---------|
| **Description** | Verify user can change their password |
| **Priority** | High |
| **Preconditions** | - User is logged in |

**Steps:**
1. Navigate to Settings > Security
2. Click "Change Password"
3. Enter current password
4. Enter new password
5. Confirm new password
6. Submit change

**Expected Results:**
- Current password is validated
- New password meets requirements
- Password is updated in database (bcrypt hash)
- User remains logged in
- Notification of password change
- API endpoint: `PATCH /api/v1/users/{user_id}` updates password

---

### MAN-096: Configure Notification Preferences

| Field | Details |
|-------|---------|
| **Description** | Verify user can configure notification settings |
| **Priority** | Low |
| **Preconditions** | - User is logged in |

**Steps:**
1. Navigate to Settings > Notifications
2. Toggle notification preferences (email, in-app)
3. Select which events trigger notifications
4. Save preferences

**Expected Results:**
- Preferences are saved
- Notifications respect user preferences
- User can disable all notifications
- Changes take effect immediately

---

### MAN-097: View System Information

| Field | Details |
|-------|---------|
| **Description** | Verify system info page shows version and status |
| **Priority** | Low |
| **Preconditions** | - User is logged in (may be admin-only) |

**Steps:**
1. Navigate to Settings > System Info or About
2. View displayed information

**Expected Results:**
- LangBuilder version is shown (v1.6.5)
- Python version is displayed
- Database type is shown
- Dependency versions may be listed
- System health indicators present

---

### MAN-098: Configure Theme/Appearance

| Field | Details |
|-------|---------|
| **Description** | Verify user can customize UI appearance |
| **Priority** | Low |
| **Preconditions** | - User is logged in |

**Steps:**
1. Navigate to Settings > Appearance
2. Select theme (light/dark/auto)
3. Optionally configure accent colors
4. Apply changes

**Expected Results:**
- Theme changes immediately
- Preference is saved
- Theme persists across sessions
- All UI components respect theme

---

### MAN-099: Export User Data

| Field | Details |
|-------|---------|
| **Description** | Verify user can export their data (GDPR compliance) |
| **Priority** | Medium |
| **Preconditions** | - User is logged in |

**Steps:**
1. Navigate to Settings > Privacy
2. Click "Export My Data" button
3. Confirm export request
4. Wait for export processing
5. Download export archive

**Expected Results:**
- Export includes all user data (flows, variables, settings)
- Export is in portable format (JSON/ZIP)
- Export completion is notified
- Export can be downloaded
- Data is complete and readable

---

### MAN-100: Delete User Account

| Field | Details |
|-------|---------|
| **Description** | Verify user can delete their account |
| **Priority** | Medium |
| **Preconditions** | - User is logged in |

**Steps:**
1. Navigate to Settings > Account
2. Click "Delete Account" button
3. Review warning about data deletion
4. Confirm deletion with password
5. Account deletion is processed

**Expected Results:**
- Serious warning is displayed
- Password confirmation required
- All user data is deleted (flows, variables, etc.)
- User is logged out
- Account cannot be recovered
- API endpoint: `DELETE /api/v1/users/{user_id}` returns 200

---

## 10. Integration Testing

### MAN-101: OpenAI Integration

| Field | Details |
|-------|---------|
| **Description** | Verify OpenAI LLM integration works end-to-end |
| **Priority** | Critical |
| **Preconditions** | - Valid OpenAI API key<br>- OpenAI component available |

**Steps:**
1. Create new flow
2. Add OpenAI LLM component to canvas
3. Configure with API key and model (e.g., gpt-4)
4. Set temperature and other parameters
5. Add prompt input
6. Execute flow with test prompt

**Expected Results:**
- Component loads without errors
- Configuration options are complete
- API key is securely stored
- Execution calls OpenAI API successfully
- Response is returned and displayed
- Streaming works if enabled
- Error handling works for API failures

---

### MAN-102: Anthropic Claude Integration

| Field | Details |
|-------|---------|
| **Description** | Verify Anthropic Claude integration works end-to-end |
| **Priority** | High |
| **Preconditions** | - Valid Anthropic API key<br>- Anthropic component available |

**Steps:**
1. Create flow with Anthropic LLM component
2. Configure with API key and model (e.g., claude-3-opus)
3. Execute flow with test prompt

**Expected Results:**
- Component connects to Anthropic API
- Responses are returned correctly
- Streaming works if supported
- Component handles rate limits gracefully

---

### MAN-103: ChromaDB Vector Store Integration

| Field | Details |
|-------|---------|
| **Description** | Verify ChromaDB vector store integration for RAG |
| **Priority** | High |
| **Preconditions** | - ChromaDB accessible<br>- Embedding model configured |

**Steps:**
1. Create flow with document ingestion
2. Add ChromaDB vector store component
3. Configure collection name and connection
4. Add documents and generate embeddings
5. Perform similarity search
6. Verify retrieved documents

**Expected Results:**
- Connection to ChromaDB succeeds
- Documents are ingested and embedded
- Embeddings are stored in collection
- Similarity search returns relevant documents
- Metadata filtering works

---

### MAN-104: Pinecone Vector Store Integration

| Field | Details |
|-------|---------|
| **Description** | Verify Pinecone cloud vector store integration |
| **Priority** | High |
| **Preconditions** | - Pinecone account and API key<br>- Pinecone index created |

**Steps:**
1. Create RAG flow with Pinecone component
2. Configure API key and index name
3. Upload and embed documents
4. Execute search queries
5. Verify results

**Expected Results:**
- Pinecone connection is established
- Documents are upserted to index
- Search returns ranked results
- Metadata filtering works
- Namespaces work if configured

---

### MAN-105: LangSmith Observability Integration

| Field | Details |
|-------|---------|
| **Description** | Verify LangSmith tracing captures flow execution |
| **Priority** | Medium |
| **Preconditions** | - LangSmith account<br>- API key configured |

**Steps:**
1. Configure LangSmith API key in settings
2. Execute flow with LangSmith enabled
3. View traces in LangSmith dashboard
4. Verify execution details are captured

**Expected Results:**
- LangSmith captures flow execution traces
- All LLM calls are logged
- Latency and token usage tracked
- Errors are captured
- Traces link to flow executions

---

### MAN-106: Hugging Face Models Integration

| Field | Details |
|-------|---------|
| **Description** | Verify Hugging Face model integration |
| **Priority** | Medium |
| **Preconditions** | - Hugging Face API token<br>- Model selection available |

**Steps:**
1. Add Hugging Face LLM component
2. Configure API token
3. Select model from HF hub
4. Execute flow with model

**Expected Results:**
- HF models are accessible
- Inference runs successfully
- Both API and local models work (if supported)
- Model parameters are configurable

---

### MAN-107: Ollama Local Models Integration

| Field | Details |
|-------|---------|
| **Description** | Verify Ollama local model integration |
| **Priority** | Medium |
| **Preconditions** | - Ollama installed locally<br>- Model downloaded (e.g., llama2) |

**Steps:**
1. Add Ollama component to flow
2. Configure Ollama endpoint (typically localhost:11434)
3. Select local model
4. Execute flow

**Expected Results:**
- Component connects to local Ollama instance
- Available models are detected
- Inference runs without API keys
- Performance depends on local hardware
- Streaming works

---

### MAN-108: PostgreSQL/PGVector Integration

| Field | Details |
|-------|---------|
| **Description** | Verify PostgreSQL with pgvector extension for vector storage |
| **Priority** | Medium |
| **Preconditions** | - PostgreSQL with pgvector extension<br>- Database connection details |

**Steps:**
1. Configure PGVector component
2. Provide database connection string
3. Create vector collection
4. Store and query vectors
5. Verify SQL integration

**Expected Results:**
- Connection to PostgreSQL succeeds
- pgvector extension is utilized
- Vectors are stored efficiently
- Hybrid search (vector + SQL) works
- CRUD operations function correctly

---

### MAN-109: AWS Bedrock Integration

| Field | Details |
|-------|---------|
| **Description** | Verify AWS Bedrock LLM integration |
| **Priority** | Medium |
| **Preconditions** | - AWS account with Bedrock access<br>- AWS credentials configured |

**Steps:**
1. Add AWS Bedrock LLM component
2. Configure AWS credentials (access key, secret, region)
3. Select Bedrock model (e.g., Claude, Titan)
4. Execute flow

**Expected Results:**
- AWS authentication succeeds
- Bedrock models are accessible
- Inference calls work correctly
- Pricing and rate limits are respected
- Error handling for AWS errors

---

### MAN-110: Multi-Provider Comparison Flow

| Field | Details |
|-------|---------|
| **Description** | Verify flow can call multiple LLM providers in parallel |
| **Priority** | Medium |
| **Preconditions** | - Multiple LLM provider credentials<br>- Flow with parallel branches |

**Steps:**
1. Create flow with 3+ LLM providers in parallel
2. Configure each with same prompt
3. Execute flow
4. Compare responses

**Expected Results:**
- All providers execute in parallel
- Each returns response independently
- Execution time ~= slowest provider
- Responses can be compared
- Useful for A/B testing models

---

---

## Summary

This manual test scenarios document covers **110 test scenarios** across **10 functional areas** of LangBuilder v1.6.5:

| Functional Area | Scenario Count | Critical/High Priority |
|----------------|----------------|------------------------|
| 1. User Authentication & Authorization | 10 | 7 |
| 2. Flow Builder Canvas | 15 | 10 |
| 3. Component Management | 10 | 6 |
| 4. Flow Execution | 13 | 9 |
| 5. Project Management | 12 | 7 |
| 6. API Endpoints | 10 | 7 |
| 7. File Management | 10 | 5 |
| 8. Store/Marketplace | 10 | 5 |
| 9. Settings & Configuration | 10 | 4 |
| 10. Integration Testing | 10 | 5 |
| **Total** | **110** | **65** |

**Testing Recommendations:**

1. **Pre-Release**: Execute all Critical priority scenarios
2. **Release Candidates**: Execute Critical + High priority scenarios
3. **Regular Testing**: Rotate through all scenarios on a schedule
4. **New Features**: Add specific scenarios for new features
5. **Regression Testing**: Focus on areas with recent code changes
6. **Integration Testing**: Verify external service integrations regularly (API keys may expire)

**Automation Opportunities:**

Many of these scenarios can be automated using:
- **Backend API Testing**: pytest with httpx
- **E2E Testing**: Playwright (already in use with 150+ specs)
- **Integration Testing**: Custom test fixtures for external services
- **CI/CD Integration**: Run automated subset on every PR

**Next Steps:**

1. Review and prioritize scenarios based on release timeline
2. Assign scenarios to QA team members
3. Track test execution in test management tool
4. Update scenarios as features evolve
5. Automate high-value, stable scenarios

---

*Generated: 2026-02-09 | LangBuilder v1.6.5 | CG AIx SDLC*
