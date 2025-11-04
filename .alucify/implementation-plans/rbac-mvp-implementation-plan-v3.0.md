# RBAC MVP Implementation Plan

**Version**: v3.0
**Previous Version**: v2.0
**Audit Report**: rbac-mvp-implementation-plan-v2-audit.md
**Last Updated**: 2025-11-04

## Revision History

| Version | Date | Changes | Audit Reference |
|---------|------|---------|-----------------|
| v3.0 | 2025-11-04 | Addressed all minor recommendations from v2.0 audit: (1) Added explicit nl0511 node for batch permission endpoint, (2) Clarified cache invalidation strategy in Task 2.1, (3) Added explicit rollback testing success criteria to Task 1.4, (4) Defined specific load testing scenarios in Task 5.2, (5) Added database index performance analysis to Task 1.3, (6) Enhanced frontend caching strategy documentation in Task 4.4 | rbac-mvp-implementation-plan-v2-audit.md |
| v2.0 | 2025-11-03 | Added 4 audit recommendations: (1) monitoring/observability for 99.9% uptime, (2) explicit data migration task for existing users/projects, (3) batch permission check optimization details, (4) enhanced error messages for RBAC operations | rbac-mvp-implementation-plan-audit.md |
| v1.0 | 2025-10-30 | Initial implementation plan | N/A |

## Overview

This implementation plan details the complete integration of Role-Based Access Control (RBAC) into LangBuilder. The RBAC MVP introduces a customizable, fine-grained permission system that enforces secure access control across Flows and Projects. The system uses four predefined roles (Admin, Owner, Editor, Viewer) with standard CRUD permissions, managed exclusively through a web-based administrative interface.

The implementation spans data model creation, backend services, API endpoints, permission enforcement throughout the application, and a comprehensive admin UI for role assignment management.

## Current State Analysis

### What Exists Now

**Authentication Infrastructure:**
- JWT-based authentication system (`src/backend/base/langbuilder/services/auth/utils.py`)
- API key authentication as alternative
- User model with `is_superuser` flag (`src/backend/base/langbuilder/services/database/models/user/model.py:25-51`)
- Simple ownership-based authorization: `flow.user_id == current_user.id`
- Admin guard component for route protection (`src/frontend/src/components/authorization/authAdminGuard/index.tsx`)

**Data Models:**
- User model with relationships to flows, folders, API keys, variables
- Flow model with `user_id` foreign key and `access_type` enum (not enforced)
- Folder model (represents Projects in UI) with `user_id` foreign key and placeholder `auth_settings` field
- Admin page with user management (`src/frontend/src/pages/AdminPage/index.tsx`)

**Authorization Pattern:**
- Endpoint handlers check `current_user.is_superuser` OR `resource.user_id == current_user.id`
- Example in `src/backend/base/langbuilder/api/v1/flows.py` and `src/backend/base/langbuilder/api/v1/projects.py`

### What's Missing

**RBAC Infrastructure:**
- No role or permission data models
- No role-to-permission mapping tables
- No user-role assignment tables
- No RBAC service for permission evaluation
- No API endpoints for RBAC management
- No frontend components for role assignment management
- No permission checks integrated into existing endpoints
- No permission-based UI filtering (list views, action buttons)
- No explicit data migration task for existing users/projects/flows
- No RBAC-specific monitoring or observability

**Key Constraints Discovered:**

1. **Database**: SQLModel/SQLAlchemy with async support, migrations via Alembic
2. **Service Pattern**: Services use factory pattern with dependency injection via FastAPI `Depends()`
3. **API Structure**: RESTful endpoints under `/api/v1/` with clear CRUD patterns
4. **Frontend State**: TanStack Query for server state, Zustand for client state, React Context for auth
5. **Authorization Guards**: Route-level guards using React components that check auth state
6. **Starter Projects**: System creates default "Starter Project" for each user - Owner role is immutable per PRD 1.4
7. **Observability**: Application has existing telemetry service (opentelemetry) that can be extended
8. **Performance Requirements**: 99.9% availability, permission checks <50ms p95, assignment API <200ms p95

## Desired End State

### System State After Implementation

**Data Layer:**
- Four database tables: `role`, `permission`, `role_permission`, `user_role_assignment`
- Predefined roles (Admin, Owner, Editor, Viewer) with permission mappings
- User role assignments linked to global, project, or flow scopes
- Automatic Owner assignment on project/flow creation
- Immutable Owner assignment for Starter Projects
- All existing users/projects/flows migrated with appropriate role assignments

**Service Layer:**
- RBACService providing `can_access(user_id, permission, scope_type, scope_id)` method
- Service caching for performance (p95 < 50ms per PRD 5.1)
- Integration with existing auth utilities
- Batch permission check optimization for list views
- RBAC operation logging for monitoring
- Cache invalidation strategy for role-permission mappings

**API Layer:**
- `/api/v1/rbac/roles` - List available roles
- `/api/v1/rbac/assignments` - CRUD operations for role assignments (admin only)
- `/api/v1/rbac/check-permission` - Permission check endpoint for frontend
- `/api/v1/rbac/check-permissions-batch` (nl0511) - Batch permission check endpoint for list views
- All existing Flow and Project endpoints enforce RBAC permissions

**Frontend Layer:**
- RBAC Management section in AdminPage with tabbed interface
- Assignment list view with filtering by user, role, scope
- Create/edit assignment wizard modal
- `usePermission` hook for permission checks with 5-minute client-side caching
- RBACGuard component for route/component-level permission enforcement
- UI elements (buttons, lists) filtered based on user permissions
- Specific, user-friendly error messages for RBAC permission failures

**Observability Layer:**
- Application-level health checks for RBACService availability
- Logging and metrics for RBAC operation failures (permission checks, assignments)
- Integration with existing telemetry service (OpenTelemetry)
- Alerting when permission checks fail or timeout
- Monitoring dashboard showing RBAC operation latency and error rates

### Verification Criteria

**Data Integrity:**
- Database migrations execute without errors
- Role and permission seed data loads correctly
- All existing users/projects/flows assigned appropriate roles (Owner or Admin)
- Foreign key constraints enforce referential integrity
- Migration rollback works correctly (Task 1.4 success criterion)

**Functional:**
- Admin can create, modify, delete role assignments via UI
- Non-admin users cannot access RBAC management
- Permission checks return results < 50ms (p95)
- Users see only resources they have Read permission for
- Create/Update/Delete actions blocked when user lacks permission
- Starter Project Owner role cannot be modified or deleted
- Project-level roles inherit to contained Flows
- Flow-specific roles override inherited Project roles
- Error messages clearly indicate permission issues and provide guidance

**Performance:**
- CanAccess check: < 50ms p95 (PRD 5.1)
- Assignment API calls: < 200ms p95 (PRD 5.1)
- Editor page load with RBAC: < 2.5s p95 (PRD 5.3)
- Batch permission checks reduce list view load time vs. individual checks
- Load testing scenarios pass under realistic conditions (100 concurrent users, 1000 flows)

**Availability:**
- System maintains 99.9% uptime during RBAC operations
- RBACService automatically retries on transient database failures
- Graceful degradation if cache initialization fails

## What We're NOT Doing

The following items are explicitly out-of-scope for this MVP:

- **Custom Roles**: Only the four predefined roles (Admin, Owner, Editor, Viewer) are supported
- **Extended Permissions**: Only CRUD permissions; no custom permissions like `Can_export_flow`, `Can_deploy_environment`
- **Extended Scopes**: No Component, Environment, Workspace, API/Token scopes - only Global, Project, Flow
- **SSO Integration**: No Single Sign-On, SAML, or OAuth integration
- **User Groups**: No group-based role assignment
- **Service Accounts**: No programmatic access control entities
- **SCIM Support**: No automated user provisioning
- **API/IaC Management**: No API or Infrastructure-as-Code based access management
- **User-Triggered Sharing**: No flow sharing initiated by non-admin users
- **Public Flows**: No public access to flows (access_type enum exists but not enforced)
- **Audit Logging**: No detailed audit trail of permission changes (future enhancement)
- **Role Hierarchies**: No parent/child role relationships

## Implementation Approach

### Overall Architectural Strategy

**1. Database-First Approach:**
We'll implement the RBAC data model first, seed with predefined roles and permissions, then build services and APIs on top. This ensures referential integrity and allows for easy testing of the permission logic.

**2. Service Layer Abstraction:**
The RBACService will be the single source of truth for permission evaluation. All endpoints will call `RBACService.can_access()` rather than implementing permission logic directly. This ensures consistency and makes the system testable.

**3. Backward-Compatible Migration:**
Existing superuser checks (`is_superuser`) will be preserved during migration. Superusers will be automatically granted Admin role globally. All existing users will be assigned Owner roles for flows/projects they own, and all existing flows/projects will maintain their ownership. This allows for gradual rollout and rollback if needed.

**4. Progressive Enhancement:**
- Phase 1: Data model and backend services (no breaking changes)
- Phase 2: Backend API endpoints and enforcement (Admin role required)
- Phase 3: Frontend UI for management (Admin only)
- Phase 4: Integration and enforcement across all endpoints
- Phase 5: Testing, performance, documentation, and observability

**5. Performance Optimization:**
- In-memory caching of role-permission mappings (static data) with 1-hour expiration
- Database indexing on user_id, scope_type, scope_id for fast lookups
- Async batch loading for list view permission checks
- Batch permission check endpoint (nl0511) to reduce N+1 queries in list views
- TanStack Query client-side caching (staleTime: 5 minutes) for permission checks
- Cache invalidation on role-permission updates (manual or automatic)

### Why This Approach

**Database-First**: Ensures data integrity and allows for incremental feature development without breaking changes.

**Service Abstraction**: Single point of control makes the system easier to test, debug, and enhance. Reduces code duplication across endpoints.

**Backward Compatibility**: Minimizes risk during deployment. Existing admin users continue to work during transition period. All data is migrated transparently.

**Progressive Enhancement**: Each phase delivers value independently and can be tested in isolation. Reduces risk of large-scale failures.

### Risk Mitigation Strategies

**Risk: Performance Degradation**
- Mitigation: Implement caching, indexing, and benchmark against PRD requirements
- Monitoring: Add telemetry to track permission check latency
- Fallback: Permission check timeout defaults to deny access

**Risk: Data Migration Failures**
- Mitigation: Explicit migration task with testing on production data snapshots
- Testing: Test migrations on copy of production data before deployment
- Rollback: Alembic downgrade support to revert if issues detected

**Risk: Breaking Existing Functionality**
- Mitigation: Preserve superuser bypass during transition
- Testing: Comprehensive integration tests for all existing endpoints
- Phased Rollout: Deploy with feature flags to enable RBAC gradually

**Risk: Complex Permission Inheritance**
- Mitigation: Clear precedence rules (Flow-specific > Project-inherited > None)
- Testing: Unit tests for all inheritance scenarios
- Documentation: Clear explanation of inheritance rules in code and docs

**Risk: Availability Impact**
- Mitigation: Health checks for RBACService availability
- Monitoring: Alerts on permission check failures or timeouts
- Graceful Degradation: Cache allows offline operation during DB issues (for reads)

### Testing Strategy

**Unit Tests:**
- RBACService permission evaluation logic
- Role-permission mapping correctness
- Assignment creation/modification/deletion logic
- Immutability enforcement for Starter Projects
- Permission inheritance rules (Flow > Project > None)
- Batch permission check correctness

**Integration Tests:**
- End-to-end permission checks through API endpoints
- Flow and Project CRUD operations with RBAC enforcement
- Admin UI workflow for creating assignments
- Permission inheritance from Project to Flow
- Data migration correctness (existing users/projects assigned roles)
- Error message clarity and user guidance

**Performance Tests:**
- Benchmark CanAccess method against 50ms requirement
- Load test assignment API against 200ms requirement
- Measure editor page load time with RBAC enabled
- Batch permission check performance vs. individual checks
- List view performance with 100+ flows/projects
- Specific load testing scenarios (100 concurrent users, 1000 flows)

**User Acceptance Tests:**
- Admin can manage all role assignments
- Editor cannot delete flows
- Viewer can execute but not modify flows
- Owner role cannot be removed from Starter Project
- Existing users can access their flows/projects after migration
- Error messages provide clear guidance on permission issues

