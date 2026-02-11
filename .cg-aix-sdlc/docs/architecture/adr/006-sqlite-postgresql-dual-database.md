# ADR-006: SQLite/PostgreSQL Dual Database Strategy

## Status

Accepted

## Date

2026-02-09

## Decision Makers

- LangBuilder Development Team

## Context

### Problem Statement

LangBuilder needs a relational database for persisting users, flows, messages, variables, API keys, credentials, and other application data across 10 models and 50 schema migrations. The project must support two distinct deployment contexts: (1) local development where a zero-configuration database accelerates developer productivity, and (2) production deployment where the database must handle concurrent access from multiple backend replicas and Celery workers with strong reliability guarantees. These two contexts have fundamentally different requirements.

### Constraints

- Development environments must be zero-configuration -- developers should not need to install and run a database server locally
- Production environments must support concurrent read/write access from multiple FastAPI backend instances and Celery workers
- The same SQLModel/SQLAlchemy model definitions must work with both databases without modification
- Alembic migrations (50 migrations) must be compatible with both database dialects
- Data integrity and ACID compliance are required for production workloads
- The database must support JSON fields for storing flow graph definitions

### Requirements

- Zero-configuration database for development (no external process or installation)
- Production-grade database with connection pooling, concurrent access, and replication support
- Single ORM model definition compatible with both databases
- JSON field support for storing workflow graph definitions
- Async driver support for both databases
- Backup and recovery capabilities in production

## Decision

Use a dual-database strategy: SQLite for development and PostgreSQL for production. SQLite is the default database when no `DATABASE_URL` is configured, providing an instant zero-configuration development experience. PostgreSQL 15 is used for staging and production deployments, configured via the `DATABASE_URL` environment variable. SQLAlchemy's dialect system (used by SQLModel) abstracts the differences, allowing the same model definitions and most queries to work with both databases.

This dual strategy was chosen because it provides the best developer experience (no database setup for local development) while meeting production requirements (concurrent access, connection pooling, reliability) without requiring developers to maintain two separate codebases.

## Consequences

### Positive

- Developers can start working immediately without installing PostgreSQL; SQLite creates a database file automatically on first run
- Production deployments get PostgreSQL's full feature set: connection pooling, concurrent access, WAL-based replication, and mature backup tooling
- SQLAlchemy's dialect abstraction means the same SQLModel classes work with both databases, with minimal dialect-specific code
- CI pipelines can run tests against SQLite for fast feedback, with integration tests against PostgreSQL for dialect-specific validation
- Transitioning from development to production requires only setting the `DATABASE_URL` environment variable

### Negative

- SQLite and PostgreSQL have behavioral differences that can cause subtle bugs: SQLite is more permissive with type coercion, does not enforce foreign key constraints by default, and handles concurrent writes differently
- Some PostgreSQL-specific features (e.g., `JSONB` operators, array types, full-text search) cannot be used in code that must also run on SQLite
- Alembic migrations must be tested against both dialects to ensure compatibility, as some DDL operations differ between SQLite and PostgreSQL
- SQLite's single-writer concurrency model means development environments do not exercise the concurrent access patterns that occur in production

### Neutral

- The async driver for SQLite (`aiosqlite`) is a wrapper around synchronous SQLite access; true async I/O is only achieved with PostgreSQL's `psycopg` async driver
- Docker Compose development setups can optionally include PostgreSQL for testing closer to production conditions
- The database file for SQLite development is stored locally and is not committed to version control

## Alternatives Considered

### PostgreSQL Only

**Pros**: Single database dialect eliminates behavior differences between dev and prod; developers test against the exact same database engine used in production; full access to PostgreSQL-specific features everywhere
**Cons**: Every developer must install and run PostgreSQL locally (or use Docker), adding setup friction; connection configuration is required even for simple local development; new contributors face a higher barrier to entry
**Why not chosen**: The developer experience cost of requiring PostgreSQL for local development was deemed too high. Many contributors work on frontend or component code that does not require a production-grade database, and forcing PostgreSQL setup for all developers would slow onboarding.

### SQLite Only

**Pros**: Maximum simplicity; single database everywhere; no dialect differences; zero configuration for all environments
**Cons**: SQLite does not support concurrent writes from multiple processes, making it unsuitable for production deployments with multiple backend replicas and Celery workers; no connection pooling; limited backup and replication options; no row-level locking; WAL mode helps but does not fully solve concurrent access
**Why not chosen**: SQLite cannot meet production requirements for concurrent access from multiple backend instances and Celery workers. A single-writer database is fundamentally incompatible with a horizontally scaled deployment.

### MySQL / MariaDB

**Pros**: Widely deployed, good performance, strong ecosystem, supports concurrent access and replication
**Cons**: Less feature-rich than PostgreSQL (weaker JSON support, fewer data types, limited window functions in older versions); SQLAlchemy/SQLModel ecosystem has stronger PostgreSQL support and testing; PostgreSQL is more common in the Python web application ecosystem
**Why not chosen**: PostgreSQL offers stronger JSON support (critical for storing flow graph definitions), better SQLAlchemy ecosystem integration, and is the more common choice in the Python and LangChain communities, which simplifies troubleshooting and community support.

## Implementation Notes

- Default configuration uses SQLite with the database file at `langbuilder.db` in the working directory
- PostgreSQL connection is configured via `DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/langbuilder`
- Alembic migration URL uses synchronous drivers: `SQLMODEL_MIGRATE_URL=postgresql://user:pass@host:5432/langbuilder`
- Connection pool settings for PostgreSQL: `pool_size=20`, `max_overflow=30`, `connect_timeout=30s`
- Docker Compose deployment includes PostgreSQL 15 as a service with persistent volume (`app-db-data`)
- Health checks use `pg_isready` for PostgreSQL container readiness
- Backup strategy: `pg_dump` for logical backups, WAL archiving for point-in-time recovery

## Related Decisions

- [ADR-005](005-sqlmodel-orm.md) - SQLModel provides the dialect abstraction that enables dual-database support
- [ADR-015](015-docker-multi-stage-builds.md) - Production Docker deployment includes PostgreSQL as a containerized service
- [ADR-011](011-celery-rabbitmq-redis-task-queue.md) - Celery workers require a production database that supports concurrent access

## References

- https://www.sqlite.org/
- https://www.postgresql.org/docs/15/
- https://docs.sqlalchemy.org/en/20/dialects/
- https://www.psycopg.org/psycopg3/docs/
- https://aiosqlite.omnilib.dev/
