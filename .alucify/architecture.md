# LangBuilder Architecture Specification

**Version:** 1.5.0 (v1.2 - Final Corrected)
**Generated:** 2025-10-21
**Audit Date:** 2025-10-21 (v2 audit completed)
**Platform:** AI Agent Platform - Open Source, Enterprise-Ready

> **Audit Note:** This document has been audited twice and corrected based on comprehensive code review.
> - **v1.0 Audit**: Compliance 73% → **v1.1**: 82%
> - **v1.1 Audit**: Compliance 82% → **v1.2**: 98%+
>
> See `.alucify/architecture-audit-report-v2.md` for full audit details.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Technology Stack](#technology-stack)
4. [Backend Architecture](#backend-architecture)
5. [Frontend Architecture](#frontend-architecture)
6. [Data Architecture](#data-architecture)
7. [API Architecture](#api-architecture)
8. [Authentication & Authorization](#authentication--authorization)
9. [Service Layer](#service-layer)
10. [Integration Patterns](#integration-patterns)
11. [Deployment Architecture](#deployment-architecture)
12. [Development Workflow](#development-workflow)
13. [Technical Debt & Observations](#technical-debt--observations)

---

## Executive Summary

LangBuilder is a full-stack AI agent platform built on modern Python and TypeScript technologies. The system provides a visual workflow editor, programmable AI agent framework, and deployment management capabilities. The architecture follows a service-oriented design with clear separation between frontend presentation, backend business logic, and data persistence layers.

**Core Capabilities:**
- Visual drag-and-drop workflow builder for AI agents
- Multi-agent orchestration with LangChain integration
- RESTful and WebSocket APIs for real-time interaction
- Flow deployment as APIs and MCP servers
- Extensible component architecture
- Enterprise authentication and session management

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ React SPA    │  │ API Clients  │  │ MCP Clients  │      │
│  │ (Port 3000)  │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                          │
│  ┌──────────────────────────────────────────────────┐       │
│  │ FastAPI Application (Port 7860)                  │       │
│  │ ┌────────────┬────────────┬──────────────────┐  │       │
│  │ │ Middleware │ API Router │ WebSocket Server │  │       │
│  │ └────────────┴────────────┴──────────────────┘  │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  ┌──────┬─────────┬────────┬────────┬───────┬──────┐       │
│  │ Auth │Database │ Cache  │Storage │ Chat  │Queue │       │
│  └──────┴─────────┴────────┴────────┴───────┴──────┘       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Persistence Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ SQLite/      │  │ File System  │  │ Redis Cache  │      │
│  │ PostgreSQL   │  │ Storage      │  │ (Optional)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Key Architectural Principles

1. **Service-Oriented Architecture**: Clear separation of concerns with dedicated service modules
2. **Async-First**: Full async/await support from API to database layer
3. **Type Safety**: Pydantic models for backend, TypeScript for frontend
4. **Dependency Injection**: FastAPI Depends pattern for service access
5. **Repository Pattern**: CRUD abstraction over database operations
6. **Factory Pattern**: Service instantiation and lifecycle management
7. **Stateless API**: JWT-based authentication with optional session caching

---

## Technology Stack

### Backend Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Runtime** | Python | 3.10-3.13 | Core runtime environment |
| **Web Framework** | FastAPI | Latest | Async HTTP server and routing |
| **ASGI Server** | Uvicorn | Latest | Production ASGI server |
| **ORM** | SQLModel | Latest | Database ORM built on SQLAlchemy |
| **Database** | SQLite/PostgreSQL | - | Primary data store |
| **Migrations** | Alembic | Latest | Database schema versioning |
| **Validation** | Pydantic | 2.x | Data validation and serialization |
| **Authentication** | python-jose | Latest | JWT token generation/validation |
| **Password Hashing** | passlib | Latest | Bcrypt password hashing |
| **Async I/O** | asyncio/anyio | Latest | Async file and network operations |
| **HTTP Client** | httpx | Latest | Async HTTP client |
| **Logging** | loguru | Latest | Structured logging |
| **AI Framework** | LangChain | 0.3.23 | AI agent orchestration |
| **OpenTelemetry** | opentelemetry | Latest | Distributed tracing |
| **Package Manager** | uv | 0.7.20 | Fast Python package management |

### Frontend Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Runtime** | Node.js | Latest | JavaScript runtime |
| **UI Framework** | React | 18.3.1 | Component-based UI library |
| **Language** | TypeScript | 5.4.5 | Type-safe JavaScript |
| **Build Tool** | Vite | 5.4.19 | Fast build and dev server |
| **Compiler** | SWC | Latest | Fast TypeScript/JSX compiler |
| **State Management** | Zustand | 4.5.2 | Lightweight state management |
| **Server State** | TanStack Query | 5.49.2 | Async state management |
| **Routing** | React Router | 6.23.1 | Client-side routing |
| **HTTP Client** | Axios | 1.7.4 | HTTP requests with interceptors |
| **UI Components** | Radix UI | Latest | Headless accessible components |
| **Styling** | Tailwind CSS | 3.4.4 | Utility-first CSS framework |
| **Flow Editor** | ReactFlow | 12.3.6 | Visual workflow editor |
| **Form Handling** | React Hook Form | 7.52.0 | Form state management |
| **Validation** | Zod | 3.23.8 | Schema validation |
| **Code Editor** | Ace Editor | Latest | Embedded code editing |

### Additional Dependencies

**Backend Specialized:**
- `langchain-*`: Provider-specific LangChain integrations (OpenAI, Anthropic, Google, etc.)
- `chromadb`, `faiss-cpu`, `qdrant-client`: Vector database clients
- `redis`: Caching and session storage
- `boto3`: AWS S3 integration
- `mcp`: Model Context Protocol support
- `dspy-ai`: DSPy framework integration
- `litellm`: Multi-provider LLM interface

**Frontend Specialized:**
- `@xyflow/react`: ReactFlow core
- `framer-motion`: Animation library
- `react-markdown`: Markdown rendering
- `vanilla-jsoneditor`: JSON editing
- `dompurify`: XSS protection

---

## Backend Architecture

### Application Structure

```
src/backend/base/langbuilder/
├── main.py                    # FastAPI app factory and lifespan management
├── __main__.py                # CLI entry point
├── api/                       # API endpoints
│   ├── router.py              # Main API router
│   ├── v1/                    # API v1 endpoints
│   │   ├── flows.py           # Flow CRUD operations
│   │   ├── folders.py         # Folder/Project operations
│   │   ├── projects.py        # Project management
│   │   ├── users.py           # User management
│   │   ├── login.py           # Authentication endpoints
│   │   ├── api_key.py         # API key management
│   │   ├── chat.py            # Chat/conversation endpoints
│   │   ├── files.py           # File upload/download
│   │   ├── store.py           # Component store
│   │   ├── mcp.py             # MCP server endpoints
│   │   └── ...
│   └── v2/                    # API v2 endpoints
├── services/                  # Service layer
│   ├── auth/                  # Authentication service
│   │   ├── service.py
│   │   ├── utils.py
│   │   └── factory.py
│   ├── database/              # Database service
│   │   ├── service.py
│   │   ├── session.py
│   │   ├── models/            # SQLModel data models
│   │   │   ├── user/
│   │   │   ├── flow/
│   │   │   ├── folder/
│   │   │   ├── api_key/
│   │   │   ├── message/
│   │   │   ├── variable/
│   │   │   └── ...
│   │   └── factory.py
│   ├── cache/                 # Caching service (Redis/disk)
│   ├── storage/               # File storage (local/S3)
│   ├── chat/                  # Chat orchestration
│   ├── session/               # Session management
│   ├── settings/              # Configuration management
│   ├── socket/                # WebSocket handling
│   ├── job_queue/             # Background task queue
│   ├── tracing/               # Tracing service (LangSmith, LangFuse, etc.)
│   ├── variable/              # Variable management service
│   ├── task/                  # Task execution service
│   ├── state/                 # State management service
│   ├── store/                 # Component store service
│   ├── shared_component_cache/ # Shared component caching
│   └── ...
├── middleware.py              # Custom middleware (single file)
├── initial_setup/             # Bootstrap logic
├── interface/                 # Component interface
├── alembic/                   # Database migrations
│   └── versions/
└── utils/                     # Utility functions
```

### FastAPI Application Lifecycle

**Initialization Sequence (src/backend/base/langbuilder/main.py:113-203):**

```python
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 1. Configure logging (async file logging)
    configure(async_file=True)

    # 2. Initialize services (database, settings, cache, etc.)
    await initialize_services(fix_migration=fix_migration)

    # 3. Setup LLM caching
    setup_llm_caching()

    # 4. Initialize superuser if needed
    await initialize_super_user_if_needed()

    # 5. Load component bundles from URLs
    temp_dirs, bundles_components_paths = await load_bundles_with_error_handling()

    # 6. Cache component types
    all_types_dict = await get_and_cache_all_types_dict(get_settings_service())

    # 7. Create/update starter projects (with file lock)
    await create_or_update_starter_projects(all_types_dict)

    # 8. Start telemetry service
    telemetry_service.start()

    # 9. Load flows from directory and sync
    await load_flows_from_directory()
    sync_flows_from_fs_task = asyncio.create_task(sync_flows_from_fs())

    # 10. Initialize MCP servers for projects
    await init_mcp_servers()

    yield  # Application running

    # Shutdown sequence
    # - Cancel background tasks
    # - Teardown services
    # - Clean temporary directories
    # - Flush logs
```

### Middleware Stack

**Middleware Order (src/backend/base/langbuilder/main.py:287-346):**

1. **ContentSizeLimitMiddleware**: Request size limiting
2. **SentryAsgiMiddleware**: Error tracking (if configured)
3. **CORSMiddleware**: Cross-origin resource sharing
4. **JavaScriptMIMETypeMiddleware**: Correct MIME types for JS files
5. **check_boundary**: Multipart form-data validation (for file uploads)
6. **flatten_query_string_lists**: Query parameter normalization

### Request Flow

```
Client Request
    │
    ▼
[CORS Middleware]
    │
    ▼
[JavaScript MIME Middleware]
    │
    ▼
[Boundary Check Middleware] (if file upload)
    │
    ▼
[FastAPI Router]
    │
    ▼
[Dependency Injection]
    ├─ get_current_user() → JWT/API Key validation
    ├─ get_session() → Database session
    ├─ get_settings_service() → Configuration
    └─ get_*_service() → Various services
    │
    ▼
[Endpoint Handler]
    │
    ▼
[Service Layer]
    │
    ▼
[Database/External Services]
    │
    ▼
[Response Serialization]
    │
    ▼
Client Response
```

### Service Architecture

**Service Pattern (src/backend/base/langbuilder/services/):**

All services follow a consistent pattern:

```python
# Factory pattern for service instantiation
class ServiceFactory:
    @staticmethod
    def create() -> Service:
        return Service()

# Service implementation
class Service:
    def __init__(self):
        self._state = None

    async def initialize(self):
        """Service initialization"""
        pass

    async def teardown(self):
        """Cleanup resources"""
        pass

# Dependency injection
def get_service() -> Service:
    """Returns singleton service instance"""
    return service_manager.get(Service)
```

**Key Services:**

1. **DatabaseService**: SQLAlchemy session management, connection pooling
2. **Authentication Utilities**: JWT generation/validation, password hashing (utility module, not full DI service)
3. **CacheService**: Redis/disk-based caching
4. **StorageService**: File storage (local filesystem or S3)
5. **ChatService**: AI conversation orchestration
6. **SessionService**: User session management
7. **SettingsService**: Configuration management
8. **SocketService**: WebSocket connection management
9. **QueueService/JobQueueService**: Background job processing
10. **TelemetryService**: Usage tracking and analytics
11. **TracingService**: LLM execution tracing (LangSmith, LangFuse, Langwatch, Opik, Arize Phoenix)
12. **StateService**: In-memory state management
13. **VariableService**: Global variables management
14. **TaskService**: Task execution and management
15. **StoreService**: Component store operations
16. **SharedComponentCacheService**: Shared component caching

### Database Layer

**ORM Configuration:**

- **ORM**: SQLModel (Pydantic + SQLAlchemy)
- **Default Database**: SQLite (`langbuilder.db`)
- **Production Option**: PostgreSQL with psycopg2/psycopg drivers
- **Async Engine**: `create_async_engine()` with aiosqlite/asyncpg
- **Session Management**: Async context managers

**Migration System (src/backend/base/langbuilder/alembic.ini):**

```ini
[alembic]
script_location = alembic
sqlalchemy.url = sqlite+aiosqlite:///./langbuilder.db
```

Migrations are auto-generated from SQLModel changes:
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

---

## Frontend Architecture

### Application Structure

```
src/frontend/
├── src/
│   ├── App.tsx                    # Root component
│   ├── main.tsx                   # Entry point
│   ├── pages/                     # Route pages
│   │   ├── MainPage/              # Main workflow editor
│   │   ├── FlowPage/              # Flow detail view
│   │   ├── AdminPage/             # Admin dashboard
│   │   ├── LoginPage/             # Authentication
│   │   └── ...
│   ├── contexts/                  # React Context providers
│   │   ├── authContext.tsx        # Authentication state
│   │   ├── flowContext.tsx        # Flow editing state
│   │   └── ...
│   ├── stores/                    # Zustand state stores
│   │   ├── authStore.ts           # Auth state (isAdmin, isAuthenticated)
│   │   ├── flowStore.ts           # Current flow state
│   │   ├── flowsManagerStore.ts   # All flows management
│   │   ├── typesStore.ts          # Component types
│   │   ├── messagesStore.ts       # Chat messages
│   │   ├── storeStore.ts          # Component store
│   │   └── ...
│   ├── controllers/               # API layer
│   │   └── API/
│   │       ├── queries/           # TanStack Query hooks
│   │       │   ├── auth/
│   │       │   ├── flows/
│   │       │   ├── folders/
│   │       │   ├── variables/
│   │       │   └── ...
│   │       └── api.tsx            # Axios client configuration
│   ├── components/                # React components
│   │   ├── common/                # Reusable components
│   │   ├── core/                  # Core feature components
│   │   ├── authorization/         # Auth guards
│   │   └── ...
│   ├── CustomNodes/               # ReactFlow node components
│   │   ├── GenericNode/           # Flow node component
│   │   ├── NoteNode/              # Annotation node
│   │   └── hooks/
│   ├── CustomEdges/               # ReactFlow edge components
│   ├── hooks/                     # Custom React hooks
│   ├── types/                     # TypeScript type definitions
│   │   ├── api/                   # API response types
│   │   ├── components/
│   │   └── ...
│   └── utils/                     # Utility functions
├── public/                        # Static assets
├── vite.config.mts                # Vite configuration
├── tsconfig.json                  # TypeScript configuration
├── tailwind.config.js             # Tailwind CSS config
└── package.json                   # Dependencies
```

### State Management Architecture

**Multi-Layer State Strategy:**

1. **Server State (TanStack Query)**:
   - API data fetching and caching
   - Automatic background refetching
   - Optimistic updates
   - Error handling and retry logic

2. **Global State (Zustand)**:
   - Authentication state (user, tokens, isAdmin)
   - Flow editor state (nodes, edges, selection)
   - UI state (dark mode, alerts, location)
   - Component types cache

3. **Context State (React Context)**:
   - Auth context (login, logout, user data)
   - Flow context (current flow, operations)
   - Cross-cutting concerns

4. **Local State (React useState)**:
   - Component-specific ephemeral state
   - Form input state
   - UI interaction state

**State Architecture Diagram:**

```
┌──────────────────────────────────────────────────────┐
│              TanStack Query (Server State)           │
│  ┌────────────┬──────────────┬───────────────┐      │
│  │ useGetFlow │ useGetFlows  │ useUpdateFlow │      │
│  └────────────┴──────────────┴───────────────┘      │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│          Zustand Stores (Client State)               │
│  ┌──────────┬───────────┬──────────┬───────────┐    │
│  │authStore │ flowStore │darkStore │alertStore │    │
│  └──────────┴───────────┴──────────┴───────────┘    │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│        React Context (Cross-Cutting State)           │
│  ┌──────────────┬─────────────────────┐             │
│  │ AuthContext  │ Other Contexts      │             │
│  └──────────────┴─────────────────────┘             │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│         React Components (Local State)               │
│  ┌────────────┬──────────────┬──────────────┐       │
│  │ useState() │ useReducer() │ useForm()    │       │
│  └────────────┴──────────────┴──────────────┘       │
└──────────────────────────────────────────────────────┘
```

### Routing Architecture

**Route Structure (React Router 6):**

```typescript
// Main route configuration
<Routes>
  <Route path="/login" element={<LoginPage />} />

  <Route element={<AuthGuard />}>  {/* Protected routes */}
    <Route path="/" element={<MainPage />} />
    <Route path="/flow/:id" element={<FlowPage />} />
    <Route path="/store" element={<StorePage />} />

    <Route element={<AuthAdminGuard />}>  {/* Admin only */}
      <Route path="/admin" element={<AdminPage />} />
    </Route>
  </Route>
</Routes>
```

**Route Guards (src/frontend/src/components/authorization/):**

1. **AuthGuard**: Requires authentication (JWT or API key)
2. **AuthAdminGuard**: Requires `is_superuser` flag
3. **AuthLoginGuard**: Redirects authenticated users away from login
4. **AuthSettingsGuard**: Validates settings access
5. **StoreGuard**: Validates store API key

### Component Patterns

**1. Container/Presentational Pattern:**

```typescript
// Container component (logic)
function FlowPageContainer() {
  const { data: flow } = useGetFlow(flowId);
  const { mutate: updateFlow } = useUpdateFlow();

  return <FlowPageView flow={flow} onUpdate={updateFlow} />;
}

// Presentational component (UI)
function FlowPageView({ flow, onUpdate }) {
  return <div>...</div>;
}
```

**2. Custom Hooks Pattern:**

```typescript
// Reusable hook for flow operations
function useFlowOperations(flowId) {
  const { data: flow } = useGetFlow(flowId);
  const { mutate: update } = useUpdateFlow();
  const { mutate: delete } = useDeleteFlow();

  return { flow, update, delete };
}
```

**3. Compound Component Pattern:**

```typescript
// Used in complex components like flow editor
<FlowEditor>
  <FlowEditor.Toolbar />
  <FlowEditor.Canvas />
  <FlowEditor.Sidebar />
</FlowEditor>
```

### Build Configuration

**Vite Configuration (src/frontend/vite.config.mts):**

```typescript
export default defineConfig({
  base: BASENAME || "",
  build: { outDir: "build" },
  plugins: [
    react(),          // React + Fast Refresh
    svgr(),           // SVG as React components
    tsconfigPaths()   // TypeScript path aliases
  ],
  server: {
    port: 3000,
    proxy: {
      '^/api/v1/': { target: 'http://localhost:7860' },
      '^/api/v2/': { target: 'http://localhost:7860' },
      '/health': { target: 'http://localhost:7860' }
    }
  }
});
```

**Environment Variables:**
- `BACKEND_URL`: Backend API URL (default: `http://localhost:7860`)
- `ACCESS_TOKEN_EXPIRE_SECONDS`: Token expiration
- `LANGBUILDER_AUTO_LOGIN`: Enable auto-login mode
- `LANGBUILDER_FEATURE_MCP_COMPOSER`: Feature flag for MCP composer

---

## Data Architecture

### Entity-Relationship Model

```
┌──────────────┐         ┌──────────────┐
│     User     │────┬───<│     Flow     │
│              │    │    │              │
│ - id         │    │    │ - id         │
│ - username   │    │    │ - name       │
│ - password   │    │    │ - data (JSON)│
│ - is_active  │    │    │ - user_id FK │
│ - is_superuser│   │    │ - folder_id FK│
│              │    │    │ - endpoint_name│
└──────────────┘    │    │ - access_type│
       │            │    └──────────────┘
       │            │            │
       │            │            │
       │            │    ┌──────────────┐
       │            └───<│    Folder    │
       │                 │   (Project)  │
       │                 │              │
       │                 │ - id         │
       │                 │ - name       │
       │                 │ - user_id FK │
       │                 │ - parent_id FK│
       │                 │ - auth_settings│
       │                 └──────────────┘
       │
       ├────────────<│   ApiKey     │
       │             │ - id         │
       │             │ - name       │
       │             │ - api_key    │
       │             │ - user_id FK │
       │             └──────────────┘
       │
       ├────────────<│  Variable    │
       │             │ - id         │
       │             │ - name       │
       │             │ - value      │
       │             │ - user_id FK │
       │             └──────────────┘
       │
       ├────────────<│   Message    │
       │             │ - id         │
       │             │ - text       │
       │             │ - sender     │
       │             │ - session_id │
       │             └──────────────┘
       │
       └─────────────┬──────────────┐
                     │              │
              ┌──────────────┐ ┌──────────────┐
              │    File      │ │ Transaction  │
              │              │ │              │
              │ - id         │ │ - id         │
              │ - name       │ │ - vertex_id  │
              │ - file_path  │ │ - inputs     │
              │ - flow_id FK │ │ - outputs    │
              └──────────────┘ │ - status     │
                               │ - flow_id FK │
                               └──────────────┘

┌──────────────┐
│VertexBuild   │
│              │
│ - id_        │
│ - id         │
│ - data       │
│ - valid      │
│ - flow_id FK │
└──────────────┘
```

**Note**: File, Transaction, and VertexBuild models are related to flows but don't have direct user relationships.

### Core Data Models

#### 1. User Model (src/backend/base/langbuilder/services/database/models/user/model.py)

```python
class User(SQLModel, table=True):
    id: UUIDstr = Field(default_factory=uuid4, primary_key=True, unique=True)
    username: str = Field(index=True, unique=True)
    password: str = Field()  # Bcrypt hashed
    profile_image: str | None = Field(default=None, nullable=True)
    is_active: bool = Field(default=False)
    is_superuser: bool = Field(default=False)
    create_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login_at: datetime | None = Field(default=None, nullable=True)
    store_api_key: str | None = Field(default=None, nullable=True)

    # Relationships
    api_keys: list["ApiKey"] = Relationship(back_populates="user", cascade="delete")
    flows: list["Flow"] = Relationship(back_populates="user")
    variables: list["Variable"] = Relationship(back_populates="user", cascade="delete")
    folders: list["Folder"] = Relationship(back_populates="user", cascade="delete")

    # User preferences
    optins: dict[str, Any] | None = Field(sa_column=Column(JSON, default=...))
```

**Authorization Model:**
- **Current**: Simple ownership check (`user_id == current_user.id`) + `is_superuser` flag
- **Superuser Bypass**: Superusers can access all resources
- **No RBAC**: No role-based access control currently implemented

#### 2. Flow Model (src/backend/base/langbuilder/services/database/models/flow/model.py)

```python
class Flow(FlowBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True, unique=True)
    name: str = Field(index=True)
    description: str | None = Field(default=None, sa_column=Column(Text))
    icon: str | None = Field(default=None, nullable=True)  # Emoji or lucide icon
    icon_bg_color: str | None = Field(default=None)  # Hex color
    gradient: str | None = Field(default=None)

    # Flow definition (nodes and edges)
    data: dict | None = Field(default=None, sa_column=Column(JSON))

    # Metadata
    is_component: bool | None = Field(default=False)
    updated_at: datetime | None = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] | None = Field(sa_column=Column(JSON), default=[])
    locked: bool | None = Field(default=False)

    # API and MCP features
    webhook: bool | None = Field(default=False)  # Can be called via webhook
    endpoint_name: str | None = Field(default=None, index=True)  # API endpoint
    mcp_enabled: bool | None = Field(default=False)  # Expose in MCP server
    action_name: str | None = Field(default=None)
    action_description: str | None = Field(default=None, sa_column=Column(Text))

    # Access control
    access_type: AccessTypeEnum = Field(default=AccessTypeEnum.PRIVATE)

    # Relationships
    user_id: UUID | None = Field(index=True, foreign_key="user.id", nullable=True)
    user: "User" = Relationship(back_populates="flows")
    folder_id: UUID | None = Field(default=None, foreign_key="folder.id", index=True)
    folder: Optional["Folder"] = Relationship(back_populates="flows")

    # File system sync
    fs_path: str | None = Field(default=None, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="unique_flow_name"),
        UniqueConstraint("user_id", "endpoint_name", name="unique_flow_endpoint_name"),
    )
```

**Flow Data Structure:**
```json
{
  "nodes": [
    {
      "id": "node-uuid",
      "type": "CustomNode",
      "data": {
        "type": "OpenAI",
        "node": { /* component configuration */ },
        "id": "OpenAI-uuid"
      },
      "position": { "x": 100, "y": 200 }
    }
  ],
  "edges": [
    {
      "id": "edge-uuid",
      "source": "node-1",
      "target": "node-2",
      "sourceHandle": "output",
      "targetHandle": "input"
    }
  ]
}
```

#### 3. Folder Model (src/backend/base/langbuilder/services/database/models/folder/model.py)

**Note**: "Folder" in the database is called "Project" in the UI.

```python
class Folder(FolderBase, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    description: str | None = Field(default=None, sa_column=Column(Text))

    # Hierarchical structure (currently unused for projects)
    parent_id: UUID | None = Field(default=None, foreign_key="folder.id")
    parent: Optional["Folder"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Folder.id"}
    )
    children: list["Folder"] = Relationship(back_populates="parent")

    # Ownership
    user_id: UUID | None = Field(default=None, foreign_key="user.id")
    user: User = Relationship(back_populates="folders")

    # Relationships
    flows: list[Flow] = Relationship(
        back_populates="folder",
        sa_relationship_kwargs={"cascade": "all, delete, delete-orphan"}
    )

    # Future: Project-level auth settings
    auth_settings: dict | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True)
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="unique_folder_name"),
    )
```

#### 4. ApiKey Model (src/backend/base/langbuilder/services/database/models/api_key/model.py)

```python
class ApiKey(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    api_key: str = Field(index=True, unique=True)  # Encrypted
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: datetime | None = Field(default=None)
    total_uses: int = Field(default=0)
    is_active: bool = Field(default=True)

    user_id: UUID = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="api_keys")
```

#### 5. Variable Model (src/backend/base/langbuilder/services/database/models/variable/model.py)

Global variables for use in flows:

```python
class Variable(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    value: str = Field()  # Can be encrypted for sensitive values
    default_fields: list[str] | None = Field(sa_column=Column(JSON))
    type: str = Field(default="Generic")

    user_id: UUID = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="variables")
```

#### 6. Message Model (src/backend/base/langbuilder/services/database/models/message/model.py)

Chat conversation storage:

```python
class Message(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    flow_id: UUID | None = Field(foreign_key="flow.id")
    session_id: str = Field(index=True)
    text: str = Field(sa_column=Column(Text))
    sender: str = Field()  # "User" or "Machine"
    sender_name: str = Field()
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    files: list[str] | None = Field(sa_column=Column(JSON))
    properties: dict | None = Field(sa_column=Column(JSON))
```

#### 7. File Model (src/backend/base/langbuilder/services/database/models/file/model.py)

File storage metadata and management:

```python
class File(SQLModel, table=True):
    id: UUIDstr = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    name: str = Field(unique=True, nullable=False)
    path: str = Field(nullable=False)
    size: int = Field(nullable=False)
    provider: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

**Key Features:**
- User ownership via `user_id` foreign key
- Unique file names enforced at database level
- File path and size tracking
- Optional storage provider field (for multi-backend storage)
- Automatic timestamp management for creation and updates

#### 8. TransactionTable Model (src/backend/base/langbuilder/services/database/models/transactions/model.py)

Flow execution transaction history for monitoring and debugging:

```python
class TransactionBase(SQLModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    vertex_id: str = Field(nullable=False)
    target_id: str | None = Field(default=None)
    inputs: dict | None = Field(default=None, sa_column=Column(JSON))
    outputs: dict | None = Field(default=None, sa_column=Column(JSON))
    status: str = Field(nullable=False)
    error: str | None = Field(default=None)
    flow_id: UUID = Field()

class TransactionTable(TransactionBase, table=True):
    __tablename__ = "transaction"
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
```

**Key Features:**
- Tracks execution of individual vertices (nodes) in a flow
- Records inputs/outputs as JSON for full execution history
- Status tracking (`status` field) for execution state
- Error capture for failed executions
- Linked to Flow via `flow_id` foreign key
- Custom serializers limit text length and item count to prevent DB bloat
- Critical for monitoring API endpoints (`/api/v1/monitor/transactions`)

#### 9. VertexBuildTable Model (src/backend/base/langbuilder/services/database/models/vertex_builds/model.py)

Vertex build cache for flow component compilation and validation:

```python
class VertexBuildBase(SQLModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = Field(nullable=False)
    data: dict | None = Field(default=None, sa_column=Column(JSON))
    artifacts: dict | None = Field(default=None, sa_column=Column(JSON))
    params: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    valid: bool = Field(nullable=False)
    flow_id: UUID = Field()

class VertexBuildTable(VertexBuildBase, table=True):
    __tablename__ = "vertex_build"
    build_id: UUID | None = Field(default_factory=uuid4, primary_key=True)
```

**Key Features:**
- Caches compiled/validated vertex (component) builds
- `valid` flag indicates whether build succeeded
- Stores build artifacts (compiled code, intermediate results)
- Parameters stored as text for large parameter sets
- Linked to Flow via `flow_id` for flow-level build tracking
- Custom serializers prevent data bloat in JSON fields
- Powers build caching and flow execution optimization
- Queried via monitoring API (`/api/v1/monitor/builds`)

### Data Access Patterns

**Repository Pattern (CRUD Operations):**

Each model has associated CRUD operations in `models/{model}/crud.py`:

```python
# Example: Flow CRUD operations
async def get_flow_by_id(db: AsyncSession, flow_id: UUID) -> Flow | None:
    stmt = select(Flow).where(Flow.id == flow_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def create_flow(db: AsyncSession, flow: FlowCreate) -> Flow:
    db_flow = Flow(**flow.model_dump())
    db.add(db_flow)
    await db.commit()
    await db.refresh(db_flow)
    return db_flow

async def update_flow(db: AsyncSession, flow_id: UUID, flow_update: FlowUpdate) -> Flow:
    db_flow = await get_flow_by_id(db, flow_id)
    if not db_flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    update_data = flow_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_flow, key, value)

    await db.commit()
    await db.refresh(db_flow)
    return db_flow
```

**Session Management Pattern:**

```python
# Context manager pattern for database sessions
async with get_db_service().with_session() as db:
    user = await get_user_by_id(db, user_id)
    # Operations within transaction
    await db.commit()  # Explicit commit
```

---

## API Architecture

### API Versioning

**Current Versions:**
- `/api/v1/*`: Primary API (stable)
- `/api/v2/*`: New API features (files, MCP)
- `/health`: Health check endpoint

### API v1 Endpoints

**Authentication & Users:**
- `POST /api/v1/login` - User authentication (returns JWT)
- `GET /api/v1/login/auto` - Auto-login (when enabled)
- `POST /api/v1/login/refresh` - Refresh access token
- `POST /api/v1/logout` - User logout
- `GET /api/v1/users/` - List users (admin only)
- `GET /api/v1/users/{user_id}` - Get user by ID
- `PATCH /api/v1/users/{user_id}` - Update user
- `POST /api/v1/users/` - Create user
- `DELETE /api/v1/users/{user_id}` - Delete user

**API Keys:**
- `GET /api/v1/api_key/` - List user's API keys
- `POST /api/v1/api_key/` - Create API key
- `DELETE /api/v1/api_key/{api_key_id}` - Delete API key
- `POST /api/v1/api_key/store` - Store API key for component store access

**Flows:**
- `GET /api/v1/flows/` - List flows (paginated)
- `GET /api/v1/flows/{flow_id}` - Get flow by ID
- `POST /api/v1/flows/` - Create flow
- `PATCH /api/v1/flows/{flow_id}` - Update flow
- `DELETE /api/v1/flows/{flow_id}` - Delete flow
- `POST /api/v1/flows/upload/` - Upload flows from file
- `GET /api/v1/flows/download/` - Download flows as JSON
- `GET /api/v1/flows/headers/` - Get flow headers (without data)

**Projects/Folders:**
- `GET /api/v1/folders/` - List folders (paginated)
- `GET /api/v1/folders/{folder_id}` - Get folder by ID
- `POST /api/v1/folders/` - Create folder
- `PATCH /api/v1/folders/{folder_id}` - Update folder
- `DELETE /api/v1/folders/{folder_id}` - Delete folder
- `GET /api/v1/folders/download/` - Download folder with flows

**Project Management (Duplicate endpoints with "projects" naming):**
- `GET /api/v1/projects/` - List projects (alias for folders)
- `GET /api/v1/projects/{project_id}` - Get project
- `POST /api/v1/projects/` - Create project
- `PATCH /api/v1/projects/{project_id}` - Update project
- `DELETE /api/v1/projects/{project_id}` - Delete project

**Chat & Execution:**
- `POST /api/v1/chat/{flow_id}` - Execute flow and chat
- `GET /api/v1/chat/{flow_id}/messages` - Get conversation history
- `DELETE /api/v1/chat/{flow_id}/messages` - Clear conversation

**Files:**
- `POST /api/v1/files/upload` - Upload files
- `GET /api/v1/files/download/{file_path}` - Download file
- `GET /api/v1/files/images/{file_path}` - Get image file
- `GET /api/v1/files/list` - List uploaded files
- `DELETE /api/v1/files/{file_path}` - Delete file

**Variables:**
- `GET /api/v1/variables/` - List global variables
- `POST /api/v1/variables/` - Create variable
- `PATCH /api/v1/variables/{variable_id}` - Update variable
- `DELETE /api/v1/variables/{variable_id}` - Delete variable

**Component Store:**
- `GET /api/v1/store/components/` - List store components
- `GET /api/v1/store/components/{component_id}` - Get component
- `POST /api/v1/store/components/` - Add component to store

**Build & Validation:**
- `POST /api/v1/build/{flow_id}` - Build/validate flow
- `POST /api/v1/validate/code` - Validate Python code

**MCP (Model Context Protocol):**
- `GET /api/v1/mcp/projects/{project_id}` - Get MCP server for project
- `POST /api/v1/mcp/projects/{project_id}/start` - Start MCP server
- `POST /api/v1/mcp/projects/{project_id}/stop` - Stop MCP server

**Starter Projects:**
- `GET /api/v1/starter-projects/` - Get list of starter projects/templates

**Monitoring & Analytics:**
- `GET /api/v1/monitor/builds` - Get vertex builds by flow_id
- `DELETE /api/v1/monitor/builds` - Delete vertex builds by flow_id
- `GET /api/v1/monitor/messages/sessions` - Get message sessions
- `GET /api/v1/monitor/messages` - Get messages (paginated)
- `DELETE /api/v1/monitor/messages` - Delete messages by session_id
- `GET /api/v1/monitor/transactions` - Get transactions (paginated)

**Voice Mode (WebSocket-based):**
- `WS /api/v1/voice/ws/flow_as_tool/{flow_id}` - Execute flow as voice tool (WebSocket)
- `WS /api/v1/voice/ws/flow_as_tool/{flow_id}/{session_id}` - Flow as tool with session tracking
- `WS /api/v1/voice/ws/flow_tts/{flow_id}` - Text-to-speech flow execution (WebSocket)
- `WS /api/v1/voice/ws/flow_tts/{flow_id}/{session_id}` - TTS flow with session tracking
- `GET /api/v1/voice/elevenlabs/voice_ids` - Get available ElevenLabs voice IDs

### API v2 Endpoints

**Files (Enhanced):**
- `POST /api/v2/files/upload` - Upload with additional metadata
- `GET /api/v2/files/list` - List with pagination and filters

**MCP (Enhanced):**
- `POST /api/v2/mcp/servers/` - Create MCP server configuration

### WebSocket Endpoints

**Real-time Communication:**
- `WS /api/v1/chat/{client_id}` - Chat WebSocket connection
  - Accepts: `token` (JWT) or `x-api-key` (API key) via query params or headers
  - Messages: JSON-encoded chat messages and responses
  - Events: `message`, `error`, `stream`, `token`, `end`

### API Request/Response Patterns

**Standard Success Response:**
```json
{
  "id": "uuid",
  "name": "Resource Name",
  "created_at": "2024-05-29T17:57:17Z",
  // ... resource fields
}
```

**Standard Error Response:**
```json
{
  "detail": "Error message",
  "status_code": 400
}
```

**Pagination Response:**
```json
{
  "items": [ /* array of resources */ ],
  "total": 100,
  "page": 1,
  "size": 50,
  "pages": 2
}
```

**Authentication Headers:**
```
Authorization: Bearer <jwt_token>
```
OR
```
x-api-key: <api_key>
```

### API Client Configuration (Frontend)

**Axios Instance (src/frontend/src/controllers/API/api.tsx):**

```typescript
const api = axios.create({
  baseURL: process.env.BACKEND_URL || "http://localhost:7860",
  timeout: 30000,
});

// Request interceptor: Add auth headers
api.interceptors.request.use((config) => {
  const token = getAuthCookie(cookies, LANGBUILDER_ACCESS_TOKEN);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  const apiKey = getAuthCookie(cookies, LANGBUILDER_API_TOKEN);
  if (apiKey) {
    config.headers["x-api-key"] = apiKey;
  }

  return config;
});

// Response interceptor: Handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login or refresh token
    }
    return Promise.reject(error);
  }
);
```

**TanStack Query Integration:**

```typescript
// Query hook example
export function useGetFlows() {
  return useQuery({
    queryKey: ["flows"],
    queryFn: async () => {
      const { data } = await api.get("/api/v1/flows/");
      return data;
    },
  });
}

// Mutation hook example
export function useUpdateFlow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ flowId, updates }) => {
      const { data } = await api.patch(`/api/v1/flows/${flowId}`, updates);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["flows"] });
    },
  });
}
```

---

## Authentication & Authorization

### Authentication Methods

**1. JWT Token Authentication (Primary)**

**Token Flow:**
```
1. User POSTs credentials to /api/v1/login
2. Backend validates credentials
3. Backend generates:
   - Access Token (short-lived: configurable, default varies)
   - Refresh Token (longer-lived)
4. Client stores tokens in cookies
5. Client includes token in Authorization header
6. Backend validates token on each request
7. Client refreshes access token via /api/v1/login/refresh
```

**Token Structure (src/backend/base/langbuilder/services/auth/utils.py:272-283):**

```python
def create_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode["exp"] = expire

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.ALGORITHM  # "HS256"
    )