**Observability Tests:**
- RBAC operation failures are logged with appropriate severity
- Metrics are recorded and queryable (latency, error rates)
- Alerts trigger on availability issues (>99.9% uptime)
- Health check endpoints return correct status

## Implementation Phases

### Phase 1: Core RBAC Data Model and Initialization

**Description:** Establish the foundational RBAC data model with all tables, relationships, seed data, and migration scripts. This phase creates the persistence layer without impacting existing functionality.

**Scope:** Database schema, models, seed data, migrations, data migration task

**Goals:**
- Define RBAC database tables
- Create SQLModel models with Pydantic schemas
- Seed predefined roles and permissions
- Migrate existing users/projects/flows to RBAC assignments
- Ensure referential integrity with foreign keys

**Entry Criteria:** PRD approved, architecture document reviewed

**Exit Criteria:** Database migrations run successfully, seed data loads correctly, all existing users/projects/flows assigned roles, all models pass validation

---

#### Task 1.1: Define Permission and Role Models

**Scope and Goals:**
Create the `Permission` and `Role` tables to store the predefined RBAC entities. Permissions represent CRUD actions (Create, Read, Update, Delete) applicable to Flow and Project entity types. Roles (Admin, Owner, Editor, Viewer) are predefined sets of permissions.

**Impact Subgraph:**
- New Nodes:
  - `ns0010`: Role (schema)
  - `ns0011`: Permission (schema)
- Modified Nodes: None
- Edges: None yet (associations defined in next task)

**Architecture & Tech Stack:**
- Framework: SQLModel (Pydantic + SQLAlchemy)
- Database: SQLite/PostgreSQL with async support (aiosqlite/asyncpg)
- Patterns: Table inheritance from SQLModel, Pydantic schemas for validation
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/services/database/models/rbac/__init__.py`
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/services/database/models/rbac/role.py`
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/services/database/models/rbac/permission.py`

**Implementation Details:**

Permission model:
```python
class Permission(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True, index=True)  # "Create", "Read", "Update", "Delete"
    description: str | None = Field(default=None)
    scope_type: str = Field(index=True)  # "Flow", "Project", "Global"
```

Role model:
```python
class Role(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True, index=True)  # "Admin", "Owner", "Editor", "Viewer"
    description: str | None = Field(default=None)
    is_system: bool = Field(default=True)  # Prevents deletion of predefined roles
```

**Success Criteria:**
- Models defined with correct fields and types
- Models include Pydantic schemas (Create, Read, Update)
- Unique constraints on role and permission names
- Models validate successfully with SQLModel
- Unit tests verify model creation and validation

---

#### Task 1.2: Define RolePermission Junction Table

**Scope and Goals:**
Create the many-to-many relationship table between roles and permissions. This defines which permissions each role has (e.g., Viewer has only Read permission, Owner has all CRUD permissions).

**Impact Subgraph:**
- New Nodes:
  - `ns0012`: RolePermission (schema)
- Modified Nodes: None
- Edges:
  - Role (1) → (N) RolePermission
  - Permission (1) → (N) RolePermission

**Architecture & Tech Stack:**
- Framework: SQLModel with Relationship() for ORM associations
- Patterns: Junction table pattern, composite foreign keys
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/services/database/models/rbac/role_permission.py`

**Implementation Details:**

```python
class RolePermission(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    role_id: UUID = Field(foreign_key="role.id", index=True)
    permission_id: UUID = Field(foreign_key="permission.id", index=True)

    # Relationships
    role: "Role" = Relationship(back_populates="role_permissions")
    permission: "Permission" = Relationship(back_populates="role_permissions")

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="unique_role_permission"),
    )
```

Update Role model:
```python
class Role(SQLModel, table=True):
    # ... existing fields ...
    role_permissions: list["RolePermission"] = Relationship(back_populates="role")
```

Update Permission model:
```python
class Permission(SQLModel, table=True):
    # ... existing fields ...
    role_permissions: list["RolePermission"] = Relationship(back_populates="permission")
```

**Success Criteria:**
- Junction table created with composite unique constraint
- Relationships defined bidirectionally
- Foreign key constraints enforced
- Unit tests verify relationship traversal (role.permissions, permission.roles)
- Attempting to create duplicate role-permission pair raises IntegrityError

---

#### Task 1.3: Define UserRoleAssignment Model

**Scope and Goals:**
Create the table that assigns roles to users for specific scopes (global, project, flow). This is the core assignment table that drives all permission checks. Supports the immutability constraint for Starter Project Owner assignments.

**Impact Subgraph:**
- New Nodes:
  - `ns0013`: UserRoleAssignment (schema)
- Modified Nodes:
  - `ns0001`: User (schema) - add relationship to assignments
- Edges:
  - User (1) → (N) UserRoleAssignment
  - Role (1) → (N) UserRoleAssignment
  - Flow (1) → (N) UserRoleAssignment (optional)
  - Folder (1) → (N) UserRoleAssignment (optional)

**Architecture & Tech Stack:**
- Framework: SQLModel with polymorphic scope relationships
- Patterns: Polymorphic association (scope_type + scope_id)
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/services/database/models/rbac/user_role_assignment.py`

**Implementation Details:**

```python
class UserRoleAssignment(SQLModel, table=True):
    __tablename__ = "user_role_assignment"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    role_id: UUID = Field(foreign_key="role.id", index=True)

    # Polymorphic scope
    scope_type: str = Field(index=True)  # "global", "project", "flow"
    scope_id: UUID | None = Field(default=None, nullable=True, index=True)

    # Immutability tracking (for Starter Project Owner)
    is_immutable: bool = Field(default=False)

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: UUID | None = Field(default=None, foreign_key="user.id")

    # Relationships
    user: "User" = Relationship(back_populates="role_assignments")
    role: "Role" = Relationship(back_populates="user_assignments")

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "scope_type", "scope_id",
                        name="unique_user_role_scope"),
        Index("idx_scope_lookup", "user_id", "scope_type", "scope_id"),
    )
```

Update User model to add relationship:
```python
# In src/backend/base/langbuilder/services/database/models/user/model.py
role_assignments: list["UserRoleAssignment"] = Relationship(back_populates="user")
```

**Database Index Performance Analysis:**

The index design for UserRoleAssignment has been carefully chosen to optimize permission check queries:

1. **idx_scope_lookup (user_id, scope_type, scope_id)**:
   - **Purpose**: Optimizes the most common query pattern: finding a user's assignments for a specific scope
   - **Query Pattern**: `SELECT * FROM user_role_assignment WHERE user_id = ? AND scope_type = ? AND scope_id = ?`
   - **Expected Performance**: Single index lookup, O(log n) complexity
   - **Rationale**: Permission checks always start with user_id and scope, making this a composite index covering all WHERE clauses

2. **Individual Indexes (user_id, role_id, scope_type, scope_id)**:
   - **Purpose**: Support filtering in admin UI and other non-permission-check queries
   - **Query Patterns**: Admin filtering by role, scope type, or individual ID
   - **Expected Performance**: O(log n) for each filter dimension
   - **Rationale**: Admin queries may filter on any combination of these fields

3. **Composite Unique Constraint (user_id, role_id, scope_type, scope_id)**:
   - **Purpose**: Prevents duplicate assignments (data integrity)
   - **Side Effect**: Creates implicit index that can be used for queries with all 4 fields
   - **Rationale**: Enforces business rule while providing query optimization

**Performance Characteristics:**
- Permission checks (most frequent): ~0.1-0.5ms per query with idx_scope_lookup
- Assignment list queries (admin UI): ~1-5ms with individual indexes
- Insert performance: ~1-2ms with all index updates
- Database size impact: ~15-20% storage overhead for indexes (acceptable for permission data)

**Success Criteria:**
- Table created with composite unique constraint
- Indexes created for efficient permission lookups
- Foreign key relationships established
- is_immutable flag prevents deletion when true
- Unit tests verify:
  - Global scope assignment (scope_type="global", scope_id=None)
  - Project scope assignment (scope_type="project", scope_id=project_id)
  - Flow scope assignment (scope_type="flow", scope_id=flow_id)
  - Immutability enforcement
- Performance test confirms permission check uses idx_scope_lookup (query plan analysis)
- Performance test confirms <50ms p95 for permission checks

---

#### Task 1.4: Create Alembic Migration for RBAC Tables

**Scope and Goals:**
Generate and test the Alembic migration that creates all RBAC tables in the correct order with all constraints. Ensure migration can be applied and rolled back cleanly.

**Impact Subgraph:**
- New Nodes: All schema nodes (ns0010, ns0011, ns0012, ns0013)
- Modified Nodes: None (migration only)
- Edges: All relationships defined in previous tasks

**Architecture & Tech Stack:**
- Framework: Alembic for schema migrations
- Patterns: Auto-generated migrations with manual review
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/alembic/versions/[timestamp]_add_rbac_tables.py`

**Implementation Details:**

```bash
# Generate migration
alembic revision --autogenerate -m "add_rbac_tables"

# Review and edit generated migration to ensure:
# 1. Tables created in correct order (role, permission, role_permission, user_role_assignment)
# 2. Indexes created
# 3. Foreign key constraints added
# 4. Unique constraints enforced

# Test migration
alembic upgrade head

# Test rollback
alembic downgrade -1
```

Migration should create tables in this order:
1. `role`
2. `permission`
3. `role_permission`
4. `user_role_assignment`

**Success Criteria:**
- Migration generates without errors
- Migration applies cleanly to empty database
- Migration applies cleanly to existing database with users/flows/folders
- **Rollback testing**: Migration rollback (`alembic downgrade -1`) successfully removes all RBAC tables without affecting existing tables
- **Rollback verification**: After rollback, application starts without errors and existing functionality works
- **Rollback testing on production snapshot**: Test rollback on copy of production data to ensure no data loss in related tables
- All foreign key constraints are enforced
- All indexes are created
- Manual testing on SQLite and PostgreSQL
- Migration can be rolled back multiple times without errors

---

#### Task 1.5: Create RBAC Seed Data Script

**Scope and Goals:**
Create an initialization script that populates the database with predefined roles, permissions, and role-permission mappings. This runs during application startup if RBAC tables are empty.

**Impact Subgraph:**
- New Nodes: ns0010, ns0011, ns0012 (populated with data)
- Modified Nodes: None
- Edges: Role-Permission associations per PRD

**Architecture & Tech Stack:**
- Framework: Python async functions using SQLModel ORM
- Patterns: Idempotent seed data (check before insert)
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/initial_setup/rbac_setup.py`

**Implementation Details:**

Predefined Permissions (per PRD 1.1, 1.2):
- Create (Flow, Project)
- Read (Flow, Project)
- Update (Flow, Project)
- Delete (Flow, Project)

Predefined Roles with Permissions (per PRD 1.2):
- **Admin**: All permissions on all scopes (global assignment)
- **Owner**: Create, Read, Update, Delete on assigned scope
- **Editor**: Create, Read, Update (no Delete) on assigned scope
- **Viewer**: Read only on assigned scope

Special Permission Rules (per PRD 1.2):
- Read permission enables: Flow execution, saving, exporting, downloading
- Update permission enables: Flow/Project import

**Success Criteria:**
- Script runs without errors on empty database
- Script is idempotent (can run multiple times safely)
- All 4 roles created (Admin, Owner, Editor, Viewer)
- All 8 permissions created (4 CRUD × 2 entity types)
- Role-permission mappings match PRD requirements:
  - Admin: 8 permissions
  - Owner: 8 permissions
  - Editor: 4 permissions (Create, Read, Update only)
  - Viewer: 2 permissions (Read only)
- Integration test verifies data integrity

---

#### Task 1.6: Integrate RBAC Initialization into Application Startup

**Scope and Goals:**
Add the RBAC seed data script to the application's lifespan startup sequence. Ensure it runs after database initialization but before the application accepts requests.

**Impact Subgraph:**
- New Nodes: None (integration only)
- Modified Nodes: Application startup logic
- Edges: None

**Architecture & Tech Stack:**
- Framework: FastAPI lifespan context manager
- Patterns: Async initialization with dependency on database service
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/main.py` (lifespan function)

**Implementation Details:**

Add to existing lifespan function after database initialization:

```python
# In src/backend/base/langbuilder/main.py

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # ... existing initialization steps (1-4) ...

    # 4b. Initialize RBAC data
    from langbuilder.initial_setup.rbac_setup import initialize_rbac_data
    async with get_db_service().with_session() as session:
        await initialize_rbac_data(session)

    # ... rest of initialization steps (5-10) ...
```

