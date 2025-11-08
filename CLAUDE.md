# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LangBuilder is an open-source AI agent platform providing a visual workflow editor, programmable AI agent framework built on LangChain, and deployment management capabilities. The platform enables both no-code and low-code development of AI agents with support for multiple LLMs, vector databases, and enterprise deployment.

**Key Capabilities:**
- Visual drag-and-drop workflow builder for AI agents
- Multi-agent orchestration with LangChain/LangGraph
- Flow deployment as REST APIs and MCP servers
- 80+ component types across agents, models, data processing, tools, and vector stores
- Real-time chat and streaming execution
- Enterprise authentication and RBAC (in development)

## Architecture

LangBuilder follows a service-oriented architecture with clear separation between:

- **Frontend (React/TypeScript)**: Visual flow editor using ReactFlow, component-based UI with Radix UI and Tailwind CSS
- **Backend (FastAPI/Python)**: Async-first API server with dependency injection, repository pattern for data access
- **Services Layer**: Auth, Database, Cache, Session, Chat, Job Queue
- **Component System**: 80+ extensible components organized by category (agents, models, data, embeddings, tools, vectorstores, etc.)
- **Graph Engine**: Vertex-based execution engine with state management and dependency resolution

### Directory Structure

```
src/
├── backend/
│   ├── base/langbuilder/          # Core backend package
│   │   ├── api/                   # FastAPI routers and endpoints
│   │   │   ├── v1/                # API version 1 (chat, flows, users, etc.)
│   │   │   └── v2/                # API version 2
│   │   ├── components/            # 80+ component implementations
│   │   │   ├── agents/            # Agent components
│   │   │   ├── data/              # Data processing
│   │   │   ├── embeddings/        # Embedding components
│   │   │   ├── models/            # LLM components
│   │   │   ├── processing/        # Text processing
│   │   │   ├── tools/             # Tool integrations
│   │   │   └── vectorstores/      # Vector DB components
│   │   ├── services/              # Service layer
│   │   │   ├── auth/              # Authentication service
│   │   │   ├── database/          # Database service and models
│   │   │   ├── cache/             # Cache service
│   │   │   ├── chat/              # Chat service
│   │   │   └── session/           # Session management
│   │   ├── graph/                 # Graph execution engine
│   │   │   ├── vertex/            # Vertex implementation
│   │   │   ├── edge/              # Edge implementation
│   │   │   ├── graph/             # Graph orchestration
│   │   │   └── state/             # State management
│   │   ├── alembic/               # Database migrations
│   │   └── initial_setup/         # Starter projects and templates
│   └── tests/                     # Backend tests
│       └── unit/                  # Unit tests (mirror component structure)
└── frontend/
    └── src/
        ├── components/            # Reusable UI components
        ├── pages/                 # Page-level components
        ├── icons/                 # Custom SVG icons
        ├── stores/                # Zustand state management
        ├── types/                 # TypeScript definitions
        └── controllers/           # API client and services
```

## Common Commands

### Development Setup

```bash
# Install all dependencies (frontend + backend)
make init

# Install backend only
make install_backend

# Install frontend only (uses npm)
make install_frontend
```

### Running Services

```bash
# Run backend dev server (port 7860, auto-reload)
make backend

# Run frontend dev server (port 3000, hot-reload)
make frontend

# Run full stack via CLI
make run_cli

# Run with specific env file
make backend env=.env.local
```

### Testing

```bash
# Run all backend unit tests (parallel, async)
make unit_tests

# Run tests sequentially (async=false)
make unit_tests async=false

# Run tests starting from last failure (lf=true)
make unit_tests lf=true

# Run specific test file
uv run pytest src/backend/tests/unit/test_specific.py

# Run specific test method
uv run pytest src/backend/tests/unit/test_file.py::test_method

# Run integration tests
make integration_tests

# Run frontend tests
make tests_frontend
```

### Code Quality

```bash
# Format backend code (ALWAYS RUN FIRST - prevents most lint errors)
make format_backend

# Format frontend code
make format_frontend

# Format both
make format

# Run linting (mypy type checking)
make lint

# Check spelling
make codespell

# Fix spelling errors
make fix_codespell
```

