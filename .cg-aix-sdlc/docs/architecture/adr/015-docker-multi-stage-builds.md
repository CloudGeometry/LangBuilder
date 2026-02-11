# ADR-015: Docker Multi-Stage Builds

## Status

Accepted

## Date

2026-02-09

## Decision Makers

- LangBuilder Development Team

## Context

### Problem Statement

LangBuilder must be packaged and deployed as container images for staging and production environments. The project has two primary images: a backend image (Python/FastAPI with LangChain and all component dependencies) and a frontend image (static React assets served by Nginx). Container images must be optimized for size (to reduce pull times and storage costs), security (to minimize the attack surface by excluding build tools from runtime images), and reproducibility (to ensure identical builds across CI and deployment environments). Naive single-stage Dockerfiles produce images that include build tools, compilers, and intermediate artifacts that are not needed at runtime.

### Constraints

- Backend image must include Python runtime, UV package manager, all pip dependencies, and the application code
- Frontend image must include only the static build output (HTML, CSS, JS) and a web server
- Images must not include build tools, source code, or development dependencies in the final layer
- Build times must be reasonable for CI pipelines (under 10 minutes for a full rebuild)
- Images must be reproducible: building from the same source and lock files must produce functionally identical images
- Images must support the `linux/amd64` platform (AWS EC2 deployment target)

### Requirements

- Separate build and runtime stages to minimize final image size
- Exclude build tools, compilers, and development dependencies from production images
- Reproducible builds using lock files (`uv.lock` for backend, `package-lock.json` for frontend)
- Layer caching for dependency installation (dependencies change less frequently than application code)
- Health check configuration built into the images
- Non-root user execution for security
- Consistent base images (pinned versions) for reproducibility

## Decision

Use Docker multi-stage builds for both the backend and frontend container images. Multi-stage builds use separate `FROM` stages for building and running: the build stage includes compilers, build tools, and development dependencies; the final stage copies only the runtime artifacts (installed packages, compiled assets) into a minimal base image. This produces optimized images that contain only what is needed at runtime.

Multi-stage builds were chosen because they provide a clean separation between the build environment and the runtime environment, producing smaller and more secure images without requiring complex build scripts or external build tools. The Dockerfile itself serves as both the build recipe and the deployment specification.

## Consequences

### Positive

- Final images contain only runtime dependencies, dramatically reducing image size (frontend: from ~1GB build stage to ~50MB Nginx stage; backend: significant reduction by excluding build tools)
- Excluding build tools (compilers, linkers, package managers) from the final image reduces the attack surface for security vulnerabilities
- Layer caching ensures that dependency installation (the slowest step) is cached and only re-executed when `pyproject.toml`/`uv.lock` or `package.json`/`package-lock.json` change
- Reproducible builds: lock files (`uv.lock`, `package-lock.json`) ensure the same dependency versions are installed in every build
- The Dockerfile is self-contained: no external build scripts, CI-specific logic, or manual steps needed
- Multi-stage builds are a Docker-native feature supported by all Docker-compatible runtimes (Docker, Podman, Buildah, Kaniko)

### Negative

- Multi-stage Dockerfiles are more complex to read and debug than single-stage Dockerfiles
- Build context must include all files needed by all stages, which can lead to large build context transfers if `.dockerignore` is not carefully maintained
- Debugging the final image is harder because build tools (e.g., `pip`, `npm`, `curl`) are not present; debugging requires either adding tools temporarily or using multi-stage debug targets
- Cache invalidation can be surprising: changing a file early in the COPY chain invalidates all subsequent layers, potentially rebuilding dependencies unnecessarily

### Neutral

- The backend uses `python:3.11-slim` as the base image, balancing image size with library compatibility (some Python packages require system libraries present in `slim` but not `alpine`)
- The frontend uses `node:20-alpine` for the build stage and `nginx:alpine` for the runtime stage
- Docker Compose orchestrates both images alongside PostgreSQL, Redis, RabbitMQ, and supporting services
- GitHub Actions CI builds and pushes images to the container registry using `docker build` with build caching

## Alternatives Considered

### Single-Stage Dockerfile

