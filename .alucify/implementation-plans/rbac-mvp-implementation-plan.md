# RBAC MVP Implementation Plan

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

**Key Constraints Discovered:**

1. **Database**: SQLModel/SQLAlchemy with async support, migrations via Alembic
2. **Service Pattern**: Services use factory pattern with dependency injection via FastAPI `Depends()`
3. **API Structure**: RESTful endpoints under `/api/v1/` with clear CRUD patterns
4. **Frontend State**: TanStack Query for server state, Zustand for client state, React Context for auth
5. **Authorization Guards**: Route-level guards using React components that check auth state
6. **Starter Projects**: System creates default "Starter Project" for each user - Owner role is immutable per PRD 1.4

## Desired End State

### System State After Implementation

**Data Layer:**
- Four database tables: `role`, `permission`, `role_permission`, `user_role_assignment`
- Predefined roles (Admin, Owner, Editor, Viewer) with permission mappings
- User role assignments linked to global, project, or flow scopes
- Automatic Owner assignment on project/flow creation
- Immutable Owner assignment for Starter Projects

**Service Layer:**
- RBACService providing `can_access(user_id, permission, scope_type, scope_id)` method
- Service caching for performance (p95 < 50ms per PRD 5.1)
- Integration with existing auth utilities

**API Layer:**
- `/api/v1/rbac/roles` - List available roles
- `/api/v1/rbac/assignments` - CRUD operations for role assignments (admin only)
- `/api/v1/rbac/check-permission` - Permission check endpoint for frontend
- All existing Flow and Project endpoints enforce RBAC permissions

**Frontend Layer:**
- RBAC Management section in AdminPage with tabbed interface
- Assignment list view with filtering by user, role, scope
- Create/edit assignment wizard modal
- `usePermission` hook for permission checks
- RBACGuard component for route/component-level permission enforcement
- UI elements (buttons, lists) filtered based on user permissions

### Verification Criteria

**Data Integrity:**
- Database migrations execute without errors
- Role and permission seed data loads correctly
- Foreign key constraints enforce referential integrity

**Functional:**
- Admin can create, modify, delete role assignments via UI
- Non-admin users cannot access RBAC management
- Permission checks return results < 50ms (p95)
- Users see only resources they have Read permission for
- Create/Update/Delete actions blocked when user lacks permission
- Starter Project Owner role cannot be modified or deleted
- Project-level roles inherit to contained Flows
- Flow-specific roles override inherited Project roles

**Performance:**
- CanAccess check: < 50ms p95 (PRD 5.1)
- Assignment API calls: < 200ms p95 (PRD 5.1)
- Editor page load with RBAC: < 2.5s p95 (PRD 5.3)

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
Existing superuser checks (`is_superuser`) will be preserved during migration. Superusers will be automatically granted Admin role globally. This allows for gradual rollout and rollback if needed.

**4. Progressive Enhancement:**
- Phase 1: Data model and backend services (no breaking changes)
- Phase 2: Backend API endpoints and enforcement (Admin role required)
- Phase 3: Frontend UI for management (Admin only)
- Phase 4: Integration and enforcement across all endpoints

**5. Performance Optimization:**
- In-memory caching of role-permission mappings (static data)
- Database indexing on user_id, scope_type, scope_id
- Async batch loading for list view permission checks

### Why This Approach

**Database-First**: Ensures data integrity and allows for incremental feature development without breaking changes.

**Service Abstraction**: Single point of control makes the system easier to test, debug, and enhance. Reduces code duplication across endpoints.

**Backward Compatibility**: Minimizes risk during deployment. Existing admin users continue to work during transition period.

**Progressive Enhancement**: Each phase delivers value independently and can be tested in isolation. Reduces risk of large-scale failures.

### Risk Mitigation Strategies

**Risk: Performance Degradation**
- Mitigation: Implement caching, indexing, and benchmark against PRD requirements
- Monitoring: Add telemetry to track permission check latency

**Risk: Data Migration Failures**
- Mitigation: Comprehensive Alembic migration with rollback support
- Testing: Test migrations on copy of production data before deployment

**Risk: Breaking Existing Functionality**
- Mitigation: Preserve superuser bypass during transition
- Testing: Comprehensive integration tests for all existing endpoints

**Risk: Complex Permission Inheritance**
- Mitigation: Clear precedence rules (Flow-specific > Project-inherited > None)
- Testing: Unit tests for all inheritance scenarios

### Testing Strategy

**Unit Tests:**
- RBACService permission evaluation logic
- Role-permission mapping correctness
- Assignment creation/modification/deletion logic
- Immutability enforcement for Starter Projects

**Integration Tests:**
- End-to-end permission checks through API endpoints
- Flow and Project CRUD operations with RBAC enforcement
- Admin UI workflow for creating assignments
- Permission inheritance from Project to Flow

**Performance Tests:**
- Benchmark CanAccess method against 50ms requirement
- Load test assignment API against 200ms requirement
- Measure editor page load time with RBAC enabled

**User Acceptance Tests:**
- Admin can manage all role assignments
- Editor cannot delete flows
- Viewer can execute but not modify flows
- Owner role cannot be removed from Starter Project

## Implementation Phases

### Phase 1: Core RBAC Data Model and Initialization

**Description:** Establish the foundational RBAC data model with all tables, relationships, seed data, and migration scripts. This phase creates the persistence layer without impacting existing functionality.

**Scope:** Database schema, models, seed data, migrations

**Goals:**
- Define RBAC database tables
- Create SQLModel models with Pydantic schemas
- Seed predefined roles and permissions
- Ensure referential integrity with foreign keys

**Entry Criteria:** PRD approved, architecture document reviewed

**Exit Criteria:** Database migrations run successfully, seed data loads correctly, all models pass validation

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
- Rollback removes all RBAC tables without affecting existing tables
- All foreign key constraints are enforced
- All indexes are created
- Manual testing on SQLite and PostgreSQL

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

```python
async def initialize_rbac_data(session: AsyncSession):
    """Seed RBAC tables with predefined roles and permissions."""

    # Check if already initialized
    existing_roles = await session.exec(select(Role))
    if existing_roles.first():
        return  # Already initialized

    # Create Permissions
    permissions = {
        "flow_create": Permission(name="Create", scope_type="Flow", description="Create new flows"),
        "flow_read": Permission(name="Read", scope_type="Flow", description="View and execute flows"),
        "flow_update": Permission(name="Update", scope_type="Flow", description="Edit and import flows"),
        "flow_delete": Permission(name="Delete", scope_type="Flow", description="Delete flows"),
        "project_create": Permission(name="Create", scope_type="Project", description="Create new projects"),
        "project_read": Permission(name="Read", scope_type="Project", description="View projects"),
        "project_update": Permission(name="Update", scope_type="Project", description="Edit and import projects"),
        "project_delete": Permission(name="Delete", scope_type="Project", description="Delete projects"),
    }

    for perm in permissions.values():
        session.add(perm)
    await session.commit()

    # Create Roles
    roles = {
        "admin": Role(name="Admin", description="Full system access", is_system=True),
        "owner": Role(name="Owner", description="Full access to owned resources", is_system=True),
        "editor": Role(name="Editor", description="Create, read, and update access", is_system=True),
        "viewer": Role(name="Viewer", description="Read-only access", is_system=True),
    }

    for role in roles.values():
        session.add(role)
    await session.commit()

    # Map Roles to Permissions
    role_permission_mappings = {
        "admin": list(permissions.values()),  # All permissions
        "owner": list(permissions.values()),  # All permissions
        "editor": [p for k, p in permissions.items() if "delete" not in k],  # No delete
        "viewer": [p for k, p in permissions.items() if "read" in k],  # Read only
    }

    for role_name, perms in role_permission_mappings.items():
        role = roles[role_name]
        for perm in perms:
            rp = RolePermission(role_id=role.id, permission_id=perm.id)
            session.add(rp)

    await session.commit()
```

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

### Phase 2: RBAC Service and Backend API Endpoints

**Description:** Implement the core RBAC business logic service and create RESTful API endpoints for role management and assignment operations. This phase builds the authorization engine and admin-only management APIs.

**Scope:** Service layer, API endpoints, permission evaluation logic

**Goals:**
- Create RBACService with can_access() method
- Implement API endpoints for listing roles and managing assignments
- Enforce admin-only access to RBAC management
- Support assignment creation, modification, deletion with immutability checks

**Entry Criteria:** Phase 1 complete, RBAC tables exist and populated

**Exit Criteria:** RBACService passes unit tests, API endpoints functional and secured, performance benchmarks met

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

