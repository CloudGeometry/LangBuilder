# Integration Ecosystem - LangBuilder v1.6.5

> Generated: 2026-02-09 | LangBuilder v1.6.5

## Overview

LangBuilder integrates with **62 external services and platforms** across 8 categories, enabling users to assemble AI workflows from best-of-breed components without writing integration code. Every integration is delivered as a pluggable component package built on the LangChain framework, meaning users drag a node onto the canvas, provide credentials, and connect it to the rest of their flow.

| Metric | Value |
|--------|-------|
| **Total Integrations** | 62 `[CODE]` |
| **AI / LLM Providers** | 28 `[CODE]` |
| **Vector Databases** | 13 `[CODE]` |
| **Observability Tools** | 6 `[CODE]` |
| **Auth Providers** | 4 `[CODE]` |
| **Infrastructure Services** | 3 `[CODE]` |
| **Cloud Services** | 2 `[CODE]` |
| **Internal Platforms** | 2 `[CODE]` |
| **Third-Party Specialty** | 4 `[CODE]` |

---

## Integrations by Category

### 1. AI / LLM Providers (28)

**What it enables:** Users can select the optimal language model for each task based on cost, latency, capability, data residency, or compliance requirements -- and switch between providers by changing a single node on the canvas.

#### Tier 1 -- Major Cloud Providers

| Provider | User Benefit | Setup | Key Configuration |
|----------|-------------|-------|-------------------|
| **OpenAI** | Industry-standard GPT-4o, o1, GPT-4 models for general-purpose text generation, code, and vision tasks `[CODE]` | API key via LangBuilder Variables | Model selection, temperature, max tokens, JSON mode |
| **Anthropic** | Claude 3.5 / Claude 3 family with strong reasoning, safety alignment, and large context windows `[CODE]` | API key | Model, temperature, max tokens, system prompt |
| **Google Vertex AI** | Gemini models with multimodal (text + image) capabilities and Google Cloud integration `[CODE]` | GCP service account / API key | Project ID, location, model, safety settings |
| **AWS Bedrock** | Access to Claude, Llama, Titan, and other models through a single AWS-managed endpoint with IAM-based access control `[CODE]` | AWS credentials (access key + secret) | Region, model ID, inference parameters |

#### Tier 2 -- High-Performance / Specialized

| Provider | User Benefit | Setup | Key Configuration |
|----------|-------------|-------|-------------------|
| **Groq** | Ultra-low-latency inference for real-time applications `[CODE]` | API key | Model, temperature, streaming |
| **Mistral** | Open-weight European models for EU data sovereignty and cost-effective workloads `[CODE]` | API key | Model (Mistral, Mixtral), temperature |
| **Cohere** | Enterprise-grade RAG optimization and semantic search via Command and Embed models `[CODE]` | API key | Model, embedding dimension |
| **DeepSeek** | Specialized reasoning models strong in code generation and mathematical problem-solving `[CODE]` | API key | Model, temperature, max tokens |
| **xAI** | Grok models for research and conversational tasks `[CODE]` | API key | Model, temperature |
| **Perplexity** | Research-focused AI with built-in web search for fact-grounded answers `[CODE]` | API key | Model, search domain |
| **NVIDIA** | NIM inference endpoints optimized for GPU-accelerated workloads `[CODE]` | API key / NIM endpoint | Model, endpoint URL |
| **SambaNova** | Enterprise AI inference with custom silicon for high throughput `[CODE]` | API key | Model, parameters |
| **IBM** | watsonx.ai models for enterprise AI with governance features `[CODE]` | API key / IAM token | Project ID, model |

#### Tier 3 -- Local and Self-Hosted

| Provider | User Benefit | Setup | Key Configuration |
|----------|-------------|-------|-------------------|
| **Ollama** | Run LLMs entirely on local hardware for air-gapped environments, development, and maximum data privacy `[CODE]` | Local Ollama server (no API key) | Server URL, model name, context length |
| **HuggingFace** | Access thousands of open-source models from the HuggingFace Hub or Inference API `[CODE]` | HF token | Model ID, task, inference endpoint |

