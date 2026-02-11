# Product Overview - LangBuilder v1.6.5

> Generated: 2026-02-09 | LangBuilder v1.6.5

---

## What is LangBuilder? `[INFERRED from codebase analysis]`

LangBuilder is a **visual AI workflow builder** -- an enterprise fork of LangFlow -- that enables teams to design, test, execute, and deploy AI-powered applications through a drag-and-drop interface. Instead of writing hundreds of lines of integration code, users connect pre-built components on a visual canvas to construct workflows that span large language models, vector databases, enterprise tools, and custom logic.

The platform is a self-hosted solution composed of four cooperating services `[CODE]`:

| Service | Technology | Purpose |
|---------|-----------|---------|
| **LangBuilder Backend** | FastAPI (Python) | Core API server: flow management, graph execution engine, authentication, 157 REST endpoints |
| **LangBuilder Frontend** | React 18 + TypeScript | Visual flow builder: React Flow canvas, component sidebar, project management UI |
| **OpenWebUI Backend** | FastAPI (Python) | Chat interface backend: OAuth2/OIDC, LDAP, conversation management, model serving |
| **OpenWebUI Frontend** | Svelte | Conversational UI: end-user chat interface for published flows |

**Key numbers from the codebase** `[CODE]`:

| Metric | Value |
|--------|-------|
| REST API endpoints | 157 (68 GET, 53 POST, 19 DELETE, 9 PATCH, 2 PUT, 4 WebSocket, 2 HEAD) |
| Database models | 10 (User, Flow, ApiKey, Variable, Folder, MessageTable, File, TransactionTable, VertexBuildTable, PublishRecord) |
| Component packages | 96 across 12 categories |
| LLM provider integrations | 28 |
| Vector database integrations | 13+ |
| Total integrations | 62 |
| Alembic migrations | 50 |
| Authentication methods | JWT (HS256), OAuth2 (Google, Microsoft, GitHub), API Keys, LDAP, Trusted Headers |

---

## Who is LangBuilder For? `[ASSUMED - VALIDATE WITH STAKEHOLDERS]`

### Primary Personas

#### 1. AI/ML Engineer

| Aspect | Detail |
|--------|--------|
| **Role** | ML Engineer, AI Engineer, Data Scientist |
| **Goal** | Rapidly prototype and iterate on AI solutions without boilerplate code |
| **Pain points** | Repetitive integration code, slow experiment cycles, difficulty comparing model providers |
| **How LangBuilder helps** | Visual canvas for quick experimentation; swap LLM providers by changing a single component; 28 LLM providers available without writing integration code; encrypted variables for managing API keys securely `[CODE]` |
| **Key features used** | Flow builder, LLM components, vector store components, agent components, streaming execution |

#### 2. Software Developer

| Aspect | Detail |
|--------|--------|
| **Role** | Backend Developer, Full-Stack Developer, Platform Developer |
| **Goal** | Add AI capabilities to existing applications via APIs |
| **Pain points** | Learning curve for AI frameworks, complex prompt engineering, deployment complexity |
| **How LangBuilder helps** | OpenAI-compatible API (`/v1/chat/completions`) for drop-in integration `[CODE]`; REST API for flow execution (`POST /api/v1/run/{flow_id}`) `[CODE]`; webhook support for event-driven architectures; MCP protocol for tool integration |
| **Key features used** | REST API, OpenAI-compatible endpoints, API keys, webhooks, MCP server/client |

#### 3. DevOps / Platform Engineer

| Aspect | Detail |
|--------|--------|
| **Role** | Infrastructure Engineer, Platform Team Lead, SRE |
| **Goal** | Standardize AI tooling, maintain security and compliance, control infrastructure costs |
| **Pain points** | Vendor lock-in, scattered AI tools, compliance requirements for data sovereignty |
| **How LangBuilder helps** | Self-hosted deployment with full data control `[CODE]`; Docker containerization; SQLite (dev) / PostgreSQL (prod) database support `[CODE]`; LDAP integration for enterprise directory services `[CODE]`; AES-GCM encryption for secrets at rest `[CODE]` |
| **Key features used** | Docker deployment, health check endpoints, variable encryption, LDAP auth, monitoring APIs |