**Success Criteria:**
- Application starts successfully with RBAC initialization
- RBAC tables are populated on first startup
- Subsequent startups skip initialization (idempotent)
- No errors in application logs
- Integration test verifies roles and permissions exist after startup

---

#### Task 1.7: Create Data Migration Script for Existing Users and Projects

**Scope and Goals:**
Create a migration script that assigns RBAC roles to all existing users, projects, and flows based on current ownership. This ensures backward compatibility and allows all users to access their existing resources after RBAC enforcement is enabled. Superusers are granted Admin role globally, all other users are granted Owner roles for their owned flows/projects, and all existing projects/flows maintain their ownership assignments.

**Impact Subgraph:**
- Modified Nodes:
  - `ns0013`: UserRoleAssignment (schema) - populated with existing user data
  - `ns0001`: User (schema) - user assignments created
- Edges: User → UserRoleAssignment relationships for all existing users

**Architecture & Tech Stack:**
- Framework: Python async script using SQLModel ORM
- Patterns: Bulk insert with transaction rollback support
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/alembic/versions/[timestamp]_migrate_existing_users_to_rbac.py`
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/scripts/migrate_rbac_data.py`

**Implementation Details:**

Migration logic:
1. For each superuser (is_superuser=true): Create global Admin assignment
2. For each non-superuser: Create Owner assignment for each flow they own (user_id matches flow.user_id)
3. For each non-superuser: Create Owner assignment for each project they own (user_id matches folder.user_id)
4. For Starter Project: Mark Owner assignment as immutable (is_immutable=True)
5. Verify no assignments were created for users without owned resources
6. Provide rollback plan and success/error reporting

```python
async def migrate_existing_users_to_rbac(session: AsyncSession, dry_run: bool = True):
    """
    Migrate existing users/projects/flows to RBAC assignments.

    - Superusers get global Admin role
    - Regular users get Owner role for owned flows/projects
    - Starter Project Owner assignments are marked immutable
    """
    from langbuilder.services.database.models import User, Flow, Folder

    created_count = 0
    skipped_count = 0
    errors = []

    try:
        # Get all users
        users = await session.exec(select(User))
        users_list = users.all()

        # Get Admin and Owner roles
        admin_role = await session.exec(select(Role).where(Role.name == "Admin"))
        admin_role = admin_role.first()

        owner_role = await session.exec(select(Role).where(Role.name == "Owner"))
        owner_role = owner_role.first()

        if not admin_role or not owner_role:
            raise ValueError("Admin and Owner roles not found. Run seed data first.")

        for user in users_list:
            try:
                # Superusers get global Admin role
                if user.is_superuser:
                    existing = await session.exec(
                        select(UserRoleAssignment).where(
                            UserRoleAssignment.user_id == user.id,
                            UserRoleAssignment.role_id == admin_role.id,
                            UserRoleAssignment.scope_type == "global"
                        )
                    )
                    if not existing.first():
                        assignment = UserRoleAssignment(
                            user_id=user.id,
                            role_id=admin_role.id,
                            scope_type="global"
                        )
                        session.add(assignment)
                        created_count += 1
                    else:
                        skipped_count += 1
                else:
                    # Regular users: Owner of their flows and projects

                    # Flows
                    flows = await session.exec(
                        select(Flow).where(Flow.user_id == user.id)
                    )
                    for flow in flows.all():
                        existing = await session.exec(
                            select(UserRoleAssignment).where(
                                UserRoleAssignment.user_id == user.id,
                                UserRoleAssignment.role_id == owner_role.id,
                                UserRoleAssignment.scope_type == "flow",
                                UserRoleAssignment.scope_id == flow.id
                            )
                        )
                        if not existing.first():
                            assignment = UserRoleAssignment(
                                user_id=user.id,
                                role_id=owner_role.id,
                                scope_type="flow",
                                scope_id=flow.id
                            )
                            session.add(assignment)
                            created_count += 1

                    # Projects/Folders
                    projects = await session.exec(
                        select(Folder).where(Folder.user_id == user.id)
                    )
                    for project in projects.all():
                        existing = await session.exec(
                            select(UserRoleAssignment).where(
                                UserRoleAssignment.user_id == user.id,
                                UserRoleAssignment.role_id == owner_role.id,
                                UserRoleAssignment.scope_type == "project",
                                UserRoleAssignment.scope_id == project.id
                            )
                        )
                        if not existing.first():
                            assignment = UserRoleAssignment(
                                user_id=user.id,
                                role_id=owner_role.id,
                                scope_type="project",
                                scope_id=project.id,
                                # Mark Starter Project as immutable
                                is_immutable=(project.name == "Starter Project")
                            )
                            session.add(assignment)
                            created_count += 1
                        else:
                            # Mark as immutable if it's Starter Project
                            assignment = existing.first()
                            if project.name == "Starter Project":
                                assignment.is_immutable = True
                                session.add(assignment)
                                created_count += 1

            except Exception as e:
                errors.append(f"Error migrating user {user.id}: {str(e)}")

        if not dry_run:
            await session.commit()
            return {
                "status": "success",
                "created": created_count,
                "skipped": skipped_count,
                "errors": errors
            }
        else:
            await session.rollback()
            return {
                "status": "dry_run",
                "would_create": created_count,
                "would_skip": skipped_count,
                "errors": errors
            }

    except Exception as e:
        await session.rollback()
        return {
            "status": "error",
            "error": str(e),
            "created": created_count,
            "errors": errors
        }
```

**Success Criteria:**
- Script successfully migrates all existing users to RBAC assignments
- Superusers assigned global Admin role
- Regular users assigned Owner roles for owned flows and projects
- Starter Project Owner assignments marked immutable
- No data loss (all users can still access their resources)
- Script is idempotent (safe to run multiple times)
- Dry-run mode available for pre-deployment testing
- Comprehensive error reporting and rollback support
- Integration test on production data snapshot passes
- Documentation includes rollback instructions

---

### Phase 2: RBAC Service and Backend API Endpoints

**Description:** Implement the core RBAC business logic service and create RESTful API endpoints for role management and assignment operations. This phase builds the authorization engine and admin-only management APIs.

**Scope:** Service layer, API endpoints, permission evaluation logic

**Goals:**
- Create RBACService with can_access() method
- Implement API endpoints for listing roles and managing assignments
- Enforce admin-only access to RBAC management
- Support assignment creation, modification, deletion with immutability checks
- Implement batch permission check endpoint for list view optimization

**Entry Criteria:** Phase 1 complete, RBAC tables exist and populated, data migration successful

**Exit Criteria:** RBACService passes unit tests, API endpoints functional and secured, performance benchmarks met, batch permission checks working

---

#### Task 2.1: Implement RBACService Core Logic

**Scope and Goals:**
Create the central RBACService that evaluates user permissions. This service provides the `can_access(user_id, permission, scope_type, scope_id)` method used by all authorization checks. Implements Project-to-Flow permission inheritance and Admin bypass logic.

**Impact Subgraph:**
- New Nodes:
  - `nl0504`: RBACService (logic)
- Modified Nodes: None
- Edges: RBACService depends on User, Role, Permission, UserRoleAssignment models

**Architecture & Tech Stack:**
- Framework: Python async service following factory pattern
- Libraries: SQLModel for ORM queries
- Patterns: Singleton service via service manager, async methods, in-memory caching for role-permission mappings
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/services/rbac/service.py`
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/services/rbac/factory.py`
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/services/rbac/__init__.py`

**Implementation Details:**

Core methods:
- `can_access(user_id, permission_name, scope_type, scope_id=None) -> bool`: Check if user has permission for scope
- `get_user_assignments(user_id) -> list[UserRoleAssignment]`: Get all assignments for user
- `create_assignment(user_id, role_id, scope_type, scope_id=None, is_immutable=False)`: Create assignment
- `update_assignment(assignment_id, role_id)`: Update assignment role
- `delete_assignment(assignment_id)`: Delete assignment
- `initialize()`: Load role-permission cache on startup
- `_role_has_permission(role_id, permission_name, scope_type) -> bool`: Helper for cache lookup
- `invalidate_cache()`: Invalidate role-permission cache (called on role/permission updates)

Permission check logic (per PRD 2.1):
1. If user is Admin (global assignment) -> return True
2. Check for direct scope assignment (global/project/flow)
3. If scope_type is "flow" and no direct assignment, check inherited Project role
4. Return False if no permission found

**Cache Invalidation Strategy:**

The RBACService implements a dual-cache strategy with clear invalidation rules:

1. **Role-Permission Mappings Cache** (static data):
   - **What is cached**: The mapping of which permissions each role has (e.g., "Owner has Create, Read, Update, Delete")
   - **Cache lifetime**: 1 hour (TTL)
   - **Invalidation triggers**:
     - Manual: When admin updates role definitions (future feature)
     - Automatic: On service restart via `initialize()` method
     - TTL: After 1 hour, cache automatically refreshes
   - **Invalidation method**: Call `invalidate_cache()` to force refresh
   - **Rationale**: Role-permission mappings are static in MVP (predefined roles only), so aggressive caching is safe

2. **User Assignment Lookups** (dynamic data):
   - **What is NOT cached**: User role assignments (which users have which roles on which scopes)
   - **Cache lifetime**: Not cached in service (fresh database query every time)
   - **Rationale**: Assignments change frequently (admins add/remove roles), must always be current
   - **Client-side caching**: Frontend uses TanStack Query with 5-minute staleTime (see Task 4.4)

3. **Cache Consistency Guarantees**:
   - Role-permission cache refresh happens atomically (no partial updates)
   - If cache initialization fails on startup, service falls back to direct DB queries (graceful degradation)
   - Cache miss automatically triggers reload from database
   - No stale permission grants (assignments always fresh from DB)

4. **Performance Trade-offs**:
   - Cached role-permission lookups: ~0.01ms (in-memory)
   - Uncached user assignment lookups: ~0.5-2ms (database query with idx_scope_lookup)
   - Total permission check time: ~0.5-2ms (well under 50ms requirement)
   - Memory footprint: ~10KB for role-permission cache (4 roles × 8 permissions)

**Caching strategy:**
- Load role-permission mappings into memory on startup (static data)
- Cache expires after 1 hour or on manual invalidation via `invalidate_cache()`
- User assignment lookups use database (dynamic data)
- Graceful degradation: If cache fails, fall back to database queries

**Success Criteria:**
- All permission check methods implemented and tested
- Admin bypass works correctly (returns true for all checks)
- Permission inheritance works (Flow inherits from Project)
- Immutability prevents deletion when is_immutable=True
- Performance meets <50ms p95 benchmark with caching
- Cache invalidation works correctly (manual and TTL-based)
- Graceful degradation when cache initialization fails
- Unit tests for all permission scenarios
- Integration tests verify real database queries
- Unit tests verify cache invalidation behavior

---

#### Task 2.2: Create RBAC API Router and Endpoints

**Scope and Goals:**
Create FastAPI router with endpoints for RBAC management. All endpoints require Admin role. Implements:
- GET /api/v1/rbac/roles - List available roles
- GET /api/v1/rbac/assignments - List role assignments with filtering
- POST /api/v1/rbac/assignments - Create new assignment
- PATCH /api/v1/rbac/assignments/{id} - Update assignment
- DELETE /api/v1/rbac/assignments/{id} - Delete assignment
- GET /api/v1/rbac/check-permission - Single permission check
- POST /api/v1/rbac/check-permissions-batch (nl0511) - Batch permission checks

**Impact Subgraph:**
- New Nodes:
  - `nl0505`: GET /api/v1/rbac/roles (logic)
  - `nl0506`: GET /api/v1/rbac/assignments (logic)
  - `nl0507`: POST /api/v1/rbac/assignments (logic)
  - `nl0508`: PATCH /api/v1/rbac/assignments/{id} (logic)
  - `nl0509`: DELETE /api/v1/rbac/assignments/{id} (logic)
  - `nl0510`: GET /api/v1/rbac/check-permission (logic)
  - `nl0511`: POST /api/v1/rbac/check-permissions-batch (logic)
- Modified Nodes: None
- Edges: All endpoints depend on RBACService (nl0504)

**Architecture & Tech Stack:**
- Framework: FastAPI with dependency injection
- Libraries: Pydantic for request/response schemas
- Patterns: RESTful CRUD, Dependency injection for auth/service
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/rbac.py`

