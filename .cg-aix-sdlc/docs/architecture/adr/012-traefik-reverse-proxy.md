# ADR-012: Traefik v3 for Reverse Proxy

## Status

Accepted

## Date

2026-02-09

## Decision Makers

- LangBuilder Development Team

## Context

### Problem Statement

LangBuilder's production deployment consists of multiple services (frontend, backend API, Flower, Grafana, PgAdmin) that need to be exposed to users through a single entry point with TLS termination, path-based routing, and load balancing. The reverse proxy must route requests to the correct service based on URL path or hostname, terminate TLS with automatic certificate provisioning, load balance across multiple backend and frontend replicas, and provide operational visibility into routing configuration. The deployment is Docker-based, and the proxy should integrate natively with Docker to minimize manual configuration.

### Constraints

- Must integrate natively with Docker and Docker Compose for automatic service discovery
- Must support automatic TLS certificate provisioning via Let's Encrypt
- Must support path-based and host-based routing rules
- Must support WebSocket proxying (required for LLM token streaming)
- Must support health check-based load balancing
- Must provide a dashboard for routing visibility and debugging
- Must have minimal resource footprint compared to the services it proxies

### Requirements

- Automatic service discovery from Docker container labels
- Let's Encrypt TLS certificate provisioning and renewal
- HTTP to HTTPS redirect
- Path-based routing (`/api/v1/*` to backend, `/*` to frontend)
- Host-based routing (`flower.domain.com`, `pgadmin.domain.com`)
- Load balancing across replicated services
- WebSocket support for real-time streaming
- Dashboard for route inspection
- Docker-native configuration (no external config files for service registration)

## Decision

Use Traefik v3 as the reverse proxy and load balancer for LangBuilder's production deployment. Traefik is configured entirely through Docker container labels, automatically discovering services and generating routing rules without manual configuration files for service registration. TLS certificates are provisioned automatically via Let's Encrypt's ACME protocol. The routing configuration routes API traffic to backend replicas, serves the frontend SPA, and provides access to monitoring tools (Grafana, Flower, PgAdmin) via subdomain or path-based rules.

Traefik was chosen because its Docker-native service discovery eliminates the configuration synchronization problem that occurs with traditional reverse proxies: when a new service is added or replicas are scaled, Traefik automatically detects the change and updates its routing table without manual intervention or configuration reload.

## Consequences

### Positive

- Docker-native service discovery means adding or scaling a service requires only adding Docker labels to the container definition; Traefik automatically updates routing without manual configuration or reload
- Automatic Let's Encrypt TLS certificate provisioning and renewal eliminates manual certificate management
- HTTP to HTTPS redirect is configured with a single middleware label
- WebSocket support is built-in, enabling transparent proxying of LLM token streaming connections
- The Traefik dashboard provides real-time visibility into active routers, services, middlewares, and their health status
- Traefik's resource footprint is small compared to Nginx (single binary, low memory usage)
- Configuration as Docker labels keeps routing rules co-located with the service definitions in `docker-compose.yml`

### Negative

- Traefik's Docker label-based configuration syntax is less familiar to teams experienced with Nginx's configuration file format
- Debugging routing issues requires understanding Traefik's router/service/middleware abstraction, which has a learning curve
- Traefik v3 is newer than Nginx, with fewer production deployment examples and Stack Overflow answers
- Advanced routing scenarios (complex regex matching, request body inspection) are less straightforward than in Nginx
- Traefik's dashboard, while useful, must be secured (authentication middleware) to prevent exposing routing internals

### Neutral

- Traefik replaces the need for Nginx or HAProxy in the deployment stack
- The Let's Encrypt integration requires port 80 and 443 to be accessible for the ACME HTTP-01 challenge
- Traefik's configuration can also be done via file, Consul, or etcd in addition to Docker labels, providing flexibility for future deployment changes

## Alternatives Considered

### Nginx

