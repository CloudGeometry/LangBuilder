# ADR-002: FastAPI for Backend API

## Status

Accepted

## Date

2026-02-09

## Decision Makers

- LangBuilder Development Team

## Context

### Problem Statement

LangBuilder requires a high-performance Python web framework to serve its REST API. The API layer handles workflow CRUD operations, component registry queries, flow execution triggers, chat interactions, user authentication, and real-time streaming of LLM output tokens. The framework must support asynchronous I/O natively because the majority of operations involve waiting on external LLM providers, database queries, and message broker interactions -- all of which are I/O-bound.

### Constraints

- Must be a Python framework (the entire backend, including LangChain, is Python)
- Must support native async/await for non-blocking I/O
- Must provide automatic API documentation for developer experience
- Must integrate well with Pydantic for request/response validation (LangChain and the component system already use Pydantic extensively)
- Must support WebSocket connections for real-time LLM output streaming
- Must support middleware for CORS, sessions, authentication, and audit logging

### Requirements

- Native async route handlers
- Automatic OpenAPI (Swagger) documentation generation
- Pydantic integration for request validation and response serialization
- WebSocket support for streaming
- Dependency injection system for service layer composition
- High throughput for concurrent I/O-bound requests
- Active maintenance and strong community

## Decision

Use FastAPI (version 0.115+) as the backend API framework. FastAPI is built on top of Starlette (ASGI) and Pydantic, providing native async support, automatic OpenAPI documentation, and first-class Pydantic integration. The API is organized into 18 v1 routers and 2 v2 routers, served by Uvicorn as the ASGI server with optional Gunicorn for production process management.

FastAPI was chosen because its core design aligns precisely with LangBuilder's requirements: async-first for I/O-heavy LLM operations, Pydantic-native for seamless integration with the component schema system, and automatic OpenAPI docs that serve as both developer documentation and an interactive testing tool.

## Consequences

### Positive

- Native async/await eliminates the need for thread pools or callback-based patterns when calling LLM providers, databases, and message brokers
- Automatic OpenAPI documentation at `/docs` (Swagger UI) and `/redoc` provides interactive API exploration without manual documentation effort
- Pydantic integration means request bodies are automatically validated against typed schemas, and response models are automatically serialized -- the same Pydantic models used by LangChain components can serve as API schemas
- Dependency injection via `Depends()` provides clean composition of services, database sessions, and authentication middleware
- High performance for I/O-bound workloads, consistently ranking among the fastest Python web frameworks in benchmarks
- WebSocket support is built into Starlette, enabling real-time streaming of LLM tokens to the frontend

### Negative

- FastAPI's async model requires care to avoid blocking the event loop -- CPU-bound operations (e.g., large graph computations) must be offloaded to Celery workers or run in thread pool executors
- The ecosystem of third-party middleware and extensions is smaller than Django's
- FastAPI does not include an ORM, admin panel, or migration system, requiring separate tools (SQLModel, Alembic) for data access
- Debugging async stack traces can be more complex than synchronous frameworks

### Neutral

- FastAPI is a "micro-framework" that provides API tooling but not a full application framework; this aligns with LangBuilder's modular monolith design where each concern (ORM, migrations, task queue) uses a best-of-breed tool
- The choice of ASGI (via Uvicorn) over WSGI means traditional WSGI middleware is not directly compatible

## Alternatives Considered

### Django + Django REST Framework

**Pros**: Batteries-included framework with ORM, admin panel, migration system, and a massive ecosystem of third-party packages; Django REST Framework provides mature serialization, viewsets, and browsable API; large community and extensive documentation
**Cons**: Synchronous by default; Django's async support (introduced in 3.1+) is still evolving and many ORM operations remain synchronous; Django REST Framework does not use Pydantic, requiring a separate serialization layer; heavyweight for an API-focused application that does not need Django's templating, forms, or admin features
**Why not chosen**: Django's synchronous-first design was incompatible with LangBuilder's requirement for native async I/O across all operations. The overhead of a full framework with unused features (templates, forms, admin) added complexity without benefit.

### Flask

**Pros**: Lightweight, flexible, widely adopted, large ecosystem of extensions, simple to learn
**Cons**: Synchronous by default (WSGI); async support via `async def` routes was added later but lacks the first-class async ecosystem of FastAPI; no built-in validation or OpenAPI generation; requires Flask-RESTful or similar extension for structured API development; no native Pydantic integration
**Why not chosen**: Flask's lack of native async support and the need for multiple extensions to achieve what FastAPI provides out of the box (validation, OpenAPI docs, dependency injection) made it a less productive choice.

### Litestar (formerly Starlite)

**Pros**: ASGI-native, built-in validation, OpenAPI support, dependency injection, performance-oriented design
**Cons**: Smaller community and ecosystem compared to FastAPI, less third-party integration support, fewer learning resources and tutorials, Pydantic integration is available but not as deeply embedded as in FastAPI
**Why not chosen**: While Litestar is technically capable, its smaller community and ecosystem meant less available middleware, fewer third-party integrations, and a higher risk of encountering undocumented edge cases. FastAPI's larger community and LangChain ecosystem alignment were decisive factors.

## Implementation Notes

- The API is versioned with `/api/v1/` (18 routers) and `/api/v2/` (2 routers) prefixes
- An OpenAI-compatible chat completions endpoint allows deployed flows to be consumed by any OpenAI-compatible client
- Middleware stack order: CORS -> Session (Redis) -> Audit Logging -> Compression -> Authentication -> Route Handler
- Dependency injection is used extensively: `get_session` provides async database sessions, `get_current_user` provides the authenticated user, and service factories provide domain services
- Uvicorn serves the application in development with `--reload`; Gunicorn with Uvicorn workers is used in production

## Related Decisions

- [ADR-003](003-langchain-ai-framework.md) - LangChain integrates with FastAPI's async handlers for non-blocking LLM execution
- [ADR-005](005-sqlmodel-orm.md) - SQLModel was chosen partly for its native FastAPI integration
- [ADR-014](014-jwt-oauth2-authentication.md) - Authentication middleware integrates with FastAPI's dependency injection

## References

- https://fastapi.tiangolo.com/
- https://www.starlette.io/
- https://docs.pydantic.dev/
- https://www.uvicorn.org/