**Implementation Details:**

Auth dependency:
```python
async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require Admin role for endpoint access."""
    rbac_service = get_rbac_service()
    is_admin = await rbac_service.can_access(
        current_user.id, "Read", "global"
    )
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

GET /api/v1/rbac/roles:
```python
@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(current_user: User = Depends(require_admin)):
    """List all available roles."""
    rbac_service = get_rbac_service()
    return await rbac_service.list_roles()
```

GET /api/v1/rbac/assignments:
```python
@router.get("/assignments", response_model=list[AssignmentResponse])
async def list_assignments(
    user_id: Optional[UUID] = None,
    role_id: Optional[UUID] = None,
    scope_type: Optional[str] = None,
    current_user: User = Depends(require_admin)
):
    """List role assignments with filtering."""
    rbac_service = get_rbac_service()
    return await rbac_service.get_assignments(
        user_id=user_id, role_id=role_id, scope_type=scope_type
    )
```

POST /api/v1/rbac/check-permissions-batch (nl0511):
```python
@router.post("/check-permissions-batch")
async def check_permissions_batch(
    request: PermissionCheckBatchRequest,
    current_user: User = Depends(get_current_user)
):
    """Check multiple permissions in single request (for list view optimization)."""
    rbac_service = get_rbac_service()
    results = {}
    for resource in request.resources:
        results[resource.id] = await rbac_service.can_access(
            current_user.id,
            request.permission,
            resource.scope_type,
            resource.scope_id
        )
    return {"results": results}
```

**Success Criteria:**
- All 7 endpoints implemented and functional (including nl0511)
- Admin-only access enforced on all endpoints
- PATCH rejects immutable assignments with 400 error and clear message
- DELETE rejects immutable assignments with 400 error and clear message
- All responses follow OpenAPI spec
- Request validation with Pydantic
- Error responses include descriptive messages
- Batch permission endpoint (nl0511) reduces list view queries by N:1
- Batch endpoint documented in OpenAPI spec
- Unit tests for all endpoints
- Integration tests verify real permission checks
- Performance test confirms batch endpoint is 10x faster than individual checks

---

#### Task 2.3: Add Default User Role Assignments During Flow/Project Creation

**Scope and Goals:**
Integrate RBAC into flow and project creation endpoints so that new entities are automatically assigned to the creating user with Owner role. Also update User model to track default_project_id for Starter Project.

**Impact Subgraph:**
- Modified Nodes:
  - `nl0004`: Create Flow Endpoint Handler (logic)
  - `nl0003`: Create Project Endpoint Handler (logic)
  - `ns0001`: User (schema) - add default_project_id
- Edges: Creation endpoints now depend on RBACService for assignment

**Architecture & Tech Stack:**
- Framework: FastAPI endpoints, RBACService
- Patterns: Post-creation assignment in transaction
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/flows.py`
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/projects.py`

**Implementation Details:**

Update User model:
```python
class User(SQLModel, table=True):
    # ... existing fields ...
    default_project_id: UUID | None = Field(default=None, foreign_key="folder.id")
```

Flow creation update:
```python
@router.post("/flows")
async def create_flow(
    flow_request: FlowCreate,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
    db: AsyncSession = Depends(get_db)
):
    """Create a new flow and assign Owner role to creator."""
    # Create flow
    flow = Flow(**flow_request.dict(), user_id=current_user.id)
    db.add(flow)
    await db.flush()

    # Assign Owner role to creator
    owner_role = await db.exec(select(Role).where(Role.name == "Owner"))
    owner_role = owner_role.first()

    assignment = UserRoleAssignment(
        user_id=current_user.id,
        role_id=owner_role.id,
        scope_type="flow",
        scope_id=flow.id
    )
    db.add(assignment)
    await db.commit()

    return FlowResponse.from_orm(flow)
```

**Success Criteria:**
- New flows/projects automatically assigned to creator with Owner role
- Default project correctly set for new users
- Assignments created in same transaction as entity creation
- Unit tests verify assignment creation
- Integration tests verify Owner can access immediately after creation

---

### Phase 3: Permission Enforcement Throughout Application

**Description:** Integrate RBAC permission checks into existing endpoints for flows and projects. Enforce Read, Create, Update, Delete permissions at the API layer and implement permission-based UI filtering.

**Scope:** Flow endpoints, Project endpoints, Permission check integration

**Goals:**
- Enforce Read permission on flow/project list views
- Enforce Create permission on flow/project creation
- Enforce Update permission on flow/project modification
- Enforce Delete permission on flow/project deletion
- Implement permission inheritance from Project to Flow
- Add permission checks to all impacted endpoints

**Entry Criteria:** Phase 2 complete, RBACService and API endpoints working

**Exit Criteria:** All endpoints enforce permissions, permission inheritance working, users see only resources they can access

---

#### Task 3.1: Enforce Read/View Permission on Flow and Project Lists

**Scope and Goals:**
Update flow and project list endpoints to filter results by Read permission. Only return flows/projects the user has Read permission for. Implement batch permission checking to optimize performance for large lists using the nl0511 endpoint.

**Impact Subgraph:**
- Modified Nodes:
  - `nl0005`: List Flows Endpoint Handler (logic)
  - `nl0008`: List Projects Endpoint Handler (logic)
- Edges: List endpoints now check Read permission for each resource, use nl0511 for batch checks

**Architecture & Tech Stack:**
- Framework: FastAPI with RBACService dependency
- Libraries: TanStack Query (frontend) with caching
- Patterns: Async batch permission checks via nl0511, in-memory filtering
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/flows.py`
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/projects.py`

**Implementation Details:**

Backend approach:
```python
@router.get("/flows", response_model=list[FlowResponse])
async def list_flows(
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
    db: AsyncSession = Depends(get_db)
):
    """List flows with Read permission check."""
    # Get all flows (or paginated results)
    flows = await db.exec(select(Flow))

    # Filter by Read permission using batch check
    readable_flows = []
    for flow in flows.all():
        can_read = await rbac_service.can_access(
            current_user.id, "Read", "flow", flow.id
        )
        if can_read:
            readable_flows.append(flow)

    return [FlowResponse.from_orm(f) for f in readable_flows]
```

Or use batch endpoint nl0511 (more efficient):
```python
# In frontend: use batch permission check endpoint
const flows = await fetch("/api/v1/flows").then(r => r.json())
const permissions = await fetch("/api/v1/rbac/check-permissions-batch", {
    method: "POST",
    body: JSON.stringify({
        permission: "Read",
        resources: flows.map(f => ({id: f.id, scope_type: "flow", scope_id: f.id}))
    })
}).then(r => r.json())

const readableFlows = flows.filter((f, i) => permissions.results[f.id])
```

**Success Criteria:**
- List endpoints return only readable flows/projects
- Unreadable resources hidden from user (not in list)
- Batch permission check (nl0511) reduces N+1 query problem
- Performance still <2.5s for editor load time
- Unit tests verify filtering logic
- Integration tests verify permission checks work
- Performance test confirms batch check is faster than individual checks

---

#### Task 3.2: Enforce Create Permission on Flow and Project Creation

**Scope and Goals:**
Update flow and project creation endpoints to check Create permission before allowing creation. Check Create permission on the target project scope.

**Impact Subgraph:**
- Modified Nodes:
  - `nl0004`: Create Flow Endpoint Handler (logic)
  - `nl0003`: Create Project Endpoint Handler (logic)
- Edges: Creation endpoints now check Create permission

**Architecture & Tech Stack:**
- Framework: FastAPI with RBACService dependency
- Patterns: Permission check before operation
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/flows.py`
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/projects.py`

**Implementation Details:**

```python
@router.post("/flows")
async def create_flow(
    flow_request: FlowCreate,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
    db: AsyncSession = Depends(get_db)
):
    """Create a new flow with Create permission check."""
    # Check Create permission on project scope
    can_create = await rbac_service.can_access(
        current_user.id, "Create", "project", flow_request.folder_id
    )
    if not can_create:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to create flows in this project"
        )

    # ... create flow ...
```

**Success Criteria:**
- Create endpoints reject requests without Create permission
- Error message clearly indicates permission issue
- Unit tests verify permission check
- Integration tests verify unauthorized users cannot create

---

#### Task 3.3: Enforce Update Permission for Flow and Project Modification

**Scope and Goals:**
Update flow and project modification endpoints to check Update permission before allowing edits. Also implement read-only mode for users with Read but not Update permission.

**Impact Subgraph:**
- Modified Nodes:
  - `nl0009`: Update Flow Endpoint Handler (logic)
  - `nl0008`: Update Project Endpoint Handler (logic)
- Edges: Update endpoints now check Update permission

**Architecture & Tech Stack:**
- Framework: FastAPI with RBACService dependency
- Patterns: Permission check before operation
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/flows.py`
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/projects.py`

**Implementation Details:**

```python
@router.patch("/flows/{flow_id}")
async def update_flow(
    flow_id: UUID,
    flow_update: FlowUpdate,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
    db: AsyncSession = Depends(get_db)
):
    """Update a flow with Update permission check."""
    # Check Update permission
    can_update = await rbac_service.can_access(
        current_user.id, "Update", "flow", flow_id
    )
    if not can_update:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to update this flow"
        )

    # ... update flow ...
```

**Success Criteria:**
- Update endpoints reject requests without Update permission
- Error message clearly indicates permission issue
- Unit tests verify permission check
- Integration tests verify unauthorized users cannot update

---

#### Task 3.4: Enforce Delete Permission for Flow and Project Deletion

**Scope and Goals:**
Update flow and project deletion endpoints to check Delete permission. Only Admin and Owner can delete resources.

**Impact Subgraph:**
- Modified Nodes:
  - `nl0010`: Delete Flow Endpoint Handler (logic)
  - `nl0009`: Delete Project Endpoint Handler (logic)
- Edges: Delete endpoints now check Delete permission

**Architecture & Tech Stack:**
- Framework: FastAPI with RBACService dependency
- Patterns: Permission check before operation
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/flows.py`
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/projects.py`

**Implementation Details:**

```python
@router.delete("/flows/{flow_id}")
async def delete_flow(
    flow_id: UUID,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
    db: AsyncSession = Depends(get_db)
):
    """Delete a flow with Delete permission check."""
    # Check Delete permission
    can_delete = await rbac_service.can_access(
        current_user.id, "Delete", "flow", flow_id
    )
    if not can_delete:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this flow"
        )

    # ... delete flow ...
