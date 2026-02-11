# Feature Catalog - LangBuilder v1.6.5

## Overview

This document provides a comprehensive inventory of LangBuilder features organized by functional category. Each feature entry includes a technical description, user-facing capability, associated API endpoints, and current maturity status.

**Version**: 1.6.5
**Total API Endpoints**: 157 across 22 routers
**Total Components**: 96 packages across 12 categories
**Total Integrations**: 62 (28 LLM providers, 13 vector DBs, 6 observability, 4 auth, 3 infra, 2 cloud, 2 internal, 4 third-party)

**Status Legend**:
- **Stable** - Feature is fully implemented, tested, and production-ready
- **Beta** - Feature is implemented but may have limitations or undergo changes
- **Verify** - Feature exists in codebase but requires validation of completeness

---

## 1. Visual Workflow Builder

React Flow-based canvas providing drag-and-drop visual construction of AI workflows.

### 1.1 Node-Based Canvas

| Attribute | Detail |
|-----------|--------|
| **Description** | `React Flow canvas rendering a directed graph of AI components as interactive nodes with typed input/output handles` |
| **Capability** | `Users can visually construct AI workflows by placing and arranging component nodes on an infinite canvas with zoom, pan, and minimap navigation` |
| **API Endpoints** | `GET /api/v1/flows/{flow_id} (load canvas state), PATCH /api/v1/flows/{flow_id} (save canvas state)` |
| **Status** | Stable |

### 1.2 Drag-and-Drop Component Placement

| Attribute | Detail |
|-----------|--------|
| **Description** | `Sidebar component library with 12 searchable categories enabling drag-to-canvas instantiation of 96 component types` |
| **Capability** | `Users can browse, search, and drag components from a categorized sidebar onto the canvas to add LLMs, vector stores, tools, and other nodes to their workflow` |
| **API Endpoints** | `GET /api/v1/endpoints/custom_component (list available components)` |
| **Status** | Stable |

### 1.3 Edge Connections and Data Flow

| Attribute | Detail |
|-----------|--------|
| **Description** | `Typed edge connections between node output and input handles enforcing compatible data type wiring in the directed acyclic graph` |
| **Capability** | `Users can connect component outputs to inputs via visual edges, with type validation ensuring only compatible connections are allowed` |
| **API Endpoints** | `POST /api/v1/validate/code (validate flow graph integrity)` |
| **Status** | Stable |

### 1.4 Node Configuration Editor

| Attribute | Detail |
|-----------|--------|
| **Description** | `Per-node configuration panel with typed form fields, credential selectors, and advanced parameter controls rendered from component schema definitions` |
| **Capability** | `Users can click any node to open a detail panel for configuring model parameters, API credentials, prompt templates, and component-specific settings` |
| **API Endpoints** | `POST /api/v1/validate/prompt (validate prompt configuration)` |
| **Status** | Stable |

### 1.5 Canvas Interaction Controls

| Attribute | Detail |
|-----------|--------|
| **Description** | `Standard canvas manipulation including zoom, pan, minimap overview, auto-layout, copy/paste, undo/redo, and keyboard shortcuts` |
| **Capability** | `Users can efficiently navigate large workflows using zoom/pan, get an overview via minimap, auto-arrange nodes, and use keyboard shortcuts for rapid editing` |
| **API Endpoints** | `N/A (client-side only)` |
| **Status** | Stable |

---

## 2. Flow Execution Engine

DAG-based execution engine that processes workflow graphs with parallel vertex execution and real-time SSE streaming.

### 2.1 DAG Build Execution

| Attribute | Detail |
|-----------|--------|
| **Description** | `Directed acyclic graph executor that resolves node dependencies, schedules parallel vertex builds, and propagates data through the flow graph` |
| **Capability** | `Users can execute their complete workflow with a single action, with the engine automatically determining execution order and running independent branches in parallel` |
| **API Endpoints** | `POST /api/v1/build/{flow_id}/flow (trigger full flow build)` |
| **Status** | Stable |

### 2.2 Individual Vertex Build

| Attribute | Detail |
|-----------|--------|
| **Description** | `Granular single-vertex execution enabling isolated testing of individual components within a flow without running the entire graph` |
| **Capability** | `Users can build and test individual nodes in isolation to debug specific components before executing the full workflow` |
| **API Endpoints** | `POST /api/v1/build/{flow_id}/vertices (build specific vertices)` |
| **Status** | Stable |

### 2.3 Server-Sent Events Streaming