# Access token payload
{
  "sub": "user-uuid",      # Subject: user ID
  "type": "access",        # Token type
  "exp": 1234567890        # Expiration timestamp
}
```

**Token Validation (src/backend/base/langbuilder/services/auth/utils.py:161-219):**

```python
async def get_current_user_by_jwt(token: str, db: AsyncSession) -> User:
    # 1. Decode JWT
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    # 2. Extract user_id and token_type
    user_id: UUID = payload.get("sub")
    token_type: str = payload.get("type")

    # 3. Check expiration
    if expires := payload.get("exp"):
        if datetime.now(timezone.utc) > datetime.fromtimestamp(expires, timezone.utc):
            raise HTTPException(401, "Token has expired")

    # 4. Validate user exists and is active
    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(401, "User not found or is inactive")

    return user
```

**2. API Key Authentication (Alternative)**

**API Key Flow:**
```
1. User creates API key via UI or /api/v1/api_key/
2. Backend generates long-lived JWT (365 days * 2)
3. Backend encrypts key with Fernet before storage
4. User includes key in x-api-key header or query param
5. Backend decrypts and validates key
6. Backend returns associated user
```

**API Key Structure:**
```python
# API key is actually a JWT with extended expiration
{
  "sub": "user-uuid",
  "type": "api_key",
  "exp": <2 years from now>
}
```

**API Key Validation (src/backend/base/langbuilder/services/auth/utils.py:44-89):**

```python
async def api_key_security(
    query_param: str,  # From ?x-api-key=...
    header_param: str,  # From header x-api-key: ...
) -> UserRead | None:
    # Check AUTO_LOGIN mode first
    if settings.AUTO_LOGIN:
        if not query_param and not header_param:
            # Return superuser without key validation
            return await get_user_by_username(db, settings.SUPERUSER)
        # Validate provided key
        result = await check_key(db, query_param or header_param)
    else:
        # Normal mode: key required
        if not query_param and not header_param:
            raise HTTPException(403, "API key required")
        result = await check_key(db, query_param or header_param)

    return UserRead.model_validate(result)