**Pros**: Industry standard reverse proxy with extensive documentation, massive community, proven performance at scale, well-understood configuration format, extensive module ecosystem, widely deployed in production
**Cons**: Configuration is file-based and must be manually synchronized with service changes; no automatic service discovery from Docker; TLS certificate management requires additional tooling (certbot, cert-manager); configuration changes require reload; no built-in dashboard for routing visibility
**Why not chosen**: Nginx's file-based configuration does not integrate with Docker's dynamic nature. Adding a new service or scaling replicas requires manually updating Nginx configuration and reloading, which introduces a configuration synchronization problem. Traefik's Docker-native discovery eliminates this operational burden.

### Caddy

**Pros**: Automatic HTTPS by default, simple configuration syntax (Caddyfile), good performance, built-in Let's Encrypt support, modern design with fewer legacy concerns
**Cons**: Smaller community than Nginx or Traefik; Docker integration is less mature than Traefik's (requires API plugin or file-based config); less granular control over routing and middleware; fewer production deployment examples for complex multi-service architectures
**Why not chosen**: While Caddy's simplicity and automatic HTTPS are appealing, its Docker integration is less mature than Traefik's label-based discovery. For a multi-service Docker Compose deployment where services are frequently added or scaled, Traefik's native Docker integration provides a better operational experience.

### HAProxy

**Pros**: Extremely high performance, battle-tested in high-traffic environments, detailed health checking, sophisticated load balancing algorithms, stable and reliable
**Cons**: Configuration is complex and file-based; no automatic service discovery; no built-in Let's Encrypt integration; no dashboard (requires separate tools like HAProxy Stats or Dataplane API); designed for high-throughput scenarios that exceed LangBuilder's current scale
**Why not chosen**: HAProxy's performance characteristics are designed for scales far beyond LangBuilder's current needs (100+ concurrent users). Its file-based configuration and lack of Docker integration or automatic TLS provisioning add operational complexity without proportional benefit.

### AWS Application Load Balancer (ALB)

**Pros**: Fully managed by AWS, no infrastructure to maintain, automatic scaling, AWS Certificate Manager integration, path-based routing, WebSocket support
**Cons**: AWS-specific, creating vendor lock-in; monthly cost regardless of traffic; configuration via AWS console or Terraform, not co-located with application code; adds latency for same-VPC traffic; does not work in non-AWS environments (local development, on-premises)
**Why not chosen**: LangBuilder supports deployment on any Docker-compatible infrastructure, not just AWS. Tying the reverse proxy to AWS ALB would prevent deployment on other cloud providers, on-premises, or local development Docker environments. Traefik's portability across all Docker environments aligns with the project's deployment flexibility goals.

## Implementation Notes

- Traefik is configured as the first service in the Docker Compose stack, binding to ports 80 and 443
- Service routing rules are defined as Docker labels on each service container:
  - Backend: `traefik.http.routers.backend.rule=PathPrefix('/api/v1') || PathPrefix('/api/v2') || PathPrefix('/docs') || PathPrefix('/health')`
  - Frontend: `traefik.http.routers.frontend.rule=PathPrefix('/')`
  - Flower: `traefik.http.routers.flower.rule=Host('flower.${DOMAIN}')`
  - PgAdmin: `traefik.http.routers.pgadmin.rule=Host('pgadmin.${DOMAIN}')`
  - Grafana: `traefik.http.routers.grafana.rule=PathPrefix('/grafana')`
- Let's Encrypt certificates are provisioned via the `le` certificate resolver with HTTP-01 challenge
- HTTPS redirect middleware is applied globally: `traefik.http.middlewares.https-redirect.redirectscheme.scheme=https`
- Traefik dashboard is accessible for routing debugging but should be secured with basic auth middleware in production
- Environment variables `DOMAIN`, `TRAEFIK_PUBLIC_NETWORK`, `TRAEFIK_TAG`, and `STACK_NAME` configure the deployment

## Related Decisions

- [ADR-002](002-fastapi-backend-api.md) - FastAPI backend traffic is routed through Traefik
- [ADR-011](011-celery-rabbitmq-redis-task-queue.md) - Flower monitoring dashboard is exposed through Traefik
- [ADR-015](015-docker-multi-stage-builds.md) - Docker containers are the deployment units that Traefik discovers

## References

- https://doc.traefik.io/traefik/
- https://doc.traefik.io/traefik/providers/docker/
- https://doc.traefik.io/traefik/https/acme/
- https://letsencrypt.org/