| Attribute | Detail |
|-----------|--------|
| **Description** | `SSE event stream delivering real-time build progress, vertex completion status, intermediate outputs, and LLM token streaming to the client` |
| **Capability** | `Users see live progress updates, streaming LLM responses, and per-node build status in real time as their workflow executes` |
| **API Endpoints** | `GET /api/v1/build/{flow_id}/events (SSE event stream)` |
| **Status** | Stable |

### 2.4 Build Cancellation

| Attribute | Detail |
|-----------|--------|
| **Description** | `Graceful cancellation mechanism that terminates in-progress vertex builds and cleans up partial execution state` |
| **Capability** | `Users can cancel a running flow execution at any point, stopping all in-progress operations and freeing resources` |
| **API Endpoints** | `POST /api/v1/build/{flow_id}/cancel (cancel active build)` |
| **Status** | Stable |

### 2.5 Public Flow Execution

| Attribute | Detail |
|-----------|--------|
| **Description** | `Unauthenticated flow execution endpoint for flows marked with PUBLIC access type, enabling external consumption without API keys` |
| **Capability** | `Users can share public-facing flows that external consumers can execute without authentication` |
| **API Endpoints** | `POST /api/v1/build/public/{flow_id}/flow (execute public flow)` |
| **Status** | Stable |

---

## 3. AI Model Integration

Support for 24+ LLM providers with unified model management and an OpenAI-compatible API gateway.

### 3.1 Multi-Provider LLM Access

| Attribute | Detail |
|-----------|--------|
| **Description** | `Unified abstraction over 28 LLM providers (OpenAI, Anthropic, Google AI, Azure OpenAI, AWS Bedrock, Groq, Mistral, Cohere, NVIDIA NIM, Ollama, Perplexity, DeepSeek, HuggingFace, IBM watsonx, xAI, OpenRouter, LM Studio, Vertex AI, SambaNova, Cloudflare, Maritalk, Novita, NotDiamond, LiteLLM, and more) through pluggable component packages` |
| **Capability** | `Users can select from 28 LLM providers via drop-down, configure model-specific parameters (temperature, max tokens, top-p), and swap providers without rewiring their workflow` |
| **API Endpoints** | `GET /api/v1/endpoints/custom_component (list model components), POST /api/v1/build/{flow_id}/flow (execute model calls)` |
| **Status** | Stable |

### 3.2 OpenAI-Compatible API Gateway

| Attribute | Detail |
|-----------|--------|
| **Description** | `Drop-in OpenAI API compatibility layer exposing LangBuilder flows as /v1/models and /v1/chat/completions endpoints with streaming support` |
| **Capability** | `Users can point any OpenAI SDK client at LangBuilder to use their flows as if they were OpenAI models, enabling integration with existing toolchains` |
| **API Endpoints** | `GET /api/v1/openai/models (list available flow-models), POST /api/v1/openai/chat/completions (chat completions with streaming)` |
| **Status** | Stable |

### 3.3 Model Parameter Management

| Attribute | Detail |
|-----------|--------|
| **Description** | `Per-node model configuration supporting temperature, max tokens, top-p, frequency/presence penalties, stop sequences, system prompts, and JSON mode` |
| **Capability** | `Users can fine-tune LLM behavior per node, including response formatting, creativity controls, and structured output modes` |
| **API Endpoints** | `N/A (embedded in flow configuration persisted via Flows CRUD)` |
| **Status** | Stable |

### 3.4 Embedding Model Support

| Attribute | Detail |
|-----------|--------|
| **Description** | `Embedding components for multiple providers (OpenAI, Cohere, HuggingFace, local models) used in RAG pipelines and semantic search` |
| **Capability** | `Users can configure embedding models from various providers to power vector search, document retrieval, and similarity matching in their workflows` |
| **API Endpoints** | `POST /api/v1/build/{flow_id}/flow (execute embedding calls within flow)` |
| **Status** | Stable |

---

## 4. Vector Database Support

Integration with 13+ vector store backends for embeddings storage, similarity search, and RAG applications.

### 4.1 Multi-Backend Vector Storage