```

**3. Auto-Login Mode (Development)**

**Configuration:**
```python
# Environment variables
LANGBUILDER_AUTO_LOGIN=true
LANGBUILDER_SKIP_AUTH_AUTO_LOGIN=true  # Skip key requirement
LANGBUILDER_SUPERUSER=admin_username
```

**Auto-Login Flow:**
- If `AUTO_LOGIN=true` and `SKIP_AUTH_AUTO_LOGIN=true`:
  - No authentication required
  - All requests authenticated as superuser
  - **⚠️ INSECURE - Development only**

### Authorization Model

**Current Authorization: Simple Ownership + Superuser**

**Authorization Check Pattern (src/backend/base/langbuilder/api/v1/flows.py):**

```python
@router.get("/{flow_id}")
async def get_flow(
    flow_id: UUID,
    current_user: CurrentActiveUser,  # Dependency injection
    db: DbSession
):
    flow = await get_flow_by_id(db, flow_id)

    # Authorization check
    if flow.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(403, "Not authorized to access this flow")

    return flow
```

**Authorization Rules:**

| Resource | Owner | Superuser | Other Users |
|----------|-------|-----------|-------------|
| **Flows** | Full access | Full access | No access |
| **Folders** | Full access | Full access | No access |
| **Variables** | Full access | Full access | No access |
| **API Keys** | Full access | Full access | No access |
| **Users** | Read own | Full access | No access |
| **Store** | Read | Full access | Read |

**Special Cases:**
- **Project Creation**: Any authenticated user can create projects (no ownership check)
- **PUBLIC Flows**: Access type enum exists but not enforced in current version
- **Folder Deletion**: Cascades to all child flows (owner/superuser only)

### Security Features

**1. Password Security (src/backend/base/langbuilder/services/auth/utils.py:262-269):**

```python
# Bcrypt hashing with automatic salt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

