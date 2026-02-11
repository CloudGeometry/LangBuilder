# Configuration Index

Comprehensive index of all configuration options across the LangBuilder monorepo (FastAPI backend + React frontend + OpenWebUI integration).

---

## Environment Variables

### Defined in `.env.example`

Root `.env.example` at project root. This is the primary configuration template for local development.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama LLM backend URL |
| `OPENAI_API_BASE_URL` | No | (empty) | OpenAI-compatible API base URL |
| `OPENAI_API_KEY` | No | (empty) | OpenAI API key |
| `FRONTEND_PORT` | No | `5175` | Frontend dev server port |
| `BACKEND_PORT` | No | `8002` | Backend API port |
| `OPEN_WEBUI_PORT` | No | `8767` | Open WebUI port |
| `CORS_ALLOW_ORIGIN` | No | `http://localhost:${FRONTEND_PORT};http://localhost:${BACKEND_PORT}` | CORS allowed origins (semicolon-separated) |
| `FORWARDED_ALLOW_IPS` | No | `*` | Proxy allowed IPs |
| `SCARF_NO_ANALYTICS` | No | `true` | Disable Scarf analytics |
| `DO_NOT_TRACK` | No | `true` | Do not track flag |
| `ANONYMIZED_TELEMETRY` | No | `false` | Disable anonymized telemetry |
| `GOOGLE_CLIENT_ID` | Yes (if OAuth) | (placeholder) | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes (if OAuth) | (placeholder) | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | Yes (if OAuth) | `http://localhost:${BACKEND_PORT}/oauth/google/callback` | Google OAuth callback URI |
| `GOOGLE_DRIVE_CLIENT_ID` | No | (placeholder) | Google Drive integration client ID |
| `GOOGLE_DRIVE_CLIENT_SECRET` | No | (placeholder) | Google Drive integration client secret |
| `GOOGLE_WORKSPACE_DOMAIN` | No | `actionbridge.com` | Google Workspace domain |
| `GOOGLE_WORKSPACE_ADMIN_EMAIL` | No | `admin@actionbridge.com` | Google Workspace admin email |
| `GOOGLE_SERVICE_ACCOUNT_KEY_FILE` | No | `/app/secrets/google-service-account.json` | Google service account key file path |
| `GOOGLE_DRIVE_TOKEN` | No | (placeholder) | Google Drive access token |
| `GOOGLE_DRIVE_USER_ID` | No | (placeholder) | Google Drive user ID |
| `GOOGLE_DRIVE_AGENT_URL` | No | `http://localhost:8000/process` | Google Drive agent endpoint URL |
| `GOOGLE_DRIVE_AGENT_PATH` | No | (path) | Google Drive agent installation path |
| `ZOHO_CLIENT_ID` | Yes (if Zoho) | (placeholder) | Zoho OAuth client ID |
| `ZOHO_CLIENT_SECRET` | Yes (if Zoho) | (placeholder) | Zoho OAuth client secret |
| `ZOHO_REDIRECT_URI` | Yes (if Zoho) | `http://localhost:${BACKEND_PORT}/api/v1/services/zoho/callback` | Zoho OAuth callback URI |
| `WEBUI_SECRET_KEY` | Yes | (placeholder) | Application secret key for JWT signing |
| `JWT_EXPIRES_IN` | No | `24h` | JWT expiration time |
| `WEBUI_SESSION_COOKIE_SAME_SITE` | No | `lax` | Session cookie SameSite policy |
| `WEBUI_SESSION_COOKIE_SECURE` | No | `false` | Session cookie Secure flag |
| `DATA_DIR` | No | `./data` | Data directory path |
| `DATABASE_URL` | No | `sqlite:///./data/webui.db` | Database connection string |
| `WEBUI_NAME` | No | `ActionBridge` | Application display name |
| `GLOBAL_LOG_LEVEL` | No | `DEBUG` | Global logging level |
| `OPENID_PROVIDER_URL` | No | `https://accounts.google.com/.well-known/openid_configuration` | Google OpenID endpoint |
| `CORPORATE_AUTH_CONFIG` | No | `/app/corporate_config.json` | Path to corporate auth config file |
| `CORPORATE_GROUP_MAPPINGS` | No | (JSON string) | JSON group-to-role mappings |
| `ENABLE_OAUTH_SIGNUP` | No | `true` | Enable OAuth signup |
| `ENABLE_SIGNUP` | No | `true` | Enable user signup |
| `ENABLE_LOGIN_FORM` | No | `true` | Enable login form |
| `ENABLE_API_KEY` | No | `true` | Enable API key authentication |
| `OAUTH_ALLOWED_DOMAINS` | No | `*` | OAuth allowed domains |
| `OAUTH_MERGE_ACCOUNTS_BY_EMAIL` | No | `true` | Merge OAuth accounts by email |
| `OAUTH_UPDATE_PICTURE_ON_LOGIN` | No | `true` | Update avatar on OAuth login |
| `KMS_MASTER_KEY` | Yes | (base64 encoded) | Encryption master key (base64 encoded) |
| `WEBUI_URL` | No | `http://localhost:${FRONTEND_PORT}` | Application base URL |
| `PORT` | No | `8767` | Server port (OpenWebUI backend) |
| `HOST` | No | `0.0.0.0` | Server bind address |