```

**Success Criteria:**
- Delete endpoints reject requests without Delete permission
- Only Admin and Owner roles have Delete permission
- Error message clearly indicates permission issue
- Unit tests verify permission check
- Integration tests verify unauthorized users cannot delete

---

#### Task 3.5: Enforce RBAC on Project and Associated Flows

**Scope and Goals:**
Ensure all flow endpoints (get, list, create, update, delete) enforce permissions. Implement permission inheritance from Project to contained Flows. Flows inherit project-level permissions unless explicit flow-specific role is assigned.

**Impact Subgraph:**
- Modified Nodes:
  - `nl0005`: List Flows Endpoint Handler
  - `nl0007`: Get Flow by ID Endpoint Handler
  - `nl0004`: Create Flow Endpoint Handler
  - `nl0009`: Update Flow Endpoint Handler
  - `nl0010`: Delete Flow Endpoint Handler
  - `ni0006`: CollectionPage (modified for permission checks)
  - `ni0009`: FlowPage (modified for permission checks)
- Edges: All flow endpoints now enforce RBAC

**Architecture & Tech Stack:**
- Framework: FastAPI with RBACService dependency
- Patterns: Consistent permission enforcement across all endpoints
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/flows.py`
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/projects.py`

**Implementation Details:**

Get flow by ID with inheritance check:
```python
@router.get("/flows/{flow_id}", response_model=FlowResponse)
async def get_flow(
    flow_id: UUID,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
    db: AsyncSession = Depends(get_db)
):
    """Get flow by ID with Read permission check."""
    # Check Read permission (checks flow-specific, then project-inherited)
    can_read = await rbac_service.can_access(
        current_user.id, "Read", "flow", flow_id
    )
    if not can_read:
        raise HTTPException(status_code=403, detail="Access denied")

    flow = await db.get(Flow, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    return FlowResponse.from_orm(flow)
```

**Success Criteria:**
- All flow endpoints enforce appropriate permissions
- Permission inheritance works (Flow inherits from Project)
- Explicit flow permissions override inherited project permissions
- Unit tests verify inheritance logic
- Integration tests verify end-to-end permission enforcement

---

#### Task 3.6: Implement Permission-Based UI Filtering

**Scope and Goals:**
Add permission checks to the frontend to hide/disable UI elements based on user permissions. This includes hiding Create/Delete buttons for users lacking permission, disabling form inputs, and showing permission-denied messages.

**Impact Subgraph:**
- Modified Nodes:
  - `ni0006`: CollectionPage (show/hide actions based on permissions)
  - `ni0009`: FlowPage (show/hide buttons based on permissions)
- Edges: UI components use usePermission hook for permission checks

**Architecture & Tech Stack:**
- Framework: React with TypeScript
- Libraries: TanStack Query for data fetching, usePermission hook
- Patterns: Conditional rendering based on permissions
- File Locations:
  - `/home/nick/LangBuilder/src/frontend/src/pages/CollectionPage/index.tsx`
  - `/home/nick/LangBuilder/src/frontend/src/pages/FlowPage/index.tsx`

**Implementation Details:**

Example filtering in CollectionPage:
```typescript
export function CollectionPage() {
    const { flows } = useFlows()
    const { canRead, canCreate, canDelete } = usePermission()

    return (
        <div>
            {canCreate && (
                <button onClick={handleCreate}>Create Flow</button>
            )}

            {flows.map(flow => (
                <FlowCard key={flow.id} flow={flow}>
                    {canRead(flow.id) && (
                        <button onClick={() => navigate(`/flows/${flow.id}`)}>
                            View
                        </button>
                    )}
                    {canDelete(flow.id) && (
                        <button onClick={() => deleteFlow(flow.id)}>
                            Delete
                        </button>
                    )}
                </FlowCard>
            ))}
        </div>
    )
}
```

**Success Criteria:**
- UI elements hidden when user lacks permission
- Read-only mode for Viewer/Editor users
- Batch permission checks (nl0511) reduce API calls
- Error messages shown for denied actions
- Unit tests verify UI logic
- Integration tests verify end-to-end UI behavior

---

### Phase 4: Frontend RBAC Management UI

**Description:** Create the web-based admin interface for managing role assignments. Implement the RBAC Management section in AdminPage with tabbed interface, assignment list view, and create/edit workflows.

**Scope:** Frontend UI components, RBAC management interface

**Goals:**
- Create RBAC Management tab in AdminPage
- Implement Assignment List view with filtering
- Create Assignment creation wizard
- Implement error handling with user-friendly messages
- Implement usePermission hook and RBACGuard component

**Entry Criteria:** Phase 3 complete, permission enforcement working

**Exit Criteria:** Admin can manage assignments via UI, all UI workflows functional, error messages clear and actionable

---

#### Task 4.1: Create RBAC Management Page Tab in AdminPage

**Scope and Goals:**
Add RBAC Management section to AdminPage with tabbed interface. Default tab is User Management, second tab is RBAC Management. Implement deep linking support for direct access to RBAC section.

**Impact Subgraph:**
- New Nodes:
  - `ni0083`: RBACManagementPage (interface)
- Modified Nodes:
  - `ni0001`: AdminPage (add RBAC tab)
- Edges: AdminPage contains RBACManagementPage

**Architecture & Tech Stack:**
- Framework: React 18.3.1 with TypeScript 5.4.5
- Libraries: Radix UI tabs, React Router for deep linking
- Patterns: Tab-based navigation, conditional rendering
- File Locations:
  - `/home/nick/LangBuilder/src/frontend/src/pages/AdminPage/RBACManagementPage/index.tsx`
  - `/home/nick/LangBuilder/src/frontend/src/pages/AdminPage/index.tsx`

**Implementation Details:**

AdminPage update:
```typescript
export function AdminPage() {
    const [activeTab, setActiveTab] = useState("user-management")
    const location = useLocation()

    // Check for deep link
    useEffect(() => {
        if (location.hash === "#rbac") {
            setActiveTab("rbac-management")
        }
    }, [location])

    return (
        <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
                <TabsTrigger value="user-management">
                    User Management
                </TabsTrigger>
                <TabsTrigger value="rbac-management">
                    RBAC Management
                </TabsTrigger>
            </TabsList>

            <TabsContent value="user-management">
                <UserManagementSection />
            </TabsContent>

            <TabsContent value="rbac-management">
                <RBACManagementPage />
            </TabsContent>
        </Tabs>
    )
}
```

**Success Criteria:**
- RBAC Management tab visible in AdminPage
- User Management is default tab
- RBAC Management accessible via deep link (#rbac)
- Non-admin users cannot see RBAC Management tab
- Tab switching works smoothly
- Unit tests verify tab navigation

---

#### Task 4.2: Create Assignment List View with Filtering

**Scope and Goals:**
Implement the main assignment list view showing all User:Role:Scope assignments. Support filtering by User, Role, and Scope. Show inherited roles from Project to Flow with clear messaging. Provide inline delete actions with enhanced error messages for immutable assignments.

**Impact Subgraph:**
- New Nodes:
  - `ni0084`: AssignmentListView (interface)
- Modified Nodes: None
- Edges: RBACManagementPage contains AssignmentListView

**Architecture & Tech Stack:**
- Framework: React with TypeScript
- Libraries: TanStack Query for data fetching, TanStack Table for table rendering
- Libraries: Radix UI for components (Select, Input, Button)
- Patterns: Server state management with TanStack Query, component composition
- File Locations:
  - `/home/nick/LangBuilder/src/frontend/src/pages/AdminPage/RBACManagementPage/AssignmentListView.tsx`

**Implementation Details:**

Assignment list component:
```typescript
export function AssignmentListView() {
    const [userFilter, setUserFilter] = useState<string>("")
    const [roleFilter, setRoleFilter] = useState<string>("")
    const [scopeFilter, setScopeFilter] = useState<string>("")

    const { data: assignments, isLoading } = useQuery({
        queryKey: ["rbac-assignments", { userFilter, roleFilter, scopeFilter }],
        queryFn: () => api.rbac.getAssignments({
            user_id: userFilter,
            role_id: roleFilter,
            scope_type: scopeFilter
        })
    })

    const deleteMutation = useMutation({
        mutationFn: api.rbac.deleteAssignment,
        onSuccess: () => queryClient.invalidateQueries(["rbac-assignments"]),
        onError: (error: any) => {
            // Enhanced error message for immutable assignments
            if (error.status === 400 && error.detail.includes("immutable")) {
                showErrorAlert(
                    "Cannot modify Starter Project Owner assignment. " +
                    "This assignment is protected to ensure users always have access to their default project."
                )
            } else {
                showErrorAlert(error.detail || "Failed to delete assignment")
            }
        }
    })

    return (
        <div>
            {/* Filters */}
            <div className="filters">
                <Input
                    placeholder="Filter by user"
                    value={userFilter}
                    onChange={(e) => setUserFilter(e.target.value)}
                />
                <Select value={roleFilter} onValueChange={setRoleFilter}>
                    <option value="">All Roles</option>
                    <option value="admin">Admin</option>
                    <option value="owner">Owner</option>
                    <option value="editor">Editor</option>
                    <option value="viewer">Viewer</option>
                </Select>
                <Select value={scopeFilter} onValueChange={setScopeFilter}>
                    <option value="">All Scopes</option>
                    <option value="global">Global</option>
                    <option value="project">Project</option>
                    <option value="flow">Flow</option>
                </Select>
            </div>

            {/* Inheritance message */}
            <div className="info-message">
                Project-level assignments are inherited by contained Flows and can be
                overridden by explicit Flow-specific roles.
            </div>

            {/* Table */}
            <Table>
                {assignments?.map(assignment => (
                    <TableRow key={assignment.id}>
                        <TableCell>{assignment.user.name}</TableCell>
                        <TableCell>{assignment.role.name}</TableCell>
                        <TableCell>{assignment.scope_type}</TableCell>
                        <TableCell>{assignment.scope_id || "Global"}</TableCell>
                        <TableCell>
                            {assignment.is_immutable ? (
                                <Badge>Immutable</Badge>
                            ) : (
                                <Button
                                    onClick={() => deleteMutation.mutate(assignment.id)}
                                    variant="destructive"
                                >
                                    Delete
                                </Button>
                            )}
                        </TableCell>
                    </TableRow>
                ))}
            </Table>
        </div>
    )
}
```

**Success Criteria:**
- Assignment list displays all User:Role:Scope assignments
- Filtering works by User, Role, and Scope
- Inheritance message clearly displayed
- Inline delete works for non-immutable assignments
- Immutable assignments show "Immutable" badge and disable delete
- Error messages are clear and actionable (especially for immutable assignments)
- Real-time updates on assignment changes
- Unit tests verify filtering logic
- Integration tests verify UI behavior

---

#### Task 4.3: Create Assignment Creation and Edit Wizard

**Scope and Goals:**
Implement multi-step wizard for creating and editing role assignments. Workflow: Select User → Select Scope → Select Role → Confirm. Include validation, error handling with enhanced messages, and immutability checks.

**Impact Subgraph:**
- New Nodes:
  - `ni0085`: CreateAssignmentModal (interface)
- Modified Nodes: None
- Edges: RBACManagementPage contains CreateAssignmentModal

**Architecture & Tech Stack:**
- Framework: React with TypeScript
- Libraries: Radix UI (Dialog, Select), React Hook Form for state, Zod for validation
- Patterns: Multi-step form wizard, controlled components
- File Locations:
  - `/home/nick/LangBuilder/src/frontend/src/pages/AdminPage/RBACManagementPage/CreateAssignmentModal.tsx`

**Implementation Details:**

Assignment wizard component:
```typescript
type WizardStep = "select-user" | "select-scope" | "select-role" | "confirm"

export function CreateAssignmentModal({ open, onClose }: Props) {
    const [step, setStep] = useState<WizardStep>("select-user")
    const [selectedUser, setSelectedUser] = useState<User | null>(null)
    const [selectedScope, setSelectedScope] = useState<Scope | null>(null)
    const [selectedRole, setSelectedRole] = useState<Role | null>(null)

    const createMutation = useMutation({
        mutationFn: api.rbac.createAssignment,
        onSuccess: () => {
            queryClient.invalidateQueries(["rbac-assignments"])
            onClose()
            showSuccessAlert("Assignment created successfully")
        },
        onError: (error: any) => {
            // Enhanced error messages
            if (error.status === 400) {
                if (error.detail.includes("duplicate")) {
                    showErrorAlert(
                        `This user already has the ${selectedRole?.name} role for this ${selectedScope?.type}. ` +
                        "Please edit the existing assignment instead."
                    )
                } else if (error.detail.includes("immutable")) {
                    showErrorAlert(
                        "Cannot modify this assignment. Starter Project Owner assignments are protected."
                    )
                } else {
                    showErrorAlert(error.detail || "Failed to create assignment")
                }
            } else {
                showErrorAlert("An unexpected error occurred. Please try again.")
            }
        }
    })

    const handleConfirm = () => {
        createMutation.mutate({
            user_id: selectedUser!.id,
            role_id: selectedRole!.id,
            scope_type: selectedScope!.type,
            scope_id: selectedScope!.id
        })
    }

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent>
                {step === "select-user" && (
                    <UserSelectionStep
                        onSelect={(user) => {
                            setSelectedUser(user)
                            setStep("select-scope")
                        }}
                    />
                )}

                {step === "select-scope" && (
                    <ScopeSelectionStep
                        onSelect={(scope) => {
                            setSelectedScope(scope)
                            setStep("select-role")
                        }}
                        onBack={() => setStep("select-user")}
                    />
                )}

                {step === "select-role" && (
                    <RoleSelectionStep
                        onSelect={(role) => {
                            setSelectedRole(role)
                            setStep("confirm")
                        }}
                        onBack={() => setStep("select-scope")}
                    />
                )}

                {step === "confirm" && (
                    <ConfirmationStep
                        user={selectedUser!}
                        scope={selectedScope!}
                        role={selectedRole!}
                        onConfirm={handleConfirm}
                        onBack={() => setStep("select-role")}
                    />
                )}
            </DialogContent>
        </Dialog>
    )
}
```

**Success Criteria:**
- Multi-step wizard works smoothly (4 steps)
- User can navigate forward and backward
- Only 4 default roles + Admin are selectable
- Validation prevents invalid assignments
- Error messages are specific and actionable (duplicate, immutable, etc.)
- Confirmation step shows summary
- Assignment created successfully
- Core Role Assignment Logic (Epic 1.3) called on confirm
- Unit tests verify wizard flow
- Integration tests verify end-to-end creation

---

#### Task 4.4: Create usePermission Hook and RBACGuard Component

**Scope and Goals:**
Implement custom React hook for permission checks and guard component for conditional rendering. Hook should cache results and provide methods for checking Create, Read, Update, Delete permissions. Guard should render children only if permission is granted.

**Impact Subgraph:**
- New Nodes:
  - `ni0086`: RBACGuard (interface)
  - `ni0087`: usePermission (interface)
- Modified Nodes: None
- Edges: All permission-aware components use these utilities

**Architecture & Tech Stack:**
- Framework: React hooks, TypeScript
- Libraries: TanStack Query for caching
- Patterns: Custom hooks, render props, conditional rendering
- File Locations:
  - `/home/nick/LangBuilder/src/frontend/src/hooks/usePermission.ts`
  - `/home/nick/LangBuilder/src/frontend/src/components/rbac/RBACGuard.tsx`

**Implementation Details:**

usePermission hook:
```typescript
export function usePermission() {
    const { user } = useAuth()

    // Check single permission
    const checkPermission = async (
        permission: Permission,
        scopeType: ScopeType,
        scopeId?: string
    ): Promise<boolean> => {
        const response = await api.rbac.checkPermission({
            permission,
            scope_type: scopeType,
            scope_id: scopeId
        })
        return response.granted
    }

    // Use TanStack Query for caching
    const usePermissionQuery = (
        permission: Permission,
        scopeType: ScopeType,
        scopeId?: string
    ) => {
        return useQuery({
            queryKey: ["permission", user?.id, permission, scopeType, scopeId],
            queryFn: () => checkPermission(permission, scopeType, scopeId),
            staleTime: 5 * 60 * 1000, // 5 minutes cache
            gcTime: 10 * 60 * 1000, // 10 minutes garbage collection
            enabled: !!user
        })
    }

    // Convenience methods
    const canCreate = (scopeType: ScopeType, scopeId?: string) => {
        const { data } = usePermissionQuery("Create", scopeType, scopeId)
        return data ?? false
    }

    const canRead = (scopeType: ScopeType, scopeId?: string) => {
        const { data } = usePermissionQuery("Read", scopeType, scopeId)
        return data ?? false
    }

    const canUpdate = (scopeType: ScopeType, scopeId?: string) => {
        const { data } = usePermissionQuery("Update", scopeType, scopeId)
        return data ?? false
    }

    const canDelete = (scopeType: ScopeType, scopeId?: string) => {
        const { data } = usePermissionQuery("Delete", scopeType, scopeId)
        return data ?? false
    }

    return { canCreate, canRead, canUpdate, canDelete, checkPermission }
}
```

**Frontend Caching Strategy Details:**

The usePermission hook implements a sophisticated client-side caching strategy using TanStack Query to minimize API calls while ensuring permission checks remain reasonably fresh:

1. **Cache Duration (staleTime: 5 minutes)**:
   - **Rationale**: Permission assignments typically don't change frequently during a user's session
   - **Trade-off**: 5-minute window where permission changes won't be reflected immediately
   - **Mitigation**: Acceptable for most use cases; critical operations still check server-side
   - **Alternative considered**: 1 minute (too aggressive), 15 minutes (too stale)

2. **Garbage Collection (gcTime: 10 minutes)**:
   - **Purpose**: Keep unused permission checks in memory for 10 minutes after last use
   - **Rationale**: User may navigate back to pages and reuse same permissions
   - **Memory impact**: Minimal (~100 bytes per permission check × typical 50 checks = 5KB)

3. **Cache Invalidation Triggers**:
   - **Explicit invalidation**: When admin modifies assignments, invalidate affected user's cache
   - **Background refetch**: TanStack Query automatically refetches on window focus after staleTime
   - **Manual invalidation**: Call `queryClient.invalidateQueries(["permission"])` when needed

4. **Batch Optimization**:
   - **List views use batch endpoint (nl0511)**: Instead of individual permission checks, fetch multiple at once
   - **Cache population**: Batch results populate individual query caches
   - **Performance gain**: 10x reduction in API calls for list views with 50+ items

5. **Staleness vs. Security**:
   - **Server-side enforcement**: All actions are permission-checked on server (authoritative)
   - **Client-side caching**: Only affects UI visibility, not actual authorization
   - **Security guarantee**: Even if cache is stale, server blocks unauthorized actions
   - **User experience**: Fresh enough to prevent confusion, stale enough to reduce API load

6. **Performance Characteristics**:
   - **Cache hit (warm)**: ~0.01ms (in-memory)
   - **Cache miss (cold)**: ~50-100ms (API call to single permission endpoint)
   - **Batch check (50 items)**: ~100-200ms vs. 2500-5000ms for individual checks
   - **Memory usage**: ~5-10KB for typical user session (negligible)

7. **Edge Cases Handled**:
   - **User not logged in**: Queries disabled, all permissions default to false
   - **Network error**: Return cached value if available, false otherwise
   - **Concurrent requests**: TanStack Query deduplicates requests for same permission

RBACGuard component:
```typescript
interface RBACGuardProps {
    permission: Permission
    scopeType: ScopeType
    scopeId?: string
    children: React.ReactNode
    fallback?: React.ReactNode
}