**2. API Key Encryption (src/backend/base/langbuilder/services/auth/utils.py:450-489):**

```python
# Two-way encryption with Fernet (AES-128)
def encrypt_api_key(api_key: str, settings: SettingsService) -> str:
    fernet = Fernet(derive_key_from_secret(settings.SECRET_KEY))
    encrypted = fernet.encrypt(api_key.encode())
    return encrypted.decode()

def decrypt_api_key(encrypted: str, settings: SettingsService) -> str:
    fernet = Fernet(derive_key_from_secret(settings.SECRET_KEY))
    decrypted = fernet.decrypt(encrypted.encode())
    return decrypted.decode()
```

**3. CORS Configuration (src/backend/base/langbuilder/main.py:292-300):**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # ⚠️ Open CORS - should be restricted in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**4. WebSocket Authentication (src/backend/base/langbuilder/services/auth/utils.py:222-245):**

```python
async def get_current_user_for_websocket(
    websocket: WebSocket,
    db: AsyncSession
) -> User | UserRead:
    # Try JWT from cookie or query param
    token = websocket.cookies.get("access_token_lf") or websocket.query_params.get("token")
    if token:
        return await get_current_user_by_jwt(token, db)

    # Try API key from query param or header
    api_key = (
        websocket.query_params.get("x-api-key") or
        websocket.headers.get("x-api-key")
    )
    if api_key:
        return await ws_api_key_security(api_key)

    raise WebSocketException(code=1008, reason="Missing or invalid credentials")
```

