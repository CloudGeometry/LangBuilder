# System Architecture - LangBuilder

> Generated: 2026-02-09 | LangBuilder v1.6.5

## Overview

LangBuilder is an AI workflow builder platform that enables developers and teams to create, deploy, and manage LangChain-based AI workflows through a visual drag-and-drop interface. Built as a fork and extension of LangFlow, LangBuilder adds enterprise-grade infrastructure, a plugin-first component system, and production deployment tooling on top of the core graph execution paradigm.

## Architecture Style

**Modular Monolith with Plugin System**

LangBuilder follows a modular monolith architecture where the backend is deployed as a single process but is internally structured into well-defined modules with clear boundaries. The plugin system allows 96 component packages to be loaded, discovered, and executed independently without modifying the core application.

### Primary Pattern: Component-based Graph Execution

Workflows are represented as directed acyclic graphs (DAGs). Each node in the graph is a pluggable component that performs a discrete unit of work (LLM call, data transformation, tool invocation, etc.). The graph engine handles dependency resolution via topological sorting, cycle detection, and coordinated async execution of vertices.

```
                                    ┌──────────────────────────────────────────┐
                                    │            External Systems               │
                                    │  ┌─────────┐ ┌─────────┐ ┌───────────┐   │
                                    │  │   LLM   │ │ Vector  │ │Enterprise │   │
                                    │  │Providers│ │ Stores  │ │   Tools   │   │
                                    │  └────┬────┘ └────┬────┘ └─────┬─────┘   │
                                    └───────│──────────│────────────│─────────┘
                                            │          │            │
                     ┌──────────────────────│──────────│────────────│───────────┐
                     │                      │    LangBuilder System  │           │
                     │                      v          v            v           │
 ┌─────────┐        │  ┌──────────────────────────────────────────────────┐    │
 │  Users  │◄───────┼─►│                  Backend API                      │    │
 │(Browser)│  HTTPS  │  │              (FastAPI + LangChain)                │    │
 └─────────┘        │  │                                                   │    │
      │             │  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │    │
      │             │  │  │   API    │  │  Graph   │  │  Component   │    │    │
      │             │  │  │ Routers  │──│  Engine  │──│  Registry    │    │    │
      │             │  │  └──────────┘  └──────────┘  └──────────────┘    │    │
      │             │  │        │                            │            │    │
      │             │  └────────│────────────────────────────│────────────┘    │
      │             │           │                            │                 │
      │             │           v                            v                 │
      │             │  ┌─────────────┐              ┌─────────────────┐       │
      │             │  │  Database   │              │  Celery Workers │       │
      │             │  │(PostgreSQL) │              │  (Background)   │       │
      │             │  └─────────────┘              └─────────────────┘       │
      │             │                                       │                 │
      │             │                               ┌───────┴───────┐         │
      │             │                               │               │         │
      │             │                          ┌────┴───┐     ┌─────┴────┐    │
      │             │                          │ Redis  │     │ RabbitMQ │    │
      │             │                          └────────┘     └──────────┘    │
      │             └─────────────────────────────────────────────────────────┘
      │
      │             ┌─────────────────────────────────────────────────────────┐
      └─────────────┤                  Frontend Web App                        │
          HTTPS     │                   (React + React Flow)                    │
                    │                                                          │
                    │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐       │
                    │  │  Pages   │  │  Flow    │  │  State Stores    │       │
                    │  │ (Router) │──│  Canvas  │──│    (Zustand)     │       │
                    │  └──────────┘  └──────────┘  └──────────────────┘       │
                    └─────────────────────────────────────────────────────────┘
```

## System Purpose and Goals

### Primary Goals

1. **Visual Workflow Design**: Enable no-code and low-code workflow creation through an intuitive graph canvas interface
2. **LLM Provider Agnostic**: Support multiple LLM providers (OpenAI, Anthropic, Google, Ollama, and others) through consistent component interfaces
3. **Extensibility**: Plugin-first architecture with 96 component packages across 12 categories
4. **Production Ready**: Full deployment pipeline from local development through Docker Compose to AWS EC2 with Traefik, monitoring, and observability
5. **Developer Experience**: Visual editor, REST API (v1/v2), OpenAI-compatible endpoint, and programmatic access

### Target Users