| Attribute | Detail |
|-----------|--------|
| **Description** | `Pluggable vector store components supporting 13+ backends: ChromaDB, Pinecone, Qdrant, Weaviate, Milvus, FAISS, PGVector, Redis, Elasticsearch, OpenSearch, MongoDB Atlas, Supabase, Upstash, AstraDB, Cassandra, ClickHouse, Couchbase, Vectara, and HCD` |
| **Capability** | `Users can select their preferred vector database, configure connection parameters, and switch backends without modifying the rest of their RAG workflow` |
| **API Endpoints** | `POST /api/v1/build/{flow_id}/flow (execute vector operations within flow)` |
| **Status** | Stable |

### 4.2 Document Ingestion and Chunking

| Attribute | Detail |
|-----------|--------|
| **Description** | `Document loading and text splitting components with configurable chunk size, overlap, and splitting strategy (recursive, character, token-based)` |
| **Capability** | `Users can ingest documents from various sources, split them into optimally-sized chunks, and store embeddings in their chosen vector database` |
| **API Endpoints** | `POST /api/v1/build/{flow_id}/flow (execute ingestion pipeline)` |
| **Status** | Stable |

### 4.3 Similarity and Hybrid Search

| Attribute | Detail |
|-----------|--------|
| **Description** | `Query-time retrieval supporting pure vector similarity search, keyword search, and hybrid search combining both approaches with metadata filtering` |
| **Capability** | `Users can configure retrieval nodes to find the most relevant documents using semantic similarity, keyword matching, or a weighted combination with metadata filters` |
| **API Endpoints** | `POST /api/v1/build/{flow_id}/flow (execute search within flow)` |
| **Status** | Stable |

---

## 5. Component System

Pluggable architecture with 96 component packages across 12 categories supporting custom component development.

### 5.1 Component Registry

| Attribute | Detail |
|-----------|--------|
| **Description** | `Dynamic component discovery system that scans 96 packages across 12 categories (LLMs, vector stores, embeddings, tools, agents, memories, chains, prompts, data loaders, output parsers, text splitters, utilities) at startup` |
| **Capability** | `Users can browse the full component library organized by category, with each component providing typed inputs/outputs, configuration schema, and documentation` |
| **API Endpoints** | `GET /api/v1/endpoints/custom_component (list all registered components)` |
| **Status** | Stable |

### 5.2 Custom Component Development

| Attribute | Detail |
|-----------|--------|
| **Description** | `Python-based custom component API allowing users to define new node types with typed inputs/outputs, configuration fields, and execution logic` |
| **Capability** | `Users can create and upload custom components written in Python that appear alongside built-in components in the sidebar, extending the platform with proprietary logic` |
| **API Endpoints** | `POST /api/v1/endpoints/custom_component (upload custom component), GET /api/v1/endpoints/custom_component/config (get component config)` |
| **Status** | Stable |

### 5.3 Component Store

| Attribute | Detail |
|-----------|--------|
| **Description** | `Community component marketplace enabling sharing, discovery, tagging, and downloading of reusable components with like/download tracking` |
| **Capability** | `Users can share their custom components with the community, discover components built by others, and install them with one click` |
| **API Endpoints** | `GET /api/v1/store/ (list shared components), POST /api/v1/store/components/ (share component), GET /api/v1/store/tags/ (browse tags), POST /api/v1/store/likes/ (like component), GET /api/v1/store/downloads/ (download counts)` |
| **Status** | Stable |

### 5.4 Code Validation

| Attribute | Detail |
|-----------|--------|
| **Description** | `Server-side validation of custom component code and prompt templates before execution, catching syntax errors and type mismatches` |
| **Capability** | `Users receive immediate feedback on code and prompt errors before running their flows, reducing debug cycles` |
| **API Endpoints** | `POST /api/v1/validate/code (validate component code), POST /api/v1/validate/prompt (validate prompt template)` |
| **Status** | Stable |

---

## 6. Project and Flow Management

Full lifecycle management for flows and projects including CRUD, batch operations, import/export, and starter templates.

### 6.1 Flow CRUD Operations

| Attribute | Detail |
|-----------|--------|
| **Description** | `Complete flow lifecycle management with create, read, update, delete, duplicate, and list operations persisted to the database` |
| **Capability** | `Users can create new flows, save progress, rename and describe flows, duplicate existing flows as starting points, and delete flows they no longer need` |
| **API Endpoints** | `POST /api/v1/flows/ (create), GET /api/v1/flows/ (list), GET /api/v1/flows/{flow_id} (read), PATCH /api/v1/flows/{flow_id} (update), DELETE /api/v1/flows/{flow_id} (delete)` |
| **Status** | Stable |

### 6.2 Batch Flow Operations