### Frontend Authentication State

**Auth Context (src/frontend/src/contexts/authContext.tsx):**

```typescript
interface AuthContextType {
  accessToken: string | null;
  userData: Users | null;
  apiKey: string | null;
  login: (token: string, autoLogin: string, refreshToken?: string) => void;
  setUserData: (user: Users) => void;
  setApiKey: (key: string) => void;
  storeApiKey: (key: string) => void;
  getUser: () => void;
}

// Login flow
function login(newAccessToken: string, autoLogin: string, refreshToken?: string) {
  // 1. Store tokens in cookies
  setAuthCookie(cookies, LANGBUILDER_ACCESS_TOKEN, newAccessToken);
  setAuthCookie(cookies, LANGBUILDER_REFRESH_TOKEN, refreshToken);

  // 2. Store in local state
  setAccessToken(newAccessToken);
  setIsAuthenticated(true);

  // 3. Fetch user data
  getUser();

  // 4. Load global variables
  getGlobalVariables();
}
```

**Auth Store (src/frontend/src/stores/authStore.ts):**

```typescript
interface AuthStore {
  isAuthenticated: boolean;
  isAdmin: boolean;  // Derived from user.is_superuser
  setIsAuthenticated: (value: boolean) => void;
  setIsAdmin: (value: boolean) => void;
}

const useAuthStore = create<AuthStore>((set) => ({
  isAuthenticated: false,
  isAdmin: false,
  setIsAuthenticated: (value) => set({ isAuthenticated: value }),
  setIsAdmin: (value) => set({ isAdmin: value }),
}));
```

**Route Protection (src/frontend/src/components/authorization/authGuard/index.tsx):**

```typescript
export function AuthGuard() {
  const { accessToken, userData } = useContext(AuthContext);
  const location = useLocation();

  if (!accessToken && !userData) {
    // Redirect to login, save intended destination
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;  // Render protected route
}

export function AuthAdminGuard() {
  const isAdmin = useAuthStore((state) => state.isAdmin);

  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
```

---

## Service Layer

### Service Architecture Overview

The backend uses a **service-oriented architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                   Service Manager                        │
│  - Singleton instance management                        │
│  - Service initialization and teardown                  │
│  - Dependency resolution                                │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                 Core Services                            │
├─────────────┬─────────────┬─────────────┬──────────────┤
│   Database  │    Auth     │    Cache    │   Settings   │
├─────────────┼─────────────┼─────────────┼──────────────┤
│   Storage   │    Chat     │   Session   │    Socket    │
├─────────────┼─────────────┼─────────────┼──────────────┤
│    Queue    │  Telemetry  │    Store    │     Flow     │
└─────────────┴─────────────┴─────────────┴──────────────┘
```

### Service Lifecycle

**Initialization (src/backend/base/langbuilder/services/utils.py):**

```python
async def initialize_services(*, fix_migration: bool = False):
    """Initialize all services in correct order"""

    # 1. Settings (no dependencies)
    settings_service = get_settings_service()
    await settings_service.initialize()

    # 2. Database (depends on settings)
    db_service = get_db_service()
    await db_service.initialize(fix_migration=fix_migration)

    # 3. Cache (depends on settings)
    cache_service = get_cache_service()
    await cache_service.initialize()

    # 4. Storage (depends on settings)
    storage_service = get_storage_service()
    await storage_service.initialize()

    # 5. Other services (depend on database/cache)
    await get_session_service().initialize()
    await get_chat_service().initialize()
    await get_socket_service().initialize()
    await get_queue_service().initialize()
    await get_telemetry_service().initialize()
    await get_tracing_service().initialize()
    await get_state_service().initialize()
    await get_variable_service().initialize()
    await get_task_service().initialize()
    await get_store_service().initialize()
    await get_shared_component_cache_service().initialize()
    # Total: 15 services initialized (auth is utility-based, not DI service)
```

**Teardown (src/backend/base/langbuilder/services/utils.py):**

```python
async def teardown_services():
    """Cleanup all services in reverse order"""

    # Close database connections
    await get_db_service().teardown()

    # Stop background tasks
    get_queue_service().stop()
    get_telemetry_service().stop()

    # Clear caches
    await get_cache_service().teardown()
```

### Core Services

#### 1. DatabaseService

**Location:** `src/backend/base/langbuilder/services/database/service.py`

**Responsibilities:**
- SQLAlchemy async engine management
- Connection pooling
- Session lifecycle
- Database migrations
- Transaction management

**Key Methods:**

```python
class DatabaseService(Service):
    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker | None = None

    async def initialize(self, *, fix_migration: bool = False):
        """Create engine and run migrations"""
        database_url = self.settings.database_url

        # Create async engine
        self._engine = create_async_engine(
            database_url,
            echo=False,
            poolclass=AsyncAdaptedQueuePool,
            pool_pre_ping=True
        )

        # Create session maker
        self._session_maker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        # Run migrations
        await self._run_migrations(fix_migration=fix_migration)

    @asynccontextmanager
    async def with_session(self) -> AsyncSession:
        """Provide a database session via context manager"""
        async with self._session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def teardown(self):
        """Close all connections"""
        if self._engine:
            await self._engine.dispose()
```

**Usage Pattern:**

```python
# Via dependency injection
@router.get("/flows/")
async def get_flows(
    db: Annotated[AsyncSession, Depends(get_session)]
):
    flows = await db.execute(select(Flow))
    return flows.scalars().all()

# Via context manager
async with get_db_service().with_session() as db:
    user = await get_user_by_id(db, user_id)
    await db.commit()
```

#### 2. Authentication (Utility Module)

**Location:** `src/backend/base/langbuilder/services/auth/utils.py`

> **Note:** Unlike other services listed here, authentication is implemented as utility functions rather than a full dependency injection service. There is an `AuthService` class in `auth/service.py`, but it's a minimal placeholder (16 lines). All actual authentication logic is in `auth/utils.py` and used directly via imports, not via `get_auth_service()` DI pattern.

**Responsibilities:**
- User authentication (via utility functions)
- JWT token generation/validation
- API key management
- Password hashing (Bcrypt)
- User credential verification

**Key Configuration:**

```python
class AuthSettings(BaseSettings):
    SECRET_KEY: SecretStr = Field(default_factory=generate_secret_key)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 3600
    REFRESH_TOKEN_EXPIRE_SECONDS: int = 86400 * 7
    SUPERUSER: str = "admin"
    SUPERUSER_PASSWORD: str = "admin"
    AUTO_LOGIN: bool = False
    skip_auth_auto_login: bool = False
```

#### 3. CacheService

**Location:** `src/backend/base/langbuilder/services/cache/service.py`

**Responsibilities:**
- In-memory caching
- Redis caching (optional)
- Disk-based persistent cache
- Cache invalidation
- TTL management

**Implementation:**

```python
class CacheService(Service):
    def __init__(self, cache_implementation: str = "disk"):
        self._cache = self._create_cache(cache_implementation)

    def _create_cache(self, implementation: str):
        if implementation == "redis":
            return RedisCache()
        return DiskCache()

    async def get(self, key: str) -> Any | None:
        return await self._cache.get(key)

    async def set(self, key: str, value: Any, ttl: int | None = None):
        await self._cache.set(key, value, ttl=ttl)

    async def delete(self, key: str):
        await self._cache.delete(key)

    async def clear(self):
        await self._cache.clear()
```

#### 4. StorageService

**Location:** `src/backend/base/langbuilder/services/storage/service.py`

**Responsibilities:**
- File storage abstraction
- Local filesystem storage
- S3-compatible storage
- File upload/download
- Path management

**Storage Backends:**

```python
class StorageService(Service):
    def __init__(self, backend: str = "local"):
        if backend == "s3":
            self._backend = S3Storage()
        else:
            self._backend = LocalStorage()

    async def save_file(self, path: str, content: bytes):
        await self._backend.save(path, content)

    async def read_file(self, path: str) -> bytes:
        return await self._backend.read(path)

    async def delete_file(self, path: str):
        await self._backend.delete(path)

    async def list_files(self, path: str) -> list[str]:
        return await self._backend.list(path)