Source: `.env.example`

---

### Docker Environment Variables

From `.env.docker.example` -- adaptations for Docker networking and containerized development.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LANGBUILDER_DATABASE_URL` | No | `postgresql://langbuilder:langbuilder@postgres:5432/langbuilder` | PostgreSQL connection for Docker |
| `DATABASE_URL` | No | `sqlite:///./data/webui.db` | OpenWebUI database URL |
| `DATA_DIR` | No | `./data` | Data directory |
| `OLLAMA_BASE_URL` | No | `http://host.docker.internal:11434` | Ollama URL (Docker host networking) |
| `OPENAI_API_BASE_URL` | No | (empty) | OpenAI API base URL |
| `OPENAI_API_KEY` | No | (placeholder) | OpenAI API key |
| `FRONTEND_PORT` | No | `5175` | Frontend host port |
| `BACKEND_PORT` | No | `8002` | Backend host port |
| `OPEN_WEBUI_PORT` | No | `8767` | OpenWebUI host port |
| `VITE_PORT` | No | `3000` | Frontend dev port inside Docker |
| `VITE_PROXY_TARGET` | No | `http://langbuilder-backend:8002` | Backend proxy target (Docker service name) |
| `LANGBUILDER_BACKEND_PORT` | No | `8002` | Backend port for LangBuilder service |
| `PORT` | No | `8767` | OpenWebUI server port |
| `HOST` | No | `0.0.0.0` | Server bind address |
| `CORS_ALLOW_ORIGIN` | No | `http://localhost:5175;http://localhost:8002;http://localhost:3000;http://localhost:8767` | CORS allowed origins |
| `FORWARDED_ALLOW_IPS` | No | `*` | Proxy allowed IPs |
| `ENV` | No | `dev` | Environment mode |
| `NODE_ENV` | No | `development` | Node environment |
| `PYTHONUNBUFFERED` | No | `1` | Python output unbuffered |
| `LOG_LEVEL` | No | `debug` | Logging level |
| `WEBUI_NAME` | No | `LangBuilder` | Application display name |

Source: `.env.docker.example`

---

### Deployment Environment Variables

