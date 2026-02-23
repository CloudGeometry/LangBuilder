# LangBuilder Platform — Docker Compose Deployment

Production-ready Docker Compose configuration for the LangBuilder platform: **LangBuilder**, **OpenWebUI**, and **LangWatch**.

## Prerequisites

- Docker Engine 24+ with Compose v2.20+ (for `include:` support)
- Access to `ghcr.io/cloudgeometry` (GHCR) for private images
- Images must be built first via the GHA workflows (see [Building Images](#building-images))

## Quick Start

```bash
cd deploy

# 1. Create the shared network (once)
docker network create langbuilder-network

# 2. Configure environment
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY and WEBUI_SECRET_KEY

# 3. Log in to GHCR (required for private images)
echo "$GITHUB_TOKEN" | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# 4. Start everything
docker compose --env-file .env up -d
```

## Architecture

All services share a single external Docker network (`langbuilder-network`) for inter-service communication. Each stack has its own compose file and can be run independently.

```text
┌────────────────────────────────────────────────────────────────────┐
│  langbuilder-network                                               │
│                                                                    │
│  ┌──────────────┐  ┌──────────┐  ┌──────────────────────────────┐ │
│  │  LangBuilder │  │ OpenWebUI│  │         LangWatch            │ │
│  │              │  │          │  │                              │ │
│  │  backend:7860│  │    :8080 │  │  app:5560   nlp:5561        │ │
│  │  frontend:80 │  │          │  │  langevals:5562              │ │
│  │              │  │          │  │  postgres  redis  opensearch │ │
│  └──────────────┘  └──────────┘  └──────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

### Port Allocation

| Service              | Container Port | Host Port (default) |
|----------------------|---------------|---------------------|
| LangBuilder Backend  | 7860          | 7860                |
| LangBuilder Frontend | 80            | 3000                |
| OpenWebUI            | 8080          | 8080                |
| LangWatch App        | 5560          | 5560                |
| LangWatch NLP        | 5561          | 5561                |
| LangWatch LangEvals  | 5562          | 5562                |
| LangWatch Postgres   | 5432          | 5434                |
| LangWatch Redis      | 6379          | 6379                |
| LangWatch OpenSearch | 9200          | 9200                |

All host ports are configurable via `.env`.

## Running Individual Stacks

Run only the services you need:

```bash
# LangBuilder only
docker compose -f docker-compose.langbuilder.yml --env-file .env up -d

# OpenWebUI only
docker compose -f docker-compose.openwebui.yml --env-file .env up -d

# LangWatch only
docker compose -f docker-compose.langwatch.yml --env-file .env up -d

# All services at once (uses include: directive)
docker compose --env-file .env up -d
```

## Stopping Services

```bash
# Stop all
docker compose --env-file .env down

# Stop a single stack
docker compose -f docker-compose.langbuilder.yml --env-file .env down

# Stop and remove volumes (destructive — deletes data)
docker compose --env-file .env down -v
```

## Viewing Logs

```bash
# All services
docker compose --env-file .env logs -f

# Single service
docker compose --env-file .env logs -f langbuilder-backend

# Last 100 lines
docker compose --env-file .env logs --tail 100 openwebui
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable               | Required | Default                    | Description                        |
|------------------------|----------|----------------------------|------------------------------------|
| `OPENAI_API_KEY`       | Yes      | —                          | OpenAI API key for LLM access      |
| `WEBUI_SECRET_KEY`     | Yes      | —                          | OpenWebUI session encryption key   |
| `LW_NEXTAUTH_SECRET`   | Yes      | —                          | LangWatch auth secret (generate with `openssl rand -base64 32`) |
| `LB_BACKEND_TAG`       | No       | `latest`                   | LangBuilder backend image tag      |
| `LB_FRONTEND_TAG`      | No       | `latest`                   | LangBuilder frontend image tag     |
| `OPENWEBUI_TAG`        | No       | `latest`                   | OpenWebUI image tag                |

See `.env.example` for the full list of configurable variables.

### Database

- **LangBuilder**: SQLite by default (data in `langbuilder-app-data` volume). To switch to Postgres, follow the instructions in `docker-compose.langbuilder.yml`.
- **OpenWebUI**: SQLite by default. To migrate to Postgres, set `OPENWEBUI_DATABASE_URL` in `.env` to a `postgresql://` connection string.
- **LangWatch**: Dedicated Postgres instance included in its compose file.

## Building Images

Images are built by GitHub Actions workflows and pushed to GHCR:

| Workflow                          | Images Built                                      | Trigger                          |
|-----------------------------------|---------------------------------------------------|----------------------------------|
| `docker-build-langbuilder.yml`    | `langbuilder`, `langbuilder-backend`, `langbuilder-frontend` | Push to `main` (langbuilder paths) or manual |
| `docker-build-openwebui.yml`      | `openwebui`                                       | Push to `main` (openwebui paths) or manual |

To trigger a manual build:

```bash
# Build LangBuilder images with a specific tag
gh workflow run docker-build-langbuilder.yml -f tag=v1.0.0

# Build OpenWebUI
gh workflow run docker-build-openwebui.yml -f tag=v1.0.0
```

LangWatch uses official images from Docker Hub (`langwatch/langwatch:latest`) — no build workflow needed.

## Files

```text
deploy/
├── .env.example                      # Environment template — copy to .env
├── docker-compose.yml                # Top-level: includes all 3 stacks
├── docker-compose.langbuilder.yml    # LangBuilder backend + frontend
├── docker-compose.openwebui.yml      # OpenWebUI (GHCR fork)
├── docker-compose.langwatch.yml      # LangWatch + Postgres + Redis + OpenSearch
└── README.md                         # This file
```

## Troubleshooting

**GHCR auth errors**: Make sure you're logged in with `docker login ghcr.io` and your token has `read:packages` scope.

**OpenWebUI won't start**: `WEBUI_SECRET_KEY` is required. Set it in `.env`.

**LangWatch health check fails**: OpenSearch takes ~45s to start. Wait and check with `docker compose logs langwatch-opensearch`.

**Port conflicts**: All host ports are configurable via `.env`. Check `docker ps` for conflicts.

**Container memory issues**: Resource limits are set on all containers. Increase them in the compose file if services are OOM-killed.