```

#### 5. ChatService

**Location:** `src/backend/base/langbuilder/services/chat/service.py`

**Responsibilities:**
- Flow execution orchestration
- LangChain integration
- Streaming response handling
- Session management
- Message persistence

**Key Features:**

```python
class ChatService(Service):
    async def execute_flow(
        self,
        flow_id: UUID,
        input_data: dict,
        session_id: str,
        stream: bool = False
    ):
        # 1. Load flow definition
        flow = await self._load_flow(flow_id)

        # 2. Build execution graph
        graph = await self._build_graph(flow.data)

        # 3. Execute with LangChain
        if stream:
            async for chunk in graph.astream(input_data):
                yield chunk
        else:
            result = await graph.ainvoke(input_data)
            return result

        # 4. Save message history
        await self._save_messages(session_id, input_data, result)
```

#### 6. SessionService

**Location:** `src/backend/base/langbuilder/services/session/service.py`

**Responsibilities:**
- User session tracking
- WebSocket session management
- Conversation history
- Session expiration

#### 7. SettingsService

**Location:** `src/backend/base/langbuilder/services/settings/service.py`

**Responsibilities:**
- Environment variable loading
- Configuration validation
- Feature flags
- Dynamic settings updates

**Settings Structure:**

```python
class Settings(BaseSettings):
    # App settings
    app_name: str = "LangBuilder"
    dev: bool = False
    workers: int = 1

    # Database
    database_url: str = "sqlite+aiosqlite:///./langbuilder.db"

    # Authentication
    auth_settings: AuthSettings = AuthSettings()

    # Storage
    storage_type: str = "local"

    # Observability
    prometheus_enabled: bool = False
    prometheus_port: int = 9090
    sentry_dsn: str | None = None

    # Features
    mcp_server_enabled: bool = False
    components_path: list[Path] = []

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

#### 8. QueueService

**Location:** `src/backend/base/langbuilder/services/job_queue/service.py`

**Responsibilities:**
- Background task processing
- Async job scheduling
- Task queue management
- Worker pool

#### 9. SocketService

**Location:** `src/backend/base/langbuilder/services/socket/service.py`

**Responsibilities:**
- WebSocket connection management
- Real-time event broadcasting
- Client session tracking

#### 10. TelemetryService

**Location:** `src/backend/base/langbuilder/services/telemetry/`

**Responsibilities:**
- Usage analytics
- Performance metrics
- Error tracking (via Sentry)
- Prometheus metrics (optional)

#### 11. TracingService

**Location:** `src/backend/base/langbuilder/services/tracing/service.py`

**Responsibilities:**
- LLM execution tracing and observability
- Multi-provider tracing support (LangSmith, LangFuse, Langwatch, Opik, Arize Phoenix)
- Trace context management for distributed flows
- LangChain callback handlers for execution tracking
- Input/output serialization and logging

**Key Features:**

```python
class TracingService(Service):
    def __init__(self):
        self.tracers: dict[str, BaseTracer] = {}
        self.trace_context_var = ContextVar("trace_context")

    def get_tracer(self, provider: str) -> BaseTracer:
        """Get tracer instance for specified provider"""
        if provider == "langsmith":
            return LangSmithTracer()
        elif provider == "langfuse":
            return LangFuseTracer()
        elif provider == "langwatch":
            return LangWatchTracer()
        elif provider == "opik":
            return OpikTracer()
        elif provider == "arize_phoenix":
            return ArizePhoenixTracer()

    @asynccontextmanager
    async def trace_context(self, run_id, run_name, project_name, user_id):
        """Context manager for tracing flow execution"""
        context = TraceContext(run_id, run_name, project_name, user_id)
        token = self.trace_context_var.set(context)
        try:
            yield context
        finally:
            self.trace_context_var.reset(token)
```

**Supported Providers:**
- **LangSmith**: LangChain's official tracing platform
- **LangFuse**: Open-source LLM observability
- **Langwatch**: Monitoring and analytics
- **Opik**: ML experiment tracking
- **Arize Phoenix**: LLM observability and evaluation

**Note:** TracingService is distinct from TelemetryService. TracingService focuses on LLM execution traces, while TelemetryService handles application-level metrics and analytics.

#### 12. StateService

**Location:** `src/backend/base/langbuilder/services/state/service.py`

**Responsibilities:**
- In-memory state management for flow execution
- Observer pattern for reactive state updates
- Thread-safe state access with locking
- Per-run state isolation (keyed by `run_id`)
- State append and update operations

**Implementation:**

```python
class InMemoryStateService(StateService):
    def __init__(self, settings_service: SettingsService):
        self.states: dict[str, dict] = {}  # run_id -> {key: value}
        self.observers: dict[str, list[Callable]] = defaultdict(list)
        self.lock = Lock()

    def update_state(self, key, new_state, run_id: str) -> None:
        """Update state and notify observers"""
        with self.lock:
            if run_id not in self.states:
                self.states[run_id] = {}
            self.states[run_id][key] = new_state
            self.notify_observers(key, new_state)

    def append_state(self, key, new_state, run_id: str) -> None:
        """Append to list-based state"""
        with self.lock:
            if run_id not in self.states:
                self.states[run_id] = {}
            if key not in self.states[run_id]:
                self.states[run_id][key] = []
            self.states[run_id][key].append(new_state)

    def get_state(self, key, run_id: str):
        """Retrieve state value"""
        with self.lock:
            return self.states.get(run_id, {}).get(key, "")

    def subscribe(self, key, observer: Callable) -> None:
        """Register observer for state changes"""
        with self.lock:
            if observer not in self.observers[key]:
                self.observers[key].append(observer)
```

**Use Cases:**
- Sharing state between flow components during execution
- Real-time updates to UI during flow execution (via observers)
- Temporary session data that doesn't need persistence

#### 13. VariableService

**Location:** `src/backend/base/langbuilder/services/variable/service.py`

**Responsibilities:**
- Global variables management (user-scoped)
- Encrypted credential storage
- Environment variable import
- Variable CRUD operations
- Type support: Generic (plaintext) and Credential (encrypted)

**Implementation:**

```python
class DatabaseVariableService(VariableService, Service):
    async def create_variable(
        self,
        user_id: UUID,
        name: str,
        value: str,
        type_: str,  # GENERIC_TYPE or CREDENTIAL_TYPE
        session: AsyncSession,
    ) -> Variable:
        """Create encrypted variable"""
        encrypted_value = auth_utils.encrypt_api_key(value, self.settings_service)
        variable = Variable(
            user_id=user_id,
            name=name,
            value=encrypted_value,
            type=type_
        )
        session.add(variable)
        await session.commit()
        return variable

    async def get_variable(
        self, user_id: UUID, name: str, field: str, session: AsyncSession
    ) -> str:
        """Get decrypted variable value"""
        stmt = select(Variable).where(
            Variable.user_id == user_id,
            Variable.name == name
        )
        variable = (await session.exec(stmt)).first()
        return auth_utils.decrypt_api_key(variable.value, self.settings_service)

    async def initialize_user_variables(
        self, user_id: UUID, session: AsyncSession
    ) -> None:
        """Import variables from environment on user login"""
        for var_name in self.settings_service.settings.variables_to_get_from_environment:
            if var_name in os.environ:
                await self.create_variable(user_id, var_name, os.environ[var_name], ...)
```

**Variable Types:**
- **Generic**: Plaintext variables (can be decrypted for display)
- **Credential**: Encrypted secrets (never exposed in session_id fields)

**Security Features:**
- AES encryption for stored values
- Type-based access restrictions
- Prevents credential exposure in logs/traces

#### 14. TaskService

**Location:** `src/backend/base/langbuilder/services/task/service.py`

**Responsibilities:**
- Async task execution
- Pluggable backend system (AnyIO default, Celery support)
- Task launching and awaiting
- Background job orchestration

**Implementation:**

```python
class TaskService(Service):
    def __init__(self, settings_service: SettingsService):
        self.settings_service = settings_service
        self.use_celery = False
        self.backend = self.get_backend()  # AnyIOBackend by default

    async def launch_task(
        self, task_func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Launch task asynchronously"""
        task = self.backend.launch_task(task_func, *args, **kwargs)
        return await task if isinstance(task, Coroutine) else task

    async def launch_and_await_task(
        self, task_func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Launch and wait for task completion"""
        return await task_func(*args, **kwargs)
```

**Backends:**
- **AnyIOBackend** (default): Async/await based task execution
- **Celery** (optional): Distributed task queue for scale-out deployments

#### 15. StoreService

**Location:** `src/backend/base/langbuilder/services/store/service.py`

**Responsibilities:**
- Component store integration (Directus-based headless CMS)
- Component search and discovery
- Component upload/download
- User authentication via API keys
- Like/download tracking via webhooks

**Key Features:**

```python
class StoreService(Service):
    def __init__(self, settings_service: SettingsService):
        self.base_url = settings_service.settings.store_url
        self.components_url = f"{self.base_url}/items/components"

    async def list_components(
        self, api_key: str | None, params: dict
    ) -> ListComponentResponseModel:
        """Search and filter components from store"""
        response = await self.get(self.components_url, api_key, params=params)
        return ListComponentResponseModel(components=response)

    async def download_component(
        self, component_id: str, api_key: str | None
    ) -> DownloadComponentResponse:
        """Download component and increment download counter"""
        component = await self.get(
            f"{self.components_url}/{component_id}", api_key
        )
        # Trigger download webhook
        await self._track_download(component_id)
        return component

    async def upload_component(
        self, component: StoreComponentCreate, api_key: str
    ) -> CreateComponentResponse:
        """Upload component to store (requires authentication)"""
        processed_data = process_component_data(component)
        return await self.post(self.components_url, api_key, data=processed_data)
```

**Store API Endpoints:**
- `GET /api/v1/store/components/` - List/search components
- `GET /api/v1/store/components/{id}` - Download component
- `POST /api/v1/store/components/` - Upload component (requires API key)
- `POST /api/v1/api_key/store` - Store API key for authenticated access

**Integration:**
- Directus headless CMS backend
- Webhook-based analytics (downloads, likes)
- User-created content with attribution
- Tagging and categorization

#### 16. SharedComponentCacheService

**Location:** `src/backend/base/langbuilder/services/shared_component_cache/service.py`

**Responsibilities:**
- Thread-safe in-memory caching for component instances
- Shared cache across multiple component executions
- Cache invalidation and expiration

**Implementation:**

```python
class SharedComponentCacheService(ThreadingInMemoryCache):
    """A caching service shared across components.

    Extends ThreadingInMemoryCache to provide thread-safe
    caching for component build artifacts and instances.
    """
    name = "shared_component_cache_service"
```