From `langbuilder/deploy/.env.example` -- production deployment with Docker Swarm/Compose stack.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DOMAIN` | No | `localhost` | Deployment domain |
| `STACK_NAME` | No | `langbuilder-stack` | Docker stack name |
| `TRAEFIK_PUBLIC_NETWORK` | No | `traefik-public` | Traefik public network name |
| `TRAEFIK_TAG` | No | `langbuilder-traefik` | Traefik routing tag |
| `TRAEFIK_PUBLIC_TAG` | No | `traefik-public` | Traefik public tag |
| `LANGBUILDER_LOG_LEVEL` | No | `debug` | LangBuilder log level |
| `LANGBUILDER_SUPERUSER` | No | `superuser` | Default superuser username |
| `LANGBUILDER_SUPERUSER_PASSWORD` | No | `superuser` | Default superuser password |
| `LANGBUILDER_NEW_USER_IS_ACTIVE` | No | `False` | Whether new users are active by default |
| `BACKEND_URL` | No | `http://backend:7860` | Internal backend URL |
| `POSTGRES_USER` | No | `langbuilder` | PostgreSQL user |
| `POSTGRES_PASSWORD` | No | `langbuilder` | PostgreSQL password |
| `POSTGRES_DB` | No | `langbuilder` | PostgreSQL database name |
| `POSTGRES_PORT` | No | `5432` | PostgreSQL port |
| `DB_USER` | No | `langbuilder` | DB connection user |
| `DB_PASSWORD` | No | `langbuilder` | DB connection password |
| `DB_HOST` | No | `db` | DB connection host |
| `DB_PORT` | No | `5432` | DB connection port |
| `DB_NAME` | No | `langbuilder` | DB connection database name |
| `RABBITMQ_DEFAULT_USER` | No | `langbuilder` | RabbitMQ username |
| `RABBITMQ_DEFAULT_PASS` | No | `langbuilder` | RabbitMQ password |
| `BROKER_URL` | No | `amqp://langbuilder:langbuilder@broker:5672` | AMQP broker URL for Celery |
| `LANGBUILDER_REDIS_HOST` | No | `result_backend` | Redis hostname |
| `LANGBUILDER_REDIS_PORT` | No | `6379` | Redis port |
| `LANGBUILDER_REDIS_DB` | No | `0` | Redis database index |
| `LANGBUILDER_REDIS_EXPIRE` | No | `3600` | Redis key expiration (seconds) |
| `LANGBUILDER_REDIS_PASSWORD` | No | (empty) | Redis password |
| `RESULT_BACKEND` | No | `redis://result_backend:6379/0` | Celery result backend URL |
| `FLOWER_UNAUTHENTICATED_API` | No | `True` | Flower dashboard unauthenticated API access |
| `C_FORCE_ROOT` | No | `true` | Allow Celery to run as root |
| `PGADMIN_DEFAULT_EMAIL` | No | `admin@admin.com` | PGAdmin default login email |
| `PGADMIN_DEFAULT_PASSWORD` | No | `admin` | PGAdmin default login password |

Source: `langbuilder/deploy/.env.example`

---

## Pydantic Settings Classes

### LangBuilder Settings