| User Type | Primary Use Case |
|-----------|------------------|
| **AI Engineers** | Building complex AI pipelines with multiple LLM providers and tools |
| **Developers** | Integrating AI capabilities into applications via API |
| **Data Scientists** | Prototyping and iterating on ML/AI workflows |
| **Business Users** | Creating chatbots, automation flows, and RAG pipelines |

## Design Principles

### 1. Plugin-First Architecture

Every AI capability is encapsulated as a pluggable component package. The core system provides the execution engine, API layer, and frontend canvas; all domain-specific logic (LLM calls, vector stores, document loaders, etc.) lives in independently versioned component packages.

- **96 component packages** organized into **12 categories**
- Components are discovered at startup via a registry/discovery mechanism
- New capabilities are added by creating a new component package -- no changes to the core required
- Each component declares its inputs, outputs, and configuration schema via Pydantic models

### 2. Graph-Based Execution

Workflows are first-class directed acyclic graphs:

- **Cycle detection** prevents invalid workflow topologies at build time
- **Topological sorting** determines correct execution order respecting data dependencies
- **Async execution** allows independent branches to run concurrently
- The visual canvas (React Flow 12.x) is a direct representation of the execution graph -- what you see is what runs

### 3. Async-First Design

The entire backend is built around Python's async/await:

- FastAPI with async route handlers
- Async database access via SQLModel/SQLAlchemy async sessions
- Async LangChain chain and agent execution
- Celery for offloading long-running or CPU-bound tasks to background workers
- WebSocket connections for real-time streaming of LLM outputs

### 4. Dual-Frontend Strategy

LangBuilder maintains two frontend experiences:

- **React Flow Canvas**: The primary visual workflow editor for building and testing flows
- **Chat Interface**: A conversational interface for interacting with deployed flows
- Both share state management (Zustand) and API client layers (TanStack Query)

### 5. LangChain Ecosystem Integration

LangBuilder is built on top of LangChain 0.3.x and its ecosystem:

- Components wrap LangChain primitives (BaseChatModel, BaseRetriever, VectorStore, etc.)
- LangChain's provider abstraction ensures LLM-agnostic workflows
- MCP (Model Context Protocol) integration for dynamic tool discovery
- Compatible with LangSmith for tracing and observability

## Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Architecture Style** | Modular Monolith | Simpler deployment and operations than microservices while maintaining clear internal module boundaries; single process avoids network overhead between components |
| **API Framework** | FastAPI 0.115+ | Native async support, automatic OpenAPI docs, Pydantic integration, high performance for I/O-bound LLM operations |
| **AI Framework** | LangChain 0.3.x | Provider-agnostic LLM abstraction, large ecosystem of integrations, active community, pre-built chains and agents |
| **Graph Engine** | Custom DAG Engine | Tight integration with component registry; supports cycle detection, topological sorting, parallel async vertex execution, and real-time streaming |
| **ORM** | SQLModel 0.0.22 | Combines SQLAlchemy power with Pydantic validation; single model serves both DB schema and API serialization; FastAPI-native |
| **Database** | SQLite (dev) / PostgreSQL (prod) | SQLite for zero-config development; PostgreSQL for production with connection pooling, concurrent access, and reliability |
| **Frontend Framework** | React 18.x + TypeScript 5.4 | Mature ecosystem, strong typing, excellent developer tooling; React 18 concurrent features for responsive canvas |
| **Flow Canvas** | React Flow 12.x (@xyflow/react) | Purpose-built for node-based graph editors; custom node/edge rendering, built-in pan/zoom/selection, active maintenance |
| **State Management** | Zustand 4.5 | Minimal boilerplate compared to Redux, direct state access, excellent performance with large graph state, easy testing |
| **Build Tooling** | Vite + SWC | Fast HMR in development, optimized production builds with code splitting; SWC compiler for TypeScript transpilation speed |
| **Data Fetching** | TanStack Query | Automatic caching, background refetching, optimistic updates; decouples server state from client state |
| **Task Queue** | Celery + RabbitMQ + Redis | Battle-tested distributed task execution; RabbitMQ for reliable message delivery, Redis for result backend and caching |
| **Reverse Proxy** | Traefik v3 | Automatic service discovery, Let's Encrypt TLS, Docker-native configuration, dashboard for routing visibility |
| **Migrations** | Alembic (50 migrations) | Industry-standard SQLAlchemy migration tool; supports auto-generation, branching, and rollback |
| **Monitoring** | Prometheus + Grafana | De facto standard for metrics collection and visualization; extensive ecosystem of exporters and dashboards |
| **Containerization** | Docker multi-stage builds | Optimized image sizes; separate build and runtime stages; reproducible builds across environments |
| **CI/CD** | GitHub Actions | Integrated with repository; manual workflow_dispatch trigger for controlled deployments to AWS EC2 via SSH |
| **Python Versions** | 3.10 - 3.14 | Broad compatibility; 3.10 minimum for match statements and modern typing; 3.14 support for forward-looking adoption |

