# ADR-003: LangChain 0.3.x for AI Framework

## Status

Accepted

## Date

2026-02-09

## Decision Makers

- LangBuilder Development Team

## Context

### Problem Statement

LangBuilder is an AI workflow builder that needs to support a wide range of LLM providers (OpenAI, Anthropic, Google, Ollama, and dozens more), retrieval strategies, memory backends, tool integrations, and agent patterns. Building and maintaining direct integrations with each provider's API would require significant engineering effort and ongoing maintenance as provider APIs evolve. The project needs an abstraction layer that provides a consistent interface for interacting with heterogeneous AI services while enabling advanced patterns like chains, agents, and retrieval-augmented generation (RAG).

### Constraints

- Must support at least 28 LLM provider integrations (the current count of component packages)
- Must provide a consistent abstraction for chat models, embeddings, vector stores, document loaders, and retrievers
- Must support async execution for integration with FastAPI's async handlers
- Must be actively maintained with timely updates for new LLM provider features
- LangBuilder was originally forked from LangFlow, which is built on LangChain, establishing a strong existing dependency

### Requirements

- Provider-agnostic model abstraction (BaseChatModel, BaseLanguageModel)
- Pre-built integrations for major LLM providers, vector stores, and tools
- Support for chains, agents, and complex multi-step workflows
- Async API for non-blocking execution
- Pydantic-based configuration for compatibility with the component schema system
- Observability integration (tracing, LangSmith compatibility)
- Active ecosystem with community-contributed integrations

## Decision

Use LangChain 0.3.x as the core AI framework. LangBuilder's 96 component packages wrap LangChain primitives (BaseChatModel, BaseRetriever, VectorStore, BaseEmbeddings, etc.), providing a consistent interface for the graph execution engine. LangChain's provider-specific packages (e.g., `langchain-openai`, `langchain-anthropic`) are used for individual provider integrations, while `langchain-core` provides the base abstractions.

LangChain was chosen because it provides the most comprehensive ecosystem of LLM integrations, pre-built patterns (chains, agents, RAG), and tooling (LangSmith for tracing) in the Python AI landscape. Its provider abstraction allows LangBuilder to offer 28+ LLM provider integrations without maintaining direct API clients for each.

## Consequences

### Positive

- Provider-agnostic abstractions mean workflows built with one LLM provider can be switched to another by changing a single component, without modifying the workflow graph
- Pre-built integrations for 28+ LLM providers, 12+ vector databases, and dozens of tools dramatically reduce integration development effort
- LangChain's chain and agent patterns provide proven implementations of common AI workflow patterns (ReAct, tool-calling, RAG) out of the box
- LangSmith integration provides execution tracing, debugging, and observability for AI workflows
- MCP (Model Context Protocol) support enables dynamic tool discovery
- Active maintenance with regular releases means new LLM provider features are quickly available
- Pydantic v2 configuration in LangChain 0.3.x aligns with LangBuilder's component schema system

### Negative

- LangChain introduces a significant dependency tree; each provider package brings its own transitive dependencies
- LangChain's API surface has undergone breaking changes between major versions (0.1 -> 0.2 -> 0.3), requiring migration effort
- The abstraction layer adds overhead compared to calling provider APIs directly, though this is marginal for I/O-bound LLM calls
- Some advanced provider-specific features may not be exposed through LangChain's abstraction layer, requiring workarounds or direct API access
- LangChain's rapid development pace means documentation can lag behind the latest API changes

### Neutral

- LangBuilder components are thin wrappers around LangChain primitives, meaning LangChain's design decisions and limitations propagate to LangBuilder's user-facing behavior
- The 0.3.x version series introduced a modular package structure (`langchain-core`, `langchain-openai`, etc.) which aligns with LangBuilder's component-per-provider design
- LangChain's LCEL (LangChain Expression Language) is available but LangBuilder primarily uses the component-and-graph paradigm rather than LCEL chains

## Alternatives Considered

### LlamaIndex

**Pros**: Strong focus on data indexing and RAG, good document processing pipelines, simpler API for retrieval-focused use cases, growing ecosystem
**Cons**: Primarily optimized for retrieval and indexing rather than general-purpose LLM orchestration; smaller ecosystem of provider integrations; less mature agent and chain patterns; would require building general-purpose orchestration capabilities on top
**Why not chosen**: LlamaIndex excels at RAG and data indexing but lacks the breadth of LangChain's general-purpose orchestration, agent patterns, and tool integrations. LangBuilder needs to support diverse workflow types beyond retrieval, making LangChain's broader scope essential.

### Direct Provider SDKs (OpenAI SDK, Anthropic SDK, etc.)

**Pros**: Maximum control over API interactions, no abstraction overhead, access to all provider-specific features, simpler dependency tree per provider
**Cons**: Each provider has a different API, requiring 28+ separate integration implementations; no shared abstraction means workflows cannot be provider-agnostic; massive engineering effort to maintain direct integrations; no pre-built chain, agent, or RAG patterns
**Why not chosen**: The engineering cost of building and maintaining direct integrations with 28+ providers, plus implementing chain, agent, and retrieval patterns from scratch, would be prohibitive. LangChain provides this infrastructure as a mature, community-maintained library.

### Semantic Kernel (Microsoft)

**Pros**: Strong enterprise backing from Microsoft, good Azure integration, plugin architecture, multi-language support (Python, C#, Java)
**Cons**: Smaller Python ecosystem compared to LangChain, fewer provider integrations, less community-contributed tooling, Microsoft-centric design philosophy, less mature in the Python ecosystem
**Why not chosen**: Semantic Kernel's Python ecosystem is significantly smaller than LangChain's. The number of available provider integrations, community plugins, and learning resources was insufficient for LangBuilder's requirement to support a wide range of AI services.

## Implementation Notes

- Component packages import from `langchain-core` for base classes and from provider-specific packages (e.g., `langchain-openai`) for concrete implementations
- LangChain 0.3.x's Pydantic v2 compatibility allows component parameters to be defined using the same Pydantic models that generate UI schemas
- Async execution uses LangChain's `ainvoke()`, `astream()`, and `abatch()` methods within the graph engine's async execution coordinator
- LangSmith tracing is optional and configured via environment variables (`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`)
- LangFuse and LangWatch are also supported as alternative observability backends

## Related Decisions

- [ADR-002](002-fastapi-backend-api.md) - FastAPI's async handlers are used to invoke LangChain operations without blocking
- [ADR-004](004-custom-dag-graph-engine.md) - The graph engine orchestrates LangChain component execution
- [ADR-013](013-pluggable-component-architecture.md) - Components wrap LangChain primitives with standardized schemas

## References

- https://python.langchain.com/docs/
- https://api.python.langchain.com/
- https://docs.smith.langchain.com/ - LangSmith documentation
- https://modelcontextprotocol.io/ - Model Context Protocol