**Class:** `Settings(BaseSettings)`
**File:** `langbuilder/src/backend/base/langbuilder/services/settings/base.py`
**Environment prefix:** `LANGBUILDER_`
**Config source:** `MyCustomSource(EnvSettingsSource)` -- supports comma-separated list parsing for list fields.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `config_dir` | `str \| None` | `None` (auto-resolved via `platformdirs.user_cache_dir`) | Configuration directory |
| `save_db_in_config_dir` | `bool` | `False` | Save database in config dir instead of package dir |
| `dev` | `bool` | `False` | Development mode flag |
| `database_url` | `str \| None` | `None` (auto-migrates to SQLite) | Database URL; supports `sqlite` and `postgresql` (auto-converts to async drivers) |
| `database_connection_retry` | `bool` | `False` | Retry database connection on failure |
| `pool_size` | `int` | `20` | Connection pool size |
| `max_overflow` | `int` | `30` | Max connections beyond pool size |
| `db_connect_timeout` | `int` | `30` | Database connection timeout (seconds) |
| `mcp_server_timeout` | `int` | `20` | MCP server timeout (seconds) |
| `mcp_max_sessions_per_server` | `int` | `10` | Max MCP sessions per server |
| `mcp_session_idle_timeout` | `int` | `400` | MCP session idle timeout (seconds) |
| `mcp_session_cleanup_interval` | `int` | `120` | MCP session cleanup interval (seconds) |
| `sqlite_pragmas` | `dict \| None` | `{"synchronous": "NORMAL", "journal_mode": "WAL"}` | SQLite pragmas |
| `db_driver_connection_settings` | `dict \| None` | `None` | Database driver connection settings |
| `db_connection_settings` | `dict \| None` | `{"pool_size": 20, "max_overflow": 30, ...}` | Database connection pool settings |
| `use_noop_database` | `bool` | `False` | Disable all DB operations (no-op session) |
| `cache_type` | `Literal["async","redis","memory","disk"]` | `"async"` | Cache backend type |
| `cache_expire` | `int` | `3600` | Cache TTL (seconds) |
| `variable_store` | `str` | `"db"` | Variable store backend (`db` or `kubernetes`) |
| `prometheus_enabled` | `bool` | `False` | Expose Prometheus metrics |
| `prometheus_port` | `int` | `9090` | Prometheus metrics port |
| `disable_track_apikey_usage` | `bool` | `False` | Disable API key usage tracking |
| `remove_api_keys` | `bool` | `False` | Remove API keys from responses |
| `components_path` | `list[str]` | `[]` (resolved to `BASE_COMPONENTS_PATH`) | Custom component paths |
| `langchain_cache` | `str` | `"InMemoryCache"` | LangChain cache type |
| `load_flows_path` | `str \| None` | `None` | Path to auto-load flows from |
| `bundle_urls` | `list[str]` | `[]` | Custom bundle URLs |
| `redis_host` | `str` | `"localhost"` | Redis hostname |
| `redis_port` | `int` | `6379` | Redis port |
| `redis_db` | `int` | `0` | Redis database index |
| `redis_url` | `str \| None` | `None` | Full Redis URL (overrides host/port/db) |
| `redis_cache_expire` | `int` | `3600` | Redis cache expiration (seconds) |
| `sentry_dsn` | `str \| None` | `None` | Sentry DSN for error tracking |
| `sentry_traces_sample_rate` | `float \| None` | `1.0` | Sentry traces sample rate |
| `sentry_profiles_sample_rate` | `float \| None` | `1.0` | Sentry profiles sample rate |
| `store` | `bool \| None` | `True` | Enable LangBuilder store |
| `store_url` | `str \| None` | `"https://api.langbuilder.store"` | LangBuilder store API URL |
| `storage_type` | `str` | `"local"` | Storage backend type |
| `celery_enabled` | `bool` | `False` | Enable Celery task queue |
| `fallback_to_env_var` | `bool` | `True` | Fall back to env vars for global variables |
| `store_environment_variables` | `bool` | `True` | Store env vars as global variables in DB |
| `worker_timeout` | `int` | `300` | API call timeout (seconds) |
| `frontend_timeout` | `int` | `0` | Frontend API call timeout (seconds, 0 = unlimited) |
| `user_agent` | `str` | `"langbuilder"` | User agent for API calls |
| `backend_only` | `bool` | `False` | Run without serving frontend |
| `do_not_track` | `bool` | `True` | Disable telemetry |
| `transactions_storage_enabled` | `bool` | `True` | Track transactions between flows |
| `vertex_builds_storage_enabled` | `bool` | `True` | Track vertex builds in UI |
| `host` | `str` | `"localhost"` | Server bind host |
| `port` | `int` | `7860` | Server bind port |
| `workers` | `int` | `1` | Number of workers |
| `log_level` | `str` | `"critical"` | Log level |
| `log_file` | `str \| None` | `"logs/langbuilder.log"` | Log file path |
| `alembic_log_file` | `str` | `"alembic/alembic.log"` | Alembic log file path |
| `frontend_path` | `str \| None` | `None` | Frontend build directory (dev only) |
| `open_browser` | `bool` | `False` | Open browser on startup |
| `auto_saving` | `bool` | `True` | Auto-save flows |
| `auto_saving_interval` | `int` | `1000` | Auto-save interval (ms) |
| `health_check_max_retries` | `int` | `5` | Health check max retries |
| `max_file_size_upload` | `int` | `1024` | Max upload file size (MB) |
| `deactivate_tracing` | `bool` | `False` | Deactivate tracing |
| `max_transactions_to_keep` | `int` | `3000` | Max transactions in DB |
| `max_vertex_builds_to_keep` | `int` | `3000` | Max vertex builds in DB |
| `max_vertex_builds_per_vertex` | `int` | `2` | Max builds per vertex |
| `ssl_cert_file` | `str \| None` | `None` | SSL certificate file path |
| `ssl_key_file` | `str \| None` | `None` | SSL key file path |
| `mcp_server_enabled` | `bool` | `True` | Enable MCP server |
| `mcp_server_enable_progress_notifications` | `bool` | `False` | Send MCP progress notifications |
| `public_flow_cleanup_interval` | `int` | `3600` | Public flow cleanup interval (seconds, min 600) |
| `public_flow_expiration` | `int` | `86400` | Public flow expiration time (seconds, min 600) |
| `event_delivery` | `Literal["polling","streaming","direct"]` | `"streaming"` | Build event delivery method (auto-switches to `direct` when workers > 1) |
| `lazy_load_components` | `bool` | `False` | Lazy-load components at startup |
| `create_starter_projects` | `bool` | `True` | Create starter projects on startup |
| `update_starter_projects` | `bool` | `True` | Update starter projects on startup |

