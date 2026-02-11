# ADR-013: Pluggable Component Architecture

## Status

Accepted

## Date

2026-02-09

## Decision Makers

- LangBuilder Development Team

## Context

### Problem Statement

LangBuilder is an AI workflow builder that must support a wide and growing variety of AI capabilities: LLM providers, embedding models, vector stores, document loaders, text splitters, retrieval strategies, tools, agents, chains, memory backends, output parsers, and custom components. Each capability has its own dependencies (e.g., the Pinecone component requires the Pinecone client library) and its own configuration parameters. The system needs an architecture that allows new capabilities to be added without modifying the core application, keeps component dependencies isolated, enables automatic UI generation from component definitions, and supports runtime discovery and loading.

### Constraints

- Must support 96+ component packages across 12 categories without the core application having direct dependencies on each
- Each component package may have unique third-party dependencies (provider SDKs, client libraries) that should not be installed unless the component is used
- Component definitions must generate frontend UI automatically (input fields, output types, connection ports) without manual frontend coding per component
- New components must be addable by creating a Python package -- no modifications to the core system should be required
- Components must declare their inputs, outputs, and configuration via a standard schema for both runtime execution and UI generation

### Requirements

- Component discovery: automatic scanning and registration of component packages at startup
- Component schema: standardized input/output/configuration declaration via Pydantic models
- Component isolation: each component package is independently installable with its own dependencies
- Automatic UI generation: frontend node rendering derived from the component's Pydantic schema
- Component categories: organized classification for the sidebar component browser
- Component lifecycle: discovery -> schema generation -> instantiation -> execution -> optional caching
- Extensibility: creating a new component requires only implementing a Python class following the component base class pattern

## Decision

Implement a pluggable component architecture where each AI capability is encapsulated as an independent Python package that extends a base `Component` class from `langbuilder-base`. Components declare their display name, description, icon, input parameters (as Pydantic fields), and output methods. The component registry discovers and loads all available component packages at startup, generating schemas that the frontend uses to render custom nodes in the visual canvas.

This plugin-first architecture was chosen because it makes extensibility a first-class concern rather than an afterthought. Any new AI capability -- a new LLM provider, a new vector store, a custom data transformation -- can be added by creating a Python package that follows the component pattern, without touching the core application code. This is critical for a platform that must keep pace with the rapidly evolving AI tool ecosystem.

## Consequences

### Positive

- New capabilities can be added by creating a new component package; no changes to the core application, API, or frontend are required
- Component dependencies are isolated: installing the Pinecone component installs `langchain-pinecone`, but this dependency is not present if the Pinecone component is not installed
- Automatic UI generation from Pydantic schemas means adding a new component automatically creates the appropriate input fields, dropdowns, and connection ports in the frontend canvas
- 96 components across 12 categories provide a rich library of AI building blocks out of the box
- Components are independently versioned and can be updated without affecting other components
- The component pattern enforces a consistent structure (inputs, outputs, configuration) that makes components predictable and composable
- The `shared_component_cache` service enables caching of expensive-to-instantiate components (e.g., large model instances) across flow executions

### Negative

- The discovery and registry mechanism adds startup latency as all component packages are scanned and their schemas are generated
- The component base class pattern requires all capabilities to fit the same abstraction (inputs, outputs, build method), which may not naturally model every possible AI operation
- Managing 96+ component packages creates a significant maintenance surface: dependency updates, breaking changes in upstream libraries, and version compatibility
- The schema generation mechanism must handle edge cases in Pydantic model definitions that may not render well as UI components
- Debugging failures within components is more complex because execution occurs through the graph engine's vertex abstraction

### Neutral

- The 12 component categories (Models, Prompts, Chains, Agents, Tools, Memory, Embeddings, Vector Stores, Document Loaders, Text Splitters, Retrievers, Output Parsers) provide a classification system that mirrors the LangChain ecosystem structure
- Component packages are thin wrappers around LangChain primitives, meaning most component logic delegates to LangChain with configuration applied
- The component architecture is inherited from LangFlow (the upstream project LangBuilder forked from), providing a proven design foundation

