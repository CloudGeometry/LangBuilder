# Deployment Topology - LangBuilder

> Generated: 2026-02-09 | LangBuilder v1.6.5

## Overview

This document describes the deployment architecture for LangBuilder, including production topology, environment configurations, CI/CD pipeline, Docker image details, and infrastructure components. LangBuilder supports two primary deployment environments: a lightweight local development setup and a full production deployment on AWS EC2 with Traefik reverse proxy, monitoring, and background worker infrastructure.

## Production Architecture

The production deployment runs on AWS EC2 with Docker Compose, using Traefik v3 as the entry point for all HTTP/HTTPS traffic. The architecture includes 11 services spanning the application tier, data tier, worker tier, and monitoring tier.

```mermaid
graph TB
    subgraph Internet["Internet"]
        Users["Users / Clients"]
    end

    subgraph EC2["AWS EC2 Instance"]
        subgraph Proxy["Reverse Proxy"]
            Traefik["Traefik v3<br/>:80 / :443<br/>Let's Encrypt TLS"]
        end

        subgraph AppTier["Application Tier"]
            Frontend["Frontend<br/>(React + Nginx)<br/>:80"]
            Backend["Backend API<br/>(FastAPI + Uvicorn)<br/>:7860"]
        end

        subgraph WorkerTier["Worker Tier"]
            CeleryWorker["Celery Worker<br/>(Background Tasks)"]
            Flower["Flower<br/>(Worker Monitor)<br/>:5555"]
        end

        subgraph DataTier["Data Tier"]
            PostgreSQL[("PostgreSQL 15<br/>:5432")]
            Redis[("Redis 6.2+<br/>:6379")]
            RabbitMQ[("RabbitMQ 3.x<br/>:5672 / :15672")]
        end

        subgraph MonitoringTier["Monitoring Tier"]
            Prometheus["Prometheus<br/>:9090"]
            Grafana["Grafana<br/>:3000"]
        end
    end

    Users -->|"HTTPS :443"| Traefik

    Traefik -->|"PathPrefix(/)"| Frontend
    Traefik -->|"PathPrefix(/api)"| Backend
    Traefik -->|"PathPrefix(/grafana)"| Grafana
    Traefik -->|"Host(flower.*)"| Flower

    Frontend -->|"API calls"| Backend

    Backend --> PostgreSQL
    Backend --> Redis
    Backend --> RabbitMQ

    CeleryWorker --> PostgreSQL
    CeleryWorker --> Redis
    CeleryWorker --> RabbitMQ
    Flower --> RabbitMQ

    Prometheus -->|"Scrape metrics"| Backend
    Prometheus -->|"Scrape metrics"| CeleryWorker
    Grafana -->|"Query"| Prometheus
```

### Traefik Routing Rules

```mermaid
graph LR
    subgraph TraefikRouting["Traefik Route Resolution"]
        HTTPS["HTTPS :443"]
        HTTP["HTTP :80"]
    end

    HTTP -->|"301 Redirect"| HTTPS

    HTTPS -->|"PathPrefix(/api/v1)<br/>PathPrefix(/api/v2)<br/>PathPrefix(/docs)<br/>PathPrefix(/health)"| BackendRoute["Backend<br/>:7860"]
    HTTPS -->|"PathPrefix(/)"| FrontendRoute["Frontend<br/>:80"]
    HTTPS -->|"Host(pgadmin.*)"| PgAdminRoute["PgAdmin<br/>:5050"]
    HTTPS -->|"Host(flower.*)"| FlowerRoute["Flower<br/>:5555"]
    HTTPS -->|"PathPrefix(/grafana)"| GrafanaRoute["Grafana<br/>:3000"]
```

## Environments

### Development Environment

**Configuration**: `docker-compose.dev.yml` (5 services)

Local development uses a simplified Docker Compose setup with SQLite for zero-config database access. The frontend runs via Vite's dev server with hot module replacement.

```
┌───────────────────────────────────────────┐
│           Development Machine              │
│                                            │
│  ┌──────────────┐    ┌───────────────┐    │
│  │  Vite Dev    │    │   Uvicorn     │    │
│  │  Server      │    │   (--reload)  │    │
│  │  :5175       │    │    :8002      │    │
│  └──────────────┘    └───────────────┘    │
│                             │              │
│                      ┌──────┴──────┐       │
│                      │   SQLite    │       │
│                      │  (file DB)  │       │
│                      └─────────────┘       │
│                                            │
│  Optional (via docker-compose.dev.yml):    │
│  ┌─────────┐ ┌───────┐ ┌────────────┐    │
│  │  Redis  │ │RabbitMQ│ │   Celery   │    │
│  │  :6379  │ │ :5672  │ │   Worker   │    │
│  └─────────┘ └───────┘ └────────────┘    │
└───────────────────────────────────────────┘
```