## Technology Stack

### Backend Technologies

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Runtime** | Python | 3.10 - 3.14 | Language runtime |
| **API Framework** | FastAPI | 0.115+ | REST API with OpenAPI docs |
| **AI Framework** | LangChain | 0.3.x | LLM orchestration and abstraction |
| **Validation** | Pydantic | 2.x | Data validation and serialization |
| **ORM** | SQLModel | 0.0.22 | Database access and model definitions |
| **Migrations** | Alembic | 1.13+ | Schema migrations (50 migrations) |
| **Task Queue** | Celery | latest | Background job execution |
| **Server** | Uvicorn | 0.30+ | ASGI server |

### Frontend Technologies

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Framework** | React | 18.x | UI framework |
| **Language** | TypeScript | 5.4 | Static typing |
| **Build Tool** | Vite + SWC | 5.4 | Fast builds and HMR |
| **Canvas** | React Flow (@xyflow/react) | 12.x | Visual graph editor |
| **State** | Zustand | 4.5 | Client state management |
| **Data Fetching** | TanStack Query | latest | Server state and caching |
| **Styling** | TailwindCSS | 3.4 | Utility-first CSS |
| **Components** | Radix UI | latest | Accessible UI primitives |

### Infrastructure Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Database** | PostgreSQL 15 / SQLite | Data persistence (10 models) |
| **Cache / Result Backend** | Redis 6.2+ | Caching, sessions, Celery results |
| **Message Broker** | RabbitMQ 3.x | Celery task distribution |
| **Reverse Proxy** | Traefik v3 | Load balancing, TLS termination, routing |
| **Monitoring** | Prometheus + Grafana | Metrics collection and dashboards |
| **Containers** | Docker | Multi-stage builds, deployment packaging |

## Service Layer Architecture

LangBuilder's backend is organized around 18 internal services that encapsulate domain logic:

| Service | Responsibility |
|---------|---------------|
| **auth** | Authentication (JWT), authorization, user management |
| **cache** | Application-level caching abstraction over Redis |
| **chat** | Chat session management, message history, streaming |
| **database** | Database connection management, session factory |
| **flow** | Flow CRUD operations, flow versioning, import/export |
| **job_queue** | Celery task submission, job status tracking |
| **session** | User session lifecycle, session storage |
| **settings** | Application configuration, environment variable binding |
| **socket** | WebSocket connection management, real-time events |
| **state** | Runtime state for flow execution, vertex state tracking |
| **storage** | File storage abstraction (local filesystem, S3) |
| **store** | Component store, marketplace-style component browsing |
| **task** | Background task orchestration, task result retrieval |
| **telemetry** | Usage telemetry, anonymous analytics |
| **tracing** | Execution tracing, LangSmith integration |
| **variable** | Global and flow-scoped variable management |
| **shared_component_cache** | Cross-flow component instance caching |
| **flow** | Flow execution coordination (graph building, running) |

## API Architecture

### API Versioning

| Version | Routers | Purpose |
|---------|---------|---------|
| **v1** | 18 routers | Primary API surface -- flows, components, chat, auth, settings, store, variables, etc. |
| **v2** | 2 routers | Newer endpoints with improved contracts and additional capabilities |

### OpenAI-Compatible Endpoint

LangBuilder exposes an OpenAI-compatible chat completions endpoint, allowing deployed flows to be consumed by any client that supports the OpenAI API format. This enables drop-in replacement scenarios and integration with tools that expect the OpenAI interface.

## Graph Execution Engine

### Execution Pipeline

```
Flow Definition (JSON)
        │
        v
┌─────────────────┐
│   Parse Graph    │  Deserialize nodes and edges from flow JSON
│   Definition     │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Cycle Detection │  Validate DAG property -- reject cyclic graphs
│                  │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Topological     │  Determine execution order respecting
│  Sort            │  data dependencies between vertices
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Async Execution │  Execute vertices concurrently where
│  Coordinator     │  dependencies allow; stream results
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Result          │  Collect outputs, update state,
│  Aggregation     │  return final result
└─────────────────┘
```