---

### Auth Settings

**Class:** `AuthSettings(BaseSettings)`
**File:** `langbuilder/src/backend/base/langbuilder/services/settings/auth.py`
**Environment prefix:** `LANGBUILDER_`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `CONFIG_DIR` | `str` | (required) | Configuration directory for secret key storage |
| `SECRET_KEY` | `SecretStr` | (auto-generated via `secrets.token_urlsafe(32)`) | JWT signing secret; persisted to `CONFIG_DIR/secret_key` file |
| `ALGORITHM` | `str` | `"HS256"` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_SECONDS` | `int` | `3600` (1 hour) | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_SECONDS` | `int` | `604800` (7 days) | Refresh token lifetime |
| `API_KEY_ALGORITHM` | `str` | `"HS256"` | API key signing algorithm |
| `API_V1_STR` | `str` | `"/api/v1"` | API v1 URL prefix |
| `AUTO_LOGIN` | `bool` | `True` | Auto-login as superuser (resets credentials to defaults) |
| `skip_auth_auto_login` | `bool` | `True` | Skip authentication when AUTO_LOGIN enabled (deprecated, removal in v1.6) |
| `NEW_USER_IS_ACTIVE` | `bool` | `False` | Whether new users are active by default |
| `SUPERUSER` | `str` | `DEFAULT_SUPERUSER` (from constants) | Default superuser username |
| `SUPERUSER_PASSWORD` | `str` | `DEFAULT_SUPERUSER_PASSWORD` (from constants) | Default superuser password |
| `REFRESH_SAME_SITE` | `Literal["lax","strict","none"]` | `"none"` | Refresh token cookie SameSite attribute |
| `REFRESH_SECURE` | `bool` | `True` | Refresh token cookie Secure attribute |
| `REFRESH_HTTPONLY` | `bool` | `True` | Refresh token cookie HttpOnly attribute |
| `ACCESS_SAME_SITE` | `Literal["lax","strict","none"]` | `"lax"` | Access token cookie SameSite attribute |
| `ACCESS_SECURE` | `bool` | `False` | Access token cookie Secure attribute |
| `ACCESS_HTTPONLY` | `bool` | `False` | Access token cookie HttpOnly attribute |
| `COOKIE_DOMAIN` | `str \| None` | `None` | Cookie domain; if None, domain is not set |

Password hashing uses `bcrypt` via `passlib.context.CryptContext`.

---

## Configuration Files