**Start commands**:
```bash
# Backend (with hot reload)
cd langbuilder
uv run langbuilder run

# Frontend (separate terminal, with HMR)
cd langbuilder/src/frontend
npm run dev

# Optional: background services
cd langbuilder/deploy
docker compose -f docker-compose.dev.yml up -d
```

**Development services** (5):
| Service | Purpose |
|---------|---------|
| backend | FastAPI application with auto-reload |
| frontend | Vite dev server with HMR |
| redis | Cache and Celery result backend |
| rabbitmq | Celery message broker |
| celeryworker | Background task execution |

### Production Environment

**Configuration**: `docker-compose.yml` (11 services)
**Target**: AWS EC2 instance
**Entry Point**: Traefik v3 with automatic Let's Encrypt TLS

The production deployment runs all 11 services via Docker Compose on a single EC2 instance. Traefik handles TLS termination, routing, and load balancing.

**Production services** (11):
| Service | Image / Base | Purpose |
|---------|-------------|---------|
| proxy | Traefik v3 | Reverse proxy, TLS, routing |
| frontend | cloudgeometry/langbuilder-frontend | React app served by Nginx |
| backend | cloudgeometry/langbuilder-backend | FastAPI application |
| db | PostgreSQL 15 | Primary data store |
| redis | Redis 6.2+ | Cache, sessions, Celery results |
| rabbitmq | RabbitMQ 3.x | Celery message broker |
| celeryworker | cloudgeometry/langbuilder-backend | Background task workers |
| flower | Flower | Celery worker monitoring |
| prometheus | Prometheus | Metrics collection |
| grafana | Grafana | Metrics dashboards |
| pgadmin | PgAdmin | Database administration |

**Example simplified production docker-compose**:
```yaml
version: "3.8"
services:
  proxy:
    image: traefik:v3.0
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command:
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.le.acme.httpchallenge.entrypoint=web"

  frontend:
    image: cloudgeometry/langbuilder-frontend:latest
    labels:
      - "traefik.http.routers.frontend.rule=PathPrefix(`/`)"
      - "traefik.http.routers.frontend.priority=1"

  backend:
    image: cloudgeometry/langbuilder-backend:latest
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/langbuilder
      - REDIS_URL=redis://redis:6379/0
      - BROKER_URL=amqp://admin:admin@rabbitmq:5672//
    labels:
      - "traefik.http.routers.backend.rule=PathPrefix(`/api`)"
      - "traefik.http.routers.backend.priority=2"

  db:
    image: postgres:15
    volumes:
      - app-db-data:/var/lib/postgresql/data

  redis:
    image: redis:6.2-alpine

  rabbitmq:
    image: rabbitmq:3-management

  celeryworker:
    image: cloudgeometry/langbuilder-backend:latest
    command: celery -A langbuilder.worker worker -l info

  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  app-db-data:
  grafana_data:
```

## CI/CD Pipeline

LangBuilder uses GitHub Actions for continuous deployment. The pipeline is triggered manually via `workflow_dispatch` and deploys to an AWS EC2 instance over SSH.

```mermaid
graph LR
    subgraph GitHub["GitHub"]
        Trigger["Manual Trigger<br/>(workflow_dispatch)"]
        Actions["GitHub Actions<br/>(deployment.yml)"]
    end

    subgraph BuildStage["Build Stage"]
        Checkout["Checkout Code"]
        BuildBackend["Build Backend<br/>Docker Image"]
        BuildFrontend["Build Frontend<br/>Docker Image"]
        PushImages["Push Images to<br/>Docker Hub"]
    end

    subgraph DeployStage["Deploy Stage"]
        SSH["SSH to<br/>AWS EC2"]
        Pull["Pull Latest<br/>Images"]
        Compose["docker compose<br/>up -d"]
        Health["Health Check<br/>Verification"]
    end

    subgraph DockerHub["Docker Hub"]
        BackendImage["cloudgeometry/<br/>langbuilder-backend"]
        FrontendImage["cloudgeometry/<br/>langbuilder-frontend"]
    end

    Trigger --> Actions
    Actions --> Checkout
    Checkout --> BuildBackend
    Checkout --> BuildFrontend
    BuildBackend --> PushImages
    BuildFrontend --> PushImages
    PushImages --> BackendImage
    PushImages --> FrontendImage
    PushImages --> SSH
    SSH --> Pull
    Pull --> Compose
    Compose --> Health
```