#### 4. Product Manager (Technical)

| Aspect | Detail |
|--------|--------|
| **Role** | Technical Product Manager, AI Product Owner |
| **Goal** | Validate AI concepts quickly, demonstrate capabilities to stakeholders |
| **Pain points** | Dependency on engineering for prototypes, long iteration cycles, difficulty communicating AI capabilities |
| **How LangBuilder helps** | Visual flow builder makes AI pipelines visible and understandable; starter projects provide templates `[CODE: GET /api/v1/starter-projects/]`; flows can be shared via export/import; published flows accessible through OpenWebUI chat interface |
| **Key features used** | Visual canvas, starter projects, flow import/export, OpenWebUI publishing |

### Secondary Personas `[ASSUMED - VALIDATE WITH STAKEHOLDERS]`

| Persona | Role | Key Value |
|---------|------|-----------|
| **Enterprise Architect** | Solutions Architect | Comprehensive integration ecosystem (62 integrations); standards compliance (OpenAI API, MCP) |
| **Agency Developer** | Consultancy Developer | Reusable flow templates; multi-client deployment via API keys; flow export/import for delivery |
| **Security Engineer** | InfoSec, Compliance | Self-hosted control; AES-GCM encryption; bcrypt password hashing; audit logging middleware; CORS controls |

---

## Key Use Cases `[INFERRED]`

### 1. Building Conversational AI Chatbots

**What:** Create chatbots that combine LLM capabilities with business data and tools.

**How it works in LangBuilder** `[CODE]`:
- Select an LLM component (any of 28 providers) and configure system prompt
- Add memory component for conversation continuity (MessageTable tracks sessions)
- Connect to knowledge sources via vector store components (13+ options)
- Tag the flow as `CHATBOTS` `[CODE: Tags enum]`
- Publish to OpenWebUI for end-user access via chat interface
- Monitor conversations via message session endpoints (`GET /api/v1/monitor/messages`)

**Example flow:** User Question -> Embedding Model -> Vector Store (similarity search) -> LLM (with context) -> Response

### 2. Creating RAG (Retrieval-Augmented Generation) Pipelines

**What:** Build pipelines that ground LLM responses in private or domain-specific data.

**How it works in LangBuilder** `[CODE]`:
- Upload documents via file management endpoints (`POST /api/v1/files/upload/{flow_id}` or `POST /api/v2/files`)
- Process documents using Docling, Unstructured, or custom text splitting components
- Store embeddings in any of 13+ vector databases (ChromaDB, Pinecone, Qdrant, etc.)
- Build retrieval flow: query embedding -> vector search -> context assembly -> LLM generation
- Execute via API for application integration or via UI for testing

**Example flow:** Document Ingestion -> Text Splitter -> Embedding Model -> Vector Store -> Retrieval Chain -> LLM -> Formatted Output

### 3. Workflow Automation with AI

**What:** Automate business processes by connecting AI capabilities with enterprise tools.

**How it works in LangBuilder** `[CODE]`:
- Combine LLM components with enterprise tool integrations (HubSpot, Jira, Confluence, etc.)
- Configure encrypted variables for third-party API credentials (`POST /api/v1/variables/`)
- Set up webhook triggers for event-driven execution (`POST /api/v1/webhook/{flow_id}`)
- Use API key authentication for CI/CD pipeline integration

**Example flow:** Webhook Trigger -> Data Extraction (LLM) -> CRM Lookup (HubSpot) -> Decision Logic -> Email Notification (AWS SES)

### 4. AI Agent Development

