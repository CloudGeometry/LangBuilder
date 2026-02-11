# ADR-011: Celery + RabbitMQ + Redis for Task Queue

## Status

Accepted

## Date

2026-02-09

## Decision Makers

- LangBuilder Development Team

## Context

### Problem Statement

LangBuilder executes AI workflows that can involve multiple sequential LLM calls, document processing, embedding generation, and vector store operations. Some of these workflows take seconds to minutes to complete, and executing them synchronously within the FastAPI request-response cycle would block the API server, degrade responsiveness for other users, and risk HTTP timeout errors. The system needs a distributed task execution mechanism that can offload long-running work to background workers, scale worker capacity independently of the API tier, and provide visibility into task status and results.

### Constraints

- Must support Python async/await for task implementation
- Must support reliable message delivery (tasks must not be lost if a worker crashes)
- Must allow independent scaling of workers based on queue depth
- Must provide task result storage for retrieving execution outcomes
- Must support task routing (different task types to different worker pools)
- Must support task monitoring and visibility for operational debugging
- Must integrate with the existing infrastructure (Docker Compose deployment)

### Requirements

- Reliable task queuing with at-least-once delivery semantics
- Background worker processes that can execute LangChain workflows
- Result backend for storing and retrieving task outcomes
- Task status tracking (pending, started, success, failure)
- Worker scaling independent of the API tier
- Monitoring dashboard for queue depth, task throughput, and worker status
- Dead letter handling for failed tasks
- Integration with Docker Compose for containerized deployment

## Decision

Use Celery as the distributed task queue framework, RabbitMQ 3.x as the message broker, and Redis 6.2+ as the result backend. Celery provides the task abstraction, worker management, and scheduling capabilities. RabbitMQ provides durable message queuing with acknowledgment-based delivery guarantees. Redis provides fast result storage and also serves as the application-level cache.

This combination was chosen because it is the most battle-tested distributed task execution stack in the Python ecosystem. RabbitMQ's AMQP protocol provides stronger delivery guarantees than Redis as a broker (durable queues, message acknowledgment, dead letter exchanges), while Redis as a result backend provides the fast read access needed for polling task status. The separation of broker (RabbitMQ) and result backend (Redis) allows each component to be optimized for its specific workload.

## Consequences

### Positive

- Long-running flow executions are offloaded from the API process, keeping the FastAPI server responsive for other requests
- Celery workers can be scaled horizontally by adding more worker containers, with RabbitMQ distributing tasks across available workers
- RabbitMQ's durable queues and message acknowledgment ensure tasks are not lost if a worker crashes -- unacknowledged messages are redelivered to another worker
- Redis as the result backend provides sub-millisecond read access for task status polling from the API layer
- Flower (Celery monitoring tool) provides a web dashboard for real-time visibility into queue depth, active workers, task success/failure rates, and execution times
- Task routing allows resource-intensive tasks (e.g., large document processing) to be directed to workers with more memory or CPU
- The Celery + RabbitMQ + Redis stack is well-documented, widely deployed, and has a large community of users

### Negative

- Three additional infrastructure components (Celery workers, RabbitMQ, Redis) increase deployment complexity and resource requirements
- RabbitMQ and Redis must be monitored and maintained as separate services, each with their own failure modes and operational concerns
- Celery's configuration surface is large and has many options that can interact in non-obvious ways (prefetch multiplier, ack late, task time limits, worker concurrency)
- Task serialization requires that all task arguments and results be JSON-serializable, which can be awkward for complex objects
- The eventual-consistency model (submit task, poll for result) is more complex to program against than synchronous execution

### Neutral

- Redis serves dual duty as both the Celery result backend and the application cache, which simplifies infrastructure but means Redis outages affect both concerns
- Celery workers run the same Python codebase as the API server but in a separate process, so code changes require redeploying both
- The task queue is optional in development -- simple flows can execute synchronously within the API process

## Alternatives Considered

### Redis as Both Broker and Result Backend