| Attribute | Detail |
|-----------|--------|
| **Description** | `Bulk operations for multiple flows including batch delete, batch export, and batch update for efficient flow management at scale` |
| **Capability** | `Users can select multiple flows and perform bulk actions like delete or export, avoiding repetitive individual operations` |
| **API Endpoints** | `POST /api/v1/flows/batch/ (batch operations)` |
| **Status** | Stable |

### 6.3 Flow Import and Export

| Attribute | Detail |
|-----------|--------|
| **Description** | `JSON-based flow serialization enabling export of complete flow definitions including node configuration, edges, and metadata for backup or sharing` |
| **Capability** | `Users can export flows as JSON files and import them into the same or different LangBuilder instances for backup, sharing, or migration` |
| **API Endpoints** | `POST /api/v1/flows/upload/ (import flow), GET /api/v1/flows/{flow_id}/download/ (export flow)` |
| **Status** | Stable |

### 6.4 Project Organization

| Attribute | Detail |
|-----------|--------|
| **Description** | `Project containers that group related flows with shared settings, supporting CRUD, download, and upload at the project level (replaces legacy folder system)` |
| **Capability** | `Users can organize flows into projects, download entire projects as archives, and upload project bundles for team sharing or migration` |
| **API Endpoints** | `POST /api/v1/projects/ (create), GET /api/v1/projects/ (list), GET /api/v1/projects/{project_id} (read), PATCH /api/v1/projects/{project_id} (update), DELETE /api/v1/projects/{project_id} (delete), GET /api/v1/projects/{project_id}/download (export), POST /api/v1/projects/upload/ (import)` |
| **Status** | Stable |

### 6.5 Legacy Folder Support

| Attribute | Detail |
|-----------|--------|
| **Description** | `Backward-compatible folder endpoints that redirect to the projects system, maintaining API compatibility during migration` |
| **Capability** | `Users with existing integrations using the folders API continue to work seamlessly as requests are redirected to the projects system` |
| **API Endpoints** | `GET /api/v1/folders/ (redirects to projects), POST /api/v1/folders/ (redirects), PATCH /api/v1/folders/{id} (redirects), DELETE /api/v1/folders/{id} (redirects)` |
| **Status** | Stable |

### 6.6 Starter Project Templates

| Attribute | Detail |
|-----------|--------|
| **Description** | `Pre-built example flow templates covering common use cases (chatbots, RAG, agents) that users can instantiate as starting points` |
| **Capability** | `Users can browse a library of starter templates and create new flows from them, accelerating initial setup for common AI workflow patterns` |
| **API Endpoints** | `GET /api/v1/starter-projects/ (list available templates)` |
| **Status** | Stable |

### 6.7 Flow Example Library

| Attribute | Detail |
|-----------|--------|
| **Description** | `Curated collection of example flows demonstrating platform capabilities and integration patterns` |
| **Capability** | `Users can explore example flows to learn best practices and discover advanced features` |
| **API Endpoints** | `GET /api/v1/flows/examples/ (list example flows)` |
| **Status** | Stable |

---

## 7. Authentication and Authorization

Multi-method authentication supporting JWT tokens, OAuth2, API keys, LDAP, and superuser administration.

### 7.1 JWT Authentication

| Attribute | Detail |
|-----------|--------|
| **Description** | `Bearer token authentication using JSON Web Tokens with configurable expiration, refresh token rotation, and session management` |
| **Capability** | `Users can log in with username/password to receive a JWT token for authenticated API access, with automatic token refresh for seamless sessions` |
| **API Endpoints** | `POST /api/v1/login/ (authenticate), POST /api/v1/login/refresh (refresh token), POST /api/v1/login/logout (invalidate session)` |
| **Status** | Stable |

### 7.2 Auto-Login Mode

| Attribute | Detail |
|-----------|--------|
| **Description** | `Single-user deployment mode that bypasses authentication, creating an automatic session for development and personal-use scenarios` |
| **Capability** | `Users deploying LangBuilder for personal use can skip login setup and access the platform immediately without credentials` |
| **API Endpoints** | `GET /api/v1/login/auto_login (auto-authenticate)` |
| **Status** | Stable |

### 7.3 API Key Authentication

| Attribute | Detail |
|-----------|--------|
| **Description** | `Long-lived API key generation for programmatic access, supporting CRUD operations and optional store-specific key binding` |
| **Capability** | `Users can generate API keys for CI/CD pipelines, scripts, and external integrations to access LangBuilder programmatically without interactive login` |
| **API Endpoints** | `POST /api/v1/api_key/ (create key), GET /api/v1/api_key/ (list keys), DELETE /api/v1/api_key/{key_id} (revoke key), POST /api/v1/api_key/store (bind store key)` |
| **Status** | Stable |