```python
class RBACService:
    """Core RBAC service for permission evaluation."""

    def __init__(self):
        self._role_permission_cache: dict[UUID, set[str]] = {}
        self._cache_initialized = False

    async def initialize(self):
        """Load role-permission mappings into memory."""
        async with get_db_service().with_session() as session:
            # Load all role-permission mappings
            stmt = select(RolePermission).options(
                selectinload(RolePermission.role),
                selectinload(RolePermission.permission)
            )
            results = await session.exec(stmt)

            for rp in results.all():
                if rp.role_id not in self._role_permission_cache:
                    self._role_permission_cache[rp.role_id] = set()
                self._role_permission_cache[rp.role_id].add(
                    f"{rp.permission.name}:{rp.permission.scope_type}"
                )

        self._cache_initialized = True

    async def can_access(
        self,
        user_id: UUID,
        permission_name: str,
        scope_type: str,
        scope_id: UUID | None = None,
    ) -> bool:
        """
        Check if user has permission for given scope.

        Logic (per PRD 2.1):
        1. Check if user is Admin (global assignment) -> True
        2. Check for direct scope-specific assignment
        3. If scope_type == "Flow", check for inherited Project assignment
        4. Return False if no matching assignment found
        """
        async with get_db_service().with_session() as session:
            # Step 1: Check for Admin role (global assignment)
            admin_stmt = select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.role.has(Role.name == "Admin"),
                UserRoleAssignment.scope_type == "global"
            )
            admin_assignment = await session.exec(admin_stmt)
            if admin_assignment.first():
                return True

            # Step 2: Check for direct scope assignment
            direct_stmt = select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.scope_type == scope_type,
                UserRoleAssignment.scope_id == scope_id
            ).options(selectinload(UserRoleAssignment.role))

            direct_assignment = await session.exec(direct_stmt)
            if assignment := direct_assignment.first():
                if self._role_has_permission(assignment.role_id, permission_name, scope_type):
                    return True

            # Step 3: Check for inherited Project assignment (Flow scope only)
            if scope_type == "flow" and scope_id:
                # Get flow's project
                flow_stmt = select(Flow).where(Flow.id == scope_id)
                flow = await session.exec(flow_stmt)
                if flow_obj := flow.first():
                    if flow_obj.folder_id:
                        # Check for Project-level assignment
                        project_stmt = select(UserRoleAssignment).where(
                            UserRoleAssignment.user_id == user_id,
                            UserRoleAssignment.scope_type == "project",
                            UserRoleAssignment.scope_id == flow_obj.folder_id
                        ).options(selectinload(UserRoleAssignment.role))

                        project_assignment = await session.exec(project_stmt)
                        if proj_assign := project_assignment.first():
                            # Check if inherited role has permission
                            if self._role_has_permission(proj_assign.role_id, permission_name, "Flow"):
                                return True

            return False

    def _role_has_permission(self, role_id: UUID, permission_name: str, scope_type: str) -> bool:
        """Check if role has specific permission using cache."""
        if not self._cache_initialized:
            raise RuntimeError("RBACService not initialized")

        permission_key = f"{permission_name}:{scope_type}"
        return permission_key in self._role_permission_cache.get(role_id, set())
```

Factory pattern:
```python
# services/rbac/factory.py
class RBACServiceFactory(ServiceFactory):
    @staticmethod
    def create():
        return RBACService()

def get_rbac_service() -> RBACService:
    """Dependency injection for RBACService."""
    return service_manager.get(RBACService)
```

**Success Criteria:**
- Service initializes and caches role-permission mappings
- `can_access()` returns True for Admin users on all resources
- `can_access()` returns True for direct scope assignments with correct permission
- `can_access()` returns True for Flow scope when Project-level role grants permission
- `can_access()` returns False when no assignment or insufficient permission
- Unit tests cover all inheritance scenarios
- Performance test: can_access() completes in < 50ms (p95)

---

#### Task 2.2: Create RBAC API Router and Endpoints

**Scope and Goals:**
Implement RESTful API endpoints for RBAC management: listing roles, viewing assignments, creating/updating/deleting assignments. All endpoints require Admin role. Implements immutability checks for Starter Project Owner assignments.

**Impact Subgraph:**
- New Nodes:
  - `nl0505`: GET /api/v1/rbac/roles (logic)
  - `nl0506`: GET /api/v1/rbac/assignments (logic)
  - `nl0507`: POST /api/v1/rbac/assignments (logic)
  - `nl0508`: PATCH /api/v1/rbac/assignments/{id} (logic)
  - `nl0509`: DELETE /api/v1/rbac/assignments/{id} (logic)
  - `nl0510`: GET /api/v1/rbac/check-permission (logic)
- Modified Nodes: API router configuration
- Edges: All endpoints depend on RBACService

**Architecture & Tech Stack:**
- Framework: FastAPI with async route handlers
- Libraries: Pydantic for request/response schemas
- Patterns: RESTful CRUD operations, dependency injection for auth
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/rbac.py`

**Implementation Details:**

```python
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

router = APIRouter(prefix="/rbac", tags=["RBAC"])

# Pydantic schemas
class RoleRead(BaseModel):
    id: UUID
    name: str
    description: str | None

class AssignmentCreate(BaseModel):
    user_id: UUID
    role_id: UUID
    scope_type: str  # "global", "project", "flow"
    scope_id: UUID | None = None

class AssignmentRead(BaseModel):
    id: UUID
    user_id: UUID
    role_id: UUID
    scope_type: str
    scope_id: UUID | None
    is_immutable: bool
    created_at: datetime

class AssignmentUpdate(BaseModel):
    role_id: UUID

class PermissionCheckRequest(BaseModel):
    permission_name: str
    scope_type: str
    scope_id: UUID | None = None

# Admin-only dependency
async def require_admin(current_user: CurrentActiveUser) -> User:
    """Ensure current user has Admin role."""
    rbac_service = get_rbac_service()
    if not await rbac_service.can_access(
        current_user.id, "Read", "global", None
    ):
        raise HTTPException(403, "Admin role required")
    return current_user

@router.get("/roles", response_model=list[RoleRead])
async def list_roles(
    session: DbSession,
    admin_user: Annotated[User, Depends(require_admin)]
):
    """List all available roles. Admin only."""
    stmt = select(Role).where(Role.is_system == True)
    results = await session.exec(stmt)
    return results.all()

@router.get("/assignments", response_model=list[AssignmentRead])
async def list_assignments(
    session: DbSession,
    admin_user: Annotated[User, Depends(require_admin)],
    user_id: UUID | None = None,
    role_id: UUID | None = None,
    scope_type: str | None = None,
    scope_id: UUID | None = None,
):
    """List role assignments with optional filtering. Admin only."""
    stmt = select(UserRoleAssignment)

    if user_id:
        stmt = stmt.where(UserRoleAssignment.user_id == user_id)
    if role_id:
        stmt = stmt.where(UserRoleAssignment.role_id == role_id)
    if scope_type:
        stmt = stmt.where(UserRoleAssignment.scope_type == scope_type)
    if scope_id:
        stmt = stmt.where(UserRoleAssignment.scope_id == scope_id)

    results = await session.exec(stmt)
    return results.all()

@router.post("/assignments", response_model=AssignmentRead, status_code=201)
async def create_assignment(
    session: DbSession,
    assignment: AssignmentCreate,
    admin_user: Annotated[User, Depends(require_admin)]
):
    """Create new role assignment. Admin only."""
    # Validate user exists
    user = await session.get(User, assignment.user_id)
    if not user:
        raise HTTPException(404, "User not found")

    # Validate role exists
    role = await session.get(Role, assignment.role_id)
    if not role:
        raise HTTPException(404, "Role not found")

    # Validate scope exists (if not global)
    if assignment.scope_type == "project" and assignment.scope_id:
        project = await session.get(Folder, assignment.scope_id)
        if not project:
            raise HTTPException(404, "Project not found")
    elif assignment.scope_type == "flow" and assignment.scope_id:
        flow = await session.get(Flow, assignment.scope_id)
        if not flow:
            raise HTTPException(404, "Flow not found")

    # Create assignment
    new_assignment = UserRoleAssignment(
        user_id=assignment.user_id,
        role_id=assignment.role_id,
        scope_type=assignment.scope_type,
        scope_id=assignment.scope_id,
        created_by=admin_user.id
    )

    session.add(new_assignment)
    await session.commit()
    await session.refresh(new_assignment)

    return new_assignment

@router.patch("/assignments/{assignment_id}", response_model=AssignmentRead)
async def update_assignment(
    session: DbSession,
    assignment_id: UUID,
    update: AssignmentUpdate,
    admin_user: Annotated[User, Depends(require_admin)]
):
    """Update role assignment (change role). Admin only. Cannot modify immutable assignments."""
    assignment = await session.get(UserRoleAssignment, assignment_id)
    if not assignment:
        raise HTTPException(404, "Assignment not found")

    # Check immutability (PRD 1.4)
    if assignment.is_immutable:
        raise HTTPException(403, "Cannot modify immutable assignment (Starter Project Owner)")

    # Validate new role exists
    role = await session.get(Role, update.role_id)
    if not role:
        raise HTTPException(404, "Role not found")

    assignment.role_id = update.role_id
    await session.commit()
    await session.refresh(assignment)

    return assignment

@router.delete("/assignments/{assignment_id}", status_code=204)
async def delete_assignment(
    session: DbSession,
    assignment_id: UUID,
    admin_user: Annotated[User, Depends(require_admin)]
):
    """Delete role assignment. Admin only. Cannot delete immutable assignments."""
    assignment = await session.get(UserRoleAssignment, assignment_id)
    if not assignment:
        raise HTTPException(404, "Assignment not found")

    # Check immutability (PRD 1.4)
    if assignment.is_immutable:
        raise HTTPException(403, "Cannot delete immutable assignment (Starter Project Owner)")

    await session.delete(assignment)
    await session.commit()

    return Response(status_code=204)

@router.post("/check-permission", response_model=dict)
async def check_permission(
    request: PermissionCheckRequest,
    current_user: CurrentActiveUser,
):
    """Check if current user has specific permission. Used by frontend."""
    rbac_service = get_rbac_service()

    has_permission = await rbac_service.can_access(
        current_user.id,
        request.permission_name,
        request.scope_type,
        request.scope_id
    )

    return {"has_permission": has_permission}
```

Register router in main API router:
```python
# In src/backend/base/langbuilder/api/router.py
from langbuilder.api.v1 import rbac