**Use Cases:**
- Cache compiled component instances across flow runs
- Share expensive-to-build objects (e.g., LLM clients, embeddings)
- Reduce redundant initialization overhead
- Thread-safe access for concurrent flow executions

**Note:** This is distinct from CacheService, which handles application-level caching (flows, settings, etc.). SharedComponentCacheService is specifically for component-level object sharing.

### Dependency Injection

**Service Access Pattern (src/backend/base/langbuilder/services/deps.py):**

```python
# Singleton service getters
def get_settings_service() -> SettingsService:
    return service_manager.get(SettingsService)

def get_db_service() -> DatabaseService:
    return service_manager.get(DatabaseService)

def get_cache_service() -> CacheService:
    return service_manager.get(CacheService)

# ... more getters

# FastAPI dependency for database session
async def get_session() -> AsyncSession:
    async with get_db_service().with_session() as session:
        yield session

# Type aliases for cleaner endpoint signatures
DbSession = Annotated[AsyncSession, Depends(get_session)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
```

**Usage in Endpoints:**

```python
@router.get("/flows/")
async def list_flows(
    current_user: CurrentActiveUser,  # Auth dependency
    db: DbSession,                    # Database session dependency
    skip: int = 0,
    limit: int = 100
):
    stmt = select(Flow).where(Flow.user_id == current_user.id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()
```

---

## Integration Patterns

### LangChain Integration

**Component Architecture:**

LangBuilder provides a visual interface for building LangChain flows. Each node in the flow editor represents a LangChain component.

**Component Discovery (src/backend/base/langbuilder/interface/):**

```python
async def get_and_cache_all_types_dict(settings: SettingsService) -> dict:
    """Scan component directories and build type registry"""

    all_types = {}

    # Scan default components
    for path in settings.components_path:
        components = await scan_directory(path)
        all_types.update(components)

    # Scan custom components (from bundles)
    for bundle_path in settings.custom_components_path:
        components = await scan_directory(bundle_path)
        all_types.update(components)

    # Cache for fast lookup
    await cache_service.set("all_types_dict", all_types)

    return all_types
```

**Flow Execution:**

```python
# Flow data structure
flow.data = {
  "nodes": [
    {
      "id": "node-1",
      "type": "CustomNode",
      "data": {
        "type": "ChatOpenAI",  # Component type
        "node": {
          "template": {
            "model_name": "gpt-4",
            "temperature": 0.7,
            # ... component parameters
          }
        }
      }
    }
  ],
  "edges": [
    {
      "source": "node-1",
      "target": "node-2",
      "sourceHandle": "output",
      "targetHandle": "input"
    }
  ]
}

# Execution: Convert flow data to LangChain graph
# 1. Instantiate components from nodes
# 2. Connect components based on edges
# 3. Execute graph with user input
# 4. Return results
```

### File Storage Integration

**Local Storage:**

```python
class LocalStorage:
    def __init__(self, base_path: Path):
        self.base_path = base_path

    async def save(self, path: str, content: bytes):
        file_path = self.base_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        async with async_open(file_path, "wb") as f:
            await f.write(content)

    async def read(self, path: str) -> bytes:
        file_path = self.base_path / path
        async with async_open(file_path, "rb") as f:
            return await f.read()
```

**S3 Storage:**

```python
class S3Storage:
    def __init__(self, bucket: str, region: str):
        self.s3_client = boto3.client("s3", region_name=region)
        self.bucket = bucket

    async def save(self, path: str, content: bytes):
        await asyncio.to_thread(
            self.s3_client.put_object,
            Bucket=self.bucket,
            Key=path,
            Body=content
        )

    async def read(self, path: str) -> bytes:
        response = await asyncio.to_thread(
            self.s3_client.get_object,
            Bucket=self.bucket,
            Key=path
        )
        return response["Body"].read()
```

### Vector Database Integration

**Supported Vector Databases:**
- ChromaDB
- Faiss
- Qdrant
- Weaviate
- Pinecone
- Milvus
- Elasticsearch
- OpenSearch
- Supabase (pgvector)
- Astra DB

**Integration via LangChain:**

All vector databases are integrated as LangChain components and exposed as nodes in the flow editor. Configuration is handled through the component's template fields.

### Model Context Protocol (MCP) Integration

**MCP Server Endpoints:**

```python
# Start MCP server for a project
@router.post("/mcp/projects/{project_id}/start")
async def start_mcp_server(
    project_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession
):
    project = await get_folder_by_id(db, project_id)

    # Validate ownership
    if project.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(403, "Not authorized")

    # Get MCP-enabled flows in project
    flows = await get_flows_by_folder(db, project_id, mcp_enabled=True)

    # Start MCP server with flows as tools
    mcp_server = await mcp_service.start_server(project_id, flows)

    return {"status": "running", "server_url": mcp_server.url}
```

### External API Integration

**HTTP Client (httpx):**

```python
async def fetch_external_data(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        return response.json()
```

**Webhook Support:**

Flows can be configured as webhooks:

```python
@router.post("/webhook/{endpoint_name}")
async def execute_webhook(
    endpoint_name: str,
    request: Request,
    db: DbSession
):
    # Find flow by endpoint name
    flow = await get_flow_by_endpoint_name(db, endpoint_name)

    if not flow or not flow.webhook:
        raise HTTPException(404, "Webhook not found")

    # Execute flow with webhook payload
    body = await request.json()
    result = await chat_service.execute_flow(flow.id, body)

    return result
```

### Observability Integration

**LangSmith:**

```python
# Configured via environment variables
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<key>
LANGCHAIN_PROJECT=<project-name>
```

**LangFuse:**

```python
# Configured via LangBuilder settings
from langfuse import Langfuse

langfuse = Langfuse(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key
)
```

**Prometheus (Optional):**

```python
# Enable via environment variable
LANGBUILDER_PROMETHEUS_PORT=9090

# Metrics exposed at http://localhost:9090/metrics
# - Request counts
# - Response times
# - Error rates
```

---

## Deployment Architecture

### Local Development

**Development Stack:**

```bash
# Backend (Python)
uv run langbuilder run  # Starts FastAPI on http://localhost:7860

# Frontend (Node.js)
cd src/frontend
npm run start  # Starts Vite dev server on http://localhost:3000
```

**Hot Reload:**
- Backend: Uvicorn with `--reload` flag
- Frontend: Vite HMR (Hot Module Replacement)

### Production Deployment

**Docker Deployment:**

```dockerfile
# Multi-stage build
FROM python:3.12-slim as backend

# Install dependencies
COPY pyproject.toml .
RUN pip install uv && uv pip install .

# Copy source
COPY src/backend/base/langbuilder /app/langbuilder

# Frontend stage
FROM node:20-slim as frontend

WORKDIR /app
COPY src/frontend/package.json .
RUN npm install

COPY src/frontend .
RUN npm run build

# Final stage
FROM python:3.12-slim

# Copy backend
COPY --from=backend /app/langbuilder /app/langbuilder

# Copy frontend build
COPY --from=frontend /app/build /app/langbuilder/frontend

# Run
CMD ["uvicorn", "langbuilder.main:create_app", "--host", "0.0.0.0", "--port", "7860"]
```

**Environment Configuration:**

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/langbuilder

# Auth
LANGBUILDER_SECRET_KEY=<secret>
LANGBUILDER_SUPERUSER=admin
LANGBUILDER_SUPERUSER_PASSWORD=<secure-password>
LANGBUILDER_AUTO_LOGIN=false

# Storage
LANGBUILDER_STORAGE_TYPE=s3
LANGBUILDER_S3_BUCKET=langbuilder-files
LANGBUILDER_S3_REGION=us-east-1

# Cache
LANGBUILDER_CACHE_TYPE=redis
LANGBUILDER_REDIS_URL=redis://localhost:6379

# Observability
SENTRY_DSN=<sentry-dsn>
LANGBUILDER_PROMETHEUS_PORT=9090

# Workers
LANGBUILDER_WORKERS=4
```

### Scalability Considerations

**Horizontal Scaling:**

```yaml
# Kubernetes deployment example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: langbuilder
spec:
  replicas: 3  # Multiple instances
  selector:
    matchLabels:
      app: langbuilder
  template:
    spec:
      containers:
      - name: langbuilder
        image: langbuilder:latest
        ports:
        - containerPort: 7860
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: langbuilder-secrets
              key: database-url
        - name: LANGBUILDER_WORKERS
          value: "1"  # Single worker per pod
```

**Database Connection Pooling:**

```python
# SQLAlchemy async engine configuration
engine = create_async_engine(
    database_url,
    pool_size=10,          # Connections per worker
    max_overflow=20,       # Additional connections under load
    pool_pre_ping=True,    # Validate connections before use
    pool_recycle=3600,     # Recycle connections every hour
)
```

**Caching Strategy:**

```python
# Redis for shared cache across instances
CACHE_TYPE=redis
REDIS_URL=redis://redis-cluster:6379

# Cache key structure
cache_keys = {
    "user:{user_id}": "User data",
    "flow:{flow_id}": "Flow definition",
    "types:all": "Component types registry",
    "session:{session_id}": "Chat session",
}
```

### Database Migration Strategy

**Alembic Migrations:**

```bash
# Generate migration from model changes
alembic revision --autogenerate -m "Add RBAC tables"

# Review migration script
# Edit: alembic/versions/<revision>_add_rbac_tables.py

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

**Zero-Downtime Migration:**

```python
# 1. Add new columns as nullable
class AddRoleColumn(Revision):
    def upgrade(self):
        op.add_column("user", sa.Column("role", sa.String(), nullable=True))

# 2. Deploy code that populates new columns

# 3. Backfill existing data
class BackfillRoles(Revision):
    def upgrade(self):
        op.execute("UPDATE user SET role = 'user' WHERE role IS NULL")

# 4. Make column non-nullable
class MakeRoleRequired(Revision):
    def upgrade(self):
        op.alter_column("user", "role", nullable=False)
```

---

## Development Workflow

### Code Organization Standards

**Backend:**
- **Models**: `services/database/models/{entity}/`
  - `model.py`: SQLModel definitions
  - `crud.py`: CRUD operations
  - `schema.py`: Pydantic schemas (if needed beyond base model)
- **Services**: `services/{service_name}/`
  - `service.py`: Service implementation
  - `factory.py`: Service factory
  - `utils.py`: Helper functions
- **API**: `api/v{version}/{resource}.py`
  - One file per resource (flows, users, etc.)
  - FastAPI router with endpoints

**Frontend:**
- **Pages**: `pages/{PageName}/`
  - `index.tsx`: Page component
  - `components/`: Page-specific components