### Key Engine Characteristics

- **DAG Validation**: Cycle detection runs before execution begins, providing fast feedback on invalid topologies
- **Topological Ordering**: Ensures each vertex executes only after all its upstream dependencies have completed
- **Parallel Execution**: Independent vertices (no shared dependencies) execute concurrently using Python asyncio
- **Streaming**: LLM output tokens are streamed to the frontend via WebSocket as they are generated
- **State Isolation**: Each flow execution maintains its own state context, preventing cross-execution contamination
- **Error Propagation**: Failures in upstream vertices propagate to downstream dependents with clear error context

## Component System

### Component Categories (12)

The 96 component packages are organized into the following categories:

| Category | Description | Example Components |
|----------|-------------|-------------------|
| **Models** | LLM provider integrations | OpenAI, Anthropic, Google, Ollama, Azure |
| **Prompts** | Prompt templates and management | PromptTemplate, ChatPromptTemplate |
| **Chains** | LangChain chain compositions | ConversationChain, RetrievalQA |
| **Agents** | Autonomous agent configurations | Tool-calling agents, ReAct agents |
| **Tools** | External tool integrations | Search, Calculator, API tools, MCP |
| **Memory** | Conversation memory backends | Buffer, Summary, Entity memory |
| **Embeddings** | Text embedding providers | OpenAI, Hugging Face, Cohere |
| **Vector Stores** | Vector database integrations | Pinecone, Chroma, Qdrant, FAISS |
| **Document Loaders** | Data ingestion | PDF, Web, CSV, database loaders |
| **Text Splitters** | Document chunking | Recursive, Token-based, Semantic |
| **Retrievers** | Retrieval strategies | Multi-query, Contextual compression |
| **Output Parsers** | Response formatting | JSON, Pydantic, Structured output |

### Component Lifecycle

1. **Discovery**: Component packages are scanned at startup and registered in the component registry
2. **Schema Generation**: Each component's Pydantic model generates input/output schemas for the frontend
3. **Instantiation**: When a flow is executed, components are instantiated with their configured parameters
4. **Execution**: The graph engine invokes the component's execution method within the vertex
5. **Caching**: Frequently used component instances may be cached via `shared_component_cache`

## Integration Patterns

### LLM Provider Integration

```
┌──────────────────────────────────────────────────────────┐
│                   Component Layer                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐           │
│  │OpenAIModel │ │AnthropicLLM│ │ GoogleLLM  │  ...      │
│  └──────┬─────┘ └──────┬─────┘ └──────┬─────┘           │
└─────────│──────────────│──────────────│────────────────────┘
          │              │              │
          v              v              v
┌──────────────────────────────────────────────────────────┐
│                LangChain Abstraction                      │
│           (BaseChatModel, BaseLanguageModel)               │
└──────────────────────────────────────────────────────────┘
          │              │              │
          v              v              v
     ┌─────────┐   ┌─────────┐   ┌─────────┐
     │ OpenAI  │   │Anthropic│   │ Google  │
     │   API   │   │   API   │   │   API   │
     └─────────┘   └─────────┘   └─────────┘
```

### MCP Protocol Integration

```
┌─────────────┐         ┌─────────────┐
│ LangBuilder │◄──SSE───│  MCP Server │
│   Backend   │───POST──│  (External) │
└─────────────┘         └─────────────┘
       │
       │ Tool Discovery
       │ Tool Execution
       │ Resource Access
       v
┌─────────────────────────────────────┐
│        MCP Protocol Layer           │
│  - stdio transport                  │
│  - SSE transport                    │
│  - Tool/Resource schemas            │
└─────────────────────────────────────┘
```

## Database Architecture

### Database Models (10)

LangBuilder uses SQLModel for ORM with support for SQLite (development) and PostgreSQL (production). The schema is managed by Alembic with 50 migrations tracking the full evolution history.

| Model | Purpose |
|-------|---------|
| **User** | User accounts, credentials, roles |
| **Flow** | Workflow definitions (graph JSON, metadata) |
| **Message** | Chat message history |
| **Variable** | Global and flow-scoped variables |
| **ApiKey** | API key management |
| **Folder** | Flow organization |
| **TransactionTable** | Execution transaction records |
| **VertexBuildTable** | Vertex build/execution logs |
| **Credential** | Encrypted credential storage |
| **Component** | Custom component definitions |