### Pipeline Configuration

**Workflow file**: `.github/workflows/deployment.yml`

| Stage | Action | Details |
|-------|--------|---------|
| **Trigger** | `workflow_dispatch` | Manual trigger from GitHub UI or API; no automatic triggers on push/PR |
| **Build** | Docker multi-stage build | Backend and frontend images built from their respective Dockerfiles |
| **Push** | Docker Hub | Images pushed to `cloudgeometry/langbuilder-backend` and `cloudgeometry/langbuilder-frontend` |
| **Deploy** | SSH to EC2 | Connect to production EC2 instance via SSH, pull latest images, restart services |
| **Verify** | Health check | Confirm `/health` endpoint responds successfully after deployment |

### Deployment Flow

1. Developer triggers the `deployment.yml` workflow manually from the GitHub Actions UI
2. GitHub Actions checks out the code and builds Docker images using multi-stage Dockerfiles
3. Built images are pushed to Docker Hub under the `cloudgeometry` organization
4. The workflow SSHs into the AWS EC2 production instance
5. On the EC2 instance, `docker compose pull` fetches the latest images
6. `docker compose up -d` restarts services with the new images (zero-downtime via Traefik health checks)
7. A health check verifies the deployment was successful

## Infrastructure Components

| Component | Technology | Version | Port(s) | Purpose |
|-----------|------------|---------|---------|---------|
| **Reverse Proxy** | Traefik | v3.0 | 80, 443 | TLS termination, routing, load balancing, Let's Encrypt |
| **Frontend** | React + Nginx | - | 80 | Static SPA serving |
| **Backend API** | FastAPI + Uvicorn | 0.115+ | 7860 | REST API, WebSocket, graph execution |
| **Database** | PostgreSQL | 15 | 5432 | Primary data store (10 models, 50 Alembic migrations) |
| **Cache** | Redis | 6.2+ | 6379 | Application cache, session store, Celery result backend |
| **Message Broker** | RabbitMQ | 3.x | 5672, 15672 | Celery task distribution, management UI |
| **Task Workers** | Celery | latest | - | Background task execution (uses backend image) |
| **Worker Monitor** | Flower | latest | 5555 | Celery worker monitoring and management |
| **Metrics** | Prometheus | latest | 9090 | Metrics collection and storage |
| **Dashboards** | Grafana | latest | 3000 | Metrics visualization and alerting |
| **DB Admin** | PgAdmin | latest | 5050 | PostgreSQL administration UI |

## Docker Images

### Backend Image

**Image**: `cloudgeometry/langbuilder-backend:latest`
**Registry**: Docker Hub
**Build**: Multi-stage Dockerfile

```dockerfile
# Build stage
FROM python:3.11-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY langbuilder/ ./langbuilder/
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 7860
CMD ["uvicorn", "langbuilder.main:app", "--host", "0.0.0.0", "--port", "7860"]
```

**Characteristics**:
- Multi-stage build separates dependency installation from runtime
- Uses `uv` for fast, reproducible dependency resolution
- Same image is used for both the backend API and Celery workers (different CMD)
- Exposes port 7860 for the FastAPI application

### Frontend Image

**Image**: `cloudgeometry/langbuilder-frontend:latest`
**Registry**: Docker Hub
**Build**: Multi-stage Dockerfile

```dockerfile
# Build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

**Characteristics**:
- Multi-stage build compiles TypeScript and bundles assets with Vite + SWC
- Production stage uses Nginx Alpine for minimal image size
- Static assets are served directly by Nginx
- Nginx configuration handles SPA routing (fallback to index.html)

## Service Configuration

### Environment Variables

**Backend (required)**:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/langbuilder
SQLMODEL_MIGRATE_URL=postgresql://user:pass@db:5432/langbuilder

# Redis
REDIS_URL=redis://redis:6379/0

# RabbitMQ / Celery
BROKER_URL=amqp://admin:admin@rabbitmq:5672//

# Application
BACKEND_PORT=7860
SECRET_KEY=<generated-secret>
LANGBUILDER_AUTO_LOGIN=false
LANGBUILDER_SUPERUSER=admin@example.com
LANGBUILDER_SUPERUSER_PASSWORD=<password>
```

