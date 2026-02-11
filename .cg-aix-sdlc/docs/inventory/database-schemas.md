# Database Schemas

> Generated: 2026-02-09 | LangBuilder v1.6.5

## Overview

| Property | Value |
|----------|-------|
| **ORM** | SQLModel (SQLAlchemy + Pydantic) |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Async Support** | Yes (AsyncEngine, AsyncSession) |
| **Migration Tool** | Alembic |
| **Total Models** | 10 |
| **Total Enums** | 3 |
| **Migration Count** | 50 |

## LangBuilder Database (10 models)

**Location**: `langbuilder/src/backend/base/langbuilder/services/database/models/`

### `User`

| Field | Type | Attributes |
|-------|------|------------|
| id | UUID | primary_key |
| username | str | indexed, unique |
| password | str | |
| profile_image | str | nullable |
| is_active | bool | default=True |
| is_superuser | bool | default=False |
| create_at | datetime | default=now |
| updated_at | datetime | default=now |
| last_login_at | datetime | nullable |
| store_api_key | str | nullable |
| optins | JSON | nullable |

**Relationships**: api_keys, flows, variables, folders

### `Flow`

| Field | Type | Attributes |
|-------|------|------------|
| id | UUID | primary_key |
| name | str | indexed |
| description | Text | nullable |
| icon | str | nullable |
| icon_bg_color | str | nullable |
| gradient | str | nullable |
| data | JSON | |
| is_component | bool | nullable |
| updated_at | datetime | nullable |
| user_id | UUID | FK(user.id), nullable |
| folder_id | UUID | FK(folder.id), nullable, indexed |
| fs_path | str | nullable |
| webhook | bool | nullable |
| endpoint_name | str | nullable, indexed |
| tags | JSON list | |
| locked | bool | nullable |
| mcp_enabled | bool | nullable |
| action_name | str | nullable |
| action_description | Text | nullable |
| access_type | AccessTypeEnum | default=PRIVATE |

**Constraints**: UNIQUE(user_id, name), UNIQUE(user_id, endpoint_name)
**Relationships**: user, folder, publish_records

### `ApiKey`

| Field | Type | Attributes |
|-------|------|------------|
| id | UUID | primary_key |
| api_key | str | indexed, unique |
| name | str | indexed, nullable |
| created_at | datetime | default=now |
| last_used_at | datetime | nullable |
| total_uses | int | default=0 |
| is_active | bool | default=True |
| user_id | UUID | FK(user.id), indexed |

**Relationships**: user

### `Variable`

| Field | Type | Attributes |
|-------|------|------------|
| id | UUID | primary_key |
| name | str | |
| value | str | encrypted |
| type | str | nullable |
| default_fields | JSON list | nullable |
| created_at | datetime | default=now |
| updated_at | datetime | nullable |
| user_id | UUID | FK(user.id) |

**Relationships**: user

### `Folder`

| Field | Type | Attributes |
|-------|------|------------|
| id | UUID | primary_key |
| name | str | indexed |
| description | Text | nullable |
| parent_id | UUID | FK(folder.id), nullable |
| user_id | UUID | FK(user.id), nullable |
| auth_settings | JSON | nullable |

**Constraints**: UNIQUE(user_id, name)
**Relationships**: parent, children (self-referential), user, flows

### `MessageTable`

| Field | Type | Attributes |
|-------|------|------------|
| id | UUID | primary_key |
| timestamp | datetime | default=now |
| sender | str | |
| sender_name | str | |
| session_id | str | |
| text | Text | |
| files | JSON list | |
| error | bool | default=False |
| edit | bool | default=False |
| flow_id | UUID | nullable |
| properties | JSON | |
| category | Text | |
| content_blocks | JSON list | |

**Table name**: `message`

### `File`

| Field | Type | Attributes |
|-------|------|------------|
| id | UUID | primary_key |
| user_id | UUID | FK(user.id) |
| name | str | unique |
| path | str | |
| size | int | |
| provider | str | nullable |
| created_at | datetime | default=now |
| updated_at | datetime | default=now |

### `TransactionTable`

| Field | Type | Attributes |
|-------|------|------------|
| id | UUID | primary_key |
| timestamp | datetime | default=now |
| vertex_id | str | |
| target_id | str | nullable |
| inputs | JSON | nullable |
| outputs | JSON | nullable |
| status | str | |
| error | str | nullable |
| flow_id | UUID | |

**Table name**: `transaction`

### `VertexBuildTable`

| Field | Type | Attributes |
|-------|------|------------|
| build_id | UUID | primary_key |
| id | str | |
| timestamp | datetime | default=now |
| data | JSON | nullable |
| artifacts | JSON | nullable |
| params | Text | nullable |
| valid | bool | |
| flow_id | UUID | |

**Table name**: `vertex_build`

### `PublishRecord`

| Field | Type | Attributes |
|-------|------|------------|
| id | UUID | primary_key |
| flow_id | UUID | FK(flow.id), indexed |
| platform | str | indexed |
| platform_url | str | |
| external_id | str | |
| published_at | datetime | default=now |
| published_by | UUID | FK(user.id) |
| status | PublishStatusEnum | default=ACTIVE |
| metadata_ | JSON | nullable |
| last_sync_at | datetime | nullable |
| error_message | Text | nullable |

**Constraints**: UNIQUE(flow_id, platform, platform_url, status)
**Relationships**: flow, user
**Table name**: `publish_record`

## Relationships

| From Model | To Model | Relation Type | Local Field | Foreign Field |
|------------|----------|---------------|-------------|---------------|
| Flow | User | N:1 | user_id | id |
| Flow | Folder | N:1 | folder_id | id |
| ApiKey | User | N:1 | user_id | id |
| Variable | User | N:1 | user_id | id |
| Folder | Folder | N:1 (self) | parent_id | id |
| Folder | User | N:1 | user_id | id |
| File | User | N:1 | user_id | id |
| PublishRecord | Flow | N:1 | flow_id | id |
| PublishRecord | User | N:1 | published_by | id |

## Enums

### `AccessTypeEnum`
Values: `PRIVATE`, `PUBLIC`
**Used in**: Flow model (access_type field)
**File**: `langbuilder/src/backend/base/langbuilder/services/database/models/flow/model.py`

### `PublishStatusEnum`
Values: `ACTIVE`, `UNPUBLISHED`, `ERROR`, `PENDING`
**Used in**: PublishRecord model (status field)
**File**: `langbuilder/src/backend/base/langbuilder/services/database/models/publish_record/model.py`

### `Tags`
Values: `CHATBOTS`, `AGENTS`
**Used in**: Flow model (tags field)
**File**: `langbuilder/src/backend/base/langbuilder/services/database/models/flow/schema.py`

## Alembic Migrations

**Location**: `langbuilder/src/backend/base/langbuilder/alembic/versions/`
**Total migrations**: 50

Key migrations include:
- Initial table creation (users, flows, folders)
- Message and transaction tables
- Variable encryption support
- Vertex build tracking
- Folder system implementation
- MCP support addition
- Webhook and endpoint features
- Publish record system
- File management tables

## Database Configuration

**Service**: `langbuilder/src/backend/base/langbuilder/services/database/service.py`

| Setting | Default | Description |
|---------|---------|-------------|
| pool_size | 20 | Connection pool size |
| max_overflow | 30 | Max overflow connections |
| db_connect_timeout | 30 | Connection timeout (seconds) |
| database_connection_retry | false | Auto-retry connections |

**Supported drivers**:
- `sqlite+aiosqlite` (development default)
- `postgresql+psycopg` (production)