## Scalability Approach

### Horizontal Scaling via Celery Workers

The primary horizontal scaling mechanism is Celery workers backed by RabbitMQ (broker) and Redis (result backend):

- **Flow Execution**: Long-running or compute-intensive flow executions can be offloaded to Celery workers
- **Worker Scaling**: Additional Celery worker containers can be added independently to increase throughput
- **Queue Isolation**: Different task types can be routed to dedicated queues with independent scaling policies
- **Backend Replicas**: Multiple FastAPI instances behind Traefik share state via Redis and PostgreSQL

### Component Isolation

Each component package is independently loadable and has no direct dependencies on other component packages:

- Component failures are contained within the failing vertex -- they do not crash the engine
- Components can be hot-reloaded in development without restarting the entire backend
- Resource-intensive components (e.g., large model loading) can be scheduled on workers with appropriate resource allocation

### Caching Strategy

- **Redis**: Application-level cache for sessions, flow metadata, and frequently accessed data
- **Shared Component Cache**: In-memory cache for component instances that are expensive to instantiate
- **TanStack Query (Frontend)**: Automatic request deduplication, background refetching, and stale-while-revalidate for API data

## High Availability Patterns

### Stateless Application Tier

Both the frontend and backend containers are stateless:

- **Frontend**: Static assets served by Nginx; all state is client-side (Zustand) or server-fetched (TanStack Query)
- **Backend**: All persistent state is in PostgreSQL; all ephemeral state is in Redis; any instance can serve any request
- **Workers**: Celery workers are stateless consumers; tasks are idempotent where possible

### Data Tier Resilience

| Component | HA Strategy |
|-----------|-------------|
| **PostgreSQL** | Connection pooling, WAL-based replication for read replicas, regular backups |
| **Redis** | Persistence (RDB + AOF), optional Redis Sentinel or Cluster for failover |
| **RabbitMQ** | Durable queues, message acknowledgment, optional clustering for queue mirroring |

### Health Monitoring

- **Health Check Endpoints**: `/health` endpoint on the backend for load balancer probing
- **Docker Health Checks**: Container-level health checks for PostgreSQL, Redis, RabbitMQ, and the backend
- **Prometheus Metrics**: Application metrics exported for alerting on error rates, latency, and queue depth
- **Grafana Dashboards**: Pre-configured dashboards for system overview, API performance, and worker status

## Quality Attributes

### Performance

| Metric | Target | Approach |
|--------|--------|----------|
| API Response (non-LLM) | < 200ms | Async I/O, Redis caching, connection pooling |
| Flow Execution (simple) | < 5s | Parallel vertex execution, component caching |
| Frontend Initial Load | < 3s | Code splitting, lazy loading, Vite optimization |
| Concurrent Users | 100+ | Horizontal scaling, stateless design |

### Security

- **Authentication**: JWT tokens with refresh token rotation
- **Authorization**: Role-based access control
- **Data Protection**: Encrypted credential storage, secrets never logged
- **API Security**: Rate limiting, input validation via Pydantic, CORS policies
- **Network**: TLS termination at Traefik, internal Docker network isolation
- **API Keys**: Per-user API key management for programmatic access

### Reliability

- **Error Handling**: Graceful degradation with structured error responses; retry logic for transient failures
- **Health Checks**: Liveness and readiness probes on all services
- **Monitoring**: Prometheus metrics with Grafana dashboards and alerting
- **Logging**: Structured logging with configurable levels

## Evolution and Extensibility

### Extension Points

1. **Custom Components**: Create new component packages in Python with Pydantic schemas -- automatically discovered and available in the UI
2. **Custom Nodes**: Frontend node types can be extended for specialized rendering
3. **API Extensions**: V2 API surface for new capabilities alongside stable v1
4. **MCP Integration**: Dynamic tool discovery via Model Context Protocol servers
5. **Webhook / Callback Hooks**: Integration with external systems via HTTP callbacks

### Future Considerations

- Multi-tenant deployment with workspace isolation
- Enterprise SSO integration (SAML, OIDC)
- Advanced workflow versioning and rollback
- Collaborative real-time editing
- Component marketplace

---

*Generated by CloudGeometry AIx SDLC - Architecture Documentation*
