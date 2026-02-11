# Integration Map

> Generated: 2026-02-09 | LangBuilder v1.6.5

## AI / LLM Services

### OpenAI
- **Purpose**: Primary LLM provider (GPT-4, GPT-3.5, embeddings)
- **Type**: SDK (langchain-openai)
- **Auth**: API Key (`OPENAI_API_KEY`)
- **Criticality**: Critical
- **Status**: Active

### Anthropic
- **Purpose**: Claude LLM models
- **Type**: SDK (langchain-anthropic)
- **Auth**: API Key
- **Criticality**: High
- **Status**: Active

### Google Vertex AI
- **Purpose**: Google Cloud AI models (Gemini)
- **Type**: SDK (langchain-google-vertexai, langchain-google-genai)
- **Auth**: Service Account / API Key
- **Criticality**: High
- **Status**: Active

### Ollama
- **Purpose**: Local LLM server for self-hosted models
- **Type**: REST API
- **Auth**: None (local)
- **Usage**: `OLLAMA_BASE_URL` env var
- **Criticality**: High
- **Status**: Active

### HuggingFace
- **Purpose**: Model hub, inference API, embeddings
- **Type**: SDK (huggingface-hub, langchain-huggingface)
- **Auth**: API Token
- **Criticality**: High
- **Status**: Active

### 23 Additional LLM Providers
Including: Groq, Mistral, AWS Bedrock, Cohere, NVIDIA, SambaNova, DeepSeek, xAI, Perplexity, Cloudflare, IBM, and more - all available as pluggable component packages.

## Observability & Monitoring

### Sentry
- **Purpose**: Error tracking and performance monitoring
- **Type**: SDK (sentry-sdk[fastapi,loguru])
- **Auth**: DSN
- **Criticality**: High
- **Status**: Active

### LangWatch
- **Purpose**: LLM-specific observability and tracing
- **Type**: SDK (langwatch)
- **Auth**: API Key
- **Criticality**: Medium
- **Status**: Active

### LangFuse
- **Purpose**: LLM observability alternative
- **Type**: SDK (langfuse)
- **Auth**: API Key
- **Criticality**: Medium
- **Status**: Active

### LangSmith
- **Purpose**: LangChain ecosystem observability
- **Type**: SDK (langsmith)
- **Auth**: API Key
- **Criticality**: Medium
- **Status**: Active

### OpenTelemetry
- **Purpose**: Distributed tracing standard
- **Type**: SDK (opentelemetry-sdk, opentelemetry-instrumentation-fastapi)
- **Auth**: N/A
- **Criticality**: Medium
- **Status**: Active

### Prometheus
- **Purpose**: Metrics collection
- **Type**: SDK (opentelemetry-exporter-prometheus, prometheus-client)
- **Auth**: N/A
- **Criticality**: Medium
- **Status**: Active

## Vector Databases

| Service | SDK | Purpose | Status |
|---------|-----|---------|--------|
| Pinecone | langchain-pinecone | Cloud vector search | Active |
| ChromaDB | langchain-chroma | Embeddings database | Active |
| Weaviate | weaviate-client | Vector database | Active |
| Qdrant | qdrant-client | Vector similarity | Active |
| Milvus | langchain-milvus | Distributed vectors | Active |
| MongoDB Atlas | langchain-mongodb | Vector search | Active |
| Elasticsearch | langchain-elasticsearch | Full-text + vector | Active |
| FAISS | faiss-cpu | Local vector search | Active |
| PGVector | pgvector | PostgreSQL vectors | Active |
| Redis | redis | Vector similarity | Active |
| AstraDB | langchain-astradb | Cassandra vectors | Active |
| Upstash | upstash-vector | Serverless vectors | Active |
| OpenSearch | opensearch-py | Search + vectors | Active |

## Infrastructure

### PostgreSQL
- **Purpose**: Production relational database
- **Type**: Database
- **Auth**: Username/Password
- **Criticality**: Critical
- **Status**: Active

### Redis
- **Purpose**: Caching, Celery result backend
- **Type**: Key-value store
- **Auth**: Optional password
- **Criticality**: High
- **Status**: Active

### RabbitMQ
- **Purpose**: Message broker for Celery task queue
- **Type**: Message queue
- **Auth**: Username/Password
- **Criticality**: High
- **Status**: Active

## Authentication Providers

### Google OAuth
- **Purpose**: User authentication via Google
- **Type**: OAuth 2.0 / OIDC
- **Auth**: Client ID/Secret
- **Env**: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- **Criticality**: High
- **Status**: Active

### Microsoft OAuth
- **Purpose**: Azure AD / Entra ID authentication
- **Type**: OAuth 2.0
- **Auth**: Client ID/Secret
- **Env**: `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`
- **Criticality**: Medium
- **Status**: Active

### GitHub OAuth
- **Purpose**: GitHub authentication
- **Type**: OAuth 2.0
- **Auth**: Client ID/Secret
- **Criticality**: Medium
- **Status**: Active

### Google Workspace
- **Purpose**: Corporate authentication with service accounts
- **Type**: Google API
- **Auth**: Service Account Key File
- **Criticality**: Medium
- **Status**: Active

## Cloud Services

### AWS S3
- **Purpose**: File storage
- **Type**: SDK (boto3)
- **Auth**: AWS Credentials
- **Criticality**: Medium
- **Status**: Active

### AWS Lambda
- **Purpose**: Serverless function execution (Chez Antoine components)
- **Type**: SDK (boto3)
- **Auth**: AWS Credentials
- **Criticality**: Low
- **Status**: Active

## Internal Services

### OpenWebUI
- **Purpose**: Chat UI for published LangBuilder flows
- **Type**: REST API
- **Auth**: Internal
- **Criticality**: Medium
- **Status**: Active

### LangChain
- **Purpose**: Core LLM orchestration framework
- **Type**: SDK (langchain ecosystem)
- **Criticality**: Critical
- **Status**: Active

## Third-Party Tools

### Firecrawl
- **Purpose**: Web crawling and scraping
- **Type**: SDK (firecrawl-py)
- **Criticality**: Low
- **Status**: Active

### ElevenLabs
- **Purpose**: Text-to-speech for voice mode
- **Type**: REST API
- **Criticality**: Low
- **Status**: Active

### Composio
- **Purpose**: Multi-service integration platform
- **Type**: SDK (composio, composio-langchain)
- **Criticality**: Low
- **Status**: Active

### AssemblyAI
- **Purpose**: Speech-to-text
- **Type**: SDK (assemblyai)
- **Criticality**: Low
- **Status**: Active

## Summary

| Category | Active | Total |
|----------|--------|-------|
| LLM Providers | 28 | 28 |
| Vector Databases | 13 | 13 |
| Observability | 6 | 6 |
| Infrastructure | 3 | 3 |
| Auth Providers | 4 | 4 |
| Cloud Services | 2 | 2 |
| Internal | 2 | 2 |
| Third-Party Tools | 4 | 4 |
| **Total** | **62** | **62** |