export function RBACGuard({
    permission,
    scopeType,
    scopeId,
    children,
    fallback = null
}: RBACGuardProps) {
    const { user } = useAuth()

    const { data: hasPermission, isLoading } = useQuery({
        queryKey: ["permission", user?.id, permission, scopeType, scopeId],
        queryFn: async () => {
            const response = await api.rbac.checkPermission({
                permission,
                scope_type: scopeType,
                scope_id: scopeId
            })
            return response.granted
        },
        staleTime: 5 * 60 * 1000, // 5 minutes cache
        gcTime: 10 * 60 * 1000,
        enabled: !!user
    })

    if (isLoading) {
        return <>{fallback}</>
    }

    if (!hasPermission) {
        return <>{fallback}</>
    }

    return <>{children}</>
}
```

**Success Criteria:**
- usePermission hook provides permission check methods
- Hook results are cached for 5 minutes (staleTime)
- RBACGuard conditionally renders children based on permission
- RBACGuard shows fallback when permission denied
- Cache reduces API calls (multiple checks for same permission use cache)
- Cache invalidation works correctly (on assignment changes)
- Batch permission checks populate individual caches
- Unit tests verify hook behavior
- Integration tests verify guard behavior
- Performance test confirms cache effectiveness

---

#### Task 4.5: Implement Read-Only Mode for FlowPage

**Scope and Goals:**
Implement read-only mode for FlowPage when user has Read permission but not Update permission. Show clear message about permission limitations and disable all form inputs while allowing view and execute actions.

**Impact Subgraph:**
- Modified Nodes:
  - `ni0009`: FlowPage (interface)
- Edges: FlowPage uses usePermission hook

**Architecture & Tech Stack:**
- Framework: React with TypeScript
- Libraries: usePermission hook
- Patterns: Conditional rendering, prop drilling for readOnly state
- File Locations:
  - `/home/nick/LangBuilder/src/frontend/src/pages/FlowPage/index.tsx`

**Implementation Details:**

FlowPage with read-only mode:
```typescript
export function FlowPage({ flowId }: Props) {
    const { canUpdate, canRead } = usePermission()
    const canEdit = canUpdate("flow", flowId)
    const canView = canRead("flow", flowId)

    if (!canView) {
        return <AccessDeniedMessage />
    }

    if (!canEdit) {
        return (
            <div>
                <div className="info-banner">
                    You have read-only access to this flow. You can view and execute the flow,
                    but editing requires Update permission.
                </div>
                <FlowEditor flow={flow} readOnly={true} />
            </div>
        )
    }

    return <FlowEditor flow={flow} readOnly={false} />
}
```

**Success Criteria:**
- Read-only mode detected and displayed correctly
- Form inputs disabled in read-only mode
- Edit buttons hidden in read-only mode
- Clear message about permission limitations
- Execute button still available
- Unit tests verify read-only logic
- Integration tests verify mode detection

---

### Phase 5: Testing, Performance, Monitoring, and Documentation

**Description:** Implement comprehensive testing, performance benchmarking, monitoring/observability, and documentation for the RBAC system. Ensure all requirements are met and system is production-ready.

**Scope:** Unit tests, integration tests, performance tests, monitoring setup, documentation

**Goals:**
- Comprehensive test coverage for RBAC functionality
- Performance benchmarking against PRD requirements
- RBAC operation monitoring and observability
- Complete documentation and migration guide
- Alerting for availability issues

**Entry Criteria:** All implementation phases complete, system functional end-to-end

**Exit Criteria:** All tests passing, performance requirements met, monitoring in place, documentation complete

---

#### Task 5.1: Implement Unit and Integration Tests

**Scope and Goals:**
Create comprehensive unit tests for RBACService, models, and utilities. Create integration tests for API endpoints and permission enforcement. Achieve >90% code coverage for RBAC components.

**Impact Subgraph:**
- Modified Nodes: All RBAC components have unit/integration tests
- Edges: Tests cover all relationships and permission logic

**Architecture & Tech Stack:**
- Framework: pytest for backend, Jest/Vitest for frontend
- Libraries: pytest-asyncio for async tests, unittest.mock for mocking
- Patterns: Arrange-Act-Assert, test fixtures, parametrized tests
- File Locations:
  - `/home/nick/LangBuilder/tests/unit/rbac/`
  - `/home/nick/LangBuilder/tests/integration/rbac/`
  - `/home/nick/LangBuilder/src/frontend/src/__tests__/rbac/`

**Implementation Details:**

Example unit tests:
```python
@pytest.mark.asyncio
async def test_rbac_service_can_access_admin_bypass(rbac_service, admin_user):
    """Admin users bypass all permission checks."""
    # Arrange
    await rbac_service.initialize()

    # Act
    result = await rbac_service.can_access(admin_user.id, "Delete", "flow", uuid4())

    # Assert
    assert result is True


@pytest.mark.asyncio
async def test_rbac_service_permission_inheritance(rbac_service, user, project, flow):
    """Flow inherits permissions from project."""
    # Arrange
    await rbac_service.initialize()

    # Create project-level Owner assignment
    project_assignment = UserRoleAssignment(
        user_id=user.id,
        role_id=owner_role.id,
        scope_type="project",
        scope_id=project.id
    )
    session.add(project_assignment)
    await session.commit()

    # Act
    result = await rbac_service.can_access(user.id, "Update", "flow", flow.id)

    # Assert
    assert result is True  # Inherited from project


@pytest.mark.asyncio
async def test_immutable_assignment_cannot_be_deleted(rbac_service, assignment):
    """Immutable assignments cannot be deleted."""
    # Arrange
    assignment.is_immutable = True

    # Act & Assert
    with pytest.raises(ValueError):
        await rbac_service.delete_assignment(assignment.id)
```

Example integration tests:
```python
@pytest.mark.asyncio
async def test_create_flow_endpoint_checks_create_permission(client, user_without_permission):
    """Flow creation endpoint enforces Create permission."""
    # Act
    response = await client.post(
        "/api/v1/flows",
        json={"name": "Test Flow", "description": "Test"},
        headers={"Authorization": f"Bearer {get_token(user_without_permission)}"}
    )

    # Assert
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_flows_filters_by_read_permission(client, user, readable_flow, unreadable_flow):
    """List flows endpoint filters by Read permission."""
    # Act
    response = await client.get(
        "/api/v1/flows",
        headers={"Authorization": f"Bearer {get_token(user)}"}
    )

    # Assert
    assert response.status_code == 200
    flows = response.json()
    assert any(f["id"] == readable_flow.id for f in flows)
    assert not any(f["id"] == unreadable_flow.id for f in flows)
```

Frontend tests:
```typescript
describe("usePermission hook", () => {
    it("should check permissions", async () => {
        const { result } = renderHook(() => usePermission())

        const canRead = await result.current.canRead(flowId)

        expect(canRead).toBe(true)
    })

    it("should cache permission results", async () => {
        const { result } = renderHook(() => usePermission())

        await result.current.canRead(flowId)
        await result.current.canRead(flowId)

        expect(fetchMock).toHaveBeenCalledTimes(1)  // Cached
    })
})