api_router.include_router(rbac.router)
```

**Success Criteria:**
- All endpoints return 403 for non-admin users
- GET /rbac/roles returns all 4 system roles
- GET /rbac/assignments supports all filter combinations
- POST /rbac/assignments creates assignment successfully
- POST /rbac/assignments validates user, role, and scope existence
- PATCH /rbac/assignments updates role successfully
- PATCH /rbac/assignments rejects immutable assignment modification
- DELETE /rbac/assignments removes assignment successfully
- DELETE /rbac/assignments rejects immutable assignment deletion
- POST /rbac/check-permission returns correct permission status
- Integration tests verify all endpoints
- Performance test: Assignment API calls complete in < 200ms (p95)

---

#### Task 2.3: Implement Auto-Assignment Logic for New Resources

**Scope and Goals:**
Extend Flow and Project creation endpoints to automatically assign Owner role to the creating user. Mark Starter Project Owner assignments as immutable. Update User model to track default project for immutability enforcement.

**Impact Subgraph:**
- New Nodes: None (modification of existing logic)
- Modified Nodes:
  - `nl0004`: Create Flow Endpoint Handler
  - `nl0042`: Create Project Endpoint Handler
  - `ns0001`: User (add default_project_id field)
- Edges: Flow/Project creation triggers UserRoleAssignment creation

**Architecture & Tech Stack:**
- Framework: Async endpoint handlers with transaction management
- Patterns: Post-creation hook, database transactions
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/flows.py`
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/projects.py`
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/services/database/models/user/model.py`

**Implementation Details:**

Update User model to track Starter Project:
```python
# In services/database/models/user/model.py
class User(SQLModel, table=True):
    # ... existing fields ...
    default_project_id: UUID | None = Field(default=None, nullable=True, foreign_key="folder.id")
```

Create Alembic migration for new field:
```bash
alembic revision --autogenerate -m "add_default_project_id_to_user"
```

Update Project creation to assign Owner role:
```python
# In api/v1/projects.py
@router.post("/", response_model=FolderRead, status_code=201)
async def create_project(
    *,
    session: DbSession,
    project: FolderCreate,
    current_user: CurrentActiveUser,
):
    # ... existing project creation logic ...

    session.add(new_project)
    await session.commit()
    await session.refresh(new_project)

    # Auto-assign Owner role to creator (PRD 1.5)
    owner_role = await session.exec(select(Role).where(Role.name == "Owner"))
    owner_role_obj = owner_role.first()

    # Check if this is the user's Starter Project
    is_starter = new_project.name == STARTER_FOLDER_NAME
    if is_starter:
        # Update user's default_project_id
        current_user.default_project_id = new_project.id
        session.add(current_user)

    assignment = UserRoleAssignment(
        user_id=current_user.id,
        role_id=owner_role_obj.id,
        scope_type="project",
        scope_id=new_project.id,
        is_immutable=is_starter,  # PRD 1.4 - Starter Project is immutable
        created_by=current_user.id
    )
    session.add(assignment)
    await session.commit()

    return new_project
```

Update Flow creation to assign Owner role:
```python
# In api/v1/flows.py
async def _new_flow(
    *,
    session: AsyncSession,
    flow: FlowCreate,
    user_id: UUID,
):
    # ... existing flow creation logic ...

    session.add(db_flow)
    await session.commit()
    await session.refresh(db_flow)

    # Auto-assign Owner role to creator (PRD 1.5)
    owner_role = await session.exec(select(Role).where(Role.name == "Owner"))
    owner_role_obj = owner_role.first()

    assignment = UserRoleAssignment(
        user_id=user_id,
        role_id=owner_role_obj.id,
        scope_type="flow",
        scope_id=db_flow.id,
        is_immutable=False,  # Flow Owner assignments are mutable (PRD 1.5)
        created_by=user_id
    )
    session.add(assignment)
    await session.commit()

    return db_flow
```

**Success Criteria:**
- Creating a new Project assigns Owner role to creator
- Creating a new Flow assigns Owner role to creator
- Starter Project Owner assignment has is_immutable=True
- Regular Project Owner assignment has is_immutable=False
- User.default_project_id is set for Starter Project
- Attempting to modify/delete Starter Project Owner fails
- Attempting to modify/delete regular Project/Flow Owner succeeds
- Integration tests verify auto-assignment behavior

---

### Phase 3: Permission Enforcement Across Existing Endpoints

**Description:** Integrate RBAC permission checks into all existing Flow and Project CRUD endpoints. Replace simple ownership checks with RBACService.can_access() calls. Implement list filtering to show only resources the user has Read permission for.

**Scope:** Endpoint modifications, list filtering logic, UI element visibility

**Goals:**
- Enforce Read permission on all GET endpoints
- Enforce Create permission on POST endpoints
- Enforce Update permission on PATCH endpoints
- Enforce Delete permission on DELETE endpoints
- Filter list views to show only readable resources
- Support Admin bypass for all operations

**Entry Criteria:** Phase 2 complete, RBACService operational, API endpoints secured

**Exit Criteria:** All Flow/Project endpoints enforce RBAC, list views filtered by permission, existing admin functionality preserved

---

#### Task 3.1: Enforce Read Permission on Flow Endpoints

**Scope and Goals:**
Update all Flow read endpoints to check Read permission before returning data. Filter flow list to show only flows the user can read (via direct assignment or Project inheritance).

**Impact Subgraph:**
- New Nodes: None (modification only)
- Modified Nodes:
  - `nl0005`: List Flows Endpoint Handler
  - `nl0007`: Get Flow by ID Endpoint Handler
- Edges: Endpoints depend on RBACService

**Architecture & Tech Stack:**
- Framework: FastAPI with async/await
- Patterns: Permission check before data access, async list filtering
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/flows.py`

**Implementation Details:**

```python
# Update GET /flows/ endpoint
@router.get("/", response_model=Page[FlowRead])
async def read_flows(
    *,
    session: DbSession,
    current_user: CurrentActiveUser,
    params: Annotated[Params, Depends()],
):
    rbac_service = get_rbac_service()

    # Get all flows (will filter by permission)
    stmt = select(Flow)

    # Apply pagination
    page = await apaginate(session, stmt, params)

    # Filter flows by Read permission (PRD 2.2)
    readable_flows = []
    for flow in page.items:
        has_permission = await rbac_service.can_access(
            current_user.id,
            "Read",
            "flow",
            flow.id
        )
        if has_permission:
            readable_flows.append(flow)

    # Update page items
    page.items = readable_flows
    page.total = len(readable_flows)

    return page

# Update GET /flows/{flow_id} endpoint
@router.get("/{flow_id}", response_model=FlowRead)
async def get_flow(
    flow_id: UUID,
    current_user: CurrentActiveUser,
    session: DbSession
):
    rbac_service = get_rbac_service()

    # Check Read permission (PRD 2.2)
    has_permission = await rbac_service.can_access(
        current_user.id,
        "Read",
        "flow",
        flow_id
    )

    if not has_permission:
        raise HTTPException(403, "Insufficient permissions to read this flow")

    flow = await session.get(Flow, flow_id)
    if not flow:
        raise HTTPException(404, "Flow not found")

    return flow
```

**Success Criteria:**
- List flows returns only flows with Read permission
- Get flow by ID succeeds for flows with Read permission
- Get flow by ID returns 403 for flows without Read permission
- Admin users can read all flows
- Owner users can read their owned flows
- Editor users can read flows they have editor access to
- Viewer users can read flows they have viewer access to
- Users can read flows via inherited Project permission
- Integration tests verify all permission scenarios

---

#### Task 3.2: Enforce Create Permission on Flow Endpoints

**Scope and Goals:**
Update Flow creation endpoint to check Create permission on the target Project before allowing flow creation. Applies to flows created within a specific project.

**Impact Subgraph:**
- New Nodes: None (modification only)
- Modified Nodes:
  - `nl0004`: Create Flow Endpoint Handler
- Edges: Endpoint depends on RBACService

**Architecture & Tech Stack:**
- Framework: FastAPI async handlers
- Patterns: Pre-creation permission check
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/flows.py`

**Implementation Details:**

```python
@router.post("/", response_model=FlowRead, status_code=201)
async def create_flow(
    *,
    session: DbSession,
    flow: FlowCreate,
    current_user: CurrentActiveUser,
):
    rbac_service = get_rbac_service()

    # Check Create permission on Project (PRD 2.3)
    if flow.folder_id:
        has_permission = await rbac_service.can_access(
            current_user.id,
            "Create",
            "project",
            flow.folder_id
        )

        if not has_permission:
            raise HTTPException(403, "Insufficient permissions to create flow in this project")
    else:
        # Creating flow without project - check global Create permission
        has_permission = await rbac_service.can_access(
            current_user.id,
            "Create",
            "global",
            None
        )

        if not has_permission:
            raise HTTPException(403, "Insufficient permissions to create flows")

    # ... rest of creation logic ...
```

**Success Criteria:**
- Flow creation succeeds when user has Create permission on project
- Flow creation fails with 403 when user lacks Create permission
- Admin can create flows in any project
- Owner can create flows in owned projects
- Editor can create flows in projects with editor access
- Viewer cannot create flows
- Integration tests verify permission enforcement

---

#### Task 3.3: Enforce Update Permission on Flow Endpoints

**Scope and Goals:**
Update Flow modification endpoints to check Update permission before allowing changes. Applies to flow updates, imports, and property modifications.

**Impact Subgraph:**
- New Nodes: None (modification only)
- Modified Nodes:
  - `nl0009`: Update Flow Endpoint Handler
  - `nl0012`: Upload Flows Endpoint Handler (import)
- Edges: Endpoints depend on RBACService

**Architecture & Tech Stack:**
- Framework: FastAPI async handlers
- Patterns: Pre-update permission check
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/flows.py`

**Implementation Details:**

```python
@router.patch("/{flow_id}", response_model=FlowRead)
async def update_flow(
    *,
    session: DbSession,
    flow_id: UUID,
    flow_update: FlowUpdate,
    current_user: CurrentActiveUser,
):
    rbac_service = get_rbac_service()

    # Check Update permission (PRD 2.4)
    has_permission = await rbac_service.can_access(
        current_user.id,
        "Update",
        "flow",
        flow_id
    )

    if not has_permission:
        raise HTTPException(403, "Insufficient permissions to update this flow")

    flow = await session.get(Flow, flow_id)
    if not flow:
        raise HTTPException(404, "Flow not found")

    # ... rest of update logic ...