#### Tier 4 -- Gateway and Routing

| Provider | User Benefit | Setup |
|----------|-------------|-------|
| **Cloudflare** | Workers AI models at the edge with low latency globally `[CODE]` | API token, account ID |
| Remaining 12 providers | Additional LLM integrations covering regional providers, routing gateways, and niche models `[CODE]` | Varies by provider |

> **Product benefit:** Users avoid vendor lock-in. A workflow built with OpenAI can be switched to Anthropic, Groq, or a local Ollama model by swapping a single node -- no code changes, no redeployment. `[INFERRED]`

---

### 2. Vector Databases (13)

**What it enables:** Users build Retrieval-Augmented Generation (RAG) applications by connecting their flows to a vector store that holds embedded documents. This lets LLMs answer questions grounded in private, current, or domain-specific knowledge.

#### Cloud-Managed (Zero Infrastructure)

| Service | User Benefit | Setup | Key Configuration |
|---------|-------------|-------|-------------------|
| **Pinecone** | Fully managed, production-grade vector search with minimal operational overhead `[CODE]` | API key, environment | Index name, namespace, metric |
| **AstraDB** | DataStax-managed Cassandra-backed vector store for teams already in the DataStax ecosystem `[CODE]` | Token, API endpoint | Collection, embedding dimension |
| **Upstash** | Serverless vector database with pay-per-request pricing for intermittent workloads `[CODE]` | REST URL, token | Index name, dimension |

#### Self-Hosted / Open Source

| Service | User Benefit | Setup | Key Configuration |
|---------|-------------|-------|-------------------|
| **ChromaDB** | Lightweight embedded vector store ideal for development and small datasets `[CODE]` | None (local) or server URL | Collection name, distance function |
| **FAISS** | Facebook AI Similarity Search for high-performance batch similarity on large datasets `[CODE]` | None (in-process) | Index type, dimension |
| **Weaviate** | Hybrid keyword + vector search with built-in modules for multimodal data `[CODE]` | Server URL, API key (cloud) | Class name, vectorizer |
| **Qdrant** | Filtering-optimized vector database with rich payload support `[CODE]` | Server URL, API key (cloud) | Collection, distance metric, quantization |
| **Milvus** | Distributed vector database for large-scale production workloads `[CODE]` | Server host/port | Collection, index type, metric |
| **PGVector** | PostgreSQL extension for teams who want vectors alongside relational data `[CODE]` | PostgreSQL connection string | Table name, embedding dimension |
| **Redis** | In-memory vector storage for ultra-low-latency retrieval `[CODE]` | Redis connection URL | Index name, distance metric |

#### Database Extensions

| Service | User Benefit | Setup | Key Configuration |
|---------|-------------|-------|-------------------|
| **MongoDB Atlas** | Vector search alongside document storage for teams already using MongoDB `[CODE]` | Connection string, database name | Collection, index name |
| **Elasticsearch** | Hybrid full-text + vector search on existing Elastic infrastructure `[CODE]` | Elasticsearch URL, credentials | Index, pipeline, field mapping |
| **OpenSearch** | AWS-compatible search with vector capabilities for AWS-native architectures `[CODE]` | Endpoint URL, credentials | Index name, engine (nmslib/faiss) |

> **Product benefit:** Users select the vector store that matches their existing infrastructure, scale requirements, and budget. Switching stores only requires changing the vector store node configuration. `[INFERRED]`

---

### 3. Observability (6)

**What it enables:** Users monitor AI workflow performance, trace LLM calls, track token costs, and debug issues across flow executions.

| Integration | User Benefit | Setup | What It Tracks |
|-------------|-------------|-------|----------------|
| **LangFuse** | Open-source LLM tracing with cost tracking, prompt management, and evaluation `[CODE]` | Self-hosted or cloud URL + keys | Traces, token usage, cost, latency |
| **LangWatch** | AI quality monitoring with automated evaluation and alerting `[CODE]` | API key | Performance metrics, quality scores |
| **LangSmith** | LangChain-native tracing and debugging for deep framework-level visibility `[CODE]` | API key | Chain traces, intermediate steps, errors |
| **OpenTelemetry** | Vendor-neutral distributed tracing standard for integration with existing APM tools `[CODE]` | Collector endpoint | Spans, traces, metrics |
| **Sentry** | Error tracking and performance monitoring with alerting for production issues `[CODE]` | DSN | Exceptions, transactions, breadcrumbs |
| **Prometheus** | Metrics collection for dashboards and alerting (Grafana, etc.) `[CODE]` | Metrics endpoint | Request rates, latencies, error rates |