describe("RBACGuard component", () => {
    it("should render children if permission granted", () => {
        const { getByText } = render(
            <RBACGuard permission="Read" scopeType="flow" scopeId={flowId}>
                <div>Allowed content</div>
            </RBACGuard>
        )

        expect(getByText("Allowed content")).toBeInTheDocument()
    })

    it("should render fallback if permission denied", () => {
        const { getByText } = render(
            <RBACGuard
                permission="Read"
                scopeType="flow"
                scopeId={flowId}
                fallback={<div>Denied</div>}
            >
                <div>Allowed content</div>
            </RBACGuard>
        )

        expect(getByText("Denied")).toBeInTheDocument()
    })
})
```

**Success Criteria:**
- >90% code coverage for RBAC components
- All unit tests passing
- All integration tests passing
- Tests cover permission scenarios (admin bypass, inheritance, denial)
- Tests cover CRUD operations
- Performance tests verify <50ms requirement
- Frontend tests verify component behavior

---

#### Task 5.2: Implement Performance Benchmarking and Optimization

**Scope and Goals:**
Create performance tests to benchmark RBAC operations against PRD requirements. Optimize permission checks, API endpoints, and frontend queries. Ensure all latency targets are met: <50ms for CanAccess (p95), <200ms for assignment API (p95), <2.5s for editor load (p95). Include specific load testing scenarios.

**Impact Subgraph:**
- Modified Nodes: All components potentially optimized
- Edges: Performance monitoring integrated

**Architecture & Tech Stack:**
- Framework: pytest-benchmark for backend, Lighthouse for frontend
- Libraries: asyncio profiling, memory_profiler
- Patterns: Load testing, profiling, optimization
- File Locations:
  - `/home/nick/LangBuilder/tests/performance/rbac_benchmarks.py`
  - `/home/nick/LangBuilder/tests/performance/editor_load_test.js`

**Implementation Details:**

Performance benchmarking:
```python
@pytest.mark.performance
async def test_can_access_latency(benchmark, rbac_service, user, flow):
    """Benchmark can_access method against <50ms requirement."""
    await rbac_service.initialize()

    async def check_permission():
        return await rbac_service.can_access(user.id, "Read", "flow", flow.id)

    result = benchmark(lambda: asyncio.run(check_permission()))

    # p95 should be <50ms
    assert benchmark.stats.get_p95() < 0.050


@pytest.mark.performance
async def test_list_flows_with_permission_checks(benchmark, client, user):
    """Benchmark list flows endpoint with permission filtering."""

    def list_flows():
        return client.get(
            "/api/v1/flows",
            headers={"Authorization": f"Bearer {get_token(user)}"}
        )

    result = benchmark(list_flows)

    # Should complete in <1s for 100 flows
    assert benchmark.stats.median < 1.0


@pytest.mark.performance
async def test_batch_permission_check_optimization(benchmark, client, user):
    """Benchmark batch permission check endpoint (nl0511)."""

    def batch_check():
        return client.post(
            "/api/v1/rbac/check-permissions-batch",
            json={
                "permission": "Read",
                "resources": [
                    {"id": str(uuid4()), "scope_type": "flow", "scope_id": str(uuid4())}
                    for _ in range(50)
                ]
            },
            headers={"Authorization": f"Bearer {get_token(user)}"}
        )

    result = benchmark(batch_check)

    # Batch should be faster than individual checks
    assert benchmark.stats.median < 0.100
```

**Specific Load Testing Scenarios:**

To ensure the RBAC system performs well under realistic production conditions, the following load testing scenarios must be executed and pass:

1. **Scenario 1: Concurrent Permission Checks**
   - **Setup**: 100 users simultaneously checking permissions for different flows
   - **Load pattern**: 100 concurrent connections, each making 10 permission checks
   - **Expected result**: p95 latency < 50ms for individual checks, no errors
   - **Tools**: Locust or k6 for load generation
   - **Pass criteria**: All checks complete successfully, p95 < 50ms, no database connection pool exhaustion

2. **Scenario 2: Large List View with Permission Filtering**
   - **Setup**: User with access to 1000 flows viewing list page
   - **Load pattern**: Single user, batch permission check for 1000 flows
   - **Expected result**: Page load < 2.5s p95, batch check completes in <500ms
   - **Tools**: Playwright for browser automation, backend profiling
   - **Pass criteria**: Full page load (including batch check) < 2.5s, no timeout errors

3. **Scenario 3: Assignment Creation Under Load**
   - **Setup**: 10 admins simultaneously creating role assignments
   - **Load pattern**: 10 concurrent connections, each creating 20 assignments
   - **Expected result**: p95 latency < 200ms per assignment, no race conditions
   - **Tools**: Locust for load generation
   - **Pass criteria**: All assignments created successfully, p95 < 200ms, no duplicate assignments due to race conditions

4. **Scenario 4: Permission Inheritance at Scale**
   - **Setup**: User with project-level Owner role accessing 500 flows in that project
   - **Load pattern**: Sequential access to 500 flows, permission checks for each
   - **Expected result**: Average check < 10ms (using cache), p95 < 50ms
   - **Tools**: pytest with profiling
   - **Pass criteria**: Cache hit rate > 95%, average latency < 10ms, p95 < 50ms

5. **Scenario 5: Mixed Workload**
   - **Setup**: 50 concurrent users performing typical operations (list, read, create, update)
   - **Load pattern**: 50 concurrent users, 80% read operations, 15% write, 5% admin operations
   - **Expected result**: All operations complete within SLA, no degradation over 10 minutes
   - **Tools**: Locust with realistic user behavior scripts
   - **Pass criteria**: p95 latencies within requirements for all operations, 99.9% success rate

6. **Scenario 6: Cache Effectiveness**
   - **Setup**: 1000 permission checks for same user/permission/scope combinations
   - **Load pattern**: Sequential checks with cache warm-up
   - **Expected result**: Cache hit rate > 99%, cached checks < 1ms
   - **Tools**: pytest with cache monitoring
   - **Pass criteria**: Cache hit rate > 99%, cached check latency < 1ms, cache memory < 50MB

**Success Criteria:**
- CanAccess check: < 50ms p95 (PRD 5.1)
- Assignment API: < 200ms p95 (PRD 5.1)
- Editor load: < 2.5s p95 (PRD 5.3)
- Batch permission check (nl0511) 10x faster than N individual checks
- All 6 load testing scenarios pass
- Performance tests included in CI/CD
- Optimization recommendations documented
- Performance regression tests prevent future degradation

---

#### Task 5.3: Add RBAC Monitoring, Observability, and Health Checks

**Scope and Goals:**
Integrate RBAC operations with existing OpenTelemetry telemetry service. Add logging and metrics for permission checks, assignments, and failures. Create health check endpoints for RBACService availability. Set up alerts for permission check failures and timeouts. Ensure 99.9% system availability per PRD 5.2.

**Impact Subgraph:**
- Modified Nodes:
  - `nl0504`: RBACService (add monitoring)
  - API endpoints (add telemetry)
- Edges: All RBAC operations logged/metered

**Architecture & Tech Stack:**
- Framework: OpenTelemetry (existing telemetry service)
- Libraries: loguru for structured logging
- Libraries: prometheus-client for metrics
- Patterns: Decorator pattern for instrumentation, context propagation
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/services/rbac/monitoring.py`
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/rbac.py` (update with telemetry)

**Implementation Details:**

```python
# monitoring.py
from opentelemetry import metrics, trace
from loguru import logger

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Metrics
permission_check_counter = meter.create_counter(
    "rbac.permission_checks.total",
    description="Total permission checks",
    unit="1"
)

permission_check_latency = meter.create_histogram(
    "rbac.permission_checks.latency",
    description="Permission check latency in milliseconds",
    unit="ms"
)

permission_check_failures = meter.create_counter(
    "rbac.permission_checks.failures",
    description="Permission check failures",
    unit="1"
)

assignment_operation_counter = meter.create_counter(
    "rbac.assignments.total",
    description="Total assignment operations",
    unit="1"
)