@router.post("/upload/", response_model=list[FlowRead])
async def upload_flows(
    *,
    session: DbSession,
    file: UploadFile = File(...),
    current_user: CurrentActiveUser,
    folder_id: UUID | None = None,
):
    rbac_service = get_rbac_service()

    # Check Update permission for import operation (PRD 1.2)
    if folder_id:
        has_permission = await rbac_service.can_access(
            current_user.id,
            "Update",
            "project",
            folder_id
        )

        if not has_permission:
            raise HTTPException(403, "Insufficient permissions to import flows to this project")

    # ... rest of import logic ...
```

**Success Criteria:**
- Flow update succeeds when user has Update permission
- Flow update fails with 403 when user lacks Update permission
- Flow import requires Update permission on target project
- Admin can update any flow
- Owner can update owned flows
- Editor can update flows with editor access
- Viewer cannot update flows (read-only mode per PRD 2.4)
- Integration tests verify permission enforcement

---

#### Task 3.4: Enforce Delete Permission on Flow Endpoints

**Scope and Goals:**
Update Flow deletion endpoint to check Delete permission before allowing deletion. Only Admin and Owner roles have delete permission per PRD requirements.

**Impact Subgraph:**
- New Nodes: None (modification only)
- Modified Nodes:
  - `nl0010`: Delete Flow Endpoint Handler
- Edges: Endpoint depends on RBACService

**Architecture & Tech Stack:**
- Framework: FastAPI async handlers
- Patterns: Pre-deletion permission check
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/flows.py`

**Implementation Details:**

```python
@router.delete("/{flow_id}", status_code=204)
async def delete_flow(
    *,
    session: DbSession,
    flow_id: UUID,
    current_user: CurrentActiveUser,
):
    rbac_service = get_rbac_service()

    # Check Delete permission (PRD 2.5)
    has_permission = await rbac_service.can_access(
        current_user.id,
        "Delete",
        "flow",
        flow_id
    )

    if not has_permission:
        raise HTTPException(403, "Insufficient permissions to delete this flow")

    flow = await session.get(Flow, flow_id)
    if not flow:
        raise HTTPException(404, "Flow not found")

    # ... rest of deletion logic including cascade_delete_flow ...

    await session.delete(flow)
    await session.commit()

    return Response(status_code=204)
```

**Success Criteria:**
- Flow deletion succeeds when user has Delete permission
- Flow deletion fails with 403 when user lacks Delete permission
- Admin can delete any flow
- Owner can delete owned flows
- Editor cannot delete flows (no delete permission per PRD 1.2)
- Viewer cannot delete flows
- Integration tests verify permission enforcement

---

#### Task 3.5: Enforce Permissions on Project Endpoints

**Scope and Goals:**
Apply the same RBAC permission enforcement to all Project (Folder) CRUD endpoints. Mirror the approach used for Flows but with "project" scope type.

**Impact Subgraph:**
- New Nodes: None (modification only)
- Modified Nodes:
  - `nl0042`: Create Project Endpoint Handler
  - `nl0043`: List Projects Endpoint Handler
  - `nl0044`: Get Project by ID Endpoint Handler
  - `nl0045`: Update Project Endpoint Handler
  - `nl0046`: Delete Project Endpoint Handler
- Edges: All endpoints depend on RBACService

**Architecture & Tech Stack:**
- Framework: FastAPI async handlers
- Patterns: Consistent permission checking across CRUD operations
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/projects.py`

**Implementation Details:**

Apply the same permission check patterns as Tasks 3.1-3.4, but with:
- `scope_type="project"`
- `scope_id=project_id`
- Permission names: "Create", "Read", "Update", "Delete"

Key differences for projects:
- List projects filters by Read permission
- Create project checks global Create permission (any authenticated user per PRD 1.5)
- Update project checks Update permission on specific project
- Delete project checks Delete permission and cascades to contained flows
- Import functionality (upload) requires Update permission

**Success Criteria:**
- All Project endpoints enforce appropriate RBAC permissions
- List projects returns only projects with Read permission
- Create project available to all authenticated users (PRD 1.5)
- Update/Delete project restricted to users with appropriate permissions
- Admin can perform all operations on all projects
- Owner can fully manage owned projects
- Editor can create/read/update but not delete
- Viewer can only read
- Integration tests verify all permission scenarios

---

#### Task 3.6: Enforce Permission on Build and Execution Endpoints

**Scope and Goals:**
Update flow build and execution endpoints to require Read permission. Per PRD 1.2, Read permission enables flow execution, saving, exporting, and downloading.

**Impact Subgraph:**
- New Nodes: None (modification only)
- Modified Nodes:
  - `nl0061`: Build Flow Endpoint Handler
  - Chat/execution endpoints
- Edges: Endpoints depend on RBACService

**Architecture & Tech Stack:**
- Framework: FastAPI async handlers
- Patterns: Read permission check before execution
- File Locations:
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/build.py`
  - `/home/nick/LangBuilder/src/backend/base/langbuilder/api/v1/chat.py`

**Implementation Details:**

```python
# In api/build.py
@router.post("/build/{flow_id}/flow")
async def build_flow(
    flow_id: UUID,
    current_user: CurrentActiveUser,
    session: DbSession,
    # ... other params ...
):
    rbac_service = get_rbac_service()

    # Check Read permission for build/execution (PRD 1.2, 2.2)
    has_permission = await rbac_service.can_access(
        current_user.id,
        "Read",
        "flow",
        flow_id
    )

    if not has_permission:
        raise HTTPException(403, "Insufficient permissions to build/execute this flow")

    # ... rest of build logic ...

# In api/v1/chat.py
@router.post("/chat/{flow_id}")
async def chat_with_flow(
    flow_id: UUID,
    current_user: CurrentActiveUser,
    session: DbSession,
    # ... other params ...
):
    rbac_service = get_rbac_service()

    # Check Read permission for execution (PRD 1.2)
    has_permission = await rbac_service.can_access(
        current_user.id,
        "Read",
        "flow",
        flow_id
    )

    if not has_permission:
        raise HTTPException(403, "Insufficient permissions to execute this flow")

    # ... rest of chat logic ...
```

**Success Criteria:**
- Build endpoint requires Read permission
- Chat/execution endpoints require Read permission
- Export/download endpoints require Read permission
- Admin can execute any flow
- Owner can execute owned flows
- Editor can execute flows with editor access
- Viewer can execute flows with viewer access (read-only execution)
- Integration tests verify permission enforcement

---

### Phase 4: Frontend RBAC Management UI

**Description:** Build the complete frontend interface for RBAC management within the AdminPage. Implements a tabbed interface with assignment list view, create/edit workflows, filtering, and the usePermission hook for permission checks throughout the UI.

**Scope:** React components, state management, API integration, UI guards

**Goals:**
- Add RBAC Management tab to AdminPage
- Create assignment list view with filtering
- Implement create/edit assignment wizard modal
- Build usePermission hook for permission checks
- Add RBACGuard component for conditional rendering
- Hide/disable UI elements based on permissions

**Entry Criteria:** Phase 3 complete, backend APIs functional, permission enforcement working

**Exit Criteria:** Admins can fully manage assignments via UI, non-admins cannot access RBAC management, UI elements filtered by permissions

---

#### Task 4.1: Create RBAC Management Page Structure

**Scope and Goals:**
Extend AdminPage to include a new RBAC Management tab alongside the existing User Management tab. Implement routing to support deep linking to the RBAC section.

**Impact Subgraph:**
- New Nodes:
  - `ni0083`: RBACManagementPage (interface)
- Modified Nodes:
  - `ni0001`: AdminPage (add tab structure)
- Edges: AdminPage contains RBACManagementPage

**Architecture & Tech Stack:**
- Framework: React 18.3.1 with TypeScript 5.4.5
- UI Components: Radix UI tabs component
- Routing: React Router 6.23.1 for deep linking
- Patterns: Compound component pattern for tabs
- File Locations:
  - `/home/nick/LangBuilder/src/frontend/src/pages/AdminPage/index.tsx` (modify)
  - `/home/nick/LangBuilder/src/frontend/src/pages/AdminPage/RBACManagementPage/index.tsx` (new)

**Implementation Details:**

```typescript
// Update AdminPage/index.tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import RBACManagementPage from "./RBACManagementPage";

export default function AdminPage() {
  const { userData } = useContext(AuthContext);
  const isAdmin = useAuthStore((state) => state.isAdmin);
  const location = useLocation();
  const navigate = useNavigate();

  // Determine active tab from URL hash
  const activeTab = location.hash === "#rbac" ? "rbac" : "users";

  if (!isAdmin) {
    return <CustomNavigate to="/" replace />;
  }

  return (
    <div className="admin-page">
      <PageLayout
        title={ADMIN_HEADER_TITLE}
        description={ADMIN_HEADER_DESCRIPTION}
      >
        <Tabs value={activeTab} onValueChange={(val) => navigate(`#${val}`)}>
          <TabsList>
            <TabsTrigger value="users">User Management</TabsTrigger>
            <TabsTrigger value="rbac">RBAC Management</TabsTrigger>
          </TabsList>

          <TabsContent value="users">
            {/* Existing user management content */}
          </TabsContent>

          <TabsContent value="rbac">
            <RBACManagementPage />
          </TabsContent>
        </Tabs>
      </PageLayout>
    </div>
  );
}

