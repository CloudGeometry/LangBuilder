# ADR-004: Custom DAG Graph Engine

## Status

Accepted

## Date

2026-02-09

## Decision Makers

- LangBuilder Development Team

## Context

### Problem Statement

LangBuilder's core value proposition is visual workflow building where users compose AI pipelines by connecting components on a canvas. These workflows are directed acyclic graphs (DAGs) where each node (vertex) represents a component (LLM call, data transformation, tool invocation) and edges represent data flow between components. The system needs an execution engine that can parse workflow graph definitions, validate their structure, determine correct execution order, execute independent branches concurrently, stream intermediate results in real time, and handle errors gracefully without crashing the entire workflow.

### Constraints

- Workflows must be represented as DAGs -- cyclic graphs are invalid and must be rejected before execution
- Execution must respect data dependencies: a component can only execute after all its upstream dependencies have completed
- Independent branches (components with no mutual data dependencies) should execute concurrently to minimize total execution time
- LLM output tokens must be streamed to the frontend in real time via WebSocket as they are generated
- Each flow execution must maintain isolated state to prevent cross-execution contamination
- The engine must integrate tightly with the component registry for dynamic component instantiation

### Requirements

- Cycle detection to validate DAG property before execution
- Topological sorting to determine correct execution order
- Parallel async execution of independent vertices
- Real-time streaming of intermediate results
- Error propagation with clear context when upstream vertices fail
- State isolation per execution
- Integration with the component registry for vertex instantiation
- Support for the full range of component types (96 packages across 12 categories)

## Decision

Build a custom DAG graph execution engine tailored to LangBuilder's component model. The engine implements a five-stage execution pipeline: (1) parse the graph definition from JSON, (2) run cycle detection to validate the DAG property, (3) perform topological sorting to determine execution order, (4) execute vertices concurrently using Python asyncio where dependencies allow, and (5) aggregate results and return the final output.

A custom engine was chosen over general-purpose workflow orchestration tools because LangBuilder requires tight integration with its component registry, real-time token streaming, and a graph model that maps directly to the visual canvas representation. The engine is the bridge between the visual "what you see" and the runtime "what executes."

## Consequences

### Positive

- Tight integration with the component registry allows the engine to instantiate and configure components dynamically based on the visual graph definition
- Parallel async execution of independent branches significantly reduces total execution time for workflows with multiple independent LLM calls or data processing steps
- Cycle detection provides immediate feedback when users create invalid workflow topologies, preventing runtime errors
- Real-time streaming is a first-class concern, not bolted on after the fact, enabling smooth LLM token streaming via WebSocket
- State isolation per execution prevents data leakage between concurrent workflow runs
- The engine can evolve alongside LangBuilder's specific needs without being constrained by a third-party orchestrator's execution model

### Negative

- Building a custom graph engine requires significant engineering investment in correctness, performance, and edge-case handling
- The engine must be maintained in-house; bug fixes, optimizations, and new features are the team's responsibility
- Lacks the battle-tested reliability of mature workflow orchestration systems that have been hardened over years of production use
- No built-in support for advanced workflow features like retries with exponential backoff, conditional branching, or sub-graph execution -- these must be implemented as needed

### Neutral

- The graph engine is a core differentiator of LangBuilder and represents proprietary logic that is unlikely to be replaceable by a generic solution
- The engine's internal design is influenced by LangFlow's original graph execution model, providing a proven starting point
- The execution model is synchronous at the graph level (execute all vertices) but asynchronous at the vertex level (each vertex runs async)

## Alternatives Considered

### Apache Airflow

**Pros**: Mature, battle-tested DAG execution engine with scheduling, retry logic, monitoring, and a large community; supports parallel task execution; extensive operator ecosystem
**Cons**: Designed for batch data pipeline scheduling, not interactive real-time workflow execution; no native LLM token streaming support; heavy infrastructure requirements (scheduler, metadata database, web server); DAG definitions are Python code, not JSON-serializable visual graphs; task granularity is too coarse for per-component execution
**Why not chosen**: Airflow is optimized for scheduled batch pipelines, not interactive, user-triggered AI workflow execution with real-time streaming. Its architecture (separate scheduler, metadata database, web server) is overengineered for LangBuilder's use case, and its DAG model does not map to a visual canvas.

### Prefect

**Pros**: Modern Python-native workflow orchestration, async support, good developer experience, reactive execution model, lightweight compared to Airflow
**Cons**: Still oriented toward data engineering pipelines rather than interactive AI workflows; introduces a significant dependency with its own execution runtime; no native integration with LangChain's component model or real-time streaming; requires a Prefect server or cloud service for full functionality
**Why not chosen**: Prefect improves on Airflow's developer experience but is still designed for data pipeline orchestration. Its execution model does not support the tight component-registry integration and real-time token streaming that LangBuilder requires.

### Temporal

**Pros**: Durable execution with automatic retries, strong consistency guarantees, support for long-running workflows, language-agnostic
**Cons**: Requires a separate Temporal server cluster, adding significant infrastructure complexity; designed for durable microservice orchestration, not in-process graph execution; overkill for LangBuilder's single-process modular monolith; steep learning curve for the activity/workflow model
**Why not chosen**: Temporal's durable execution model is designed for distributed microservice orchestration across failures. LangBuilder's graph engine runs in-process within a modular monolith, and Temporal's infrastructure requirements and programming model would add complexity without proportional benefit.

### NetworkX (Graph Library Only)

**Pros**: Well-established Python graph library with topological sort, cycle detection, and many graph algorithms built in; lightweight, no execution runtime
**Cons**: Provides graph data structures and algorithms only, not an execution engine; would still require building the entire execution pipeline (component instantiation, async execution, streaming, state management) on top; no workflow-specific features
**Why not chosen**: NetworkX could provide the graph algorithm primitives (and may be used internally for topological sort and cycle detection), but it does not solve the execution problem. The custom engine is needed regardless, and implementing the graph algorithms directly (or using NetworkX as an internal utility) provides more control.

## Implementation Notes

- The graph definition is stored as JSON in the `Flow` model's `data` field, containing nodes (with component type and configuration) and edges (with source/target vertex IDs and port mappings)
- Cycle detection uses a depth-first search algorithm that runs in O(V + E) time
- Topological sorting produces a layered ordering where each layer contains vertices with no unresolved dependencies; layers are executed sequentially, but vertices within a layer run concurrently via `asyncio.gather()`
- Vertex execution wraps the component's `build()` method, passing resolved inputs from upstream edges and capturing outputs for downstream consumers
- Streaming is implemented by having LLM component vertices yield tokens through an async generator that is connected to a WebSocket channel
- Execution state (vertex status, intermediate results, errors) is tracked in the `state` service and persisted to `VertexBuildTable` for debugging and audit

## Related Decisions

- [ADR-003](003-langchain-ai-framework.md) - LangChain components are the units of execution within graph vertices
- [ADR-013](013-pluggable-component-architecture.md) - The component registry provides the components that the engine instantiates and executes
- [ADR-011](011-celery-rabbitmq-redis-task-queue.md) - Long-running flow executions can be offloaded from the graph engine to Celery workers

## References

- https://en.wikipedia.org/wiki/Directed_acyclic_graph
- https://en.wikipedia.org/wiki/Topological_sorting
- https://docs.python.org/3/library/asyncio.html