> **Product benefit:** Teams gain visibility into LLM behavior, cost, and reliability without building custom instrumentation. `[INFERRED]`

---

### 4. Authentication Providers (4)

**What it enables:** Organizations connect LangBuilder to their existing identity providers, enabling single sign-on (SSO) and centralized user management.

| Provider | Protocol | User Benefit | Setup |
|----------|----------|-------------|-------|
| **Google OAuth** | OAuth2 / OIDC | SSO for Google Workspace organizations `[CODE]` | Client ID, client secret, redirect URI |
| **Microsoft OAuth** | OAuth2 / OIDC | SSO for Microsoft 365 / Azure AD environments `[CODE]` | Client ID, client secret, tenant ID |
| **GitHub OAuth** | OAuth2 | SSO for developer teams using GitHub identity `[CODE]` | Client ID, client secret |
| **Google Workspace** | OIDC | Domain-restricted access for corporate Google accounts `[CODE]` | Workspace domain, client credentials |

> **Product benefit:** Enterprise users authenticate with their existing corporate credentials. No separate password to manage. `[INFERRED]`

---

### 5. Infrastructure Services (3)

**What it enables:** Core platform infrastructure for data persistence, caching, and asynchronous task processing.

| Service | Role in LangBuilder | Setup |
|---------|---------------------|-------|
| **PostgreSQL** | Primary production database for user data, flow definitions, and execution history `[CODE]` | Connection string via environment variable |
| **Redis** | Session store, cache layer, and Celery result backend for async task processing `[CODE]` | Redis URL via environment variable |
| **RabbitMQ** | Message broker for Celery task queue, enabling distributed flow execution `[CODE]` | AMQP URL via environment variable |

---

### 6. Cloud Services (2)

**What it enables:** Users integrate AWS cloud services directly into their AI workflows for storage and serverless compute.

| Service | User Benefit | Setup | Key Configuration |
|---------|-------------|-------|-------------------|
| **AWS S3** | Store and retrieve files (documents, images, model artifacts) within AI workflows `[CODE]` | AWS credentials | Bucket name, region, prefix |
| **AWS Lambda** | Execute custom serverless functions as part of a flow for compute-intensive or isolated tasks `[CODE]` | AWS credentials | Function ARN, region, payload format |

---

### 7. Internal Platforms (2)

**What it enables:** Deep integration between LangBuilder and its companion platforms.

| Platform | User Benefit | Setup |
|----------|-------------|-------|
| **OpenWebUI** | Publish LangBuilder flows as chat interfaces that end users can interact with through a conversational UI `[CODE]` | OpenWebUI URL, shared authentication |
| **LangChain** | Foundation framework providing the component model, chain abstractions, and tool-calling primitives that power all LangBuilder nodes `[CODE]` | Built-in (no configuration) |

---

### 8. Third-Party Specialty Services (4)

**What it enables:** Specialized capabilities that extend AI workflows beyond text -- web crawling, voice synthesis, tool orchestration, and speech-to-text.

| Service | User Benefit | Setup | Key Configuration |
|---------|-------------|-------|-------------------|
| **Firecrawl** | Extract structured content from websites for use in RAG pipelines or data collection flows `[CODE]` | API key | URL, extraction schema |
| **ElevenLabs** | Add natural voice synthesis to flows for voice assistants, audio content generation, and accessibility `[CODE]` | API key | Voice ID, model, stability |
| **Composio** | Integrate 150+ SaaS tools into AI agents through a unified tool-calling interface `[CODE]` | API key | Tool selection, authentication |
| **AssemblyAI** | Transcribe audio and extract insights (sentiment, topics, summaries) for meeting analysis and media workflows `[CODE]` | API key | Language, model, features |