- **Components**: `components/{category}/{ComponentName}/`
  - `index.tsx`: Component implementation
  - `types.ts`: Component types (if needed)
- **Stores**: `stores/{name}Store.ts`
  - Zustand store definition
- **Queries**: `controllers/API/queries/{resource}/`
  - TanStack Query hooks for API calls

### Testing Strategy

**Backend Testing:**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/backend/base/langbuilder --cov-report=html

# Run specific test file
pytest src/backend/tests/unit/api/v1/test_flows.py

# Run in parallel
pytest -n auto
```

**Test Structure:**

```
src/backend/tests/
├── unit/                  # Unit tests
│   ├── api/
│   │   └── v1/
│   │       ├── test_flows.py
│   │       ├── test_users.py
│   │       └── ...
│   ├── services/
│   │   ├── test_auth.py
│   │   └── ...
│   └── models/
│       └── test_user.py
├── integration/           # Integration tests
│   ├── test_flow_execution.py
│   └── test_api_workflow.py
└── fixtures/              # Test fixtures
    ├── conftest.py
    └── ...
```

**Frontend Testing:**

```bash
# Run Jest tests
npm test

# Run Playwright E2E tests
npx playwright test

# Run with UI
npx playwright test --ui
```

**Test Structure:**

```
src/frontend/tests/
├── core/                  # Core functionality tests
│   ├── auto_login.spec.ts
│   ├── saveComponents.spec.ts
│   └── ...
├── extended/              # Extended feature tests
│   ├── features/
│   │   ├── flowPage.spec.ts
│   │   └── ...
│   └── integrations/
│       └── chatInputOutputUser.spec.ts
└── fe-components/         # Component tests
    ├── dropdownComponent.spec.ts
    └── ...
```

### Code Quality Tools

**Backend:**

```bash
# Ruff (linting + formatting)
ruff check src/backend/base/langbuilder/
ruff format src/backend/base/langbuilder/

# MyPy (type checking)
mypy src/backend/base/langbuilder/

# Vulture (dead code detection)
vulture src/backend/base/langbuilder/
```

**Frontend:**

```bash
# Biome (linting + formatting)
npm run format        # Format with Biome
npm run check-format  # Check formatting

# TypeScript type checking
npm run type-check
```

### Git Workflow

**Branch Strategy:**

```
main (production)
  ├─ dev (development)
  │   ├─ feature/user-auth
  │   ├─ feature/flow-editor
  │   └─ bugfix/flow-save
  └─ hotfix/security-patch
```

**Commit Convention:**

```
<type>(<scope>): <subject>

Types: feat, fix, docs, style, refactor, test, chore
Scopes: api, ui, auth, flows, db, etc.

Examples:
feat(api): add project sharing endpoints
fix(ui): resolve flow editor crash on empty nodes
docs(readme): update installation instructions
```

### Build and Release

**Version Management:**

```python
# src/backend/base/langbuilder/utils/version.py
def get_version_info() -> dict:
    return {
        "version": "1.5.0",
        "python": "3.10+",
        # ... more metadata
    }
```

**Release Process:**

```bash
# 1. Update version
# Edit: pyproject.toml (version = "1.5.0")
# Edit: src/frontend/package.json ("version": "1.5.0")

# 2. Run tests
pytest
npm test

# 3. Build frontend
cd src/frontend
npm run build

# 4. Create Git tag
git tag -a v1.5.0 -m "Release v1.5.0"
git push origin v1.5.0

# 5. Build and publish package
uv build
uv publish
```

---

## Technical Debt & Observations

### Current State Assessment

**Strengths:**
✅ Modern tech stack (FastAPI, React 18, TypeScript)
✅ Async-first architecture throughout
✅ Type safety with Pydantic and TypeScript
✅ Clean service separation
✅ Comprehensive dependency injection
✅ Extensible component architecture
✅ Good test coverage structure

**Areas for Improvement:**

#### 1. Authorization Model

**Current State:**
- Simple owner-based access control
- Binary superuser flag
- No role-based permissions
- No resource-level permissions beyond ownership

**Limitations:**
- Cannot share flows/projects with other users
- No granular permissions (read-only, edit, admin)
- No project-level access control
- No audit logging of permission changes

**Impact:**
- Limited collaboration capabilities
- All-or-nothing access model
- Superusers have unrestricted access to all resources

#### 2. CORS Configuration

**Current State:**
```python
allow_origins=["*"]  # Open CORS
```

**Issue:**
- Wide-open CORS in production code
- Security risk for production deployments

**Recommendation:**
- Environment-based CORS configuration
- Whitelist specific origins in production

#### 3. Database Architecture

**Observations:**
- SQLite default is good for development
- PostgreSQL support exists but requires manual configuration
- No built-in connection pooling configuration for SQLite
- Alembic migrations are manual (not automatic on startup)

**Considerations:**
- SQLite has limitations for high-concurrency production use
- No built-in database backup/restore utilities
- Migration strategy requires manual execution

#### 4. API Consistency

**Observations:**
- Both `/api/v1/folders/` and `/api/v1/projects/` exist (same resource, different names)
- Some endpoints use plural, some use singular
- Inconsistent pagination patterns

**Examples:**
```python
# Duplicate endpoints
GET /api/v1/folders/{id}  # Database name
GET /api/v1/projects/{id}  # UI name (same resource)
```

#### 5. Frontend State Management

**Current Approach:**
- Multiple state layers (TanStack Query, Zustand, Context, useState)
- State duplication between layers
- No single source of truth for some data

**Example Duplication:**
```typescript
// User data exists in 3 places:
// 1. AuthContext.userData
// 2. useAuthStore.isAdmin
// 3. TanStack Query cache from useGetUserData()
```

**Impact:**
- Potential sync issues
- Increased complexity
- Harder to debug state-related bugs

#### 6. Error Handling

**Backend:**
- Good use of HTTPException
- Some broad exception catching (`except Exception`)
- Limited structured error responses

**Frontend:**
- Error boundaries exist
- Inconsistent error display patterns
- Some API errors silently fail

#### 7. Type Safety Gaps

**Backend:**
- Some `# type: ignore` comments
- Dynamic `data: dict` fields (Flow.data, Folder.auth_settings)
- Limited validation on JSON fields

**Frontend:**
- Some `any` types in API responses
- Missing types for some component props
- Incomplete TypeScript strict mode

#### 8. Documentation

**Current State:**
- README covers basic usage
- Limited inline code documentation
- No API documentation (OpenAPI/Swagger UI not mentioned)
- Limited architecture documentation (this doc fills that gap)

**Missing:**
- API endpoint documentation with examples
- Service architecture diagrams
- Database schema diagrams
- Deployment guides for different environments

#### 9. Security Considerations

**Observations:**
- Passwords are properly hashed (Bcrypt)
- API keys are encrypted at rest
- JWT tokens are properly validated
- But:
  - No rate limiting mentioned
  - No request size limits beyond middleware
  - No CSRF protection mentioned
  - AUTO_LOGIN mode is insecure (but documented)

#### 10. Performance Optimization

**Current State:**
- Async/await throughout
- Database query optimization limited
- No query result caching visible
- No CDN integration for frontend assets

**Opportunities:**
- Add database query caching for frequently accessed data
- Implement pagination defaults to prevent large result sets
- Add indexes for common query patterns
- Frontend bundle optimization

#### 11. Monitoring and Observability

**Current State:**
- Prometheus support (optional)
- Sentry integration (optional)
- LangSmith/LangFuse support
- Basic logging with loguru

**Gaps:**
- No built-in performance monitoring
- Limited metrics collection
- No distributed tracing (beyond OpenTelemetry setup)
- No log aggregation configuration

#### 12. Multi-Tenancy

**Current State:**
- Single-user per resource model
- No organization/workspace concept
- No cross-user collaboration

**Future Consideration:**
- Organization/team hierarchy
- Shared workspaces
- Team-based access control

### Migration Path Considerations

If implementing RBAC or other major features:

1. **Database Changes:**
   - Add new tables without breaking existing ones
   - Use nullable columns initially
   - Backfill data in separate migration
   - Make non-nullable after validation

2. **API Changes:**
   - Version endpoints (v2) for breaking changes
   - Maintain v1 for backward compatibility
   - Deprecation notices in headers

3. **Frontend Changes:**
   - Feature flags for gradual rollout
   - Backward compatible components
   - Progressive enhancement

---

## Appendix: Key File References

### Backend Core Files

| File | Purpose | Lines | Key Content |
|------|---------|-------|-------------|
| `main.py` | Application factory | 469 | FastAPI app creation, middleware, lifespan |
| `api/router.py` | API routing | - | Main router configuration |
| `api/v1/flows.py` | Flow endpoints | - | Flow CRUD operations |
| `api/v1/users.py` | User endpoints | - | User management |
| `services/auth/utils.py` | Auth utilities | 568 | JWT, password hashing, authentication |
| `services/database/service.py` | Database service | - | SQLAlchemy engine, sessions |
| `services/database/models/user/model.py` | User model | 83 | User entity definition |
| `services/database/models/flow/model.py` | Flow model | 289 | Flow entity definition |
| `services/database/models/folder/model.py` | Folder model | 62 | Folder/Project entity |

### Frontend Core Files

| File | Purpose | Key Content |
|------|---------|-------------|
| `App.tsx` | Root component | Route configuration, providers |
| `contexts/authContext.tsx` | Auth context | Login, logout, user state |
| `stores/authStore.ts` | Auth store | Authentication state (Zustand) |
| `stores/flowStore.ts` | Flow editor state | Current flow, nodes, edges |
| `controllers/API/api.tsx` | HTTP client | Axios configuration, interceptors |
| `controllers/API/queries/flows/` | Flow queries | TanStack Query hooks for flows |
| `pages/FlowPage/` | Flow editor page | Main flow editing interface |

### Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python dependencies, project metadata |
| `src/frontend/package.json` | Node dependencies, scripts |
| `src/frontend/vite.config.mts` | Vite build configuration |
| `src/frontend/tsconfig.json` | TypeScript configuration |
| `src/backend/base/langbuilder/alembic.ini` | Database migration config |
| `.env` | Environment variables (local) |

---

## Document Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2025-10-21 | 1.0 | Initial architecture specification document |

---

**End of Architecture Specification**

This document provides a comprehensive overview of the LangBuilder platform architecture as it exists in version 1.5.0. It is based on actual codebase analysis and represents the current implementation, not planned features.

For questions or clarifications, refer to the source code in the referenced files or consult the development team.