# RBACService with monitoring
class MonitoredRBACService(RBACService):
    async def can_access(self, user_id, permission, scope_type, scope_id=None):
        start_time = time.time()

        with tracer.start_as_current_span("rbac.can_access") as span:
            span.set_attribute("user_id", str(user_id))
            span.set_attribute("permission", permission)
            span.set_attribute("scope_type", scope_type)

            try:
                result = await super().can_access(user_id, permission, scope_type, scope_id)

                # Record metrics
                latency_ms = (time.time() - start_time) * 1000
                permission_check_counter.add(1, {"permission": permission, "granted": result})
                permission_check_latency.record(latency_ms)

                # Log
                logger.debug(
                    f"Permission check: user={user_id}, perm={permission}, "
                    f"result={result}, latency={latency_ms:.2f}ms"
                )

                # Alert if slow
                if latency_ms > 100:
                    logger.warning(
                        f"Slow permission check: {latency_ms:.2f}ms "
                        f"(user={user_id}, perm={permission})"
                    )

                return result

            except Exception as e:
                # Record failure
                permission_check_failures.add(1, {"permission": permission})
                logger.error(f"Permission check failed: {str(e)}")
                raise

    async def create_assignment(self, user_id, role_id, scope_type, scope_id=None):
        with tracer.start_as_current_span("rbac.create_assignment") as span:
            span.set_attribute("user_id", str(user_id))
            span.set_attribute("role_id", str(role_id))
            span.set_attribute("scope_type", scope_type)

            try:
                result = await super().create_assignment(user_id, role_id, scope_type, scope_id)
                assignment_operation_counter.add(1, {"operation": "create"})
                logger.info(f"Assignment created: {result.id}")
                return result
            except Exception as e:
                logger.error(f"Assignment creation failed: {str(e)}")
                raise


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check for RBACService."""
    rbac_service = get_rbac_service()

    try:
        # Quick permission check to verify service is responsive
        await rbac_service.can_access(uuid4(), "Read", "global")

        return {
            "status": "healthy",
            "service": "rbac",
            "cache_initialized": rbac_service._cache_initialized,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "rbac",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, 503
```

Alerting configuration:
```yaml
# prometheus.yml rules
- alert: RBACPermissionCheckHighLatency
  expr: rbac_permission_checks_latency_bucket{le="100"} < rbac_permission_checks_latency_bucket{le="+Inf"} * 0.05
  for: 5m
  annotations:
    summary: "RBAC permission checks have high latency"

- alert: RBACPermissionCheckFailures
  expr: rate(rbac_permission_checks_failures_total[5m]) > 0.01
  annotations:
    summary: "RBAC permission check failure rate elevated"

- alert: RBACServiceUnavailable
  expr: up{job="langbuilder-rbac"} == 0
  for: 1m
  annotations:
    summary: "RBAC service is unavailable"
```

**Success Criteria:**
- Permission check latency metrics recorded
- Assignment operation metrics recorded
- All failures logged with context
- Health check endpoint functional
- Alerts trigger on latency/failure thresholds
- Monitoring dashboard shows RBAC metrics
- 99.9% availability maintained (max 43 minutes downtime per month)
- No permission check timeout failures
- Integration tests verify monitoring integration

---

#### Task 5.4: Create Migration Guide and Documentation

**Scope and Goals:**
Create comprehensive documentation including migration guide for deploying RBAC to production, API documentation, admin guide, and troubleshooting guide. Document how existing users will be migrated, how to verify migration success, and how to rollback if needed.

**Impact Subgraph:**
- No code changes, documentation only
- Reference: All RBAC components

**Architecture & Tech Stack:**
- Format: Markdown, OpenAPI spec
- Tools: MkDocs for documentation site
- File Locations:
  - `/home/nick/LangBuilder/docs/rbac/`
  - `/home/nick/LangBuilder/docs/rbac/MIGRATION_GUIDE.md`
  - `/home/nick/LangBuilder/docs/rbac/ADMIN_GUIDE.md`
  - `/home/nick/LangBuilder/docs/rbac/API_REFERENCE.md`
  - `/home/nick/LangBuilder/docs/rbac/TROUBLESHOOTING.md`

**Implementation Details:**

Documentation sections:
1. **Migration Guide** - Step-by-step production deployment
   - Pre-deployment checklist
   - Data backup procedure
   - Migration script execution
   - Verification steps
   - Rollback procedure

2. **Admin Guide** - How to manage RBAC
   - Accessing RBAC Management section
   - Creating assignments
   - Editing/deleting assignments
   - Understanding permission inheritance
   - Common scenarios

3. **API Reference** - API endpoint documentation
   - All endpoints documented with examples
   - Request/response schemas
   - Error codes and meanings
   - Rate limiting info

4. **Troubleshooting** - Common issues and solutions
   - Permission denied errors
   - Performance issues
   - Data consistency issues
   - How to verify system health

5. **Architecture Overview** - RBAC design and operation
   - Permission model explained
   - Permission inheritance rules
   - Role definitions
   - Performance characteristics

**Success Criteria:**
- Migration guide clear and comprehensive
- Step-by-step instructions for deployment
- Pre/post-deployment checklists
- Rollback procedure documented
- Admin guide covers all workflows
- API documentation complete and accurate
- Troubleshooting guide covers common issues
- Documentation reviewed and approved
- Screenshots/diagrams included where helpful

---

#### Task 5.5: End-to-End User Acceptance Testing

**Scope and Goals:**
Conduct comprehensive user acceptance testing with admin users and regular users. Test complete workflows: admin managing assignments, users accessing resources with correct permissions, permission inheritance, error scenarios.

**Impact Subgraph:**
- No code changes, testing of all components
- Reference: All phases

**Architecture & Tech Stack:**
- Framework: Manual testing with checklist, automated Selenium tests optional
- Patterns: UAT scenarios mapped to PRD user stories
- File Locations:
  - `/home/nick/LangBuilder/docs/rbac/UAT_CHECKLIST.md`
  - `/home/nick/LangBuilder/tests/e2e/rbac/`

**Implementation Details:**

UAT scenarios:
1. **Admin User Scenarios**
   - Admin can access RBAC Management section
   - Admin can create assignment (User → Scope → Role → Confirm)
   - Admin can view all assignments with filtering
   - Admin can edit non-immutable assignments
   - Admin can delete non-immutable assignments
   - Admin sees clear message about Starter Project immutability

2. **Regular User Scenarios**
   - User cannot access RBAC Management section
   - User can see only flows/projects they have Read permission for
   - Owner can create/edit/delete owned flows
   - Editor can create/edit but not delete flows
   - Viewer can only view flows, cannot edit/delete
   - Read-only editor mode displays for Viewer/Editor

3. **Permission Inheritance Scenarios**
   - User with Project-level Owner inherits permission for all flows
   - Explicit Flow-level permission overrides Project-level
   - Permission changes immediately reflected in UI

4. **Error Scenarios**
   - Attempting to delete Starter Project assignment shows clear error message
   - Attempting to create duplicate assignment shows error
   - Attempting to access unauthorized resource shows permission error
   - Network failure gracefully handled

5. **Data Migration Scenarios**
   - Existing users can access their flows after migration
   - Existing owners are assigned Owner role
   - Superusers are assigned Admin role
   - Starter Projects are marked immutable

**Success Criteria:**
- All UAT scenarios pass
- No data loss after migration
- Users can perform all expected actions
- Permission errors are clear and helpful
- System performs well under normal load
- Rollback can be completed successfully
- Documentation accurately reflects system behavior

---

## Dependencies and Ordering

The implementation follows a clear dependency chain:

**Phase 1** (Independent - can be done first):
- Task 1.1 → 1.2 → 1.3 (data models sequential)
- Task 1.4 (depends on 1.1-1.3)
- Task 1.5 (depends on 1.1-1.3)
- Task 1.6 (depends on 1.5)
- Task 1.7 (depends on 1.1-1.3 and 1.5)

**Phase 2** (depends on Phase 1):
- Task 2.1 (depends on Phase 1 complete)
- Task 2.2 (depends on 2.1)
- Task 2.3 (depends on 2.1, 2.2)

**Phase 3** (depends on Phase 2):
- Tasks 3.1-3.5 (all depend on Phase 2 complete)
- Task 3.6 (depends on 3.1-3.5)

**Phase 4** (depends on Phase 3):
- Task 4.1 (independent, depends on Phase 3)
- Task 4.2-4.5 (depend on 4.1)

**Phase 5** (depends on all):
- Tasks 5.1-5.5 (can be mostly parallel, some dependencies for integration tests)

## Risk Assessment

**Risk: Performance Degradation**
- Probability: Medium | Impact: High
- Mitigation: Implement caching, indexing, and benchmark against PRD requirements
- Monitoring: Add telemetry to track permission check latency (Task 5.3)
- Contingency: Pre-computed permission tables if caching insufficient

**Risk: Data Migration Failures**
- Probability: Medium | Impact: High
- Mitigation: Comprehensive migration script with dry-run mode (Task 1.7)
- Testing: Test migrations on copy of production data before deployment
- Contingency: Rollback script to revert assignments if migration fails

**Risk: Breaking Existing Functionality**
- Probability: Low | Impact: High
- Mitigation: Preserve superuser bypass during transition
- Testing: Comprehensive integration tests for all existing endpoints (Task 5.1)
- Contingency: Feature flags to disable RBAC enforcement if issues detected

**Risk: Complex Permission Inheritance**
- Probability: Medium | Impact: Medium
- Mitigation: Clear precedence rules (Flow-specific > Project-inherited > None)
- Testing: Unit tests for all inheritance scenarios (Task 5.1)
- Documentation: Clear explanation of inheritance rules (Task 5.4)

**Risk: Availability Impact**
- Probability: Low | Impact: High
- Mitigation: Health checks for RBACService availability (Task 5.3)
- Monitoring: Alerts on permission check failures or timeouts (Task 5.3)
- Contingency: Cache allows offline operation during brief DB issues

**Risk: User Confusion with New Admin Interface**
- Probability: Medium | Impact: Medium
- Mitigation: Clear UI with step-by-step wizard (Task 4.3)
- Documentation: Admin guide with screenshots (Task 5.4)
- UAT: Test with real admin users (Task 5.5)

## Testing Strategy

Covered in Phase 5:
- **Unit Tests** (Task 5.1): RBACService, models, utilities
- **Integration Tests** (Task 5.1): API endpoints, permission enforcement
- **Performance Tests** (Task 5.2): Latency benchmarking with specific load scenarios
- **E2E Tests** (Task 5.5): User workflows and scenarios
- **UAT** (Task 5.5): Admin and regular user scenarios

Test coverage targets:
- >90% code coverage for RBAC components
- All permission scenarios covered
- All CRUD operations tested
- Performance requirements verified with 6 specific load testing scenarios
- All UAT scenarios pass

## Audit Resolution Summary

### v2.0 Audit Recommendations Addressed in v3.0

#### Minor Recommendation 1: Batch Permission Endpoint Documentation
- **Status**: ADDRESSED
- **Resolution**: Added nl0511 explicitly to Task 2.2 impact subgraph and documented throughout
- **Details**: POST /api/v1/rbac/check-permissions-batch now has explicit node ID (nl0511) in AppGraph references and implementation details
- **Verification**: Task 2.2 success criteria includes performance test for batch endpoint

#### Minor Recommendation 2: Cache Invalidation Strategy
- **Status**: ADDRESSED
- **Resolution**: Added comprehensive "Cache Invalidation Strategy" section to Task 2.1
- **Details**: Documented dual-cache strategy (role-permission vs. user assignments), TTL (1 hour), invalidation triggers, graceful degradation, and performance trade-offs
- **Verification**: Task 2.1 success criteria includes cache invalidation behavior tests

#### Minor Recommendation 3: Rollback Testing to Schema Migration
- **Status**: ADDRESSED
- **Resolution**: Enhanced Task 1.4 success criteria with explicit rollback testing requirements
- **Details**: Added 4 new success criteria: rollback testing, rollback verification, rollback on production snapshot, multiple rollback attempts
- **Verification**: Task 1.4 now requires testing rollback on production data copy

#### Minor Recommendation 4: Specific Load Testing Scenarios
- **Status**: ADDRESSED
- **Resolution**: Added "Specific Load Testing Scenarios" section to Task 5.2 with 6 detailed scenarios
- **Details**: Documented 6 scenarios with setup, load pattern, expected results, tools, and pass criteria for each
- **Verification**: Task 5.2 success criteria now includes "All 6 load testing scenarios pass"

#### Minor Recommendation 5: Database Index Performance Analysis
- **Status**: ADDRESSED
- **Resolution**: Added "Database Index Performance Analysis" section to Task 1.3
- **Details**: Documented purpose, query patterns, expected performance, and rationale for each index; added performance characteristics and side effects
- **Verification**: Task 1.3 success criteria includes query plan analysis and performance tests

#### Minor Recommendation 6: Frontend Caching Strategy Details
- **Status**: ADDRESSED
- **Resolution**: Added "Frontend Caching Strategy Details" section to Task 4.4
- **Details**: Documented cache duration rationale, trade-offs, invalidation triggers, batch optimization, staleness vs. security, performance characteristics, and edge cases
- **Verification**: Task 4.4 success criteria includes cache effectiveness verification

### v1.0 Audit Recommendations (Previously Addressed in v2.0)

#### Audit Recommendation 1: Monitoring & Observability for 99.9% Uptime
- **Status**: ADDRESSED (v2.0)
- **Resolution**: Added Task 5.3 "Add RBAC Monitoring, Observability, and Health Checks"
- **Details**: Includes OpenTelemetry integration, structured logging, metrics for all RBAC operations, health check endpoints, and alerting for failures/timeouts
- **Verification**: Health checks confirm RBACService availability, metrics show latency/error rates, alerts trigger on availability issues

#### Audit Recommendation 2: Explicit Data Migration Task
- **Status**: ADDRESSED (v2.0)
- **Resolution**: Added Task 1.7 "Create Data Migration Script for Existing Users and Projects"
- **Details**: Script assigns roles to existing users based on ownership (superusers get Admin, others get Owner), preserves Starter Project immutability, includes dry-run mode and rollback support
- **Verification**: Integration test confirms all users can access their resources after migration, no data loss, rollback succeeds

#### Audit Recommendation 3: Batch Permission Check Optimization
- **Status**: ADDRESSED (v2.0, enhanced in v3.0)
- **Resolution**: Added POST /api/v1/rbac/check-permissions-batch endpoint (nl0511) in Task 2.2
- **Details**: Enables checking multiple permissions in single request, reduces N+1 queries in list views, includes implementation details in Task 2.2 and Task 3.1
- **Verification**: Performance test shows batch checks 10x faster than individual checks (Task 5.2)

#### Audit Recommendation 4: Enhanced Error Messages
- **Status**: ADDRESSED (v2.0)
- **Resolution**: Enhanced error handling in Tasks 4.2, 4.3, and throughout API layer
- **Details**: Specific error messages for common RBAC scenarios (e.g., "You don't have permission to delete this flow. Contact your administrator to request Owner access."), clear messaging for immutable assignments, actionable guidance
- **Verification**: Integration tests verify error message clarity, UAT confirms users understand permission issues (Task 5.5)

## Conclusion

The v3.0 implementation plan addresses all minor recommendations from the v2.0 audit while maintaining the comprehensive structure and all improvements from v2.0. Key enhancements in v3.0:

1. **nl0511 explicitly documented**: Batch permission endpoint now has formal node ID throughout the plan
2. **Cache invalidation strategy clarified**: Comprehensive documentation of cache behavior, invalidation triggers, and performance trade-offs
3. **Rollback testing enhanced**: Explicit rollback testing requirements for schema migrations including production data testing
4. **Load testing scenarios defined**: 6 specific, detailed scenarios with pass criteria for realistic production conditions
5. **Database index analysis added**: Performance analysis and rationale for all index choices
6. **Frontend caching strategy documented**: Detailed explanation of client-side caching with TanStack Query, trade-offs, and edge cases

The plan now provides a complete, production-ready RBAC implementation with:
- Strong operational support (monitoring, observability, health checks)
- Clear migration path from current state (data migration, rollback)
- Performance optimization (caching, indexing, batch operations)
- Enhanced user experience (clear error messages, responsive UI)
- Comprehensive testing coverage (unit, integration, performance, UAT)
- Detailed documentation (migration guide, admin guide, API reference, troubleshooting)

All audit findings from v1.0 and v2.0 have been addressed, resulting in an implementation plan rated "PASS WITH MINOR RECOMMENDATIONS" that are now fully resolved in v3.0.