---

## Integration Summary Table

| Category | Count | Key Players | Primary Use Case |
|----------|-------|-------------|------------------|
| AI / LLM Providers | 28 | OpenAI, Anthropic, Google, AWS Bedrock, Ollama | Text generation, reasoning, vision, code |
| Vector Databases | 13 | Pinecone, ChromaDB, Weaviate, Qdrant, PGVector | RAG, semantic search, knowledge bases |
| Observability | 6 | LangFuse, LangSmith, Sentry, OpenTelemetry | Tracing, cost tracking, error monitoring |
| Auth Providers | 4 | Google, Microsoft, GitHub | SSO, enterprise identity |
| Infrastructure | 3 | PostgreSQL, Redis, RabbitMQ | Data persistence, caching, task queue |
| Cloud Services | 2 | AWS S3, AWS Lambda | Storage, serverless compute |
| Internal Platforms | 2 | OpenWebUI, LangChain | Chat UI publishing, framework foundation |
| Third-Party Specialty | 4 | Firecrawl, ElevenLabs, AssemblyAI, Composio | Web scraping, voice, transcription, tools |
| **Total** | **62** | | |

---

## Integration Architecture

All integrations in LangBuilder follow a **pluggable component package** architecture built on LangChain `[CODE]`:

```
langbuilder/
  src/backend/base/langbuilder/
    components/           # Core component definitions
      models/             # LLM provider components
      vectorstores/       # Vector database components
      embeddings/         # Embedding model components
      tools/              # Tool integrations
      ...
    base/
      langbuilder_base/   # Base classes and interfaces
```

**Key architectural properties:**

1. **Package-based discovery** `[CODE]`: Each integration is a Python package registered through LangBuilder's component discovery system. New integrations can be added by installing a package -- no core code changes required.

2. **LangChain abstraction layer** `[CODE]`: All LLM and vector store integrations use LangChain's standardized interfaces (`BaseLLM`, `BaseRetriever`, `VectorStore`). This means any LangChain-compatible provider can be integrated.

3. **Credential isolation** `[CODE]`: Integration credentials are stored as encrypted variables (AES-GCM) and decrypted only at runtime within the graph execution engine. Credentials are never exposed through the API or logged.

4. **Hot-swappable** `[INFERRED]`: Because integrations share standardized interfaces, users can replace one provider with another (e.g., swap Pinecone for Qdrant) by changing a single node without restructuring the flow.

5. **Component store** `[CODE]`: Users can share custom integration components through the built-in store (`/api/v1/store/components/`), enabling community-driven expansion of the integration ecosystem.

---

## Integration Selection Guide

### By Use Case

| I want to... | Recommended Stack |
|--------------|-------------------|
| Build a RAG chatbot | OpenAI or Anthropic + Pinecone or ChromaDB + LangFuse |
| Run AI in an air-gapped environment | Ollama + FAISS + local PostgreSQL |
| Optimize LLM costs | Multiple providers + LangFuse cost tracking |
| Add voice to a workflow | ElevenLabs (TTS) + AssemblyAI (STT) + any LLM |
| Scrape and analyze websites | Firecrawl + embedding model + vector store + LLM |
| Publish a chat interface | Any LLM flow + OpenWebUI publishing |
| Monitor production flows | OpenTelemetry + Sentry + Prometheus |

### By Deployment Context

| Context | Recommended Integrations |
|---------|-------------------------|
| **Air-gapped / on-premise** | Ollama, ChromaDB/FAISS, PostgreSQL, self-hosted Redis |
| **AWS-native** | AWS Bedrock, OpenSearch, S3, Lambda |
| **Enterprise / compliance** | Azure OpenAI or Bedrock, Pinecone, LangFuse, Microsoft OAuth |
| **Startup / cost-sensitive** | OpenAI (pay-per-token), ChromaDB, PostgreSQL |
| **Developer workstation** | Ollama, ChromaDB, SQLite (built-in) |

---

*Generated by CloudGeometry AIx SDLC - Product Analysis*
