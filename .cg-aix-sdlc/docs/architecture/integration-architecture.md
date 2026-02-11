# Integration Architecture - LangBuilder

> Generated: 2026-02-09 | LangBuilder v1.6.5

## Overview

LangBuilder integrates with 62 external services across 8 categories to deliver its AI workflow builder capabilities. This document describes the integration topology, communication patterns, resilience strategies, authentication mechanisms, and data flows that govern how LangBuilder connects to its external dependencies.

All AI-related integrations (LLM providers, vector databases, embeddings, tools) are implemented as pluggable LangChain component packages. Infrastructure integrations (PostgreSQL, Redis, RabbitMQ) are managed at the platform level. Observability and auth provider integrations are wired through dedicated service-layer modules.

---

## Table of Contents

- [Integration Topology](#integration-topology)
- [Integration Summary](#integration-summary)
- [External Integrations by Category](#external-integrations-by-category)
  - [AI / LLM Services (28 Providers)](#ai--llm-services-28-providers)
  - [Vector Databases (13 Stores)](#vector-databases-13-stores)
  - [Observability (6 Services)](#observability-6-services)
  - [Infrastructure (3 Services)](#infrastructure-3-services)
  - [Auth Providers (4 Providers)](#auth-providers-4-providers)
  - [Cloud Services (2 Services)](#cloud-services-2-services)
  - [Internal Services (2 Services)](#internal-services-2-services)
  - [Third-Party Tools (4 Services)](#third-party-tools-4-services)
- [Integration Patterns](#integration-patterns)
  - [LangChain Provider Abstraction](#langchain-provider-abstraction)
  - [Component Adapter Pattern](#component-adapter-pattern)
  - [SDK Wrapper Pattern](#sdk-wrapper-pattern)
  - [REST Client Pattern](#rest-client-pattern)
- [Authentication Patterns for External Services](#authentication-patterns-for-external-services)
- [Data Flow Between Integrations](#data-flow-between-integrations)
- [Resilience Patterns](#resilience-patterns)

---

## Integration Topology

The following diagram shows how LangBuilder connects to all 62 integrations, grouped by category and communication pattern.

```mermaid
flowchart TB
    subgraph LB["LangBuilder Platform"]
        direction TB
        API["FastAPI Backend<br/>(API Layer)"]
        GE["Graph Execution Engine"]
        CR["Component Registry<br/>(96 Packages)"]
        SL["Service Layer<br/>(18 Services)"]
        CW["Celery Workers"]

        API --> SL
        API --> GE
        GE --> CR
        SL --> CW
    end

    subgraph LLM["AI / LLM Services (28)"]
        direction TB
        OpenAI["OpenAI<br/>GPT-4, GPT-3.5, Embeddings"]
        Anthropic["Anthropic<br/>Claude Models"]
        Google["Google Vertex AI<br/>Gemini Models"]
        Ollama["Ollama<br/>Local LLM Server"]
        HuggingFace["HuggingFace<br/>Model Hub, Inference"]
        MoreLLM["+ 23 more:<br/>Groq, Mistral, Bedrock,<br/>Cohere, NVIDIA, DeepSeek,<br/>xAI, Perplexity, etc."]
    end

    subgraph VDB["Vector Databases (13)"]
        direction TB
        Pinecone["Pinecone"]
        ChromaDB["ChromaDB"]
        Weaviate["Weaviate"]
        Qdrant["Qdrant"]
        MoreVDB["+ 9 more:<br/>Milvus, MongoDB Atlas,<br/>Elasticsearch, FAISS,<br/>PGVector, Redis, etc."]
    end

    subgraph OBS["Observability (6)"]
        direction TB
        Sentry["Sentry<br/>Error Tracking"]
        LangWatch["LangWatch"]
        LangFuse["LangFuse"]
        LangSmith["LangSmith"]
        OTel["OpenTelemetry"]
        Prometheus["Prometheus"]
    end

    subgraph INFRA["Infrastructure (3)"]
        direction TB
        PostgreSQL[("PostgreSQL<br/>Production DB")]
        Redis[("Redis<br/>Cache + Results")]
        RabbitMQ[("RabbitMQ<br/>Message Broker")]
    end

    subgraph AUTH["Auth Providers (4)"]
        direction TB
        GoogleOAuth["Google OAuth<br/>OIDC"]
        MicrosoftOAuth["Microsoft OAuth<br/>Azure AD / Entra ID"]
        GitHubOAuth["GitHub OAuth"]
        GoogleWorkspace["Google Workspace<br/>Service Accounts"]
    end

    subgraph CLOUD["Cloud Services (2)"]
        direction TB
        S3["AWS S3<br/>File Storage"]
        Lambda["AWS Lambda<br/>Serverless Execution"]
    end

    subgraph INTERNAL["Internal Services (2)"]
        direction TB
        OpenWebUI["OpenWebUI<br/>Chat UI"]
        LangChain["LangChain<br/>Core Framework"]
    end

    subgraph TOOLS["Third-Party Tools (4)"]
        direction TB
        Firecrawl["Firecrawl<br/>Web Crawling"]
        ElevenLabs["ElevenLabs<br/>Text-to-Speech"]
        Composio["Composio<br/>Multi-Service Platform"]
        AssemblyAI["AssemblyAI<br/>Speech-to-Text"]
    end

    %% Component layer connections (via LangChain SDKs)
    CR -->|"langchain-openai"| OpenAI
    CR -->|"langchain-anthropic"| Anthropic
    CR -->|"langchain-google-vertexai"| Google
    CR -->|"REST API"| Ollama
    CR -->|"huggingface-hub"| HuggingFace
    CR -->|"Provider SDKs"| MoreLLM

    CR -->|"langchain-pinecone"| Pinecone
    CR -->|"langchain-chroma"| ChromaDB
    CR -->|"weaviate-client"| Weaviate
    CR -->|"qdrant-client"| Qdrant
    CR -->|"Vector SDKs"| MoreVDB

    CR -->|"SDK / REST"| Firecrawl
    CR -->|"REST API"| ElevenLabs
    CR -->|"composio-langchain"| Composio
    CR -->|"assemblyai SDK"| AssemblyAI

    %% Service layer connections
    SL -->|"sentry-sdk"| Sentry
    SL -->|"langwatch SDK"| LangWatch
    SL -->|"langfuse SDK"| LangFuse
    SL -->|"langsmith SDK"| LangSmith
    SL -->|"OTLP"| OTel
    SL -->|"metrics export"| Prometheus

    SL -->|"asyncpg"| PostgreSQL
    SL -->|"redis-py"| Redis
    CW -->|"AMQP"| RabbitMQ
    CW -->|"redis-py"| Redis

    SL -->|"OAuth2 / OIDC"| GoogleOAuth
    SL -->|"OAuth2"| MicrosoftOAuth
    SL -->|"OAuth2"| GitHubOAuth
    SL -->|"Service Account"| GoogleWorkspace

    SL -->|"boto3"| S3
    CR -->|"boto3"| Lambda

    API -->|"REST API"| OpenWebUI
    GE -->|"langchain 0.3.x"| LangChain
```

---

## Integration Summary

| Category | Count | Criticality Range | Communication Pattern |
|----------|-------|-------------------|-----------------------|
| AI / LLM Services | 28 | Critical -- Medium | SDK (LangChain provider packages), REST |
| Vector Databases | 13 | High -- Medium | SDK (LangChain vector store packages), REST |
| Observability | 6 | High -- Medium | SDK, OTLP, HTTP push |
| Infrastructure | 3 | Critical -- High | Native protocol (asyncpg, AMQP, Redis) |
| Auth Providers | 4 | High -- Medium | OAuth2 / OIDC, Service Account |
| Cloud Services | 2 | Medium -- Low | SDK (boto3) |
| Internal Services | 2 | Critical -- Medium | SDK (langchain), REST |
| Third-Party Tools | 4 | Low | SDK, REST |
| **Total** | **62** | | |

---

## External Integrations by Category

### AI / LLM Services (28 Providers)

All LLM integrations are implemented as LangBuilder component packages that wrap LangChain provider libraries. Each component exposes a uniform interface (`BaseChatModel` / `BaseLanguageModel`) regardless of the underlying provider.

#### Tier 1: Primary Providers

| Provider | Criticality | SDK / Library | Auth Method | Protocol | Models |
|----------|-------------|---------------|-------------|----------|--------|
| **OpenAI** | Critical | `langchain-openai` | API Key (`OPENAI_API_KEY`) | HTTPS REST | GPT-4, GPT-4o, GPT-3.5-turbo, text-embedding-ada-002 |
| **Anthropic** | High | `langchain-anthropic` | API Key (`ANTHROPIC_API_KEY`) | HTTPS REST | Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku |
| **Google Vertex AI** | High | `langchain-google-vertexai`, `langchain-google-genai` | Service Account / API Key | HTTPS REST + gRPC | Gemini Pro, Gemini Ultra |
| **Ollama** | High | Direct REST client | None (local network) | HTTP REST | Llama 3, Mistral, CodeLlama, any GGUF model |
| **HuggingFace** | High | `huggingface-hub`, `langchain-huggingface` | API Token (`HUGGINGFACE_TOKEN`) | HTTPS REST | Hub models, Inference API |

#### Tier 2: Additional Providers (23)

| Provider | SDK | Auth | Notable Characteristics |
|----------|-----|------|------------------------|
| Groq | `langchain-groq` | API Key | Ultra-low latency inference |
| Mistral | `langchain-mistral` | API Key | European AI, open-weight models |
| AWS Bedrock | `langchain-aws` | AWS IAM credentials | Multi-model access via AWS |
| Cohere | `langchain-cohere` | API Key | Enterprise RAG optimization |
| NVIDIA | `langchain-nvidia-ai-endpoints` | API Key | GPU-accelerated inference |
| SambaNova | `langchain-sambanova` | API Key | Custom silicon inference |
| DeepSeek | `langchain-deepseek` | API Key | Reasoning and code models |
| xAI | Provider SDK | API Key | Grok models |
| Perplexity | OpenAI-compatible | API Key | Research-focused AI |
| Cloudflare | Workers AI SDK | API Token | Edge inference |
| IBM | `langchain-ibm` | API Key | Watson models |
| Azure OpenAI | `langchain-openai` | API Key + Endpoint | Enterprise-managed OpenAI |
| OpenRouter | OpenAI-compatible | API Key | Multi-provider gateway |
| LiteLLM | OpenAI-compatible | API Key | Universal LLM interface |
| NotDiamond | SDK | API Key | Intelligent model routing |
| LM Studio | OpenAI-compatible | None (local) | Desktop LLM server |
| Together AI | `langchain-together` | API Key | Open model hosting |
| Fireworks | `langchain-fireworks` | API Key | Fast open model inference |
| AI21 | `langchain-ai21` | API Key | Jurassic models |
| Writer | SDK | API Key | Enterprise content AI |
| Cerebras | SDK | API Key | Wafer-scale inference |
| Google AI Studio | `langchain-google-genai` | API Key | Gemini via API key |
| Voyage AI | SDK | API Key | Specialized embeddings |

### Vector Databases (13 Stores)

All vector store integrations are implemented as LangBuilder component packages that wrap LangChain's `VectorStore` base class.

| Service | SDK / Library | Auth Method | Deployment Model | Key Characteristics |
|---------|---------------|-------------|------------------|---------------------|
| **Pinecone** | `langchain-pinecone` | API Key | Cloud (managed) | Fully managed, horizontal scaling, metadata filtering |
| **ChromaDB** | `langchain-chroma` | None (local) / API Key (cloud) | Local / Cloud | Simple setup, good for development, in-memory or persistent |
| **Weaviate** | `weaviate-client` | API Key / None | Self-hosted / Cloud | Hybrid search, GraphQL API, modular vectorization |
| **Qdrant** | `qdrant-client` | API Key / None | Self-hosted / Cloud | Advanced filtering, payload indexing, gRPC support |
| **Milvus** | `langchain-milvus` | None / Token | Self-hosted / Cloud | Distributed, billion-scale vectors, GPU index |
| **MongoDB Atlas** | `langchain-mongodb` | Connection string | Cloud (managed) | Document + vector in one database, Atlas Search |
| **Elasticsearch** | `langchain-elasticsearch` | Username/Password / API Key | Self-hosted / Cloud | Full-text + vector hybrid search, mature ecosystem |
| **FAISS** | `faiss-cpu` | N/A (in-process) | Local (in-memory) | High-performance CPU-based similarity, Meta research |
| **PGVector** | `pgvector` | Database credentials | Self-hosted (PostgreSQL extension) | Vectors in existing PostgreSQL, familiar SQL interface |
| **Redis** | `redis` | Password (optional) | Self-hosted / Cloud | In-memory vectors, sub-millisecond latency |
| **AstraDB** | `langchain-astradb` | Application Token | Cloud (managed) | Cassandra-backed, serverless, global distribution |
| **Upstash** | `upstash-vector` | API Key | Cloud (serverless) | Pay-per-request, serverless, REST API |
| **OpenSearch** | `opensearch-py` | Username/Password | Self-hosted / AWS | AWS-compatible, full-text + vector, k-NN plugin |

### Observability (6 Services)

Observability integrations are wired at the service layer and graph execution engine, not as user-facing flow components.

| Service | Criticality | SDK / Library | Auth | Protocol | Scope |
|---------|-------------|---------------|------|----------|-------|
| **Sentry** | High | `sentry-sdk[fastapi,loguru]` | DSN (`SENTRY_DSN`) | HTTPS | Error tracking, performance monitoring, stack traces |
| **LangWatch** | Medium | `langwatch` | API Key (`LANGWATCH_API_KEY`) | HTTPS | LLM trace capture, quality scoring, cost tracking |
| **LangFuse** | Medium | `langfuse` | API Key (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`) | HTTPS | LLM traces, prompt management, evaluation |
| **LangSmith** | Medium | `langsmith` | API Key (`LANGCHAIN_API_KEY`) | HTTPS | LangChain-native tracing, dataset management, testing |
| **OpenTelemetry** | Medium | `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi` | N/A (collector endpoint) | OTLP (gRPC / HTTP) | Distributed tracing, span collection, context propagation |
| **Prometheus** | Medium | `prometheus-client`, `opentelemetry-exporter-prometheus` | N/A (scrape endpoint) | HTTP pull | Metrics collection, alerting thresholds, Grafana dashboards |

```mermaid
flowchart LR
    subgraph LB["LangBuilder Backend"]
        FastAPI["FastAPI App"]
        GraphEngine["Graph Engine"]
        SentrySDK["Sentry SDK"]
        OTelSDK["OpenTelemetry SDK"]
        LLMCallbacks["LLM Callbacks<br/>(LangWatch / LangFuse / LangSmith)"]
    end

    subgraph ObsTargets["Observability Backends"]
        SentryCloud["Sentry Cloud"]
        OTelCollector["OTel Collector"]
        LangWatchCloud["LangWatch"]
        LangFuseCloud["LangFuse"]
        LangSmithCloud["LangSmith"]
        PromScrape["Prometheus"]
    end

    FastAPI -->|"exception + perf"| SentrySDK
    SentrySDK -->|"HTTPS"| SentryCloud

    FastAPI -->|"spans"| OTelSDK
    OTelSDK -->|"OTLP"| OTelCollector

    GraphEngine -->|"LLM traces"| LLMCallbacks
    LLMCallbacks -->|"HTTPS"| LangWatchCloud
    LLMCallbacks -->|"HTTPS"| LangFuseCloud
    LLMCallbacks -->|"HTTPS"| LangSmithCloud

    PromScrape -->|"HTTP scrape"| FastAPI
```

### Infrastructure (3 Services)

Infrastructure services are directly managed in the deployment topology. They are not pluggable components; they are platform-level dependencies.

| Service | Criticality | Protocol | Library | Auth | Role |
|---------|-------------|----------|---------|------|------|
| **PostgreSQL** | Critical | TCP (asyncpg) | `sqlmodel`, `asyncpg` | Username/Password | Primary relational store for users, flows, messages, transactions, variables, API keys |
| **Redis** | High | TCP (RESP protocol) | `redis-py` | Password (optional) | Session cache, Celery result backend, rate limiting counters, flow execution state |
| **RabbitMQ** | High | AMQP 0-9-1 | `celery[rabbitmq]` | Username/Password | Message broker for Celery task distribution, durable queues, message acknowledgment |

### Auth Providers (4 Providers)

Authentication provider integrations are handled at the service layer through the `authlib` library. They follow the OAuth2 Authorization Code Grant flow.

| Provider | Criticality | Protocol | Library | Configuration |
|----------|-------------|----------|---------|---------------|
| **Google OAuth** | High | OAuth2 / OIDC | `authlib` | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |
| **Microsoft OAuth** | Medium | OAuth2 / OIDC | `authlib` | `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET` |
| **GitHub OAuth** | Medium | OAuth2 | `authlib` | `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` |
| **Google Workspace** | Medium | Google API (Service Account) | `google-auth`, `google-api-python-client` | Service account key file |

```mermaid
sequenceDiagram
    participant User
    participant Frontend as React Frontend
    participant Backend as FastAPI Backend
    participant IdP as Identity Provider<br/>(Google / Microsoft / GitHub)

    User->>Frontend: Click "Sign in with {Provider}"
    Frontend->>Backend: GET /api/v1/auth/{provider}/login
    Backend->>IdP: Redirect to authorization endpoint
    IdP->>User: Show login / consent screen
    User->>IdP: Authenticate and authorize
    IdP->>Backend: Redirect with authorization code
    Backend->>IdP: Exchange code for tokens (POST /token)
    IdP-->>Backend: Access token + ID token
    Backend->>Backend: Extract user identity from ID token
    Backend->>Backend: Create or match local user record
    Backend->>Backend: Issue LangBuilder JWT
    Backend-->>Frontend: Set JWT cookie / return token
    Frontend-->>User: Authenticated session
```

### Cloud Services (2 Services)

| Service | Criticality | SDK | Auth | Usage |
|---------|-------------|-----|------|-------|
| **AWS S3** | Medium | `boto3` | AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) or IAM role | File uploads, flow exports, document storage for RAG pipelines |
| **AWS Lambda** | Low | `boto3` | AWS credentials or IAM role | Serverless function execution for Chez Antoine custom components |

### Internal Services (2 Services)

| Service | Criticality | Integration Type | Protocol | Description |
|---------|-------------|-----------------|----------|-------------|
| **OpenWebUI** | Medium | REST API | HTTP | Chat UI frontend for published LangBuilder flows. Communicates with the backend via the OpenAI-compatible endpoint and LangBuilder REST API. |
| **LangChain** | Critical | Core SDK | In-process | Core LLM orchestration framework (v0.3.x). Provides `BaseChatModel`, `VectorStore`, `BaseRetriever`, `BaseTool`, and other abstractions that all component packages extend. |

### Third-Party Tools (4 Services)

These integrations are available as component packages for use within AI workflows.

| Service | SDK / Library | Auth | Protocol | Purpose |
|---------|---------------|------|----------|---------|
| **Firecrawl** | `firecrawl-py` | API Key | HTTPS REST | Web crawling and structured content extraction for RAG data ingestion |
| **ElevenLabs** | REST client | API Key | HTTPS REST | Text-to-speech synthesis for voice-enabled workflows |
| **Composio** | `composio`, `composio-langchain` | API Key | HTTPS REST | Multi-service integration platform providing tools for LangChain agents (CRM, email, calendar, etc.) |
| **AssemblyAI** | `assemblyai` | API Key | HTTPS REST | Speech-to-text transcription for audio processing workflows |

---

## Integration Patterns

LangBuilder uses four primary integration patterns, each suited to different categories of external services.

### LangChain Provider Abstraction

The dominant integration pattern for AI services. LangChain's base classes define a uniform interface, and each provider implements it through a LangChain community or partner package.

```
                    ┌─────────────────────────────────────────────────┐
                    │           LangBuilder Component Layer            │
                    │                                                  │
                    │  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
                    │  │ OpenAI   │ │Anthropic │ │  Ollama  │ ...    │
                    │  │Component │ │Component │ │Component │        │
                    │  └────┬─────┘ └────┬─────┘ └────┬─────┘        │
                    └───────│────────────│────────────│────────────────┘
                            │            │            │
                            v            v            v
                    ┌─────────────────────────────────────────────────┐
                    │         LangChain Abstraction Layer              │
                    │                                                  │
                    │   BaseChatModel    BaseEmbeddings   VectorStore  │
                    │   BaseRetriever    BaseTool         BaseLoader   │
                    └─────────────────────────────────────────────────┘
                            │            │            │
                            v            v            v
                    ┌─────────────────────────────────────────────────┐
                    │         LangChain Provider SDKs                  │
                    │                                                  │
                    │  langchain-openai  langchain-anthropic           │
                    │  langchain-google-vertexai  langchain-pinecone   │
                    │  langchain-chroma  langchain-huggingface  ...    │
                    └─────────────────────────────────────────────────┘
                            │            │            │
                            v            v            v
                    ┌────────────┐ ┌────────────┐ ┌────────────┐
                    │  Provider  │ │  Provider  │ │  Provider  │
                    │  REST API  │ │  REST API  │ │  REST API  │
                    └────────────┘ └────────────┘ └────────────┘
```

**Key characteristics:**
- Provider-agnostic workflows: a flow built with OpenAI can be switched to Anthropic by changing the model component
- Consistent interface for streaming, token counting, and callback hooks
- LangChain handles serialization, retry, and provider-specific quirks inside the SDK layer
- All 28 LLM providers and 13 vector databases follow this pattern

### Component Adapter Pattern

Each LangBuilder component wraps a LangChain primitive or external SDK, adapting it to the component system's declarative interface (Pydantic inputs/outputs, display metadata, UI schema generation).

```python
class OpenAIModelComponent(Component):
    """Adapter: LangBuilder Component -> LangChain ChatOpenAI."""

    display_name = "OpenAI"
    description = "Generate text using OpenAI models"
    icon = "OpenAI"

    # Declarative inputs (Pydantic fields)
    model_name: str = Field(default="gpt-4o", description="Model to use")
    temperature: float = Field(default=0.7, ge=0, le=2)
    api_key: SecretStr = Field(description="OpenAI API key")
    max_tokens: Optional[int] = Field(default=None, description="Max output tokens")

    # Output declarations
    outputs = [
        Output(name="model", display_name="Language Model", method="build_model"),
    ]

    def build_model(self) -> BaseChatModel:
        """Build the adapted LangChain model instance."""
        return ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            api_key=self.api_key.get_secret_value(),
            max_tokens=self.max_tokens,
        )
```

**Benefits of the adapter pattern:**
- Separation of concerns: UI schema generation, validation, and external SDK invocation are decoupled
- Component authors only need to implement `build_*` methods; the framework handles graph wiring, caching, and error reporting
- New provider support requires a new component package with no changes to the core engine
- Pydantic `SecretStr` fields ensure credentials are never serialized in logs or API responses

### SDK Wrapper Pattern

For services that provide their own Python SDKs but are not part of the LangChain ecosystem (e.g., Sentry, boto3, authlib), LangBuilder wraps the SDK in a service-layer module.

```python
# Service-layer SDK wrapper for Sentry
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.loguru import LoguruIntegration

def initialize_sentry(dsn: str, environment: str, release: str):
    """Wrap the Sentry SDK initialization with LangBuilder-specific config."""
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            LoguruIntegration(),
        ],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
    )
```

```python
# Service-layer SDK wrapper for AWS S3
import boto3
from botocore.config import Config

class S3StorageService:
    """Wrap boto3 S3 client with LangBuilder storage abstraction."""

    def __init__(self, bucket: str, region: str):
        self.client = boto3.client(
            "s3",
            region_name=region,
            config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
        )
        self.bucket = bucket

    async def upload_file(self, key: str, data: bytes, content_type: str) -> str:
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=data, ContentType=content_type
        )
        return f"s3://{self.bucket}/{key}"
```

**Used by:** Sentry, AWS S3, AWS Lambda, OpenTelemetry, authlib (OAuth providers), LLM observability SDKs (LangWatch, LangFuse, LangSmith)

### REST Client Pattern

For integrations without a Python SDK or where direct HTTP access is preferred (e.g., Ollama, ElevenLabs), LangBuilder uses `httpx` async HTTP clients.

```python
import httpx

class OllamaClient:
    """Direct REST client for Ollama local LLM server."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(connect=5.0, read=120.0, write=10.0),
        )

    async def generate(self, model: str, prompt: str, stream: bool = False):
        response = await self.client.post(
            "/api/generate",
            json={"model": model, "prompt": prompt, "stream": stream},
        )
        response.raise_for_status()
        return response.json()
```

**Used by:** Ollama (local), ElevenLabs, OpenWebUI communication, any OpenAI-compatible endpoint (Perplexity, OpenRouter, LM Studio)

### Pattern Selection Guide

| Pattern | When to Use | Examples |
|---------|-------------|---------|
| **LangChain Provider Abstraction** | LLM models, embeddings, vector stores, retrievers | OpenAI, Anthropic, Pinecone, ChromaDB |
| **Component Adapter** | Wrapping any external service as a flow-usable component | All 96 component packages |
| **SDK Wrapper** | Non-LangChain services accessed at the platform level | Sentry, boto3, authlib, LangSmith |
| **REST Client** | Services without SDKs or local services | Ollama, ElevenLabs, OpenWebUI |

---

## Authentication Patterns for External Services

LangBuilder uses six distinct authentication patterns for its 62 integrations, depending on the service type and security requirements.

```mermaid
flowchart TB
    subgraph AuthPatterns["Authentication Patterns"]
        direction TB

        APIKey["API Key<br/>(Header or Query)"]
        OAuth2["OAuth2 / OIDC<br/>(Authorization Code Grant)"]
        ServiceAccount["Service Account<br/>(Key File + Token Exchange)"]
        IAMRole["IAM Role<br/>(AWS Instance Profile)"]
        ConnString["Connection String<br/>(Username + Password)"]
        NoAuth["No Auth<br/>(Local Network)"]
    end

    subgraph Services["Services Using Each Pattern"]
        direction TB

        APIKeyServices["OpenAI, Anthropic, HuggingFace,<br/>Groq, Mistral, Cohere, NVIDIA,<br/>Pinecone, Weaviate, Qdrant,<br/>Sentry, LangWatch, LangFuse,<br/>LangSmith, Firecrawl, ElevenLabs,<br/>Composio, AssemblyAI, Upstash,<br/>AstraDB, etc. (40+)"]

        OAuth2Services["Google OAuth, Microsoft OAuth,<br/>GitHub OAuth"]

        SAServices["Google Vertex AI,<br/>Google Workspace"]

        IAMServices["AWS S3, AWS Lambda,<br/>AWS Bedrock"]

        ConnStringServices["PostgreSQL, Redis,<br/>RabbitMQ, Elasticsearch,<br/>MongoDB Atlas, PGVector"]

        NoAuthServices["Ollama, FAISS,<br/>ChromaDB (local),<br/>Prometheus (scrape)"]
    end

    APIKey --> APIKeyServices
    OAuth2 --> OAuth2Services
    ServiceAccount --> SAServices
    IAMRole --> IAMServices
    ConnString --> ConnStringServices
    NoAuth --> NoAuthServices
```

### Credential Storage and Retrieval

All external service credentials follow a consistent lifecycle:

| Stage | Mechanism | Details |
|-------|-----------|---------|
| **Storage** | Fernet-encrypted `Variable` table | API keys and secrets are encrypted with AES-128-CBC + HMAC-SHA256 before database persistence |
| **Environment** | Environment variables | Infrastructure credentials (`DATABASE_URL`, `REDIS_URL`, `BROKER_URL`) and primary provider keys (`OPENAI_API_KEY`, etc.) are injected via environment |
| **Runtime Injection** | Component parameter binding | During graph execution, encrypted variables are decrypted in memory and injected into component `SecretStr` fields |
| **Scope** | Per-user isolation | Each user's credentials are bound to their account; cross-user credential access is prevented by the service layer |

```mermaid
flowchart LR
    User["User"]
    VariableAPI["Variable API<br/>(CRUD)"]
    FernetEncrypt["Fernet<br/>Encryption"]
    VariableTable[("Variable Table<br/>(encrypted)")]
    GraphEngine["Graph Engine<br/>(runtime)"]
    FernetDecrypt["Fernet<br/>Decryption"]
    Component["Component<br/>(SecretStr field)"]
    ExternalAPI["External API"]

    User -->|"Store credential"| VariableAPI
    VariableAPI -->|"Plaintext"| FernetEncrypt
    FernetEncrypt -->|"Encrypted token"| VariableTable

    GraphEngine -->|"Resolve variable"| VariableTable
    VariableTable -->|"Encrypted token"| FernetDecrypt
    FernetDecrypt -->|"Plaintext (in memory only)"| Component
    Component -->|"API key in header"| ExternalAPI
```

### Per-Pattern Details

**API Key pattern** (40+ services):
- Keys are stored as Fernet-encrypted variables or passed via environment variables
- Transported in the `Authorization: Bearer <key>` header or provider-specific header (e.g., `x-api-key`)
- Some providers (OpenAI, Anthropic) support organization-scoped keys for billing isolation
- Keys are never logged, never included in API responses, and are held in memory only during component execution

**OAuth2 / OIDC pattern** (3 providers):
- Used exclusively for user authentication, not for component-level service access
- Authorization Code Grant with PKCE where supported
- Tokens are exchanged server-side; only the resulting LangBuilder JWT is sent to the frontend
- Refresh tokens are stored server-side in the session store (Redis)

**Service Account pattern** (2 services):
- Google Cloud services use service account JSON key files
- The key file path is set via environment variable; the SDK handles token exchange and refresh automatically
- Service accounts provide machine-to-machine authentication without user interaction

**IAM Role pattern** (3 services):
- AWS services can authenticate via instance profile IAM roles when running on EC2
- Falls back to `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` environment variables for non-AWS deployments
- boto3 credential chain: environment variables, shared credential file, instance profile

**Connection String pattern** (6 services):
- Infrastructure databases use connection strings with embedded credentials
- Format: `protocol://username:password@host:port/database`
- Connection strings are injected via environment variables and never logged

**No Auth pattern** (4 services):
- Local services (Ollama, ChromaDB local, FAISS) operate without authentication
- Expected to be accessible only within the deployment network
- Prometheus uses a pull-based scrape model; the backend exposes a `/metrics` endpoint without auth

---

## Data Flow Between Integrations

The following diagram traces data flow during a typical RAG (Retrieval-Augmented Generation) workflow execution, showing how data moves between LangBuilder and multiple external integrations.

```mermaid
sequenceDiagram
    participant User
    participant Frontend as React Frontend
    participant API as FastAPI Backend
    participant Engine as Graph Engine
    participant EmbComp as Embedding Component
    participant VecComp as Vector Store Component
    participant LLMComp as LLM Component
    participant EmbAPI as Embedding API<br/>(e.g., OpenAI)
    participant VecDB as Vector Database<br/>(e.g., Pinecone)
    participant LLMAPI as LLM API<br/>(e.g., OpenAI)
    participant ObsSvc as Observability<br/>(LangSmith / LangFuse)
    participant DB as PostgreSQL
    participant Cache as Redis

    User->>Frontend: Submit query in chat
    Frontend->>API: POST /api/v1/build/{flow_id}/flow<br/>(Authorization: Bearer JWT)
    API->>DB: Load flow definition (JSONB)
    DB-->>API: Flow graph data
    API->>Engine: Build and execute graph

    Note over Engine: Topological sort determines:<br/>1. Embed query<br/>2. Vector search<br/>3. LLM generation

    Engine->>EmbComp: Execute embedding vertex
    EmbComp->>EmbAPI: POST /v1/embeddings<br/>(API Key in header)
    EmbAPI-->>EmbComp: Embedding vector [1536 dims]
    EmbComp->>ObsSvc: Trace: embedding call (tokens, latency)

    Engine->>VecComp: Execute retrieval vertex
    VecComp->>VecDB: Query(vector, top_k=5, filter)<br/>(API Key in header)
    VecDB-->>VecComp: Matched documents + scores
    VecComp->>ObsSvc: Trace: retrieval (docs count, latency)

    Engine->>LLMComp: Execute generation vertex
    Note over LLMComp: Context = query + retrieved docs
    LLMComp->>LLMAPI: POST /v1/chat/completions<br/>(stream=true, API Key)
    LLMAPI-->>LLMComp: SSE: token stream
    LLMComp-->>Engine: Stream tokens
    Engine-->>API: SSE: token stream
    API-->>Frontend: SSE: token stream
    Frontend-->>User: Display streamed response

    LLMComp->>ObsSvc: Trace: LLM call (tokens, cost, latency)

    Engine->>DB: Write TransactionTable record
    Engine->>DB: Write VertexBuildTable records
    Engine->>DB: Write MessageTable record
    Engine->>Cache: Update flow execution state
```

### Integration Data Flow Summary

| Flow Stage | Source | Destination | Data | Protocol |
|------------|--------|-------------|------|----------|
| Query submission | Frontend | Backend API | User query text, flow ID | HTTPS (REST) |
| Flow loading | Backend API | PostgreSQL | Flow ID lookup | asyncpg (TCP) |
| Credential resolution | Graph Engine | Variable table | Encrypted API keys | asyncpg (TCP) + Fernet decryption |
| Embedding | Embedding Component | OpenAI / Provider | Text to embed | HTTPS (REST) |
| Retrieval | Vector Store Component | Pinecone / Provider | Embedding vector + filters | HTTPS (REST / gRPC) |
| Generation | LLM Component | OpenAI / Provider | Prompt + context documents | HTTPS (REST, SSE stream) |
| Token streaming | Backend API | Frontend | Generated tokens | SSE over HTTPS |
| Trace capture | Graph Engine | LangSmith / LangFuse | Execution traces, token counts, latency | HTTPS (REST) |
| Error tracking | FastAPI | Sentry | Exceptions, stack traces | HTTPS (REST) |
| Result persistence | Graph Engine | PostgreSQL | Transaction record, vertex builds, messages | asyncpg (TCP) |
| State caching | Graph Engine | Redis | Execution state, build results | Redis protocol (TCP) |
| Background tasks | Service Layer | RabbitMQ | Celery task messages | AMQP |
| Task results | Celery Workers | Redis | Serialized task results | Redis protocol (TCP) |

---

## Resilience Patterns

LangBuilder implements several resilience patterns to handle failures in external integrations gracefully.

### Timeout Configuration

Every external integration has explicit timeout configuration to prevent hanging requests from blocking the graph execution engine.

| Integration Category | Connect Timeout | Read Timeout | Total Timeout | Rationale |
|---------------------|----------------|--------------|---------------|-----------|
| LLM Providers (streaming) | 5s | 120s | 300s | LLM generation can take significant time, especially for long outputs |
| LLM Providers (non-streaming) | 5s | 60s | 120s | Bounded response time for non-streaming calls |
| Vector Databases | 5s | 30s | 60s | Vector queries should complete quickly; slow queries indicate issues |
| Embedding APIs | 5s | 30s | 60s | Embedding generation is fast; long waits indicate provider issues |
| Observability (fire-and-forget) | 2s | 5s | 10s | Observability must never block workflow execution |
| Auth Providers (OAuth) | 5s | 10s | 30s | Token exchange should be fast |
| Cloud Services (S3) | 5s | 30s | 60s | File operations vary by size but should be bounded |
| Infrastructure (Redis) | 2s | 5s | 10s | Fast-fail to avoid cascading delays |
| Infrastructure (PostgreSQL) | 5s | 10s | 30s | Pool pre-ping detects stale connections |
| Infrastructure (RabbitMQ) | 5s | 10s | 30s | Connection retry handled by Celery |

### Error Handling Strategy

```mermaid
flowchart TB
    Call["External Service Call"]
    Call --> Success{"Success?"}

    Success -->|Yes| Return["Return Result"]
    Success -->|No| Classify{"Classify Error"}

    Classify -->|"Transient<br/>(429, 503, timeout)"| Retry["Retry with<br/>Exponential Backoff"]
    Classify -->|"Auth Error<br/>(401, 403)"| AuthFail["Raise Auth Error<br/>(no retry)"]
    Classify -->|"Client Error<br/>(400, 422)"| ClientFail["Raise Validation Error<br/>(no retry)"]
    Classify -->|"Server Error<br/>(500, 502)"| ServerRetry["Retry (limited)<br/>then Raise"]

    Retry --> RetryCheck{"Retries<br/>Exhausted?"}
    RetryCheck -->|No| Call
    RetryCheck -->|Yes| Fallback{"Fallback<br/>Available?"}

    ServerRetry --> ServerCheck{"Retries<br/>Exhausted?"}
    ServerCheck -->|No| Call
    ServerCheck -->|Yes| Fallback

    Fallback -->|Yes| FallbackExec["Execute Fallback<br/>(e.g., alternate provider)"]
    Fallback -->|No| PropagateError["Propagate Error<br/>to Vertex / Graph Engine"]

    FallbackExec --> Return
    PropagateError --> VertexFail["Mark Vertex Failed<br/>Propagate to Downstream"]
```

### Retry Configuration

Retry behavior is primarily handled by LangChain's built-in retry logic for LLM and vector database integrations. The following table describes the effective retry behavior:

| Error Type | Max Retries | Backoff Strategy | Base Delay | Max Delay |
|------------|-------------|------------------|------------|-----------|
| Rate limit (HTTP 429) | 5 | Exponential with jitter | 1s | 60s |
| Timeout | 3 | Exponential | 2s | 30s |
| Server error (5xx) | 3 | Exponential with jitter | 1s | 30s |
| Connection error | 3 | Exponential | 1s | 15s |
| Auth error (401/403) | 0 | N/A | N/A | N/A |
| Client error (4xx) | 0 | N/A | N/A | N/A |

```python
# LangChain retry behavior (built into provider SDKs)
# - Retries on: 429 (rate limit), 500, 502, 503, 504
# - Strategy: Exponential backoff with jitter
# - Max retries: Configurable via `max_retries` param on each model
#
# Example: OpenAI component with retry configuration
model = ChatOpenAI(
    model="gpt-4",
    api_key=api_key,
    max_retries=3,         # Override default retry count
    request_timeout=120,   # Override default timeout
)
```

### Error Propagation Flow

When an external service call fails after retry exhaustion, the error propagates through the graph engine:

```mermaid
flowchart TB
    ExternalService["External Service<br/>(LLM, Vector DB, etc.)"]
    ProviderSDK["Provider SDK<br/>(LangChain)"]
    ComponentLayer["LangBuilder Component"]
    VertexExecutor["Vertex Executor"]
    GraphEngine["Graph Engine"]
    SSEStream["SSE Event Stream"]
    TransactionTable[("TransactionTable<br/>(error recorded)")]
    UserBrowser["User Browser"]

    ExternalService -->|"Error response<br/>(timeout, 5xx, etc.)"| ProviderSDK
    ProviderSDK -->|"Retries exhausted;<br/>raises exception"| ComponentLayer
    ComponentLayer -->|"Wraps in<br/>ComponentBuildError"| VertexExecutor
    VertexExecutor -->|"Marks vertex as failed;<br/>halts downstream"| GraphEngine
    GraphEngine -->|"Emits error event"| SSEStream
    GraphEngine -->|"Records error"| TransactionTable
    SSEStream -->|"Error event via SSE"| UserBrowser
```

### Graceful Degradation

LangBuilder classifies integrations into required and optional categories with different failure behavior:

| Classification | Integrations | Failure Behavior |
|---------------|--------------|-----------------|
| **Required -- Core** | PostgreSQL | Application refuses to start; health check fails |
| **Required -- Core** | Redis, RabbitMQ | Application starts but background task processing is impaired; health check degrades |
| **Required -- Execution** | LLM Providers, Vector DBs (when used in a flow) | Vertex execution fails; error propagated to user via SSE; transaction recorded with error status |
| **Optional -- Observability** | Sentry, LangWatch, LangFuse, LangSmith, OpenTelemetry, Prometheus | Silently disabled; workflow execution continues normally; no user-visible impact |
| **Optional -- Auth** | Google OAuth, Microsoft OAuth, GitHub OAuth (when configured) | That specific OAuth provider is unavailable; fallback to local username/password authentication |
| **Optional -- Storage** | AWS S3 | Fallback to local filesystem storage for file operations |

### Rate Limit Awareness

For LLM providers that enforce rate limits, LangBuilder implements rate-limit-aware request handling:

- **HTTP 429 responses** trigger automatic retry with the `Retry-After` header value (or exponential backoff if the header is absent)
- **Token-per-minute (TPM) limits** are tracked per provider and per API key; the graph engine can delay vertex execution to stay within limits
- **Request-per-minute (RPM) limits** are enforced via a sliding window counter in Redis
- **Provider-specific limits** are configured per component (e.g., OpenAI tier-based rate limits differ from Anthropic's)

### Infrastructure Connection Resilience

| Service | Resilience Mechanism | Details |
|---------|---------------------|---------|
| **PostgreSQL** | Connection pooling with pre-ping | `pool_size=20`, `max_overflow=30`, `pool_pre_ping=True`, `pool_recycle=3600`; stale connections are detected and replaced before use |
| **Redis** | Connection retry with health checks | Docker health check (`redis-cli ping`) every 10s; application reconnects on connection loss |
| **RabbitMQ** | Celery broker connection retry | Celery automatically reconnects to the broker; durable queues survive broker restarts; dead-letter queues capture undeliverable messages |

---

*Generated by CloudGeometry AIx SDLC - Architecture Documentation*