## Alternatives Considered

### Monolithic Component Library

**Pros**: All components in a single package; simpler packaging and distribution; no discovery mechanism needed; shared utilities are directly accessible; simpler testing and CI
**Cons**: Installing the platform installs all component dependencies (every LLM provider SDK, every vector store client, every tool library), resulting in a massive dependency tree and long install times; adding a new component requires modifying the monolithic package; version conflicts between component dependencies are more likely; users pay the installation cost for components they never use
**Why not chosen**: A monolithic component library would install hundreds of third-party packages that most users do not need. The dependency tree would be massive, install times would be long, and version conflicts between provider SDKs would be frequent and difficult to resolve.

### Microservice-Per-Component

**Pros**: Maximum isolation (each component runs in its own process/container); independent scaling; no dependency conflicts; failure isolation (a crashing component does not affect others)
**Cons**: Extreme infrastructure complexity (96+ services); massive overhead for inter-component communication (network calls instead of function calls); impossible to achieve the sub-second graph execution times users expect; deployment complexity proportional to the number of components; debugging distributed execution across 96 services
**Why not chosen**: Running each of 96 components as a separate microservice would create untenable infrastructure complexity and add network overhead to every component invocation within a workflow. The latency penalty of network calls between components would make interactive workflow execution unacceptably slow.

### Dynamic Code Loading (eval/exec)

**Pros**: Maximum flexibility -- users can define components as arbitrary Python code at runtime; no package installation required; instant component creation
**Cons**: Critical security vulnerability (arbitrary code execution); no type safety; no dependency management; no schema validation; debugging arbitrary code is difficult; performance unpredictable; code quality uncontrollable
**Why not chosen**: Executing arbitrary user-provided code represents an unacceptable security risk for a platform that handles API keys, credentials, and sensitive data. The plugin architecture provides extensibility through controlled extension points rather than arbitrary code execution.

### WebAssembly (Wasm) Plugin System

**Pros**: Strong sandboxing and isolation; language-agnostic (components could be written in any Wasm-supported language); memory safety guarantees; portable execution
**Cons**: Python-to-Wasm compilation is immature; LangChain and its ecosystem are pure Python with no Wasm support; significant performance overhead for Python-in-Wasm; developer experience for writing Wasm components is poor compared to native Python; the entire LangChain ecosystem would be inaccessible from Wasm
**Why not chosen**: LangBuilder's component system is built on LangChain, which is a Python-native ecosystem. Wasm sandboxing would make LangChain's libraries inaccessible and require reimplementing all provider integrations. The technology is not mature enough for Python-centric AI applications.

## Implementation Notes

- Components inherit from the `Component` base class in `langbuilder-base`, defining `display_name`, `description`, `icon`, input fields (Pydantic `Field`), and output methods
- The component registry scans installed packages at startup, loading all classes that extend `Component`
- Each component's Pydantic schema is serialized to JSON and sent to the frontend, where it generates the node UI (input fields, dropdowns, connection handles)
- Component execution occurs within the graph engine: the vertex instantiates the component, passes resolved inputs, calls the output method, and captures results
- The `shared_component_cache` service caches component instances (keyed by component type + configuration hash) to avoid redundant instantiation of expensive objects like LLM clients
- Custom components can be created by users and stored in the `Component` database model, loaded at runtime alongside package-based components
- Component categories are defined by the directory structure and metadata in the component package

## Related Decisions

- [ADR-003](003-langchain-ai-framework.md) - Components wrap LangChain primitives for provider-agnostic AI capabilities
- [ADR-004](004-custom-dag-graph-engine.md) - The graph engine orchestrates component execution within workflow vertices
- [ADR-001](001-uv-workspace-monorepo.md) - UV workspace manages the `langbuilder-base` package that provides the component base class
- [ADR-005](005-sqlmodel-orm.md) - Custom component definitions are stored in the Component database model

## References

- https://python.langchain.com/docs/how_to/#components
- https://docs.pydantic.dev/latest/concepts/fields/
- https://docs.python.org/3/library/importlib.html - Python import system for dynamic loading