### Database Migrations

```bash
# Create new migration
make alembic-revision message="Add user table"

# Apply migrations
make alembic-upgrade

# Rollback one migration
make alembic-downgrade

# Show current revision
make alembic-current

# Show migration history
make alembic-history
```

### Building and Deployment

```bash
# Build frontend static files
make build_frontend

# Build Python packages
make build base=true main=true

# Build and run
make build_and_run

# Docker build
make docker_build
```

## Development Workflow

### Backend Component Development

1. **Create Component**: Add to appropriate subdirectory under `src/backend/base/langbuilder/components/`
   - Follow existing component patterns (inherit from `Component` base class)
   - Set `display_name`, `description`, `icon`, and other metadata
   - Implement `run()` or `message_response()` async methods

2. **Update Imports**: Add to `__init__.py` in alphabetical order:
   ```python
   from .my_component import MyComponent

   __all__ = [
       "ExistingComponent",
       "MyComponent",  # Add alphabetically
   ]
   ```

3. **Format Code FIRST**: Run `make format_backend` early and often to auto-fix style issues

4. **Create Tests**: Add tests to `src/backend/tests/unit/components/` mirroring component structure
   - Use `ComponentTestBaseWithClient` or `ComponentTestBaseWithoutClient`
   - Provide `component_class`, `default_kwargs`, and `file_names_mapping` fixtures
   - Test with both sync and async patterns

5. **Run Tests**: `make unit_tests`

6. **Test in UI**:
   - Backend auto-restarts on save
   - Refresh browser to see component changes
   - Old components show "Updates Available" after backend restart

### Frontend Development

1. **Component Development**:
   - Use TypeScript for all new code
   - Follow React 18 patterns with hooks
   - Use Zustand for state management
   - Style with Tailwind CSS utility classes

2. **API Integration**:
   - Use `api` from `@/controllers/API` for HTTP requests
   - Implement error handling with try/catch
   - Use TanStack Query for server state when appropriate

3. **Icons**:
   - Backend: Set `icon = "IconName"` in component class
   - Frontend: Create icon in `src/frontend/src/icons/IconName/`
   - Add to `lazyIconImports.ts` with exact same name
   - Support both light and dark modes using `isDark` prop

4. **Format and Lint**: Run `make format_frontend` and `make lint`

### Testing Best Practices

- **Component Tests**: Use base classes (`ComponentTestBaseWithClient`, `ComponentTestBaseWithoutClient`)
- **Version Testing**: Provide `file_names_mapping` for backward compatibility
- **Async Testing**: Mark tests with `@pytest.mark.asyncio`, use `await` properly
- **API Testing**: Use `client` fixture with `logged_in_headers`
- **External APIs**: Mark with `@pytest.mark.api_key_required` and `@pytest.mark.no_blockbuster`
- **Database Tests**: May fail in batch runs; run individually if needed
- **Mock LLMs**: Use `MockLanguageModel` from `tests.unit.mock_language_model`

### Pre-Commit Workflow

**CRITICAL**: Always run in this order:

1. **`make format_backend`** (FIRST - auto-fixes most issues)
2. `make lint`
3. `make unit_tests`
4. Commit changes

## Key Technical Details

### Backend

- **Python Version**: 3.10-3.13 required
- **Package Manager**: `uv` (fast Python package manager)
- **ASGI Server**: Uvicorn with `asyncio` loop
- **ORM**: SQLModel (SQLAlchemy + Pydantic)
- **Database**: SQLite (dev), PostgreSQL (production)
- **Authentication**: JWT tokens via python-jose, bcrypt password hashing
- **Dependency Injection**: FastAPI `Depends()` pattern throughout
- **Async**: Full async/await from API to database layer

### Frontend

- **Node Version**: v22.12 LTS
- **Package Manager**: npm (v10.9)
- **Build Tool**: Vite with SWC compiler
- **State**: Zustand for client state, TanStack Query for server state
- **Styling**: Tailwind CSS with Radix UI primitives
- **Routing**: React Router v6
- **Flow Editor**: ReactFlow (@xyflow/react) for visual graph editing