**Pros**: Simpler Dockerfile with a single `FROM` instruction; easier to read and debug; build tools remain available in the image for troubleshooting
**Cons**: Final image includes build tools, compilers, source code, and intermediate build artifacts, resulting in significantly larger images (2-5x larger); larger attack surface due to unnecessary binaries; slower image pulls; wasted storage on registries and hosts
**Why not chosen**: The image size and security implications of including build tools in production images were unacceptable. A single-stage backend image with all build tools would be 2-3GB versus ~1GB with multi-stage; the frontend image would be ~1GB versus ~50MB.

### External Build Pipeline (Build Outside Docker)

**Pros**: Full control over the build environment; can use CI-native tools (e.g., install Python/Node directly on the CI runner); potentially faster builds without Docker overhead; easy debugging
**Cons**: Not reproducible: builds depend on the CI runner's environment (OS, installed packages, versions); different CI runners may produce different results; developers cannot reproduce CI builds locally; requires maintaining separate build scripts alongside Dockerfiles
**Why not chosen**: Reproducibility is a core requirement. Building outside Docker means the build environment varies between CI runners, developer machines, and deployment targets. Docker multi-stage builds provide a self-contained, reproducible build environment that works identically everywhere.

### Buildpacks (Cloud Native Buildpacks)

**Pros**: Automatic image creation without a Dockerfile; opinionated best practices for image structure; built-in support for common languages (Python, Node.js); reproducible by design; automatic security patching of base images
**Cons**: Less control over image contents and structure; buildpack customization is more complex than Dockerfile customization; smaller community and tooling ecosystem; may not support LangBuilder's specific build requirements (UV package manager, multi-package workspace); debugging is harder when the build process is abstracted
**Why not chosen**: Cloud Native Buildpacks abstract away the build process, which limits control over image structure. LangBuilder's build requires UV for Python package management and specific multi-stage optimizations (separating dependency installation from code copy) that are difficult to achieve with buildpacks.

### Nix / Nix Flakes

**Pros**: Extremely reproducible builds; declarative package management; precise dependency specification; excellent caching; cross-compilation support
**Cons**: Steep learning curve for the Nix language and ecosystem; small community compared to Docker; limited Docker integration (can produce Docker images but the workflow is unconventional); debugging Nix derivations requires specialized knowledge; team would need Nix expertise
**Why not chosen**: Nix's learning curve and specialized expertise requirements were prohibitive. Docker multi-stage builds provide sufficient reproducibility (via lock files) with a significantly lower barrier to entry for the development team.

## Implementation Notes

- **Backend Dockerfile** (`langbuilder/deploy/Dockerfile`):
  - Stage 1: `python:3.11-slim` base; install UV, copy `pyproject.toml` and `uv.lock`, run `uv sync` to install dependencies
  - Stage 2: `python:3.11-slim` base; copy installed packages from Stage 1; copy application source; expose port 7860; run Uvicorn
- **Frontend Dockerfile**:
  - Stage 1 (build): `node:20-alpine` base; copy `package*.json`, run `npm ci`; copy source, run `npm run build`
  - Stage 2 (runtime): `nginx:alpine` base; copy `dist/` from Stage 1 to Nginx html directory; copy custom `nginx.conf`; expose port 80
- Layer ordering optimizes caching: dependency files are copied first (they change infrequently), then source code (changes frequently)
- `.dockerignore` excludes `node_modules`, `__pycache__`, `.git`, `*.pyc`, and other non-essential files from the build context
- Docker Compose defines health checks for each container (HTTP for backend, `pg_isready` for PostgreSQL, `redis-cli ping` for Redis)
- Images are tagged with both `latest` and the git commit SHA for traceability
- GitHub Actions CI uses Docker layer caching (`actions/cache` with Docker buildx) to speed up builds

## Related Decisions

- [ADR-001](001-uv-workspace-monorepo.md) - UV is installed in the Docker build stage for Python dependency management
- [ADR-002](002-fastapi-backend-api.md) - The backend Dockerfile runs Uvicorn as the entrypoint
- [ADR-010](010-vite-swc-build-tooling.md) - `npm run build` (Vite) produces the frontend static assets in the build stage
- [ADR-012](012-traefik-reverse-proxy.md) - Traefik discovers and routes traffic to the containerized services

## References

- https://docs.docker.com/build/building/multi-stage/
- https://docs.docker.com/develop/develop-images/dockerfile_best-practices/
- https://docs.docker.com/compose/
- https://github.com/features/actions - GitHub Actions CI/CD