### 7.4 OAuth2 Integration

| Attribute | Detail |
|-----------|--------|
| **Description** | `OAuth2 provider integration supporting Google and Zoho for federated authentication via redirect flow` |
| **Capability** | `Users can sign in using their Google or Zoho accounts instead of managing separate LangBuilder credentials` |
| **API Endpoints** | `Handled via login router OAuth callback endpoints` |
| **Status** | Stable |

### 7.5 LDAP Authentication

| Attribute | Detail |
|-----------|--------|
| **Description** | `LDAP/Active Directory integration for enterprise single sign-on using existing directory services` |
| **Capability** | `Enterprise users can authenticate with their corporate directory credentials, enabling centralized identity management` |
| **API Endpoints** | `POST /api/v1/login/ (LDAP auth path)` |
| **Status** | Verify |

### 7.6 Superuser Administration

| Attribute | Detail |
|-----------|--------|
| **Description** | `Elevated superuser role with full platform access including user management, system configuration, and cross-user resource visibility` |
| **Capability** | `Administrators can manage all users, access all flows and projects, configure system settings, and perform platform-wide operations` |
| **API Endpoints** | `All admin-scoped endpoints require superuser JWT` |
| **Status** | Stable |

---

## 8. File Management

Two-generation file API (V1 and V2) supporting upload, download, images, profile pictures, and batch operations.

### 8.1 File Upload and Storage (V1)

| Attribute | Detail |
|-----------|--------|
| **Description** | `File upload endpoint accepting multipart form data, storing files in the configured storage backend with metadata tracking in the File database model` |
| **Capability** | `Users can upload documents, images, and data files for use in their workflows (e.g., document ingestion, image processing)` |
| **API Endpoints** | `POST /api/v1/files/upload (upload file)` |
| **Status** | Stable |

### 8.2 File Download and Retrieval (V1)

| Attribute | Detail |
|-----------|--------|
| **Description** | `File retrieval by ID with content-type detection and streaming download support` |
| **Capability** | `Users can download previously uploaded files and workflow outputs` |
| **API Endpoints** | `GET /api/v1/files/{file_id}/download (download file), GET /api/v1/files/ (list files)` |
| **Status** | Stable |

### 8.3 Image and Profile Picture Management (V1)

| Attribute | Detail |
|-----------|--------|
| **Description** | `Specialized image handling for workflow images and user profile pictures with thumbnail generation and format validation` |
| **Capability** | `Users can upload and manage profile pictures and workflow-associated images` |
| **API Endpoints** | `POST /api/v1/files/images (upload image), GET /api/v1/files/profile_image/{user_id} (get profile pic)` |
| **Status** | Stable |

### 8.4 Enhanced File Operations (V2)

| Attribute | Detail |
|-----------|--------|
| **Description** | `Second-generation file API with enhanced CRUD, batch operations, improved metadata handling, and bulk upload/delete capabilities` |
| **Capability** | `Users benefit from improved file management with batch upload, batch delete, and richer metadata queries` |
| **API Endpoints** | `POST /api/v2/files/ (create), GET /api/v2/files/ (list), GET /api/v2/files/{file_id} (read), DELETE /api/v2/files/{file_id} (delete), POST /api/v2/files/batch/ (batch operations)` |
| **Status** | Stable |

---

## 9. Monitoring and Observability

Build tracking, message history, transaction logs, and log streaming for workflow execution visibility.

### 9.1 Build Monitoring

| Attribute | Detail |
|-----------|--------|
| **Description** | `VertexBuildTable-backed build tracking recording per-vertex execution status, duration, errors, and outputs for every flow execution` |
| **Capability** | `Users can review the execution history of every flow build, inspect individual vertex results, and diagnose build failures` |
| **API Endpoints** | `GET /api/v1/monitor/builds (list builds), GET /api/v1/monitor/builds/{build_id} (build detail)` |
| **Status** | Stable |

### 9.2 Message History

| Attribute | Detail |
|-----------|--------|
| **Description** | `MessageTable-backed conversation logging capturing all chat messages, session context, and flow interactions for audit and replay` |
| **Capability** | `Users can review conversation histories, debug chat interactions, and export message logs for analysis` |
| **API Endpoints** | `GET /api/v1/monitor/messages (list messages), GET /api/v1/monitor/messages/{session_id} (session messages)` |
| **Status** | Stable |

