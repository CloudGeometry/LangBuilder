# Phase 1, Task 1.4: RBAC Tables Migration Implementation

## Overview

This document describes the implementation of the Alembic migration that creates all RBAC (Role-Based Access Control) database tables for LangBuilder.

## Migration Details

**Migration ID**: a20a7041e437_add_rbac_tables
**Revision**: a20a7041e437
**Previous Revision**: 3162e83e485f
**Created**: 2025-11-04 10:03:29

**File Location**: `/home/nick/LangBuilder/src/backend/base/langbuilder/alembic/versions/a20a7041e437_add_rbac_tables.py`

## Tables Created

The migration creates four tables in the following order:

### 1. permission
Core permissions table for CRUD actions.

**Columns**:
- `id` (UUID, Primary Key)
- `name` (String, Unique, Indexed) - Permission name (e.g., "Create", "Read", "Update", "Delete")
- `description` (String, Nullable) - Human-readable description
- `scope_type` (String, Indexed) - Scope type (e.g., "Flow", "Project", "Global")

**Indexes**:
- `ix_permission_name` (Unique) - Fast lookup by permission name
- `ix_permission_scope_type` - Fast filtering by scope type

**Constraints**:
- Primary key on `id`
- Unique constraint on `name`

### 2. role
Predefined roles that can be assigned to users.

**Columns**:
- `id` (UUID, Primary Key)
- `name` (String, Unique, Indexed) - Role name (e.g., "Admin", "Owner", "Editor", "Viewer")
- `description` (String, Nullable) - Human-readable description
- `is_system` (Boolean) - Prevents deletion of system-defined roles

**Indexes**:
- `ix_role_name` (Unique) - Fast lookup by role name

**Constraints**:
- Primary key on `id`
- Unique constraint on `name`

### 3. role_permission
Junction table for many-to-many relationship between roles and permissions.

**Columns**:
- `id` (UUID, Primary Key)
- `role_id` (UUID, Foreign Key to role.id, Indexed)
- `permission_id` (UUID, Foreign Key to permission.id, Indexed)

**Indexes**:
- `ix_role_permission_role_id` - Fast lookup by role
- `ix_role_permission_permission_id` - Fast lookup by permission

**Constraints**:
- Primary key on `id`
- Foreign key to `role.id`
- Foreign key to `permission.id`
- Unique constraint on `(role_id, permission_id)` - Prevents duplicate role-permission assignments

### 4. user_role_assignment
Core assignment table that assigns roles to users for specific scopes.