// Create RBACManagementPage/index.tsx
export default function RBACManagementPage() {
  return (
    <div className="rbac-management-page">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Role Assignments</h2>
        <Button onClick={handleCreateAssignment}>
          <IconComponent name="Plus" className="mr-2" />
          Create Assignment
        </Button>
      </div>

      <AssignmentListView />
    </div>
  );
}
```

**Success Criteria:**
- AdminPage displays two tabs: User Management and RBAC Management
- Default tab is User Management (existing behavior preserved)
- Clicking RBAC Management tab switches to RBAC view
- URL updates to /admin#rbac when RBAC tab selected
- Direct navigation to /admin#rbac opens RBAC tab
- Non-admin users cannot access AdminPage (existing guard enforced)
- Tab state persists across page refreshes via URL hash

---

#### Task 4.2: Create Assignment List View Component

**Scope and Goals:**
Build the main list view component that displays all role assignments with filtering capabilities. Shows user, role, scope information with actions to edit/delete assignments.

**Impact Subgraph:**
- New Nodes:
  - `ni0084`: AssignmentListView (interface)
- Modified Nodes: None
- Edges: RBACManagementPage contains AssignmentListView

**Architecture & Tech Stack:**
- Framework: React with TypeScript
- State Management: TanStack Query for server state
- UI Components: Radix UI Table, Select, Input components
- Patterns: Server-side filtering via query params
- File Locations:
  - `/home/nick/LangBuilder/src/frontend/src/pages/AdminPage/RBACManagementPage/AssignmentListView.tsx`
  - `/home/nick/LangBuilder/src/frontend/src/controllers/API/queries/rbac/index.ts` (API hooks)

**Implementation Details:**

Create TanStack Query hooks:
```typescript
// controllers/API/queries/rbac/index.ts
export function useGetAssignments(filters?: {
  user_id?: string;
  role_id?: string;
  scope_type?: string;
  scope_id?: string;
}) {
  return useQuery({
    queryKey: ["rbac", "assignments", filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.user_id) params.append("user_id", filters.user_id);
      if (filters?.role_id) params.append("role_id", filters.role_id);
      if (filters?.scope_type) params.append("scope_type", filters.scope_type);
      if (filters?.scope_id) params.append("scope_id", filters.scope_id);

      const { data } = await api.get(`/api/v1/rbac/assignments?${params}`);
      return data;
    },
  });
}

