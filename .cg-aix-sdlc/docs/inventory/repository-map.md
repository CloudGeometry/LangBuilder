# Repository Map

> Generated: 2026-02-09 | LangBuilder v1.6.5

## Structure

```
langbuilder/                          # Root repository
├── langbuilder/                      # Main application (UV workspace)
│   ├── pyproject.toml               # Python package config (v1.6.5)
│   ├── src/
│   │   ├── backend/                 # Python backend
│   │   │   ├── base/               # langbuilder-base package
│   │   │   │   ├── langbuilder/
│   │   │   │   │   ├── main.py     # FastAPI app entry point
│   │   │   │   │   ├── api/        # REST API routers (v1, v2)
│   │   │   │   │   ├── services/   # Business services & DB
│   │   │   │   │   ├── components/ # 96 component packages
│   │   │   │   │   ├── custom/     # Custom component infrastructure
│   │   │   │   │   ├── interface/  # Component discovery
│   │   │   │   │   ├── graph/      # Graph/flow processing engine
│   │   │   │   │   ├── alembic/    # Database migrations (50)
│   │   │   │   │   └── settings.py # Application settings
│   │   │   │   └── pyproject.toml  # langbuilder-base config (v0.6.5)
│   │   │   ├── langbuilder/        # Main backend module
│   │   │   │   └── components/     # Additional components
│   │   │   ├── langflow/           # Langflow compatibility layer
│   │   │   └── tests/             # Backend test suite
│   │   │       ├── unit/
│   │   │       ├── integration/
│   │   │       ├── performance/
│   │   │       └── locust/         # Load testing
│   │   └── frontend/               # React frontend
│   │       ├── package.json        # Node.js config (v1.6.5)
│   │       ├── src/
│   │       │   ├── components/     # 135 component directories
│   │       │   ├── pages/          # 17 page directories
│   │       │   ├── stores/         # 16 Zustand stores
│   │       │   ├── controllers/    # API layer (21 query categories)
│   │       │   ├── CustomNodes/    # React Flow custom nodes
│   │       │   ├── CustomEdges/    # React Flow custom edges
│   │       │   ├── modals/         # 30 modal components
│   │       │   ├── hooks/          # Custom React hooks
│   │       │   ├── icons/          # 139 icon components
│   │       │   ├── contexts/       # React context providers
│   │       │   ├── types/          # TypeScript type definitions
│   │       │   └── utils/          # Utility functions
│   │       ├── tests/              # Playwright E2E tests
│   │       └── vite.config.mts     # Vite build config
│   ├── deploy/                     # Production deployment
│   │   └── docker-compose.yml     # Production services (11)
│   └── scripts/                   # Automation scripts
│       └── aws/                   # AWS CDK deployment
├── openwebui/                      # OpenWebUI integration
│   ├── backend/                   # OpenWebUI Python backend
│   └── src/                       # OpenWebUI Svelte frontend
├── docs/                           # Documentation site
├── docker/                         # Docker build files
├── docker-compose.dev.yml         # Development services (5)
├── .github/                       # GitHub Actions (34 workflows)
│   └── workflows/
└── .cg-aix-sdlc/                  # Generated documentation
```

## Services Identified

- **LangBuilder Backend**: `langbuilder/src/backend/` (Python/FastAPI)
- **LangBuilder Frontend**: `langbuilder/src/frontend/` (TypeScript/React)
- **OpenWebUI Backend**: `openwebui/backend/` (Python/FastAPI)
- **OpenWebUI Frontend**: `openwebui/src/` (TypeScript/Svelte)

## Statistics

| Metric | Count |
|--------|-------|
| Total source files | ~2,880 |
| Python files (.py) | 1,482 |
| TypeScript files (.ts) | 512 |
| TypeScript React files (.tsx) | 634 |
| JavaScript files (.js/.jsx) | 172 |
| Backend component packages | 96 |
| API endpoints | 157 |
| Database models | 10 |
| Alembic migrations | 50 |
| GitHub Actions workflows | 34 |
| Docker services (dev) | 5 |
| Docker services (prod) | 11 |

## Monorepo Structure

**Tool**: UV Workspace
**Packages**:
- `langbuilder` (main application, v1.6.5)
- `langbuilder-base` (shared library, v0.6.5)

## Special Directories

| Directory | Purpose |
|-----------|---------|
| `langbuilder/src/backend/base/langbuilder/components/` | 96 pluggable component packages (LLM providers, vector stores, tools) |
| `langbuilder/src/backend/base/langbuilder/alembic/` | 50 database migration files |
| `langbuilder/src/backend/tests/` | Unit, integration, performance, and load tests |
| `langbuilder/src/frontend/tests/` | Playwright E2E tests |
| `langbuilder/deploy/` | Production deployment configuration |
| `.github/workflows/` | 34 CI/CD workflow definitions |