**Backend (optional -- LLM providers)**:
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
```

**Frontend**:
```bash
VITE_BACKEND_URL=https://api.example.com
```

**Traefik**:
```bash
DOMAIN=langbuilder.example.com
TRAEFIK_PUBLIC_NETWORK=traefik-public
TRAEFIK_TAG=langbuilder
STACK_NAME=langbuilder
```

### TLS Configuration

Traefik handles TLS automatically via Let's Encrypt:

```yaml
# Let's Encrypt automatic certificate provisioning
- traefik.http.routers.proxy-https.tls=true
- traefik.http.routers.proxy-https.tls.certresolver=le

# HTTP to HTTPS redirect
- traefik.http.middlewares.https-redirect.redirectscheme.scheme=https
```

## Health Checks

All critical services include Docker-level health checks:

```yaml
# Backend
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:7860/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s

# PostgreSQL
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 10s
  timeout: 5s
  retries: 5

# Redis
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5

# RabbitMQ
healthcheck:
  test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## Persistent Volumes

```yaml
volumes:
  app-db-data:        # PostgreSQL data directory
  redis-data:         # Redis RDB/AOF persistence
  rabbitmq_data:      # RabbitMQ mnesia database
  rabbitmq_log:       # RabbitMQ logs
  grafana_data:       # Grafana dashboards and config
  pgadmin-data:       # PgAdmin server definitions
```

### Backup Strategy

```bash
# PostgreSQL database dump
docker exec db pg_dump -U postgres langbuilder > backup_$(date +%Y%m%d).sql

# Redis snapshot
docker exec redis redis-cli BGSAVE

# Full volume backup
docker run --rm -v app-db-data:/data -v $(pwd):/backup \
  alpine tar cvf /backup/db-backup-$(date +%Y%m%d).tar /data
```

## Scaling Considerations

### Horizontal Scaling

| Component | Strategy | Notes |
|-----------|----------|-------|
| **Frontend** | Add container replicas | Stateless Nginx containers; Traefik load balances automatically |
| **Backend** | Add container replicas | Stateless; requires shared Redis for sessions and PostgreSQL for data |
| **Celery Workers** | Add worker containers | Scale independently based on task queue depth |
| **PostgreSQL** | Read replicas | Write to primary only; read replicas for query scaling |
| **Redis** | Sentinel / Cluster | For high-availability and horizontal read scaling |
| **RabbitMQ** | Cluster with mirrored queues | For message persistence and broker HA |

### Resource Requirements

**Minimum (Development)**:
| Component | CPU | Memory |
|-----------|-----|--------|
| Backend | 0.5 | 512 MB |
| Frontend | 0.25 | 256 MB |
| Database | 0.5 | 512 MB |
| Redis | 0.25 | 256 MB |
| **Total** | **1.5** | **1.5 GB** |

**Recommended (Production)**:
| Component | CPU | Memory | Instances |
|-----------|-----|--------|-----------|
| Traefik | 0.5 | 256 MB | 1 |
| Backend | 2 | 2 GB | 2 - 4 |
| Frontend | 0.5 | 512 MB | 2 |
| Celery Workers | 2 | 2 GB | 2 - 4 |
| PostgreSQL | 4 | 4 GB | 1 (+ replicas) |
| Redis | 1 | 1 GB | 1 |
| RabbitMQ | 1 | 1 GB | 1 |
| Prometheus | 0.5 | 512 MB | 1 |
| Grafana | 0.5 | 256 MB | 1 |
| **Total** | **12+** | **12 GB+** | - |

## Deployment Checklist

### Pre-deployment

- [ ] Environment variables configured in `.env` file on EC2
- [ ] Database migrations applied (`alembic upgrade head`)
- [ ] SSL domain DNS pointing to EC2 instance
- [ ] Docker and Docker Compose installed on EC2
- [ ] Secrets (SECRET_KEY, DB passwords) generated and stored securely
- [ ] Monitoring dashboards imported into Grafana

### Post-deployment

- [ ] `/health` endpoint returning 200
- [ ] TLS certificate valid and auto-renewing
- [ ] Database connectivity verified
- [ ] Celery workers consuming from RabbitMQ queues
- [ ] Prometheus scraping metrics from backend and workers
- [ ] Grafana dashboards populating with data
- [ ] Flower UI accessible and showing active workers

---

*Generated by CloudGeometry AIx SDLC - Architecture Documentation*