**Pros**: Simplifies infrastructure by eliminating RabbitMQ; Redis supports pub/sub and list-based queuing; one fewer service to deploy, monitor, and maintain
**Cons**: Redis as a broker does not provide the delivery guarantees of AMQP: no durable queues with message acknowledgment, messages can be lost if Redis restarts or runs out of memory, no dead letter exchange for failed message handling, no native message routing
**Why not chosen**: For a system executing AI workflows where each task may represent significant compute cost (multiple LLM API calls), losing tasks due to Redis restarts or memory pressure was unacceptable. RabbitMQ's AMQP-based delivery guarantees (durable queues, acknowledgment, dead letter exchanges) provide the reliability required for production workloads.

### Dramatiq

**Pros**: Modern Python task queue with a simpler API than Celery, better default configuration, support for both RabbitMQ and Redis as brokers, built-in rate limiting and retries
**Cons**: Smaller community and ecosystem compared to Celery; fewer monitoring tools (no Flower equivalent with the same maturity); less documentation and fewer production deployment examples; some advanced Celery features (task chains, chords, canvas) have no direct equivalent
**Why not chosen**: Dramatiq's simpler API is appealing, but its smaller ecosystem means fewer monitoring tools, less community support for production issues, and fewer documented deployment patterns. Celery's maturity and the Flower monitoring dashboard were important for operational visibility.

### Arq (asyncio-based)

**Pros**: Native asyncio support (Celery uses threads/processes for concurrency); lightweight; Redis-only (simpler infrastructure); designed for modern async Python applications
**Cons**: Redis-only broker (no RabbitMQ option), losing AMQP delivery guarantees; much smaller community; no monitoring dashboard equivalent to Flower; fewer features (no task chains, groups, or chords); less battle-tested in production
**Why not chosen**: Arq's asyncio-native design is attractive, but its reliance on Redis as the sole broker sacrifices the delivery guarantees that RabbitMQ provides. Its smaller feature set and lack of a mature monitoring dashboard made it insufficient for LangBuilder's production requirements.

### Huey

**Pros**: Lightweight task queue with simple configuration; supports Redis and SQLite as storage backends; minimal dependencies; easy to get started
**Cons**: Designed for simpler use cases; limited scaling capabilities; no AMQP support; minimal monitoring tooling; small community; not designed for the scale of distributed task execution LangBuilder requires
**Why not chosen**: Huey is designed for simpler task queue use cases and lacks the horizontal scaling capabilities, monitoring tooling, and delivery guarantees needed for distributed AI workflow execution.

## Implementation Notes

- Celery is configured with RabbitMQ broker via `BROKER_URL=amqp://admin:admin@broker:5672//` and Redis result backend via `REDIS_URL=redis://redis:6379/0`
- Celery workers are deployed as separate Docker containers using the same backend image with a different entrypoint
- Flower is deployed as an additional container for task monitoring, accessible at `flower.${DOMAIN}`
- Task routing can be configured to direct resource-intensive tasks to dedicated worker pools with appropriate resource limits
- Docker health checks monitor RabbitMQ (`rabbitmq-diagnostics -q ping`) and Redis (`redis-cli ping`) availability
- Persistent volumes (`rabbitmq_data`, `rabbitmq_log`, `redis-data`) ensure state survives container restarts
- Worker scaling: production recommendation is 2-4 worker replicas, each with 2 CPU cores and 2GB memory

## Related Decisions

- [ADR-002](002-fastapi-backend-api.md) - FastAPI submits tasks to Celery for background execution
- [ADR-004](004-custom-dag-graph-engine.md) - Long-running graph executions are offloaded to Celery workers
- [ADR-006](006-sqlite-postgresql-dual-database.md) - Celery workers connect to PostgreSQL in production for database operations
- [ADR-012](012-traefik-reverse-proxy.md) - Traefik routes Flower dashboard traffic

## References

- https://docs.celeryq.dev/
- https://www.rabbitmq.com/documentation.html
- https://redis.io/docs/
- https://flower.readthedocs.io/
