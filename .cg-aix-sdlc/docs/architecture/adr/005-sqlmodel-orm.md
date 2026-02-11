# ADR-005: SQLModel for ORM

## Status

Accepted

## Date

2026-02-09

## Decision Makers

- LangBuilder Development Team

## Context

### Problem Statement

LangBuilder needs an object-relational mapper (ORM) for its 10 database models (User, Flow, Message, Variable, ApiKey, Folder, TransactionTable, VertexBuildTable, Credential, Component). The ORM must support both synchronous and asynchronous database access, integrate with Pydantic for request/response serialization in the FastAPI API layer, and provide the full power of SQLAlchemy for complex queries. A key pain point in many Python web applications is maintaining separate Pydantic models for API serialization and SQLAlchemy models for database access -- the team wanted to eliminate this duplication.

### Constraints

- Must support async database access for integration with FastAPI's async route handlers
- Must integrate with Pydantic v2 for API serialization (request/response bodies)
- Must support both SQLite (development) and PostgreSQL (production) via the same model definitions
- Must work with Alembic for schema migrations
- Must support SQLAlchemy's query builder for complex queries (joins, aggregations, subqueries)
- 10 database models with relationships between them

### Requirements

- Single model definition that serves as both database schema and API serialization schema
- Async session support via SQLAlchemy's AsyncSession
- Pydantic validation on model fields
- SQLAlchemy relationship support (foreign keys, backrefs)
- Compatibility with Alembic for migration generation and execution
- Type-safe query construction

## Decision

Use SQLModel (version 0.0.22) as the ORM layer. SQLModel is a library created by the author of FastAPI (Sebastian Ramirez) that combines SQLAlchemy and Pydantic into a single model class. A SQLModel class is simultaneously a SQLAlchemy model (for database operations) and a Pydantic model (for validation and serialization), eliminating the need to maintain separate model hierarchies.

SQLModel was chosen because it uniquely solves the model duplication problem that plagues FastAPI + SQLAlchemy applications. A single `Flow` class definition serves as the database table schema, the API response model, and the API request validation schema, with field-level control over which fields are included in each context.

## Consequences

### Positive

- A single model class serves as both the database schema and the Pydantic serialization schema, eliminating the need to maintain separate SQLAlchemy models and Pydantic schemas and the mapping logic between them
- Native FastAPI integration means SQLModel instances can be returned directly from route handlers and FastAPI will serialize them correctly
- Full SQLAlchemy power is available for complex queries, relationships, and database operations -- SQLModel is built on top of SQLAlchemy, not a simplified replacement
- Pydantic v2 validation is applied to model fields, catching invalid data before it reaches the database
- Async database access is supported via SQLAlchemy's AsyncSession, integrating seamlessly with FastAPI's async route handlers
- Alembic works with SQLModel models for migration generation, since SQLModel models are SQLAlchemy models under the hood

### Negative

- SQLModel (0.0.22) is still in pre-1.0 status, meaning the API may change in future releases
- Documentation is less comprehensive than SQLAlchemy's or Django ORM's, and some advanced SQLAlchemy patterns require referring to SQLAlchemy docs directly
- The merged model approach can lead to confusion about which fields should be exposed in API responses versus kept internal, requiring careful use of `Field(exclude=True)` and model inheritance
- Some SQLAlchemy features (e.g., complex mapper configurations) require dropping down to raw SQLAlchemy syntax, breaking the SQLModel abstraction
- Smaller community compared to SQLAlchemy or Django ORM means fewer example applications and Stack Overflow answers

### Neutral

- SQLModel is a thin layer on top of SQLAlchemy + Pydantic, so knowledge of either library transfers directly
- The 10 database models in LangBuilder are moderately complex, with foreign key relationships and JSON fields, all of which are well-supported by SQLModel
- 50 Alembic migrations manage the schema evolution, and these work identically whether using SQLModel or raw SQLAlchemy

## Alternatives Considered

### SQLAlchemy + Separate Pydantic Models

**Pros**: SQLAlchemy is the most mature and powerful Python ORM with comprehensive documentation, a massive community, and support for virtually any database pattern; Pydantic models provide clean API schemas
**Cons**: Requires maintaining two parallel model hierarchies (SQLAlchemy models for DB, Pydantic models for API) with mapping logic between them; this duplication is error-prone and adds significant boilerplate, especially with 10 models
**Why not chosen**: The model duplication problem was a primary concern. With 10 models, maintaining separate SQLAlchemy and Pydantic classes plus mappers between them would add hundreds of lines of boilerplate and create a constant synchronization burden.

### Django ORM

**Pros**: Mature, well-documented, powerful migration system, large community, admin interface
**Cons**: Tightly coupled to the Django framework, which was rejected in favor of FastAPI (see ADR-002); no native Pydantic integration; async support is limited and many ORM operations are still synchronous; using Django ORM outside Django requires django-standalone setup which adds complexity
**Why not chosen**: Django ORM cannot be cleanly used outside the Django framework, and LangBuilder uses FastAPI. Additionally, Django ORM's limited async support was incompatible with the async-first backend design.

### Tortoise ORM

**Pros**: Async-first ORM designed for modern Python async frameworks, Django-inspired API, built-in Pydantic serialization support
**Cons**: Smaller community and ecosystem compared to SQLAlchemy, less powerful query builder, fewer supported database features, less mature migration tooling (Aerich vs Alembic), not built on SQLAlchemy so no fallback to SQLAlchemy's full feature set
**Why not chosen**: Tortoise ORM's smaller ecosystem and less powerful query builder posed a risk for the complex queries LangBuilder requires. SQLModel provides async support while retaining full access to SQLAlchemy's query capabilities as a fallback.

### Piccolo ORM

**Pros**: Async-native, type-safe query builder, auto-generated admin interface, built-in migration system
**Cons**: Very small community, limited third-party integrations, less battle-tested than SQLAlchemy, no direct Pydantic model unification
**Why not chosen**: Piccolo's small community and limited ecosystem made it a risky choice for a production application. The lack of Pydantic model unification meant the model duplication problem would remain.

## Implementation Notes

- Models inherit from `SQLModel` with `table=True` for database-backed models and without for pure schema models
- Async sessions are created via SQLAlchemy's `create_async_engine()` and `async_sessionmaker()`
- Database sessions are injected into route handlers via FastAPI's `Depends(get_session)` pattern
- Alembic is configured with `target_metadata = SQLModel.metadata` for migration auto-generation
- The `aiosqlite` driver is used for async SQLite access in development; `psycopg` (async) is used for PostgreSQL in production
- Connection pool settings: `pool_size=20`, `max_overflow=30`, `connect_timeout=30s`

## Related Decisions

- [ADR-002](002-fastapi-backend-api.md) - FastAPI integration was a primary motivator for choosing SQLModel
- [ADR-006](006-sqlite-postgresql-dual-database.md) - SQLModel's SQLAlchemy foundation supports both SQLite and PostgreSQL via dialect switching

## References

- https://sqlmodel.tiangolo.com/
- https://www.sqlalchemy.org/
- https://docs.pydantic.dev/
- https://alembic.sqlalchemy.org/
