# ADR-001: UV Workspace Monorepo

## Status

Accepted

## Date

2026-02-09

## Decision Makers

- LangBuilder Development Team

## Context

### Problem Statement

LangBuilder consists of multiple Python packages that need to be developed, tested, and released together. The core platform is split into two primary packages -- `langbuilder` (the main application) and `langbuilder-base` (shared base classes, component abstractions, and utilities). Additionally, 96 component packages depend on `langbuilder-base`. The project needs a package management and workspace solution that can handle inter-package dependencies, provide fast dependency resolution, and support a productive development workflow across all packages simultaneously.

### Constraints

- Python 3.10 through 3.14 compatibility required
- Must support editable installs for local development across multiple packages
- Must handle complex dependency trees including LangChain ecosystem packages with many transitive dependencies
- Build and CI times need to remain manageable despite the large number of packages
- Team members need reproducible environments across development machines and CI

### Requirements

- Unified workspace management for multiple Python packages
- Fast dependency resolution and installation
- Lock file support for reproducible builds
- Editable (development mode) installs for cross-package development
- Compatible with `pyproject.toml` standards (PEP 621)
- Fast enough for CI pipelines without caching workarounds

## Decision

Use UV (by Astral) as the Python package manager and workspace tool for the LangBuilder monorepo. The workspace is configured in the root `pyproject.toml` with two member packages: `langbuilder` and `langbuilder-base`. UV manages dependency resolution, lock file generation (`uv.lock`), virtual environment creation, and script execution across all workspace members.

UV was chosen because it provides orders-of-magnitude faster dependency resolution and package installation compared to pip and Poetry, while supporting the workspace model needed for multi-package development. Its Rust-based resolver handles the complex dependency graph (including LangChain's extensive transitive dependencies) in seconds rather than minutes.

## Consequences

### Positive

- Dependency resolution is 10-100x faster than pip or Poetry, significantly reducing CI times and developer wait time
- Native workspace support allows `langbuilder` and `langbuilder-base` to reference each other as path dependencies without publishing to PyPI during development
- The `uv.lock` file provides fully reproducible installs across all environments
- UV supports standard `pyproject.toml` configuration, avoiding lock-in to proprietary configuration formats
- Single command (`uv sync`) sets up the entire workspace with all dependencies

### Negative

- UV is a relatively young tool (first stable release in 2024) with a smaller community and fewer Stack Overflow answers compared to pip or Poetry
- Team members must install UV separately; it is not bundled with Python
- Some edge cases in dependency resolution may differ from pip, requiring occasional debugging
- Docker images need UV installed as an additional build step

### Neutral

- UV replaces both pip and Poetry as the package management tool, consolidating tooling
- The `uv.lock` file format is UV-specific, though packages remain installable via standard pip if needed
- Component packages (96 total) are managed outside the UV workspace as independently installable packages that depend on `langbuilder-base`

## Alternatives Considered

### Poetry with Monorepo Plugin

**Pros**: Mature ecosystem, well-documented, widely adopted in the Python community, built-in virtual environment management, deterministic lock files
**Cons**: Slow dependency resolution (minutes for large dependency trees like LangChain), monorepo/workspace support requires third-party plugins (`poetry-monorepo-plugin`) that are not officially maintained, does not fully support PEP 621 `pyproject.toml` format
**Why not chosen**: Poetry's dependency resolver performance was unacceptable for the size of LangBuilder's dependency tree. Workspace support via plugins was fragile and introduced additional maintenance burden.

### pip + pip-tools

**Pros**: Standard Python tooling with no additional installation, widely understood, `pip-compile` provides lock file generation
**Cons**: No native workspace concept, manual management of inter-package dependencies, slow resolution, no built-in virtual environment management, requires separate tools for each concern (pip, pip-tools, venv)
**Why not chosen**: The lack of workspace support and the need to manually coordinate multiple packages made this approach error-prone and operationally complex for a monorepo with inter-dependent packages.

### PDM

**Pros**: PEP 621 compliant, supports workspaces natively, faster than Poetry, good lock file support
**Cons**: Smaller community than Poetry or pip, resolution speed still significantly slower than UV, less mature ecosystem of plugins and integrations
**Why not chosen**: While PDM was a viable option with good workspace support, UV's dramatically faster resolution speed and growing momentum in the Python ecosystem made it the stronger choice for a project of LangBuilder's scale.

## Implementation Notes

- The root `pyproject.toml` defines the workspace with `[tool.uv.workspace]` containing member paths
- `langbuilder-base` is listed as a path dependency in `langbuilder`'s `pyproject.toml`
- CI pipelines use `uv sync` for dependency installation, which respects the lock file
- Docker builds install UV via `pip install uv` in the build stage, then use `uv sync` to install dependencies
- Developers run the application with `uv run langbuilder run` which automatically activates the correct virtual environment

## Related Decisions

- [ADR-015](015-docker-multi-stage-builds.md) - Docker builds must install UV and use `uv sync` for reproducible container images

## References

- https://docs.astral.sh/uv/
- https://docs.astral.sh/uv/concepts/workspaces/
- https://peps.python.org/pep-0621/ - PEP 621: Storing project metadata in pyproject.toml