### Component System

- **Base Class**: All components inherit from `Component`
- **Async Methods**: `run()` and `message_response()` are async
- **Type Safety**: Input/output types defined with Pydantic
- **Build Config**: Dynamic configuration via `update_build_config()`
- **Versioning**: Components support multiple LangBuilder versions via file mapping

### Graph Execution

- **Vertex-Based**: Flows compiled to vertex graph with dependency resolution
- **Async Execution**: Parallel execution where possible
- **State Management**: Graph state tracked through execution
- **Streaming**: Real-time output streaming via WebSocket
- **Job Queue**: Background execution with job tracking

### API Structure

- **v1 API**: Main API version (`/api/v1/`)
  - `/chat` - Chat and streaming endpoints
  - `/flows` - Flow CRUD operations
  - `/users` - User management
  - `/endpoints` - Webhook endpoints
  - `/mcp` - MCP server management
  - `/build` - Flow build execution
  - `/login` - Authentication

- **WebSocket**: Real-time communication for streaming execution

### Authentication & Authorization

- **Current**: JWT-based authentication with session caching
- **In Development**: RBAC system (see `.alucify/prd.md` and `.alucify/appgraph.json`)
- **Session Management**: Optional Redis-backed sessions
- **API Keys**: Per-user API key management for external integrations

## Common Patterns

### Backend Component Pattern

```python
from langbuilder.custom import Component
from langbuilder.schema.message import Message

class MyComponent(Component):
    display_name = "My Component"
    description = "Component description"
    icon = "IconName"

    async def run(self) -> Message:
        """Main execution method."""
        # Component logic here
        result = await self.process_data()
        return Message(text=result)

    async def message_response(self) -> Message:
        """Alternative: Return a Message object directly."""
        return Message(
            text=self.input_value,
            sender=self.sender,
            session_id=self.session_id,
        )
```

### Frontend API Call Pattern

```typescript
import { api } from '@/controllers/API';

export async function fetchFlows() {
  try {
    const response = await api.get('/flows/');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch flows:', error);
    throw error;
  }
}
```

### Zustand Store Pattern

```typescript
import { create } from 'zustand';

interface MyState {
  value: string;
  setValue: (value: string) => void;
}

export const useMyStore = create<MyState>((set) => ({
  value: '',
  setValue: (value) => set({ value }),
}));
```

### Testing Pattern

```python
from tests.base import ComponentTestBaseWithClient, VersionComponentMapping

class TestMyComponent(ComponentTestBaseWithClient):
    @pytest.fixture
    def component_class(self):
        return MyComponent

    @pytest.fixture
    def default_kwargs(self):
        return {"input_value": "test"}

    @pytest.fixture
    def file_names_mapping(self):
        return [
            VersionComponentMapping(
                version="1.1.1",
                module="my_module",
                file_name="my_component.py"
            ),
        ]
```

## Important Notes

- **Format Early**: Always run `make format_backend` BEFORE running linting or tests
- **Backend Auto-Reload**: Backend restarts on file changes (uvicorn --reload)
- **Frontend Hot-Reload**: Frontend supports hot module replacement
- **Component Updates**: Refresh browser after backend restart to see component changes
- **Test Isolation**: Database tests may fail in batch runs; run individually if needed
- **Async Context**: Be aware of ContextVar propagation in async tests
- **Icon Consistency**: Icon names must match exactly between backend and frontend
- **Version Mapping**: All components need version mapping for backward compatibility

## External Resources

- **Documentation**: https://docs.langbuilder.org
- **Repository**: https://github.com/cloudgeometry/langbuilder
- **LangChain Docs**: https://python.langchain.com/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **React Flow Docs**: https://reactflow.dev/

## RBAC Development (In Progress)

A comprehensive RBAC system is currently in development. See:
- `.alucify/prd.md` - Product requirements document
- `.alucify/architecture.md` - Detailed architecture specification
- `.alucify/appgraph.json` - RBAC impact analysis and implementation graph

The RBAC implementation includes organization/workspace isolation, role-based permissions, resource-level access control, and audit logging.