export function useDeleteAssignment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (assignmentId: string) => {
      await api.delete(`/api/v1/rbac/assignments/${assignmentId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rbac", "assignments"] });
    },
  });
}
```

Create list view component:
```typescript
// AssignmentListView.tsx
export default function AssignmentListView() {
  const [filters, setFilters] = useState({
    user_id: "",
    role_id: "",
    scope_type: "",
  });

  const { data: assignments, isLoading } = useGetAssignments(filters);
  const { data: users } = useGetUsers({});
  const { data: roles } = useGetRoles();
  const { mutate: deleteAssignment } = useDeleteAssignment();
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);

  const handleDelete = (assignment) => {
    if (assignment.is_immutable) {
      setErrorData({
        title: "Cannot Delete",
        list: ["This assignment is immutable (Starter Project Owner)"],
      });
      return;
    }

    deleteAssignment(assignment.id, {
      onSuccess: () => {
        setSuccessData({ title: "Assignment deleted successfully" });
      },
      onError: (error) => {
        setErrorData({
          title: "Delete Failed",
          list: [error.response?.data?.detail || "Unknown error"],
        });
      },
    });
  };

  return (
    <div className="assignment-list">
      <div className="filters mb-4 flex gap-4">
        <Select
          value={filters.user_id}
          onValueChange={(val) => setFilters({ ...filters, user_id: val })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Filter by User" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Users</SelectItem>
            {users?.users.map((user) => (
              <SelectItem key={user.id} value={user.id}>
                {user.username}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={filters.role_id}
          onValueChange={(val) => setFilters({ ...filters, role_id: val })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Filter by Role" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Roles</SelectItem>
            {roles?.map((role) => (
              <SelectItem key={role.id} value={role.id}>
                {role.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={filters.scope_type}
          onValueChange={(val) => setFilters({ ...filters, scope_type: val })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Filter by Scope" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Scopes</SelectItem>
            <SelectItem value="global">Global</SelectItem>
            <SelectItem value="project">Project</SelectItem>
            <SelectItem value="flow">Flow</SelectItem>
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          onClick={() => setFilters({ user_id: "", role_id: "", scope_type: "" })}
        >
          Clear Filters
        </Button>
      </div>

      {isLoading ? (
        <CustomLoader />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>User</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Scope Type</TableHead>
              <TableHead>Scope</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {assignments?.map((assignment) => (
              <TableRow key={assignment.id}>
                <TableCell>{getUserName(assignment.user_id, users)}</TableCell>
                <TableCell>
                  <Badge>{getRoleName(assignment.role_id, roles)}</Badge>
                </TableCell>
                <TableCell>{assignment.scope_type}</TableCell>
                <TableCell>
                  {assignment.scope_id ? getScopeName(assignment) : "Global"}
                </TableCell>
                <TableCell>
                  {new Date(assignment.created_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    <ShadTooltip content="Edit Assignment">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleEdit(assignment)}
                        disabled={assignment.is_immutable}
                      >
                        <IconComponent name="Edit" />
                      </Button>
                    </ShadTooltip>
                    <ShadTooltip content={assignment.is_immutable ? "Cannot delete immutable assignment" : "Delete Assignment"}>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDelete(assignment)}
                        disabled={assignment.is_immutable}
                      >
                        <IconComponent name="Trash" />
                      </Button>
                    </ShadTooltip>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Display message about inherited assignments (PRD 3.5) */}
      <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded">
        <p className="text-sm text-blue-800">
          <IconComponent name="Info" className="inline mr-2" />
          Project-level assignments are inherited by contained Flows and can be overridden by explicit Flow-specific roles.
        </p>
      </div>
    </div>
  );
}
```

**Success Criteria:**
- List displays all assignments with user, role, scope information
- Filter by user updates list in real-time
- Filter by role updates list in real-time
- Filter by scope type updates list in real-time
- Clear filters button resets all filters
- Edit button enabled for mutable assignments
- Edit button disabled for immutable assignments (Starter Project Owner)
- Delete button enabled for mutable assignments
- Delete button disabled for immutable assignments
- Delete confirmation modal appears before deletion
- Deleting assignment refreshes list
- Inheritance message displayed (PRD 3.5)
- Loading state shown while fetching data

---

#### Task 4.3: Create Assignment Creation/Edit Modal

**Scope and Goals:**
Build a wizard-style modal for creating new role assignments. Implements the multi-step workflow: Select User → Select Scope → Select Role → Confirm. Also supports editing existing assignments (changing the role).

**Impact Subgraph:**
- New Nodes:
  - `ni0085`: CreateAssignmentModal (interface)
- Modified Nodes: None
- Edges: RBACManagementPage triggers modal, modal calls API

**Architecture & Tech Stack:**
- Framework: React with TypeScript
- UI Components: Radix UI Dialog, Select, Button components
- State Management: Local useState for wizard steps
- Patterns: Multi-step wizard, controlled form inputs
- File Locations:
  - `/home/nick/LangBuilder/src/frontend/src/pages/AdminPage/RBACManagementPage/CreateAssignmentModal.tsx`

**Implementation Details:**

```typescript
type WizardStep = "user" | "scope" | "role" | "confirm";

interface AssignmentFormData {
  user_id: string;
  scope_type: "global" | "project" | "flow";
  scope_id: string | null;
  role_id: string;
}

export default function CreateAssignmentModal({ open, onClose, editAssignment }) {
  const [step, setStep] = useState<WizardStep>("user");
  const [formData, setFormData] = useState<AssignmentFormData>({
    user_id: editAssignment?.user_id || "",
    scope_type: editAssignment?.scope_type || "project",
    scope_id: editAssignment?.scope_id || null,
    role_id: editAssignment?.role_id || "",
  });

  const { data: users } = useGetUsers({});
  const { data: projects } = useGetProjects();
  const { data: flows } = useGetFlows();
  const { data: roles } = useGetRoles();
  const { mutate: createAssignment } = useCreateAssignment();
  const { mutate: updateAssignment } = useUpdateAssignment();

  const handleNext = () => {
    const stepOrder: WizardStep[] = ["user", "scope", "role", "confirm"];
    const currentIndex = stepOrder.indexOf(step);
    if (currentIndex < stepOrder.length - 1) {
      setStep(stepOrder[currentIndex + 1]);
    }
  };

  const handleBack = () => {
    const stepOrder: WizardStep[] = ["user", "scope", "role", "confirm"];
    const currentIndex = stepOrder.indexOf(step);
    if (currentIndex > 0) {
      setStep(stepOrder[currentIndex - 1]);
    }
  };

  const handleSubmit = () => {
    if (editAssignment) {
      // Update existing assignment (only role can change)
      updateAssignment(
        { assignment_id: editAssignment.id, role_id: formData.role_id },
        {
          onSuccess: () => {
            setSuccessData({ title: "Assignment updated successfully" });
            onClose();
          },
          onError: (error) => {
            setErrorData({
              title: "Update Failed",
              list: [error.response?.data?.detail || "Unknown error"],
            });
          },
        }
      );
    } else {
      // Create new assignment
      createAssignment(formData, {
        onSuccess: () => {
          setSuccessData({ title: "Assignment created successfully" });
          onClose();
        },
        onError: (error) => {
          setErrorData({
            title: "Creation Failed",
            list: [error.response?.data?.detail || "Unknown error"],
          });
        },
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {editAssignment ? "Edit Assignment" : "Create New Assignment"}
          </DialogTitle>
        </DialogHeader>

        <div className="wizard-steps mb-6">
          <div className="flex justify-between">
            {["user", "scope", "role", "confirm"].map((s, i) => (
              <div
                key={s}
                className={cn(
                  "wizard-step",
                  step === s && "active",
                  ["user", "scope", "role", "confirm"].indexOf(step) > i && "completed"
                )}
              >
                {i + 1}. {s.charAt(0).toUpperCase() + s.slice(1)}
              </div>
            ))}
          </div>
        </div>

        <div className="wizard-content">
          {step === "user" && (
            <div>
              <Label>Select User</Label>
              <Select
                value={formData.user_id}
                onValueChange={(val) => setFormData({ ...formData, user_id: val })}
                disabled={!!editAssignment}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Choose a user" />
                </SelectTrigger>
                <SelectContent>
                  {users?.users.map((user) => (
                    <SelectItem key={user.id} value={user.id}>
                      {user.username}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {step === "scope" && (
            <div className="space-y-4">
              <div>
                <Label>Scope Type</Label>
                <Select
                  value={formData.scope_type}
                  onValueChange={(val: any) =>
                    setFormData({ ...formData, scope_type: val, scope_id: null })
                  }
                  disabled={!!editAssignment}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="global">Global (All Resources)</SelectItem>
                    <SelectItem value="project">Specific Project</SelectItem>
                    <SelectItem value="flow">Specific Flow</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {formData.scope_type === "project" && (
                <div>
                  <Label>Select Project</Label>
                  <Select
                    value={formData.scope_id || ""}
                    onValueChange={(val) => setFormData({ ...formData, scope_id: val })}
                    disabled={!!editAssignment}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Choose a project" />
                    </SelectTrigger>
                    <SelectContent>
                      {projects?.map((project) => (
                        <SelectItem key={project.id} value={project.id}>
                          {project.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {formData.scope_type === "flow" && (
                <div>
                  <Label>Select Flow</Label>
                  <Select
                    value={formData.scope_id || ""}
                    onValueChange={(val) => setFormData({ ...formData, scope_id: val })}
                    disabled={!!editAssignment}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Choose a flow" />
                    </SelectTrigger>
                    <SelectContent>
                      {flows?.items?.map((flow) => (
                        <SelectItem key={flow.id} value={flow.id}>
                          {flow.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
          )}

          {step === "role" && (
            <div>
              <Label>Select Role</Label>
              <Select
                value={formData.role_id}
                onValueChange={(val) => setFormData({ ...formData, role_id: val })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Choose a role" />
                </SelectTrigger>
                <SelectContent>
                  {roles?.map((role) => (
                    <SelectItem key={role.id} value={role.id}>
                      <div>
                        <div className="font-semibold">{role.name}</div>
                        <div className="text-xs text-gray-500">{role.description}</div>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {step === "confirm" && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Confirm Assignment</h3>
              <div className="bg-gray-50 p-4 rounded space-y-2">
                <div>
                  <span className="font-medium">User:</span>{" "}
                  {getUserName(formData.user_id, users)}
                </div>
                <div>
                  <span className="font-medium">Role:</span>{" "}
                  {getRoleName(formData.role_id, roles)}
                </div>
                <div>
                  <span className="font-medium">Scope:</span>{" "}
                  {formData.scope_type === "global"
                    ? "Global (All Resources)"
                    : `${formData.scope_type}: ${getScopeName(formData)}`}
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          {step !== "user" && (
            <Button variant="outline" onClick={handleBack}>
              Back
            </Button>
          )}
          {step !== "confirm" ? (
            <Button
              onClick={handleNext}
              disabled={
                (step === "user" && !formData.user_id) ||
                (step === "scope" &&
                  formData.scope_type !== "global" &&
                  !formData.scope_id) ||
                (step === "role" && !formData.role_id)
              }
            >
              Next
            </Button>
          ) : (
            <Button onClick={handleSubmit}>
              {editAssignment ? "Update Assignment" : "Create Assignment"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

**Success Criteria:**
- Modal opens when "Create Assignment" button clicked
- Wizard displays 4 steps: User, Scope, Role, Confirm
- User step shows all users in dropdown
- Scope step allows selecting global, project, or flow
- Scope step shows project/flow selector based on scope type
- Role step shows all 4 roles with descriptions
- Confirm step displays summary of assignment
- Next button disabled until current step is valid
- Back button navigates to previous step
- Create button submits assignment and closes modal
- Edit mode pre-fills form with existing assignment data
- Edit mode only allows changing the role (user/scope immutable)
- Success message shown on successful creation/update
- Error message shown on failure
- Modal closes on cancel or successful submit

---

#### Task 4.4: Create usePermission Hook and RBACGuard Component

**Scope and Goals:**
Build a reusable React hook for checking permissions and a guard component for conditional rendering. These are used throughout the UI to show/hide buttons, enable/disable actions, and control access to components.

**Impact Subgraph:**
- New Nodes:
  - `ni0087`: usePermission (interface)
  - `ni0086`: RBACGuard (interface)
- Modified Nodes: None
- Edges: Components throughout the app use these utilities

**Architecture & Tech Stack:**
- Framework: React hooks, TypeScript
- State Management: TanStack Query for API calls
- Patterns: Custom hook pattern, render prop pattern for guard
- File Locations:
  - `/home/nick/LangBuilder/src/frontend/src/hooks/usePermission.ts`
  - `/home/nick/LangBuilder/src/frontend/src/components/rbac/RBACGuard.tsx`

**Implementation Details:**

Create usePermission hook:
```typescript
// hooks/usePermission.ts
export function usePermission(
  permission: string,
  scopeType: string,
  scopeId?: string
) {
  const { data: permissionCheck, isLoading } = useQuery({
    queryKey: ["rbac", "check-permission", permission, scopeType, scopeId],
    queryFn: async () => {
      const { data } = await api.post("/api/v1/rbac/check-permission", {
        permission_name: permission,
        scope_type: scopeType,
        scope_id: scopeId,
      });
      return data.has_permission;
    },
    // Cache for 5 minutes to reduce API calls
    staleTime: 5 * 60 * 1000,
  });

  return {
    hasPermission: permissionCheck ?? false,
    isLoading,
  };
}

// Usage example:
// const { hasPermission, isLoading } = usePermission("Delete", "flow", flowId);
```

Create RBACGuard component:
```typescript
// components/rbac/RBACGuard.tsx
interface RBACGuardProps {
  permission: string;
  scopeType: string;
  scopeId?: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function RBACGuard({
  permission,
  scopeType,
  scopeId,
  children,
  fallback = null,
}: RBACGuardProps) {
  const { hasPermission, isLoading } = usePermission(permission, scopeType, scopeId);

  if (isLoading) {
    return <CustomLoader />;
  }

  if (!hasPermission) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

// Usage example:
// <RBACGuard permission="Delete" scopeType="flow" scopeId={flowId}>
//   <Button onClick={handleDelete}>Delete Flow</Button>
// </RBACGuard>
```

**Success Criteria:**
- usePermission hook calls /api/v1/rbac/check-permission endpoint
- Hook returns hasPermission boolean and isLoading state
- Hook caches results to minimize API calls
- RBACGuard renders children when permission granted
- RBACGuard renders fallback when permission denied
- RBACGuard shows loader while checking permission
- Multiple guards on same page don't cause excessive API calls (caching)
- Unit tests verify hook and guard behavior

---

#### Task 4.5: Integrate Permission Checks into Flow and Project UIs

**Scope and Goals:**
Apply RBACGuard and usePermission throughout the Flow and Project UI to hide/disable elements based on user permissions. Implements PRD requirements for hiding create/delete buttons, disabling edit mode, filtering lists.

**Impact Subgraph:**
- New Nodes: None (modification only)
- Modified Nodes:
  - `ni0006`: CollectionPage (interface) - flow/project list view
  - `ni0009`: FlowPage (interface) - flow detail/editor view
- Edges: UI components use RBACGuard and usePermission

**Architecture & Tech Stack:**
- Framework: React with TypeScript
- Patterns: Conditional rendering, disabled state management
- File Locations:
  - `/home/nick/LangBuilder/src/frontend/src/pages/MainPage/index.tsx` (collection view)
  - `/home/nick/LangBuilder/src/frontend/src/pages/FlowPage/index.tsx` (flow editor)

**Implementation Details:**

Update CollectionPage (MainPage) to filter flows and hide create button:
```typescript
// pages/MainPage/index.tsx
export default function MainPage() {
  const { data: flows } = useGetFlows();
  const currentProject = useFlowsManagerStore((state) => state.currentFolder);
  const { hasPermission: canCreateFlow } = usePermission(
    "Create",
    "project",
    currentProject?.id
  );

  return (
    <div className="main-page">
      <div className="header">
        <h1>Flows</h1>
        <RBACGuard permission="Create" scopeType="project" scopeId={currentProject?.id}>
          <Button onClick={handleCreateFlow}>
            <IconComponent name="Plus" className="mr-2" />
            New Flow
          </Button>
        </RBACGuard>
      </div>

      <div className="flow-list">
        {flows?.items.map((flow) => (
          <FlowCard key={flow.id} flow={flow} />
        ))}
      </div>
    </div>
  );
}

// Flow card component with delete button guarded
function FlowCard({ flow }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{flow.name}</CardTitle>
      </CardHeader>
      <CardContent>
        {flow.description}
      </CardContent>
      <CardFooter>
        <Button onClick={() => navigate(`/flow/${flow.id}`)}>Open</Button>
        <RBACGuard permission="Delete" scopeType="flow" scopeId={flow.id}>
          <Button variant="destructive" onClick={() => handleDelete(flow.id)}>
            Delete
          </Button>
        </RBACGuard>
      </CardFooter>
    </Card>
  );
}
```

Update FlowPage to enforce read-only mode for users without Update permission:
```typescript
// pages/FlowPage/index.tsx
export default function FlowPage() {
  const { id: flowId } = useParams();
  const { data: flow } = useGetFlow(flowId);
  const { hasPermission: canUpdate, isLoading } = usePermission(
    "Update",
    "flow",
    flowId
  );

  // Set editor to read-only mode if user lacks Update permission (PRD 2.4)
  const isReadOnly = !canUpdate;

  return (
    <div className="flow-page">
      {isReadOnly && (
        <Alert variant="info">
          <IconComponent name="Lock" className="mr-2" />
          This flow is in read-only mode. You have view/execute access only.
        </Alert>
      )}

      <FlowEditor
        flow={flow}
        readOnly={isReadOnly}
        onSave={isReadOnly ? undefined : handleSave}
      />

      <div className="flow-actions">
        <Button onClick={handleExecute}>Execute</Button>

        <RBACGuard permission="Update" scopeType="flow" scopeId={flowId}>
          <Button onClick={handleSave}>Save</Button>
          <Button onClick={handleExport}>Export</Button>
        </RBACGuard>

        <RBACGuard permission="Delete" scopeType="flow" scopeId={flowId}>
          <Button variant="destructive" onClick={handleDelete}>
            Delete Flow
          </Button>
        </RBACGuard>
      </div>
    </div>
  );
}
```

**Success Criteria:**
- Create Flow button hidden when user lacks Create permission
- Create Flow button visible when user has Create permission
- Delete Flow button hidden when user lacks Delete permission
- Delete Flow button visible when user has Delete permission
- Flow editor in read-only mode when user lacks Update permission
- Flow editor editable when user has Update permission
- Save/Export buttons hidden in read-only mode
- Execute button always visible (Read permission required to view page)
- Similar patterns applied to Project UI
- UI reflects permission changes immediately
- No console errors from permission checks

---

### Phase 5: Testing, Performance Optimization, and Documentation

**Description:** Comprehensive testing of the RBAC system, performance benchmarking against PRD requirements, optimization where needed, and documentation for developers and administrators.

**Scope:** Unit tests, integration tests, performance tests, documentation

**Goals:**
- Achieve >90% code coverage for RBAC components
- Meet all performance requirements (50ms, 200ms, 2.5s)
- Document API endpoints, permission model, and admin workflows
- Create migration guide for existing deployments

**Entry Criteria:** Phase 4 complete, all features implemented

**Exit Criteria:** All tests passing, performance benchmarks met, documentation complete

---

#### Task 5.1: Unit Tests for RBAC Service and Models

**Scope and Goals:**
Create comprehensive unit tests for RBACService permission evaluation logic, role-permission mappings, and data model constraints.

**Impact Subgraph:**
- New Nodes: None (testing only)
- Modified Nodes: None
- Edges: Tests validate all RBAC logic nodes

**Architecture & Tech Stack:**
- Framework: pytest for backend tests
- Libraries: pytest-asyncio for async tests, faker for test data
- Patterns: Arrange-Act-Assert, test fixtures
- File Locations:
  - `/home/nick/LangBuilder/tests/unit/services/test_rbac_service.py`
  - `/home/nick/LangBuilder/tests/unit/models/test_rbac_models.py`

**Implementation Details:**

Test scenarios to cover:
- Role-permission mappings are correct (Admin: all, Owner: all, Editor: no delete, Viewer: read only)
- can_access() returns True for Admin users on all resources
- can_access() returns True for direct scope assignments
- can_access() returns True for inherited Project permissions on Flows
- can_access() returns False for no assignment
- can_access() returns False for insufficient permission
- Flow-specific assignment overrides Project inheritance
- Immutable assignments cannot be modified or deleted
- Auto-assignment on Project/Flow creation
- Starter Project immutability enforcement

```python
# tests/unit/services/test_rbac_service.py
import pytest
from langbuilder.services.rbac.service import RBACService

@pytest.mark.asyncio
async def test_admin_bypass(rbac_service, admin_user, regular_user, flow):
    """Admin users can access all resources."""
    # Create global Admin assignment
    await create_assignment(admin_user, "Admin", "global", None)

    # Admin can access any flow
    assert await rbac_service.can_access(admin_user.id, "Delete", "flow", flow.id)

@pytest.mark.asyncio
async def test_owner_full_access(rbac_service, owner_user, project):
    """Owner role grants full CRUD access."""
    await create_assignment(owner_user, "Owner", "project", project.id)

    assert await rbac_service.can_access(owner_user.id, "Create", "project", project.id)
    assert await rbac_service.can_access(owner_user.id, "Read", "project", project.id)
    assert await rbac_service.can_access(owner_user.id, "Update", "project", project.id)
    assert await rbac_service.can_access(owner_user.id, "Delete", "project", project.id)

@pytest.mark.asyncio
async def test_editor_no_delete(rbac_service, editor_user, flow):
    """Editor role cannot delete resources."""
    await create_assignment(editor_user, "Editor", "flow", flow.id)

    assert await rbac_service.can_access(editor_user.id, "Create", "flow", flow.id)
    assert await rbac_service.can_access(editor_user.id, "Read", "flow", flow.id)
    assert await rbac_service.can_access(editor_user.id, "Update", "flow", flow.id)
    assert not await rbac_service.can_access(editor_user.id, "Delete", "flow", flow.id)

@pytest.mark.asyncio
async def test_project_flow_inheritance(rbac_service, user, project, flow):
    """Flow inherits permissions from Project."""
    # Flow belongs to Project
    flow.folder_id = project.id

    # User has Editor role on Project
    await create_assignment(user, "Editor", "project", project.id)

    # User can read Flow via inheritance
    assert await rbac_service.can_access(user.id, "Read", "flow", flow.id)
    assert await rbac_service.can_access(user.id, "Update", "flow", flow.id)

@pytest.mark.asyncio
async def test_flow_specific_overrides_inheritance(rbac_service, user, project, flow):
    """Flow-specific assignment overrides Project inheritance."""
    flow.folder_id = project.id

    # User is Viewer at Project level
    await create_assignment(user, "Viewer", "project", project.id)

    # User is Editor at Flow level
    await create_assignment(user, "Editor", "flow", flow.id)

    # Flow-specific role takes precedence
    assert await rbac_service.can_access(user.id, "Update", "flow", flow.id)
```

**Success Criteria:**
- All unit tests pass
- Code coverage >90% for RBACService
- All permission inheritance scenarios tested
- All role-permission mappings validated
- Immutability constraints tested
- Auto-assignment logic tested

---

#### Task 5.2: Integration Tests for RBAC API Endpoints

**Scope and Goals:**
Create end-to-end integration tests for all RBAC API endpoints, verifying authentication, authorization, data validation, and error handling.

**Impact Subgraph:**
- New Nodes: None (testing only)
- Modified Nodes: None
- Edges: Tests validate all RBAC API nodes

**Architecture & Tech Stack:**
- Framework: pytest with FastAPI TestClient
- Patterns: API testing, fixture-based setup
- File Locations:
  - `/home/nick/LangBuilder/tests/integration/api/test_rbac_endpoints.py`
  - `/home/nick/LangBuilder/tests/integration/api/test_flow_rbac_enforcement.py`
  - `/home/nick/LangBuilder/tests/integration/api/test_project_rbac_enforcement.py`

**Implementation Details:**

Test scenarios:
- GET /rbac/roles requires Admin
- GET /rbac/assignments requires Admin
- POST /rbac/assignments creates assignment successfully
- POST /rbac/assignments validates user/role/scope existence
- PATCH /rbac/assignments updates role
- PATCH /rbac/assignments rejects immutable modification
- DELETE /rbac/assignments removes assignment
- DELETE /rbac/assignments rejects immutable deletion
- POST /rbac/check-permission returns correct status
- All Flow CRUD endpoints enforce permissions
- All Project CRUD endpoints enforce permissions

```python
# tests/integration/api/test_rbac_endpoints.py
def test_list_roles_requires_admin(client, regular_user_token):
    """Non-admin users cannot list roles."""
    response = client.get(
        "/api/v1/rbac/roles",
        headers={"Authorization": f"Bearer {regular_user_token}"}
    )
    assert response.status_code == 403

def test_create_assignment_success(client, admin_token, user, role, project):
    """Admin can create role assignment."""
    response = client.post(
        "/api/v1/rbac/assignments",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "user_id": str(user.id),
            "role_id": str(role.id),
            "scope_type": "project",
            "scope_id": str(project.id),
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == str(user.id)
    assert data["role_id"] == str(role.id)

def test_delete_immutable_assignment_fails(client, admin_token, starter_project_assignment):
    """Cannot delete Starter Project Owner assignment."""
    response = client.delete(
        f"/api/v1/rbac/assignments/{starter_project_assignment.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 403
    assert "immutable" in response.json()["detail"].lower()

# tests/integration/api/test_flow_rbac_enforcement.py
def test_delete_flow_requires_permission(client, flow, viewer_user_token):
    """Viewer cannot delete flow."""
    response = client.delete(
        f"/api/v1/flows/{flow.id}",
        headers={"Authorization": f"Bearer {viewer_user_token}"}
    )
    assert response.status_code == 403

def test_update_flow_editor_succeeds(client, flow, editor_user_token):
    """Editor can update flow."""
    response = client.patch(
        f"/api/v1/flows/{flow.id}",
        headers={"Authorization": f"Bearer {editor_user_token}"},
        json={"name": "Updated Flow"}
    )
    assert response.status_code == 200
```

**Success Criteria:**
- All RBAC endpoint tests pass
- All Flow/Project permission enforcement tests pass
- Admin authorization verified
- Permission checks validated
- Immutability constraints enforced
- Error handling tested (404, 403, 400)
- Code coverage >85% for API endpoints

---

#### Task 5.3: Performance Benchmarking and Optimization

**Scope and Goals:**
Benchmark RBACService.can_access() method, assignment API endpoints, and editor page load time against PRD requirements. Optimize where necessary to meet targets.

**Impact Subgraph:**
- New Nodes: None (optimization only)
- Modified Nodes: RBACService (potential caching improvements)
- Edges: None

**Architecture & Tech Stack:**
- Framework: pytest-benchmark for Python, Lighthouse for frontend
- Tools: Database query analysis, profiling
- Patterns: Caching, query optimization, indexing
- File Locations:
  - `/home/nick/LangBuilder/tests/performance/test_rbac_performance.py`

**Implementation Details:**

Performance test scenarios:
```python
# tests/performance/test_rbac_performance.py
def test_can_access_latency(benchmark, rbac_service, user, flow):
    """can_access() completes in <50ms (PRD 5.1)."""
    result = benchmark(
        lambda: asyncio.run(rbac_service.can_access(user.id, "Read", "flow", flow.id))
    )

    # Assert p95 latency < 50ms
    assert benchmark.stats.get("mean") < 0.050

def test_create_assignment_latency(benchmark, client, admin_token):
    """Assignment creation completes in <200ms (PRD 5.1)."""
    result = benchmark(
        lambda: client.post(
            "/api/v1/rbac/assignments",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=test_assignment_data
        )
    )

    # Assert p95 latency < 200ms
    assert benchmark.stats.get("mean") < 0.200
```

Optimization strategies:
1. **Database Indexes**: Ensure indexes on (user_id, scope_type, scope_id) for fast lookups
2. **Query Optimization**: Use selectinload() to avoid N+1 queries
3. **Caching**: Cache role-permission mappings in memory (already implemented)
4. **Connection Pooling**: Configure appropriate pool size for database connections
5. **Frontend Caching**: Use TanStack Query staleTime to cache permission check results

```python
# Optimized can_access() with better query
async def can_access(self, user_id, permission, scope_type, scope_id):
    # Single query with joins instead of multiple queries
    stmt = (
        select(UserRoleAssignment)
        .join(Role)
        .where(UserRoleAssignment.user_id == user_id)
        .where(
            or_(
                # Global Admin
                and_(
                    Role.name == "Admin",
                    UserRoleAssignment.scope_type == "global"
                ),
                # Direct scope match
                and_(
                    UserRoleAssignment.scope_type == scope_type,
                    UserRoleAssignment.scope_id == scope_id
                ),
                # Project inheritance for Flow scope
                and_(
                    scope_type == "flow",
                    UserRoleAssignment.scope_type == "project",
                    UserRoleAssignment.scope_id == Flow.folder_id  # Subquery
                )
            )
        )
        .options(selectinload(UserRoleAssignment.role))
    )

    # Rest of logic...
```

**Success Criteria:**
- can_access() p95 latency < 50ms
- Assignment creation p95 latency < 200ms
- Editor page load with RBAC p95 < 2.5s
- All benchmarks pass consistently
- Database queries optimized (no N+1)
- Appropriate indexes created
- Frontend caching configured

---

#### Task 5.4: Create API Documentation and Admin Guide

**Scope and Goals:**
Document all RBAC API endpoints, permission model, and admin workflows. Create guides for managing role assignments and understanding permission inheritance.

**Impact Subgraph:**
- New Nodes: None (documentation only)
- Modified Nodes: None
- Edges: None

**Architecture & Tech Stack:**
- Format: Markdown
- Location: Project documentation directory
- File Locations:
  - `/home/nick/LangBuilder/docs/rbac-api-reference.md`
  - `/home/nick/LangBuilder/docs/rbac-admin-guide.md`
  - `/home/nick/LangBuilder/docs/rbac-permission-model.md`

**Implementation Details:**

Create comprehensive documentation covering:

1. **API Reference:**
   - All RBAC endpoints with request/response examples
   - Authentication requirements
   - Error codes and messages
   - Rate limiting (if applicable)

2. **Permission Model:**
   - Four roles and their permission sets
   - CRUD permissions explained
   - Scope types (global, project, flow)
   - Inheritance rules
   - Special cases (Admin bypass, Starter Project immutability)

3. **Admin Guide:**
   - How to access RBAC Management section
   - Creating role assignments step-by-step
   - Editing and deleting assignments
   - Understanding inheritance in the UI
   - Best practices for role assignment
   - Troubleshooting common issues

4. **Migration Guide:**
   - Upgrading from non-RBAC version
   - Data migration steps
   - Backward compatibility notes
   - Superuser to Admin role mapping

**Success Criteria:**
- All RBAC endpoints documented with examples
- Permission model fully explained with diagrams
- Admin guide includes screenshots and step-by-step instructions
- Migration guide tested on sample deployment
- Documentation reviewed and approved
- Published to project docs site

---

## Dependencies and Ordering

**Critical Path:**
1. Phase 1 (Data Model) → Phase 2 (Service & API) → Phase 3 (Enforcement) → Phase 4 (Frontend UI) → Phase 5 (Testing)
2. Within each phase, tasks are mostly sequential with some parallelization opportunities

**Parallelization Opportunities:**
- Phase 1: Tasks 1.1-1.3 can be developed in parallel (define all models at once)
- Phase 2: API endpoints (Task 2.2) can be developed while service is being finalized
- Phase 3: Flow and Project enforcement can happen in parallel
- Phase 4: UI components can be developed in parallel (list view, modal, hooks)
- Phase 5: Unit tests, integration tests, and documentation can happen in parallel

**Key Dependencies:**
- Phase 3 depends on Phase 2 (RBACService must exist)
- Phase 4 depends on Phase 3 (APIs must be functional)
- Auto-assignment (Task 2.3) depends on User model update and service availability
- Frontend guards (Task 4.4) required before UI integration (Task 4.5)

## Risk Assessment

**High Risks:**
1. **Performance Degradation**: Permission checks add latency to every request
   - Mitigation: Aggressive caching, optimized queries, benchmarking
   - Monitoring: Add telemetry to track check latency

2. **Data Migration Complexity**: Existing users/projects need role assignments
   - Mitigation: Automatic Owner assignment during startup for existing entities
   - Testing: Migration script tested on production data copy

3. **Breaking Changes**: Existing clients may rely on current authorization model
   - Mitigation: Superuser bypass preserved during transition
   - Documentation: Clear migration guide for API consumers

**Medium Risks:**
1. **Complex Permission Inheritance**: Project → Flow inheritance may be confusing
   - Mitigation: Clear UI messaging, comprehensive documentation
   - UX: Inheritance displayed in assignment list

2. **Immutability Edge Cases**: Starter Project detection may fail
   - Mitigation: Robust starter project detection via user.default_project_id
   - Testing: Comprehensive tests for immutability scenarios

3. **Frontend Performance**: Too many permission check API calls
   - Mitigation: TanStack Query caching, batch checking (future enhancement)
   - Monitoring: Track API call volume

## Testing Strategy

**Unit Testing:**
- All RBACService methods
- All data model validation
- All permission evaluation logic
- Role-permission mappings
- Inheritance logic
- Immutability constraints

**Integration Testing:**
- All RBAC API endpoints
- Flow CRUD with permission enforcement
- Project CRUD with permission enforcement
- Auto-assignment on entity creation
- Admin authorization
- Error handling (403, 404, 400)

**End-to-End Testing:**
- Admin creates assignment via UI
- User attempts unauthorized action (blocked)
- User attempts authorized action (succeeds)
- Permission inheritance from Project to Flow
- Immutable assignment cannot be deleted
- Read-only mode for Viewer users

**Performance Testing:**
- can_access() latency < 50ms (p95)
- Assignment API < 200ms (p95)
- Editor page load < 2.5s (p95)
- Load testing with 100+ concurrent users

**User Acceptance Testing:**
- Admin workflow for managing assignments
- Non-admin users see appropriate restrictions
- UI elements hidden/disabled correctly
- Error messages clear and helpful
- Documentation accurate and complete

---

## Appendix: AppGraph Reference

### New Nodes Summary (36 total)

**Schema Nodes (4):**
- ns0010: Role
- ns0011: Permission
- ns0012: RolePermission
- ns0013: UserRoleAssignment

**Logic Nodes (7):**
- nl0504: RBACService
- nl0505-nl0510: RBAC API endpoints (roles, assignments CRUD, check-permission)

**Interface Nodes (5):**
- ni0083: RBACManagementPage
- ni0084: AssignmentListView
- ni0085: CreateAssignmentModal
- ni0086: RBACGuard
- ni0087: usePermission

**Validation Nodes (20):**
- Gherkin acceptance criteria for all PRD stories (Epic 1-5)

### Modified Nodes Summary (18 total)

**Interface Nodes (3):**
- ni0001: AdminPage (add RBAC tab)
- ni0006: CollectionPage (filter by permission, hide buttons)
- ni0009: FlowPage (read-only mode, permission guards)

**Schema Nodes (3):**
- ns0001: User (add default_project_id, role_assignments relationship)
- ns0002: Flow (no schema change, enforcement only)
- ns0003: Folder (no schema change, enforcement only)

**Logic Nodes (12):**
- nl0004: Create Flow (auto-assign Owner)
- nl0005: List Flows (filter by Read permission)
- nl0007: Get Flow by ID (check Read permission)
- nl0009: Update Flow (check Update permission)
- nl0010: Delete Flow (check Delete permission)
- nl0012: Upload Flows (check Update permission)
- nl0042: Create Project (auto-assign Owner, immutability for Starter)
- nl0043: List Projects (filter by Read permission)
- nl0044: Get Project by ID (check Read permission)
- nl0045: Update Project (check Update permission)
- nl0046: Delete Project (check Delete permission)
- nl0061: Build Flow (check Read permission)

---

**Document Version:** 1.0
**Created:** 2025-11-03
**Author:** Claude (Implementation Planning Agent)
**Status:** Draft for Review