| File | Purpose |
|------|---------|
| `.env.example` | Root environment variables template (primary config) |
| `.env.docker.example` | Docker environment variables template |
| `langbuilder/deploy/.env.example` | Deployment (Docker Swarm/Compose stack) environment template |
| `langbuilder/src/backend/base/langbuilder/services/settings/base.py` | Core Pydantic `Settings` class with `LANGBUILDER_` env prefix |
| `langbuilder/src/backend/base/langbuilder/services/settings/auth.py` | Auth Pydantic `AuthSettings` class with `LANGBUILDER_` env prefix |
| `langbuilder/src/backend/base/langbuilder/settings.py` | DEV mode flag module |
| `openwebui/backend/open_webui/env.py` | OpenWebUI environment config |
| `docker-compose.dev.yml` | Docker Compose dev config |
| `langbuilder/deploy/docker-compose.yml` | Production Docker Compose |
| `langbuilder/src/frontend/vite.config.mts` | Vite frontend build config |
| `langbuilder/src/frontend/tsconfig.json` | TypeScript compiler config |

---

## By Category

### Database

| Variable / Field | Source | Default |
|-----------------|--------|---------|
| `DATABASE_URL` | `.env.example` | `sqlite:///./data/webui.db` |
| `LANGBUILDER_DATABASE_URL` | `.env.docker.example`, `deploy/.env.example` | `postgresql://langbuilder:langbuilder@postgres:5432/langbuilder` |
| `POSTGRES_USER` | `deploy/.env.example` | `langbuilder` |
| `POSTGRES_PASSWORD` | `deploy/.env.example` | `langbuilder` |
| `POSTGRES_DB` | `deploy/.env.example` | `langbuilder` |
| `POSTGRES_PORT` | `deploy/.env.example` | `5432` |
| `DB_USER` | `deploy/.env.example` | `langbuilder` |
| `DB_PASSWORD` | `deploy/.env.example` | `langbuilder` |
| `DB_HOST` | `deploy/.env.example` | `db` |
| `DB_PORT` | `deploy/.env.example` | `5432` |
| `DB_NAME` | `deploy/.env.example` | `langbuilder` |
| `DATA_DIR` | `.env.example` | `./data` |
| `pool_size` | `Settings` class | `20` |
| `max_overflow` | `Settings` class | `30` |
| `db_connect_timeout` | `Settings` class | `30` |
| `database_connection_retry` | `Settings` class | `False` |
| `sqlite_pragmas` | `Settings` class | `{"synchronous": "NORMAL", "journal_mode": "WAL"}` |

### Authentication & Security

| Variable / Field | Source | Default |
|-----------------|--------|---------|
| `WEBUI_SECRET_KEY` | `.env.example` | (required) |
| `SECRET_KEY` | `AuthSettings` class | (auto-generated) |
| `JWT_EXPIRES_IN` | `.env.example` | `24h` |
| `ACCESS_TOKEN_EXPIRE_SECONDS` | `AuthSettings` class | `3600` |
| `REFRESH_TOKEN_EXPIRE_SECONDS` | `AuthSettings` class | `604800` |
| `KMS_MASTER_KEY` | `.env.example` | (base64 encoded, required) |
| `GOOGLE_CLIENT_ID` | `.env.example` | (placeholder) |
| `GOOGLE_CLIENT_SECRET` | `.env.example` | (placeholder) |
| `GOOGLE_REDIRECT_URI` | `.env.example` | (computed) |
| `ZOHO_CLIENT_ID` | `.env.example` | (placeholder) |
| `ZOHO_CLIENT_SECRET` | `.env.example` | (placeholder) |
| `ZOHO_REDIRECT_URI` | `.env.example` | (computed) |
| `CORPORATE_AUTH_CONFIG` | `.env.example` | `/app/corporate_config.json` |
| `CORPORATE_GROUP_MAPPINGS` | `.env.example` | (JSON string) |
| `ENABLE_OAUTH_SIGNUP` | `.env.example` | `true` |
| `ENABLE_SIGNUP` | `.env.example` | `true` |
| `ENABLE_LOGIN_FORM` | `.env.example` | `true` |
| `ENABLE_API_KEY` | `.env.example` | `true` |
| `OAUTH_ALLOWED_DOMAINS` | `.env.example` | `*` |
| `OAUTH_MERGE_ACCOUNTS_BY_EMAIL` | `.env.example` | `true` |
| `AUTO_LOGIN` | `AuthSettings` class | `True` |
| `NEW_USER_IS_ACTIVE` | `AuthSettings` class | `False` |
| `SUPERUSER` | `AuthSettings` class | `DEFAULT_SUPERUSER` |
| `SUPERUSER_PASSWORD` | `AuthSettings` class | `DEFAULT_SUPERUSER_PASSWORD` |
| `REFRESH_SAME_SITE` | `AuthSettings` class | `"none"` |
| `REFRESH_SECURE` | `AuthSettings` class | `True` |
| `ACCESS_SAME_SITE` | `AuthSettings` class | `"lax"` |
| `ACCESS_SECURE` | `AuthSettings` class | `False` |
| `COOKIE_DOMAIN` | `AuthSettings` class | `None` |
| `WEBUI_SESSION_COOKIE_SAME_SITE` | `.env.example` | `lax` |
| `WEBUI_SESSION_COOKIE_SECURE` | `.env.example` | `false` |