### 9.3 Transaction Tracking

| Attribute | Detail |
|-----------|--------|
| **Description** | `TransactionTable-backed execution audit trail recording API calls, token usage, latency, and cost data per transaction` |
| **Capability** | `Users can track API consumption, monitor costs, and audit all transactions executed through their workflows` |
| **API Endpoints** | `GET /api/v1/monitor/transactions (list transactions)` |
| **Status** | Stable |

### 9.4 Session Management

| Attribute | Detail |
|-----------|--------|
| **Description** | `Session tracking for grouping related builds and messages into logical conversation sessions` |
| **Capability** | `Users can view and manage conversation sessions, correlating builds and messages within a single interaction context` |
| **API Endpoints** | `GET /api/v1/monitor/sessions (list sessions)` |
| **Status** | Stable |

### 9.5 Log Streaming

| Attribute | Detail |
|-----------|--------|
| **Description** | `Real-time log streaming via SSE and historical log retrieval for debugging and operational monitoring` |
| **Capability** | `Users can stream live application logs and retrieve historical logs for troubleshooting and audit purposes` |
| **API Endpoints** | `GET /api/v1/logs/stream (SSE log stream), GET /api/v1/logs/ (retrieve logs)` |
| **Status** | Beta |

### 9.6 Third-Party Observability Integration

| Attribute | Detail |
|-----------|--------|
| **Description** | `Integration with 6 observability platforms (LangWatch, Langfuse, LangSmith, Opik, Arize Phoenix, Green) for LLM-specific monitoring, tracing, and analytics` |
| **Capability** | `Users can connect their preferred observability platform to gain deep insights into LLM performance, token usage, latency, and quality metrics` |
| **API Endpoints** | `N/A (configured via environment variables and component settings)` |
| **Status** | Stable |

---

## 10. MCP Protocol Support

Model Context Protocol implementation enabling tool integration, server management, and project-scoped MCP configurations across three API generations.

### 10.1 MCP Server (V1)

| Attribute | Detail |
|-----------|--------|
| **Description** | `First-generation MCP server exposing flows as tools via SSE transport with JSON-RPC message handling` |
| **Capability** | `Users can expose their LangBuilder flows as MCP tools that external MCP clients (e.g., Claude Desktop, IDE extensions) can discover and invoke` |
| **API Endpoints** | `GET /api/v1/mcp/sse (SSE transport), POST /api/v1/mcp/messages (JSON-RPC messages), GET /api/v1/mcp/ (server info)` |
| **Status** | Stable |

### 10.2 MCP Project Management

| Attribute | Detail |
|-----------|--------|
| **Description** | `Project-scoped MCP configuration enabling per-project tool definitions, SSE connections, settings management, and MCP server installation` |
| **Capability** | `Users can configure MCP tools on a per-project basis, install MCP servers from registries, and manage project-specific MCP settings` |
| **API Endpoints** | `GET /api/v1/mcp/projects/tools (list tools), GET /api/v1/mcp/projects/sse (project SSE), POST /api/v1/mcp/projects/messages (project messages), GET /api/v1/mcp/projects/settings (settings), PUT /api/v1/mcp/projects/settings (update settings), POST /api/v1/mcp/projects/install (install server)` |
| **Status** | Stable |

### 10.3 MCP Server Management (V2)

| Attribute | Detail |
|-----------|--------|
| **Description** | `Second-generation MCP API with enhanced server lifecycle management, configuration, health monitoring, and multi-server orchestration` |
| **Capability** | `Users can manage multiple MCP server instances, configure server parameters, monitor server health, and orchestrate complex multi-server MCP deployments` |
| **API Endpoints** | `5 endpoints under /api/v2/mcp/ (server CRUD, configuration, health)` |
| **Status** | Beta |

---

## 11. Voice Interaction

WebSocket-based voice flows with text-to-speech integration for conversational AI interfaces.

### 11.1 Voice Mode WebSocket Flows

| Attribute | Detail |
|-----------|--------|
| **Description** | `WebSocket transport for bidirectional voice communication enabling real-time speech-to-text input and text-to-speech output within flow execution` |
| **Capability** | `Users can interact with their AI workflows via voice, speaking inputs and hearing spoken responses in real time` |
| **API Endpoints** | `WS /api/v1/voice/ws/{flow_id} (WebSocket voice flow), GET /api/v1/voice/flows (list voice-enabled flows)` |
| **Status** | Beta |