**Columns**:
- `id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key to user.id, Indexed)
- `role_id` (UUID, Foreign Key to role.id, Indexed)
- `scope_type` (String, Indexed) - Scope type ("global", "project", "flow")
- `scope_id` (UUID, Nullable, Indexed) - ID of scoped entity (None for global)
- `is_immutable` (Boolean) - Prevents deletion of critical assignments (e.g., Starter Project Owner)
- `created_at` (DateTime) - Timestamp of assignment creation
- `created_by` (UUID, Nullable, Foreign Key to user.id) - User who created the assignment

**Indexes**:
- `idx_scope_lookup` (Composite: user_id, scope_type, scope_id) - Critical index for permission checks
- `ix_user_role_assignment_user_id` - Fast filtering by user
- `ix_user_role_assignment_role_id` - Fast filtering by role
- `ix_user_role_assignment_scope_type` - Fast filtering by scope type
- `ix_user_role_assignment_scope_id` - Fast filtering by scope ID

**Constraints**:
- Primary key on `id`
- Foreign key to `user.id`
- Foreign key to `role.id`
- Foreign key to `user.id` (created_by)
- Unique constraint on `(user_id, role_id, scope_type, scope_id)` - Prevents duplicate assignments

## Index Design Rationale

### idx_scope_lookup (user_id, scope_type, scope_id)
This composite index is critical for permission check performance. It optimizes the most common query pattern:
```sql
SELECT * FROM user_role_assignment
WHERE user_id = ? AND scope_type = ? AND scope_id = ?
```

**Expected Performance**: O(log n) single index lookup
**Use Case**: Permission checks (most frequent operation)
**Target Latency**: <0.5ms per query

### Individual Indexes
The individual indexes on `user_id`, `role_id`, `scope_type`, and `scope_id` support admin UI queries that filter on these fields independently.

**Use Case**: Admin operations, role management UI
**Target Latency**: 1-5ms per query

## Migration Testing

### Upgrade Test
```bash
cd /home/nick/LangBuilder/src/backend/base/langbuilder
alembic upgrade head
```

**Result**: ✅ All tables created successfully with correct schema

### Downgrade Test
```bash
alembic downgrade -1
```

**Result**: ✅ All RBAC tables removed cleanly without affecting other tables

### Multiple Cycle Test
```bash
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
```

**Result**: ✅ Migration can be applied and rolled back multiple times

## Verification

### Tables Created
All four tables were verified to exist with correct schemas:
- ✅ permission
- ✅ role
- ✅ role_permission
- ✅ user_role_assignment

### Indexes Created
All specified indexes were verified:
- ✅ ix_permission_name (unique)
- ✅ ix_permission_scope_type
- ✅ ix_role_name (unique)
- ✅ ix_role_permission_role_id
- ✅ ix_role_permission_permission_id
- ✅ idx_scope_lookup (composite)
- ✅ ix_user_role_assignment_user_id
- ✅ ix_user_role_assignment_role_id
- ✅ ix_user_role_assignment_scope_type
- ✅ ix_user_role_assignment_scope_id

### Constraints Created
All constraints were verified:
- ✅ All primary keys
- ✅ All foreign keys
- ✅ Unique constraint on permission.name
- ✅ Unique constraint on role.name
- ✅ Unique constraint on role_permission (role_id, permission_id)
- ✅ Unique constraint on user_role_assignment (user_id, role_id, scope_type, scope_id)

### Rollback Verification
- ✅ All RBAC tables removed after downgrade
- ✅ Other tables (user, flow, folder) unaffected by rollback
- ✅ Application can start without errors after rollback

## Success Criteria Validation

All success criteria from the implementation plan have been met:

1. ✅ Migration generates without errors
2. ✅ Migration applies cleanly to empty database
3. ✅ Migration applies cleanly to existing database with users/flows/folders
4. ✅ Migration rollback successfully removes all RBAC tables without affecting existing tables
5. ✅ After rollback, existing functionality works (verified by checking other tables)
6. ✅ All foreign key constraints are enforced
7. ✅ All indexes are created (including critical idx_scope_lookup)
8. ✅ Migration can be rolled back multiple times without errors

## Files Created/Modified

### Created:
1. `/home/nick/LangBuilder/src/backend/base/langbuilder/alembic/versions/a20a7041e437_add_rbac_tables.py` - Migration file
2. `/home/nick/LangBuilder/src/backend/tests/unit/alembic/test_rbac_migration.py` - Comprehensive unit tests
3. `/home/nick/LangBuilder/docs/code-generations/phase1-task1.4-migration-implementation.md` - This documentation

### Modified:
1. `/home/nick/LangBuilder/src/backend/base/langbuilder/services/database/models/__init__.py` - Added RBAC model imports

## Usage Instructions

### Apply Migration
```bash
cd /home/nick/LangBuilder/src/backend/base/langbuilder
alembic upgrade head
```

### Rollback Migration
```bash
cd /home/nick/LangBuilder/src/backend/base/langbuilder
alembic downgrade -1
```

### Check Current Migration Status
```bash
cd /home/nick/LangBuilder/src/backend/base/langbuilder
alembic current
```

### View Migration History
```bash
cd /home/nick/LangBuilder/src/backend/base/langbuilder
alembic history
```

## Next Steps

After this migration is applied, the next tasks in the implementation plan are:

1. **Task 1.5**: Create RBAC seed data script to populate predefined roles and permissions
2. **Task 1.6**: Implement permission checker service that uses these tables
3. **Task 2.1**: Create API endpoints for role management

## Notes

- The migration uses SQLAlchemy's batch operations for SQLite compatibility
- The migration is idempotent when using Alembic's standard upgrade/downgrade commands
- The idx_scope_lookup index is critical for production performance and should never be removed
- The is_immutable flag on user_role_assignment prevents deletion of critical assignments like "Starter Project Owner"

## Database Compatibility

This migration has been tested with:
- ✅ SQLite (primary development database)
- ⏳ PostgreSQL (to be tested in production environment)

The migration uses SQLModel/SQLAlchemy abstractions that should work with both databases without modification.