### LLM Providers

| Variable | Source | Default |
|----------|--------|---------|
| `OLLAMA_BASE_URL` | `.env.example` | `http://localhost:11434` |
| `OPENAI_API_BASE_URL` | `.env.example` | (empty) |
| `OPENAI_API_KEY` | `.env.example` | (empty) |

### Caching (Redis)

| Variable / Field | Source | Default |
|-----------------|--------|---------|
| `LANGBUILDER_REDIS_HOST` | `deploy/.env.example` | `result_backend` |
| `LANGBUILDER_REDIS_PORT` | `deploy/.env.example` | `6379` |
| `LANGBUILDER_REDIS_DB` | `deploy/.env.example` | `0` |
| `LANGBUILDER_REDIS_EXPIRE` | `deploy/.env.example` | `3600` |
| `LANGBUILDER_REDIS_PASSWORD` | `deploy/.env.example` | (empty) |
| `redis_host` | `Settings` class | `"localhost"` |
| `redis_port` | `Settings` class | `6379` |
| `redis_db` | `Settings` class | `0` |
| `redis_url` | `Settings` class | `None` |
| `redis_cache_expire` | `Settings` class | `3600` |
| `cache_type` | `Settings` class | `"async"` |
| `cache_expire` | `Settings` class | `3600` |

### Message Queue (RabbitMQ / Celery)

| Variable | Source | Default |
|----------|--------|---------|
| `RABBITMQ_DEFAULT_USER` | `deploy/.env.example` | `langbuilder` |
| `RABBITMQ_DEFAULT_PASS` | `deploy/.env.example` | `langbuilder` |
| `BROKER_URL` | `deploy/.env.example` | `amqp://langbuilder:langbuilder@broker:5672` |
| `RESULT_BACKEND` | `deploy/.env.example` | `redis://result_backend:6379/0` |
| `C_FORCE_ROOT` | `deploy/.env.example` | `true` |
| `celery_enabled` | `Settings` class | `False` |

### Observability

| Variable / Field | Source | Default |
|-----------------|--------|---------|
| `GLOBAL_LOG_LEVEL` | `.env.example` | `DEBUG` |
| `LOG_LEVEL` | `.env.docker.example` | `debug` |
| `LANGBUILDER_LOG_LEVEL` | `deploy/.env.example` | `debug` |
| `log_level` | `Settings` class | `"critical"` |
| `log_file` | `Settings` class | `"logs/langbuilder.log"` |
| `sentry_dsn` | `Settings` class | `None` |
| `sentry_traces_sample_rate` | `Settings` class | `1.0` |
| `sentry_profiles_sample_rate` | `Settings` class | `1.0` |
| `prometheus_enabled` | `Settings` class | `False` |
| `prometheus_port` | `Settings` class | `9090` |
| `SCARF_NO_ANALYTICS` | `.env.example` | `true` |
| `DO_NOT_TRACK` | `.env.example` | `true` |
| `ANONYMIZED_TELEMETRY` | `.env.example` | `false` |
| `do_not_track` | `Settings` class | `True` |
| `deactivate_tracing` | `Settings` class | `False` |