### 11.2 Voice ID Management

| Attribute | Detail |
|-----------|--------|
| **Description** | `ElevenLabs TTS voice selection and configuration, providing access to available voice profiles for text-to-speech output customization` |
| **Capability** | `Users can browse available TTS voices, select a voice personality for their workflow, and preview voice characteristics` |
| **API Endpoints** | `GET /api/v1/voice/voices (list available voice IDs), GET /api/v1/voice/voices/{voice_id} (voice detail)` |
| **Status** | Beta |

### 11.3 Voice Flow Configuration

| Attribute | Detail |
|-----------|--------|
| **Description** | `Per-flow voice mode settings including voice selection, language, speed, and audio format configuration` |
| **Capability** | `Users can configure voice parameters for each flow, choosing language, voice, and audio quality settings` |
| **API Endpoints** | `PUT /api/v1/voice/flows/{flow_id}/config (configure voice settings)` |
| **Status** | Beta |

---

## 12. Publishing and Distribution

Publishing workflows to external platforms and sharing components through the community store.

### 12.1 OpenWebUI Publishing

| Attribute | Detail |
|-----------|--------|
| **Description** | `Flow publication to OpenWebUI platform, converting LangBuilder flows into OpenWebUI-consumable formats with status tracking via PublishRecord and PublishStatusEnum` |
| **Capability** | `Users can publish their flows to OpenWebUI with one click, making them available to OpenWebUI users, and track publication status (ACTIVE, UNPUBLISHED, ERROR, PENDING)` |
| **API Endpoints** | `POST /api/v1/publish/ (publish flow), POST /api/v1/publish/unpublish (unpublish flow), GET /api/v1/publish/status/{flow_id} (check status), GET /api/v1/publish/ (list published)` |
| **Status** | Stable |

### 12.2 Component Store Sharing

| Attribute | Detail |
|-----------|--------|
| **Description** | `Community marketplace for sharing, discovering, and downloading reusable components and flows with tagging, likes, and download tracking` |
| **Capability** | `Users can publish custom components to the store, tag them for discoverability, and track community engagement through likes and download counts` |
| **API Endpoints** | `POST /api/v1/store/components/ (share), GET /api/v1/store/ (browse), GET /api/v1/store/tags/ (tags), POST /api/v1/store/likes/ (like), GET /api/v1/store/downloads/ (stats)` |
| **Status** | Stable |

### 12.3 API Endpoint Exposure

| Attribute | Detail |
|-----------|--------|
| **Description** | `Flow-as-API endpoints enabling external systems to invoke flows via REST, webhooks, and advanced run configurations with versioning support` |
| **Capability** | `Users can expose any flow as a REST API endpoint, configure webhook triggers, use versioned endpoints, and integrate flows into external applications` |
| **API Endpoints** | `POST /api/v1/endpoints/run/{flow_id} (run flow), POST /api/v1/endpoints/webhook/{flow_id} (webhook trigger), POST /api/v1/endpoints/advanced_run/{flow_id} (advanced run), GET /api/v1/endpoints/version/{flow_id} (version info), GET /api/v1/endpoints/config/{flow_id} (endpoint config)` |
| **Status** | Stable |

---

## 13. Variable Management

Encrypted credential and configuration variable storage with environment variable fallback.

### 13.1 Encrypted Variable Storage

| Attribute | Detail |
|-----------|--------|
| **Description** | `Server-side encrypted variable storage using the Variable database model, storing sensitive credentials (API keys, tokens, passwords) with Fernet encryption at rest` |
| **Capability** | `Users can securely store API keys, tokens, and other sensitive credentials that are encrypted at rest and injected into flows at execution time without exposure in the UI` |
| **API Endpoints** | `POST /api/v1/variables/ (create), GET /api/v1/variables/ (list names only), PATCH /api/v1/variables/{variable_id} (update), DELETE /api/v1/variables/{variable_id} (delete)` |
| **Status** | Stable |

### 13.2 Environment Variable Fallback

| Attribute | Detail |
|-----------|--------|
| **Description** | `Hierarchical variable resolution that checks user-defined encrypted variables first, then falls back to server environment variables for deployment-level configuration` |
| **Capability** | `Users can rely on platform-level environment variables for shared credentials while overriding specific values with their own encrypted variables` |
| **API Endpoints** | `N/A (resolved at execution time within build engine)` |
| **Status** | Stable |