**What:** Build autonomous agents that can use tools, make decisions, and accomplish complex tasks.

**How it works in LangBuilder** `[CODE]`:
- Select agent framework components (CrewAI, Composio)
- Configure tool-calling capabilities with multiple tools per agent
- Add persistent memory via Mem0 integration
- Tag the flow as `AGENTS` `[CODE: Tags enum]`
- Expose agents via MCP protocol for integration with Claude Desktop and other AI systems
- Enable MCP on the flow (`mcp_enabled=True` on Flow model) `[CODE]`

**Example flow:** User Request -> Agent (with tools: Web Search, Calculator, Code Executor) -> Tool Selection -> Tool Execution -> Agent Reasoning -> Final Response

### 5. Multi-Model Comparison and Routing

**What:** Compare outputs from different LLM providers or route requests to optimal models.

**How it works in LangBuilder** `[CODE]`:
- Place multiple LLM components (e.g., OpenAI GPT-4, Anthropic Claude, Google Gemini) in parallel
- Use conditional logic or NotDiamond routing to select the best model
- Compare outputs side-by-side during development
- Switch providers without code changes by swapping components
- Use OpenRouter or LiteLLM components for unified access

---

## How It Works `[CODE]`

### High-Level Architecture

```
                    +-------------------+
                    |   User / Client   |
                    +--------+----------+
                             |
              +--------------+--------------+
              |                             |
    +---------v----------+       +----------v---------+
    | LangBuilder        |       | OpenWebUI          |
    | Frontend (React)   |       | Frontend (Svelte)  |
    | - Visual Canvas    |       | - Chat Interface   |
    | - Component Sidebar|       | - Model Selector   |
    | - Project Manager  |       | - Conversation UI  |
    +--------+-----------+       +----------+----------+
             |                              |
    +--------v-----------+       +----------v----------+
    | LangBuilder        |       | OpenWebUI           |
    | Backend (FastAPI)  |       | Backend (FastAPI)   |
    | - 157 REST API     |       | - OAuth2/OIDC       |
    | - Graph Engine     |       | - LDAP Auth         |
    | - 96 Components    |       | - Chat Management   |
    | - JWT + API Key    |       | - Model Proxy       |
    +--------+-----------+       +----------+----------+
             |                              |
             +------+-----------+-----------+
                    |           |
             +------v---+ +----v------+
             | Database | | Redis     |
             | (SQLite/ | | (Sessions,|
             | Postgres)| | Cache)    |
             +----------+ +-----------+
```

### From Canvas Design to Result Delivery `[CODE]`

The core workflow of LangBuilder follows a design-build-execute pattern:

**Phase 1: Design (Frontend)**

```
1. User opens the React 18 visual canvas (powered by React Flow)
2. Component sidebar displays 96 packages organized in 12 categories:
   - LLM Models, Embeddings, Vector Stores, Agents,
   - Tools, Data Processing, Memory, Chains,
   - Inputs/Outputs, Utilities, Custom, Chez Antoine
3. User drags components onto the canvas
4. User configures component parameters:
   - Model selection (28 LLM providers)
   - Credential references (encrypted variables)
   - Prompts, temperature, max tokens, etc.
5. User connects component outputs to inputs via edges
6. Real-time validation provides feedback on the flow structure
```

**Phase 2: Save (API)**

```
7. User saves the flow
8. Frontend sends POST /api/v1/flows/ with:
   - name, description (with UNIQUE(user_id, name) constraint)
   - data: JSON representation of the entire graph (nodes, edges, parameters)
   - tags: [CHATBOTS] or [AGENTS]
   - access_type: PRIVATE (default) or PUBLIC
9. Backend persists the Flow record to the database
```

**Phase 3: Execute (Graph Engine)**