### Frontend

| Variable | Source | Default |
|----------|--------|---------|
| `VITE_PORT` | `.env.docker.example` | `3000` |
| `VITE_PROXY_TARGET` | `.env.docker.example` | `http://langbuilder-backend:8002` |
| `FRONTEND_PORT` | `.env.example` | `5175` |
| `NODE_ENV` | `.env.docker.example` | `development` |
| `WEBUI_URL` | `.env.example` | `http://localhost:${FRONTEND_PORT}` |
| `frontend_path` | `Settings` class | `None` |
| `frontend_timeout` | `Settings` class | `0` |

### Infrastructure

| Variable / Field | Source | Default |
|-----------------|--------|---------|
| `DOMAIN` | `deploy/.env.example` | `localhost` |
| `STACK_NAME` | `deploy/.env.example` | `langbuilder-stack` |
| `TRAEFIK_PUBLIC_NETWORK` | `deploy/.env.example` | `traefik-public` |
| `TRAEFIK_TAG` | `deploy/.env.example` | `langbuilder-traefik` |
| `TRAEFIK_PUBLIC_TAG` | `deploy/.env.example` | `traefik-public` |
| `HOST` | `.env.example` | `0.0.0.0` |
| `PORT` | `.env.example` | `8767` |
| `host` | `Settings` class | `"localhost"` |
| `port` | `Settings` class | `7860` |
| `workers` | `Settings` class | `1` |
| `ssl_cert_file` | `Settings` class | `None` |
| `ssl_key_file` | `Settings` class | `None` |
| `BACKEND_URL` | `deploy/.env.example` | `http://backend:7860` |
| `BACKEND_PORT` | `.env.example` | `8002` |
| `OPEN_WEBUI_PORT` | `.env.example` | `8767` |
| `CORS_ALLOW_ORIGIN` | `.env.example` | (computed from ports) |
| `FORWARDED_ALLOW_IPS` | `.env.example` | `*` |
| `ENV` | `.env.docker.example` | `dev` |
| `PYTHONUNBUFFERED` | `.env.docker.example` | `1` |
| `PGADMIN_DEFAULT_EMAIL` | `deploy/.env.example` | `admin@admin.com` |
| `PGADMIN_DEFAULT_PASSWORD` | `deploy/.env.example` | `admin` |
| `FLOWER_UNAUTHENTICATED_API` | `deploy/.env.example` | `True` |

### MCP (Model Context Protocol)

| Field | Source | Default |
|-------|--------|---------|
| `mcp_server_enabled` | `Settings` class | `True` |
| `mcp_server_timeout` | `Settings` class | `20` |
| `mcp_max_sessions_per_server` | `Settings` class | `10` |
| `mcp_session_idle_timeout` | `Settings` class | `400` |
| `mcp_session_cleanup_interval` | `Settings` class | `120` |
| `mcp_server_enable_progress_notifications` | `Settings` class | `False` |

---

## Summary

- **Total environment variables defined:** ~80+ (across `.env.example`, `.env.docker.example`, and `deploy/.env.example`)
- **Pydantic Settings fields:** ~60+ (across `Settings` and `AuthSettings` classes)
- **Required secrets:** ~10 (API keys: `OPENAI_API_KEY`; OAuth credentials: `GOOGLE_CLIENT_ID/SECRET`, `ZOHO_CLIENT_ID/SECRET`; encryption: `KMS_MASTER_KEY`, `WEBUI_SECRET_KEY`; JWT: `SECRET_KEY`)
- **Configuration files:** 11+
- **Environment prefixes:** `LANGBUILDER_` (Pydantic Settings), none (OpenWebUI env vars)
- **Settings sources:** 3 `.env.example` files, 2 Pydantic `BaseSettings` classes, Docker Compose files
