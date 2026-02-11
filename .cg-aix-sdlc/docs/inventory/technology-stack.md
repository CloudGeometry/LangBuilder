# Technology Stack

> Generated: 2026-02-09 | LangBuilder v1.6.5

## Languages

| Language | Version | Files | Primary Usage |
|----------|---------|-------|---------------|
| Python | >=3.10, <3.14 | 1,482 | Backend API, LLM components, graph engine |
| TypeScript | 5.4.5 | 512 | Frontend logic, API clients, types |
| TypeScript React (TSX) | 5.4.5 | 634 | UI components, pages, modals |
| JavaScript | ES2022 | 172 | Build config, utilities |

## Frameworks

### Backend

| Framework | Version | Purpose |
|-----------|---------|---------|
| **FastAPI** | >=0.115.2 | REST API framework (async) |
| **SQLModel** | 0.0.22 | ORM combining SQLAlchemy + Pydantic |
| **SQLAlchemy** | 2.0+ | Database engine (async via AsyncEngine) |
| **LangChain** | 0.3.23 | LLM orchestration framework |
| **Pydantic** | ~2.10.1 | Data validation and serialization |
| **Alembic** | >=1.13.0 | Database schema migrations |
| **Uvicorn** | >=0.30.0 | ASGI server |
| **Gunicorn** | >=22.0.0 | Production WSGI server |
| **Celery** | (via broker) | Distributed task queue |
| **Loguru** | >=0.7.1 | Structured logging |
| **Structlog** | >=25.4.0 | Structured logging (alternative) |

### Frontend

| Framework | Version | Purpose |
|-----------|---------|---------|
| **React** | 18.3.1 | UI framework |
| **Vite** | 5.4.19 | Build tool with SWC compilation |
| **Zustand** | 4.5.2 | State management (16 stores) |
| **TanStack Query** | 5.49.2 | Server state / API data fetching |
| **React Flow** | 12.3.6 (@xyflow/react) | Flow diagram editor |
| **React Router** | 6.23.1 | Client-side routing (~20 routes) |
| **React Hook Form** | 7.52.0 | Form state management |
| **Tailwind CSS** | 3.4.4 | Utility-first CSS framework |
| **Radix UI** | Various | Headless UI component primitives |
| **AG Grid** | 32.0.2 | Data tables and grids |
| **Framer Motion** | 11.2.10 | Animations |
| **Axios** | 1.7.4 | HTTP client |

### UI Component Libraries

| Library | Purpose |
|---------|---------|
| Radix UI | Headless accessible components (Accordion, Dialog, Select, etc.) |
| Headless UI | Transitions and overlays |
| Chakra UI | Number input, system utilities |
| shadcn/ui | Styled component patterns |
| Lucide React | Icon library |
| Tabler Icons | Icon library |
| React Icons | Icon library |

## Databases

| Database | Type | Purpose | Driver |
|----------|------|---------|--------|
| SQLite | Relational | Default development database | aiosqlite |
| PostgreSQL | Relational | Production database | psycopg (async) |
| Redis | Key-Value | Caching, Celery result backend | redis-py |

### Database Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| pool_size | 20 | Connection pool size |
| max_overflow | 30 | Max overflow connections |
| db_connect_timeout | 30s | Connection timeout |

## Infrastructure

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | Latest | Containerization |
| Docker Compose | v2 | Multi-container orchestration |
| Traefik | v3.0 | Reverse proxy with auto HTTPS |
| GitHub Actions | N/A | CI/CD (34 workflows) |
| Prometheus | v2.37.9 | Metrics collection |
| Grafana | v8.2.6 | Metrics visualization |
| RabbitMQ | 3 | Message broker for Celery |
| Flower | Latest | Celery task monitoring |
| PGAdmin | 4 | PostgreSQL management UI |
| AWS CDK | TypeScript | Infrastructure as code |

## Build Configuration

### Backend

| Setting | Value | Source |
|---------|-------|--------|
| Python Target | >=3.10, <3.14 | pyproject.toml |
| Package Manager | UV | UV workspace |
| Linter | Ruff | pyproject.toml |
| Type Checker | MyPy | pyproject.toml |

### Frontend

| Setting | Value | Source |
|---------|-------|--------|
| TypeScript Target | ES5 | tsconfig.json |
| Strict Mode | true | tsconfig.json |
| Module System | ESNext | tsconfig.json |
| Module Resolution | Node | tsconfig.json |
| JSX | react-jsx | tsconfig.json |
| Bundler | Vite 5.4.19 + SWC | vite.config.mts |
| Linter/Formatter | Biome 2.1.1 | package.json |

## Testing Frameworks

| Framework | Version | Type | Location |
|-----------|---------|------|----------|
| Pytest | 8.2+ | Unit/Integration (Python) | langbuilder/src/backend/tests/ |
| Jest | 30.0.3 | Unit (TypeScript) | langbuilder/src/frontend/src/ |
| Playwright | 1.52.0 | E2E (Browser) | langbuilder/src/frontend/tests/ |
| Locust | Latest | Load testing | langbuilder/src/backend/tests/locust/ |
| Testing Library | 16.0.0 | React component testing | langbuilder/src/frontend/src/ |

## Observability

| Tool | Purpose | Integration |
|------|---------|-------------|
| Sentry | Error tracking | sentry-sdk[fastapi,loguru] |
| OpenTelemetry | Distributed tracing | opentelemetry-sdk |
| Prometheus | Metrics | opentelemetry-exporter-prometheus |
| LangWatch | LLM observability | langwatch SDK |
| LangFuse | LLM tracing | langfuse SDK |
| LangSmith | LangChain tracing | langsmith SDK |

## LLM Provider Integrations (28 Component Packages)

| Provider | Package | Purpose |
|----------|---------|---------|
| OpenAI | langchain-openai | GPT models |
| Anthropic | langchain-anthropic | Claude models |
| Google | langchain-google-genai | Gemini models |
| Google Vertex AI | langchain-google-vertexai | Enterprise Google AI |
| Groq | langchain-groq | Fast inference |
| Mistral | langchain-mistralai | Mistral models |
| AWS Bedrock | langchain-aws | AWS managed models |
| Cohere | langchain-cohere | Cohere models |
| HuggingFace | langchain-huggingface | Open source models |
| Ollama | langchain-ollama | Local models |
| NVIDIA | langchain-nvidia-ai-endpoints | NVIDIA NIM |
| SambaNova | langchain-sambanova | SambaNova systems |
| + 16 more | Various | Additional LLM providers |

## Vector Database Integrations

| Database | Package | Purpose |
|----------|---------|---------|
| Pinecone | langchain-pinecone | Cloud vector search |
| ChromaDB | langchain-chroma | Embeddings database |
| Milvus | langchain-milvus | Distributed vector DB |
| MongoDB Atlas | langchain-mongodb | Vector search |
| Elasticsearch | langchain-elasticsearch | Full-text + vector |
| AstraDB | langchain-astradb | Cassandra-based vectors |
| Weaviate | weaviate-client | Vector database |
| Qdrant | qdrant-client | Vector similarity |
| FAISS | faiss-cpu | Local vector search |
| PGVector | pgvector | PostgreSQL vectors |
| Redis | redis | Vector similarity |
| Upstash | upstash-vector | Serverless vectors |