---

## 14. Configuration and Administration

System settings, superuser administration, and infrastructure health monitoring.

### 14.1 Health Check Endpoints

| Attribute | Detail |
|-----------|--------|
| **Description** | `HTTP health check endpoints reporting application readiness, database connectivity, and overall system health for load balancers and monitoring systems` |
| **Capability** | `Operators can configure load balancers and monitoring tools to probe LangBuilder health endpoints for automated failover and alerting` |
| **API Endpoints** | `GET /health (basic health), GET /api/v1/health/ (detailed health)` |
| **Status** | Stable |

### 14.2 User Administration

| Attribute | Detail |
|-----------|--------|
| **Description** | `Superuser-restricted user management including CRUD operations, password resets, and user profile queries` |
| **Capability** | `Administrators can create user accounts, reset passwords, update user profiles, and deactivate users` |
| **API Endpoints** | `POST /api/v1/users/ (create), GET /api/v1/users/ (list), GET /api/v1/users/whoami (current user), PATCH /api/v1/users/{user_id} (update), DELETE /api/v1/users/{user_id} (delete), POST /api/v1/users/reset-password (reset password)` |
| **Status** | Stable |

### 14.3 System Configuration

| Attribute | Detail |
|-----------|--------|
| **Description** | `Environment-variable-driven system configuration covering database, authentication providers, storage backends, CORS, TLS, and component settings` |
| **Capability** | `Administrators can configure all aspects of the LangBuilder deployment through environment variables and configuration files` |
| **API Endpoints** | `N/A (configured via environment variables and startup configuration)` |
| **Status** | Stable |

### 14.4 Database Backend Support

| Attribute | Detail |
|-----------|--------|
| **Description** | `Dual database backend support with SQLite for development/small deployments and PostgreSQL for production, using 10 ORM models (User, Flow, ApiKey, Variable, Folder, MessageTable, File, TransactionTable, VertexBuildTable, PublishRecord)` |
| **Capability** | `Operators can choose SQLite for quick local setup or PostgreSQL for production deployments with full ACID compliance and scalability` |
| **API Endpoints** | `N/A (configured via DATABASE_URL environment variable)` |
| **Status** | Stable |

---

## Summary

### Features by Category

| # | Category | Feature Count | Stable | Beta | Verify |
|---|----------|:------------:|:------:|:----:|:------:|
| 1 | Visual Workflow Builder | 5 | 5 | 0 | 0 |
| 2 | Flow Execution Engine | 5 | 5 | 0 | 0 |
| 3 | AI Model Integration | 4 | 4 | 0 | 0 |
| 4 | Vector Database Support | 3 | 3 | 0 | 0 |
| 5 | Component System | 4 | 4 | 0 | 0 |
| 6 | Project and Flow Management | 7 | 7 | 0 | 0 |
| 7 | Authentication and Authorization | 6 | 5 | 0 | 1 |
| 8 | File Management | 4 | 4 | 0 | 0 |
| 9 | Monitoring and Observability | 6 | 5 | 1 | 0 |
| 10 | MCP Protocol Support | 3 | 2 | 1 | 0 |
| 11 | Voice Interaction | 3 | 0 | 3 | 0 |
| 12 | Publishing and Distribution | 3 | 3 | 0 | 0 |
| 13 | Variable Management | 2 | 2 | 0 | 0 |
| 14 | Configuration and Administration | 4 | 4 | 0 | 0 |
| | **Total** | **59** | **53** | **5** | **1** |

### Maturity Distribution

| Status | Count | Percentage |
|--------|:-----:|:----------:|
| Stable | 53 | 89.8% |
| Beta | 5 | 8.5% |
| Verify | 1 | 1.7% |
| **Total** | **59** | **100%** |

### Key Platform Metrics

| Metric | Value |
|--------|-------|
| API Endpoints | 157 across 22 routers |
| Component Packages | 96 across 12 categories |
| LLM Providers | 28 |
| Vector Store Backends | 13+ |
| Database Models | 10 |
| Enums | 3 (AccessTypeEnum, PublishStatusEnum, Tags) |
| Auth Methods | 4 (JWT, API Key, Superuser, None/Public) |
| Integrations | 62 total |

---

*Generated: 2026-02-09*
*Source: LangBuilder v1.6.5 codebase inventory analysis*
*Generated by CloudGeometry AIx SDLC - Product Analysis*