```
10. User initiates execution via one of three paths:
    - UI:      POST /api/v1/build/{flow_id}/flow (Bearer JWT)
    - API:     POST /api/v1/run/{flow_id_or_name} (Bearer JWT or API Key)
    - Webhook: POST /api/v1/webhook/{flow_id_or_name} (API Key)

11. Graph Execution Engine processes the flow:
    a. Loads Flow.data JSON from database
    b. Resolves encrypted variables (AES-GCM decryption in memory)
    c. Validates DAG structure (no cycles, all required inputs present)
    d. Topologically sorts vertices by dependency
    e. For each vertex in order:
       - Instantiates component class from the 96-package component library
       - Applies configured parameters
       - Executes component logic (LLM API call, vector search, etc.)
       - Records VertexBuildTable entry (build_id, data, artifacts, valid)
       - Streams intermediate results via SSE to client
       - Routes outputs to downstream components via edges
    f. Assembles final output from terminal vertices
```

**Phase 4: Deliver (Response)**

```
12. Results delivered to the caller:
    - Synchronous: JSON response body with outputs
    - Streaming: Server-Sent Events (SSE) for real-time token delivery
    - Chat: Message stored in MessageTable with session_id for continuity

13. Audit trail created:
    - TransactionTable: vertex_id, inputs, outputs, status, error
    - VertexBuildTable: per-component build data and artifacts

14. Optional: Results accessible to end users via:
    - Published OpenWebUI chat interface (PublishRecord tracks status)
    - OpenAI-compatible API (GET /v1/models, POST /v1/chat/completions)
    - MCP protocol (for AI-to-AI tool calling)
```

### Execution Paths Summary `[CODE]`

| Path | Endpoint | Auth | Response Type | Primary User |
|------|----------|------|---------------|-------------|
| UI Execution | `POST /api/v1/build/{flow_id}/flow` | Bearer JWT | SSE stream | Regular User (canvas) |
| API Execution | `POST /api/v1/run/{flow_id_or_name}` | Bearer JWT or API Key | JSON sync | Developer (application) |
| Webhook | `POST /api/v1/webhook/{flow_id_or_name}` | API Key | JSON sync | Automation (CI/CD, events) |
| OpenAI-Compatible | `POST /v1/chat/completions` | Bearer JWT or API Key | JSON or SSE | Developer (drop-in replacement) |
| Public Execution | `POST /api/v1/build_public_tmp/{flow_id}/flow` | None | SSE stream | Anonymous (public flows) |
| MCP | `POST /api/v1/mcp/` | Bearer JWT | JSON (MCP protocol) | AI system (tool calling) |

---

## Platform Statistics `[CODE]`

| Category | Detail |
|----------|--------|
| **Version** | 1.6.5 |
| **Services** | 4 (2 backends + 2 frontends) |
| **API Endpoints** | 157 total |
| **Database Models** | 10 |
| **Enums** | 3 (AccessTypeEnum, PublishStatusEnum, Tags) |
| **Component Packages** | 96 |
| **Component Categories** | 12 |
| **LLM Providers** | 28 |
| **Vector Databases** | 13+ |
| **Total Integrations** | 62 |
| **Auth Methods** | 5 (JWT, OAuth2, API Key, LDAP, Trusted Headers) |
| **OAuth Providers** | 3 (Google, Microsoft, GitHub) |
| **Database Migrations** | 50 (Alembic) |
| **Supported Databases** | SQLite (dev), PostgreSQL (prod) |

---

## Evidence Attribution Key

Throughout this document, evidence is attributed using the following tags:

| Tag | Meaning |
|-----|---------|
| `[CODE]` | Directly verified from source code, database models, API route definitions, or configuration files |
| `[INFERRED]` | Derived from codebase analysis -- logical conclusion from observed code patterns and architecture |
| `[ASSUMED - VALIDATE WITH STAKEHOLDERS]` | Reasonable assumption based on product category and codebase capabilities; requires stakeholder confirmation |

---

*Generated by CloudGeometry AIx SDLC - Product Analysis*
