# RBAC Implementation Plan for LangBuilder

**Version:** 1.0
**Created:** 2025-01-07
**Feature:** Role-Based Access Control (RBAC) MVP
**Status:** Draft - Awaiting Audit

---

## Executive Summary

This implementation plan details the phased rollout of a comprehensive Role-Based Access Control (RBAC) system for LangBuilder. The RBAC system will provide fine-grained permission enforcement across Projects (Folders) and Flows, enabling secure multi-user collaboration while maintaining backward compatibility with the existing authentication system.

### Scope

**In-Scope for MVP:**
- Core RBAC data model (Roles, Permissions, RolePermissions, UserRoleAssignments)
- Four default roles: Owner, Admin, Editor, Viewer
- CRUD permissions: Create, Read, Update, Delete
- Two entity scopes: Flow, Project
- Enforcement engine with permission checks across all API endpoints
- Web-based Admin UI for role assignment management
- Project-to-Flow role inheritance
- Immutable Starter Project Owner assignment
- Database migrations using Alembic
- Comprehensive test coverage (unit, integration, E2E)

**Out-of-Scope:**
- Custom roles or permissions beyond CRUD
- SSO/SCIM/User Groups
- Component, Environment, Workspace, or API Token scopes
- User-triggered flow sharing
- Fine-grained permissions (e.g., Can_export_flow, Can_deploy_environment)

### Key Objectives

1. **Security:** Enforce fine-grained access control on all resources
2. **Customizability:** Support flexible role assignments per user/resource
3. **Usability:** Centralized Admin UI for role management
4. **Performance:** <50ms p95 latency for permission checks
5. **Backward Compatibility:** Existing flows and projects remain accessible to owners

---

## Implementation Phases

The implementation is divided into 5 phases with 27 total tasks:

| Phase | Focus Area | Tasks | Duration Est. |
|-------|-----------|-------|---------------|
| **Phase 1** | Foundation & Data Model | 6 tasks | 3-4 days |
| **Phase 2** | Authorization Service & Enforcement | 7 tasks | 5-6 days |
| **Phase 3** | Admin UI - Backend API | 5 tasks | 2-3 days |
| **Phase 4** | Admin UI - Frontend | 5 tasks | 4-5 days |
| **Phase 5** | Testing, Performance & Documentation | 4 tasks | 3-4 days |

**Total Estimated Duration:** 17-22 days

---

## Phase 1: Foundation & Data Model

**Goal:** Establish the persistent data model for roles, permissions, and assignments, including database migrations and initial data seeding.

### Task 1.1: Define RBAC Database Models

**Description:** Create SQLModel schemas for the four core RBAC tables: Role, Permission, RolePermission, and UserRoleAssignment.

**Impact Subgraph:**
- **New Nodes:**
  - `ns0010`: Role schema (`src/backend/base/langbuilder/services/database/models/role/model.py`)
  - `ns0011`: Permission schema (`src/backend/base/langbuilder/services/database/models/permission/model.py`)
  - `ns0012`: RolePermission schema (`src/backend/base/langbuilder/services/database/models/role_permission/model.py`)
  - `ns0013`: UserRoleAssignment schema (`src/backend/base/langbuilder/services/database/models/user_role_assignment/model.py`)

**Files to Create:**
```
src/backend/base/langbuilder/services/database/models/
├── role/
│   ├── __init__.py
│   ├── model.py          # Role SQLModel
│   ├── crud.py           # CRUD operations
│   └── schema.py         # Pydantic schemas (RoleCreate, RoleRead, RoleUpdate)
├── permission/
│   ├── __init__.py
│   ├── model.py          # Permission SQLModel
│   ├── crud.py           # CRUD operations
│   └── schema.py         # Pydantic schemas
├── role_permission/
│   ├── __init__.py
│   ├── model.py          # RolePermission SQLModel (junction table)
│   ├── crud.py           # CRUD operations
│   └── schema.py         # Pydantic schemas
└── user_role_assignment/
    ├── __init__.py
    ├── model.py          # UserRoleAssignment SQLModel
    ├── crud.py           # CRUD operations
    └── schema.py         # Pydantic schemas
```

**Tech Stack:**
- SQLModel (Pydantic 2.x + SQLAlchemy)
- Python 3.10+
- Async database operations (asyncio)

**Data Model Specifications:**

**Role Model:**
```python
class Role(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True, index=True)  # "Owner", "Admin", "Editor", "Viewer"
    description: str | None = Field(default=None)
    is_system_role: bool = Field(default=False)  # Prevents deletion of default roles
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    role_permissions: list["RolePermission"] = Relationship(back_populates="role", cascade="delete")
    user_assignments: list["UserRoleAssignment"] = Relationship(back_populates="role")
```

**Permission Model:**
```python
class Permission(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)  # "Create", "Read", "Update", "Delete"
    scope: str = Field(index=True)  # "Flow", "Project"
    description: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    role_permissions: list["RolePermission"] = Relationship(back_populates="permission")

    __table_args__ = (
        UniqueConstraint("name", "scope", name="unique_permission_scope"),
    )
```

**RolePermission Model (Junction Table):**
```python
class RolePermission(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    role_id: UUID = Field(foreign_key="role.id", index=True)
    permission_id: UUID = Field(foreign_key="permission.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    role: Role = Relationship(back_populates="role_permissions")
    permission: Permission = Relationship(back_populates="role_permissions")

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="unique_role_permission"),
    )
```

**UserRoleAssignment Model:**
```python
class UserRoleAssignment(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    role_id: UUID = Field(foreign_key="role.id", index=True)
    scope_type: str = Field(index=True)  # "Flow", "Project", "Global"
    scope_id: UUID | None = Field(default=None, index=True)  # Flow/Project ID, null for Global Admin
    is_immutable: bool = Field(default=False)  # True for Starter Project Owner
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: UUID | None = Field(foreign_key="user.id", nullable=True)  # Admin who created assignment

    # Relationships
    user: "User" = Relationship()
    role: Role = Relationship(back_populates="user_assignments")
    creator: Optional["User"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[UserRoleAssignment.created_by]"})

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "scope_type", "scope_id", name="unique_user_role_scope"),
    )
```

**Success Criteria:**
- [ ] All four SQLModel classes defined with correct fields and relationships
- [ ] CRUD functions implemented for each model (create, read by ID, list, update, delete)
- [ ] Pydantic schemas created for API request/response validation
- [ ] All models properly exported in `__init__.py` files
- [ ] Type hints correct and pass mypy validation
- [ ] Code formatted with `make format_backend`

**PRD Alignment:** Epic 1, Story 1.1

---

### Task 1.2: Create Alembic Migration for RBAC Tables

**Description:** Generate and test Alembic migration script to create the four RBAC tables in the database.

**Impact Subgraph:**
- Creates database schema changes

**Files to Create:**
```
src/backend/base/langbuilder/alembic/versions/
└── <revision>_add_rbac_tables.py
```

**Implementation Steps:**
1. Run `make alembic-revision message="Add RBAC tables (Role, Permission, RolePermission, UserRoleAssignment)"`
2. Review auto-generated migration script
3. Verify foreign key constraints are correct
4. Verify unique constraints are applied
5. Add indexes for performance (user_id, scope_type, scope_id composite index)
6. Test migration: `make alembic-upgrade`
7. Test rollback: `make alembic-downgrade`

**Tech Stack:**
- Alembic (SQLAlchemy migrations)
- SQLite (development), PostgreSQL (production)

**Success Criteria:**
- [ ] Migration script created and reviewed
- [ ] Migration applies cleanly on SQLite and PostgreSQL
- [ ] All tables, indexes, and constraints created correctly
- [ ] Rollback (downgrade) works without errors
- [ ] Migration includes composite index on (user_id, scope_type, scope_id) for performance

**PRD Alignment:** Epic 1, Story 1.1

---

### Task 1.3: Create Database Seed Script for Default Roles and Permissions

**Description:** Implement initialization script to populate default roles (Owner, Admin, Editor, Viewer) and permissions (Create, Read, Update, Delete for Flow and Project scopes).

**Impact Subgraph:**
- Initializes RBAC system with default data

**Files to Create:**
```
src/backend/base/langbuilder/services/database/models/role/
└── seed_data.py

src/backend/base/langbuilder/initial_setup/
└── rbac_setup.py  # Called during app lifespan initialization
```

**Implementation:**

**Default Permissions (8 total):**
| Permission | Scope | Description |
|------------|-------|-------------|
| Create | Flow | Create new flows within a project |
| Read | Flow | View/execute/export/download flows |
| Update | Flow | Edit/import flows |
| Delete | Flow | Delete flows |
| Create | Project | Create new projects |
| Read | Project | View projects |
| Update | Project | Edit/import projects |
| Delete | Project | Delete projects |

**Default Roles and Permission Mappings:**
| Role | Permissions (Flow) | Permissions (Project) |
|------|-------------------|----------------------|
| **Viewer** | Read | Read |
| **Editor** | Create, Read, Update | Create, Read, Update |
| **Owner** | Create, Read, Update, Delete | Create, Read, Update, Delete |
| **Admin** | Create, Read, Update, Delete (Global) | Create, Read, Update, Delete (Global) |

**Seed Script Logic:**
```python
async def seed_rbac_data(db: AsyncSession):
    # 1. Create permissions
    permissions = []
    for scope in ["Flow", "Project"]:
        for action in ["Create", "Read", "Update", "Delete"]:
            perm = Permission(name=action, scope=scope, description=f"{action} access to {scope}")
            permissions.append(perm)

    db.add_all(permissions)
    await db.commit()

    # 2. Create roles
    roles_data = [
        {"name": "Viewer", "description": "Read-only access", "is_system_role": True},
        {"name": "Editor", "description": "Create, Read, Update access", "is_system_role": True},
        {"name": "Owner", "description": "Full access to owned resources", "is_system_role": True},
        {"name": "Admin", "description": "Global administrator with full access", "is_system_role": True},
    ]

    roles = {}
    for role_data in roles_data:
        role = Role(**role_data)
        db.add(role)
        roles[role_data["name"]] = role

    await db.commit()

    # 3. Map permissions to roles
    role_permission_map = {
        "Viewer": [("Read", "Flow"), ("Read", "Project")],
        "Editor": [("Create", "Flow"), ("Read", "Flow"), ("Update", "Flow"),
                   ("Create", "Project"), ("Read", "Project"), ("Update", "Project")],
        "Owner": [("Create", "Flow"), ("Read", "Flow"), ("Update", "Flow"), ("Delete", "Flow"),
                  ("Create", "Project"), ("Read", "Project"), ("Update", "Project"), ("Delete", "Project")],
        "Admin": [("Create", "Flow"), ("Read", "Flow"), ("Update", "Flow"), ("Delete", "Flow"),
                  ("Create", "Project"), ("Read", "Project"), ("Update", "Project"), ("Delete", "Project")],
    }

    for role_name, perm_list in role_permission_map.items():
        role = roles[role_name]
        for action, scope in perm_list:
            perm = await get_permission_by_name_and_scope(db, action, scope)
            role_perm = RolePermission(role_id=role.id, permission_id=perm.id)
            db.add(role_perm)

    await db.commit()
```

**Integration into App Lifespan:**
```python
# In src/backend/base/langbuilder/main.py lifespan function
async def lifespan(_app: FastAPI):
    # ... existing initialization ...

    # Initialize RBAC system (after database initialization)
    await initialize_rbac_if_needed()

    # ... rest of lifespan ...
```

**Tech Stack:**
- SQLModel CRUD operations
- Async database sessions

**Success Criteria:**
- [ ] Seed script creates all 8 permissions (4 actions x 2 scopes)
- [ ] Seed script creates all 4 default roles
- [ ] RolePermission junction records correctly map permissions to roles
- [ ] Script is idempotent (can run multiple times safely)
- [ ] Seed runs automatically during app startup if RBAC tables are empty
- [ ] All system roles have `is_system_role=True` to prevent deletion

**PRD Alignment:** Epic 1, Story 1.2

---

### Task 1.4: Update User Model with RBAC Relationships

**Description:** Add relationships to the User model to support role assignments and maintain backward compatibility with `is_superuser` flag.

**Impact Subgraph:**
- **Modified Nodes:**
  - `ns0001`: User schema (`src/backend/base/langbuilder/services/database/models/user/model.py`)

**Files to Modify:**
```
src/backend/base/langbuilder/services/database/models/user/
└── model.py
```

**Implementation:**
```python
class User(SQLModel, table=True):
    # ... existing fields ...

    # RBAC relationships
    role_assignments: list["UserRoleAssignment"] = Relationship(
        back_populates="user",
        cascade="delete"
    )

    # Helper method to check if user is Admin (either via is_superuser or Admin role)
    async def has_global_admin_role(self, db: AsyncSession) -> bool:
        """Check if user is a global Admin via is_superuser or Admin role assignment"""
        if self.is_superuser:
            return True

        stmt = select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == self.id,
            UserRoleAssignment.scope_type == "Global",
            UserRoleAssignment.role.has(Role.name == "Admin")
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None
```

**Backward Compatibility Strategy:**
- Keep existing `is_superuser` field for backward compatibility
- `is_superuser=True` users automatically treated as Global Admins in RBAC checks
- Existing users with `is_superuser=False` remain unchanged until roles are assigned

**Success Criteria:**
- [ ] User model has `role_assignments` relationship
- [ ] Helper method `has_global_admin_role()` implemented
- [ ] Backward compatibility with `is_superuser` maintained
- [ ] No breaking changes to existing User CRUD operations

**PRD Alignment:** Epic 1, Story 1.2

---

### Task 1.5: Update Flow and Folder Models with RBAC Metadata

**Description:** Add metadata fields to Flow and Folder (Project) models to support RBAC immutability checks and assignment tracking.

**Impact Subgraph:**
- **Modified Nodes:**
  - `ns0002`: Flow schema (`src/backend/base/langbuilder/services/database/models/flow/model.py`)
  - `ns0003`: Folder schema (`src/backend/base/langbuilder/services/database/models/folder/model.py`)

**Files to Modify:**
```
src/backend/base/langbuilder/services/database/models/flow/
└── model.py

src/backend/base/langbuilder/services/database/models/folder/
└── model.py
```

**Implementation:**

**Folder (Project) Model Updates:**
```python
class Folder(FolderBase, table=True):
    # ... existing fields ...

    # RBAC metadata
    is_starter_project: bool = Field(default=False)  # Marks the user's default Starter Project

    # Relationships (add to existing)
    role_assignments: list["UserRoleAssignment"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[UserRoleAssignment.scope_id]",
            "primaryjoin": "and_(Folder.id == UserRoleAssignment.scope_id, UserRoleAssignment.scope_type == 'Project')"
        }
    )
```

**Flow Model Updates:**
```python
class Flow(FlowBase, table=True):
    # ... existing fields ...

    # Relationships (add to existing)
    role_assignments: list["UserRoleAssignment"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[UserRoleAssignment.scope_id]",
            "primaryjoin": "and_(Flow.id == UserRoleAssignment.scope_id, UserRoleAssignment.scope_type == 'Flow')"
        }
    )
```

**Alembic Migration:**
Create migration to add `is_starter_project` column to Folder table:
```bash
make alembic-revision message="Add is_starter_project to Folder for RBAC immutability"
```

**Success Criteria:**
- [ ] `is_starter_project` field added to Folder model
- [ ] `role_assignments` relationships added to both Flow and Folder models
- [ ] Migration created and tested for schema changes
- [ ] Existing Starter Projects marked with `is_starter_project=True` via data migration

**PRD Alignment:** Epic 1, Story 1.4

---

### Task 1.6: Create Initial Owner Assignments for Existing Resources

**Description:** Create a data migration script to assign Owner roles to existing users for their existing Projects and Flows.

**Impact Subgraph:**
- Ensures backward compatibility by granting existing users Owner roles on their resources

**Files to Create:**
```
src/backend/base/langbuilder/alembic/versions/
└── <revision>_backfill_owner_role_assignments.py
```

**Implementation:**
```python
def upgrade():
    # Get Admin role ID
    admin_role = op.get_bind().execute(
        text("SELECT id FROM role WHERE name = 'Owner'")
    ).fetchone()

    if not admin_role:
        raise Exception("Owner role not found. Run RBAC seed script first.")

    owner_role_id = admin_role[0]

    # Assign Owner role to all users for their existing Projects
    op.execute(text(f"""
        INSERT INTO user_role_assignment (id, user_id, role_id, scope_type, scope_id, is_immutable, created_at)
        SELECT
            uuid_generate_v4(),
            f.user_id,
            '{owner_role_id}',
            'Project',
            f.id,
            f.is_starter_project,  -- Starter Projects are immutable
            NOW()
        FROM folder f
        WHERE f.user_id IS NOT NULL
    """))

    # Assign Owner role to all users for their existing Flows (where no folder assignment exists)
    # Note: Users will inherit Project-level Owner role for Flows in Projects
    op.execute(text(f"""
        INSERT INTO user_role_assignment (id, user_id, role_id, scope_type, scope_id, is_immutable, created_at)
        SELECT
            uuid_generate_v4(),
            fl.user_id,
            '{owner_role_id}',
            'Flow',
            fl.id,
            FALSE,
            NOW()
        FROM flow fl
        WHERE fl.user_id IS NOT NULL
        AND fl.folder_id IS NULL  -- Only for flows not in a project
    """))
```

**Success Criteria:**
- [ ] Data migration creates Owner role assignments for all existing Projects
- [ ] Data migration creates Owner role assignments for standalone Flows (not in Projects)
- [ ] Starter Projects have `is_immutable=True` on Owner assignments
- [ ] No duplicate assignments created
- [ ] Migration is reversible (downgrade removes assignments)

**PRD Alignment:** Epic 1, Story 1.5

---

## Phase 2: Authorization Service & Enforcement

**Goal:** Implement the core authorization service (`RBACService`) and integrate permission checks across all API endpoints.

### Task 2.1: Implement RBACService Core Logic

**Description:** Create the RBACService with the core `can_access()` method and role assignment CRUD operations.

**Impact Subgraph:**
- **New Nodes:**
  - `nl0504`: RBACService (`src/backend/base/langbuilder/services/rbac/service.py`)

**Files to Create:**
```
src/backend/base/langbuilder/services/rbac/
├── __init__.py
├── service.py           # RBACService class
├── factory.py           # Service factory
└── exceptions.py        # Custom RBAC exceptions
```

**Implementation:**

**RBACService Core Methods:**
```python
class RBACService(Service):
    """Role-Based Access Control service for permission checks and role management"""

    async def can_access(
        self,
        user_id: UUID,
        permission_name: str,  # "Create", "Read", "Update", "Delete"
        scope_type: str,        # "Flow", "Project"
        scope_id: UUID | None,  # Specific resource ID
        db: AsyncSession
    ) -> bool:
        """
        Core authorization check. Returns True if user has permission.

        Logic:
        1. Check if user is superuser (bypass all checks)
        2. Check if user has Global Admin role (bypass all checks)
        3. For Flow scope:
           - Check for explicit Flow-level role assignment
           - If none, check for inherited Project-level role assignment
        4. For Project scope:
           - Check for explicit Project-level role assignment
        5. Check if role has the required permission
        """
        # 1. Superuser bypass
        user = await get_user_by_id(db, user_id)
        if user.is_superuser:
            return True

        # 2. Global Admin role bypass
        if await self._has_global_admin_role(user_id, db):
            return True

        # 3. Get user's role for the scope
        role = await self._get_user_role_for_scope(user_id, scope_type, scope_id, db)

        if not role:
            return False

        # 4. Check if role has the permission
        return await self._role_has_permission(role.id, permission_name, scope_type, db)

    async def _has_global_admin_role(self, user_id: UUID, db: AsyncSession) -> bool:
        """Check if user has Global Admin role"""
        stmt = select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.scope_type == "Global",
        ).join(Role).where(Role.name == "Admin")

        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _get_user_role_for_scope(
        self,
        user_id: UUID,
        scope_type: str,
        scope_id: UUID | None,
        db: AsyncSession
    ) -> Role | None:
        """
        Get user's role for a specific scope.
        For Flow scope: checks Flow-specific assignment first, then inherited Project assignment.
        """
        # Check for explicit scope assignment
        stmt = select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.scope_type == scope_type,
            UserRoleAssignment.scope_id == scope_id
        ).join(Role)

        result = await db.execute(stmt)
        assignment = result.scalar_one_or_none()

        if assignment:
            return assignment.role

        # For Flow scope, check inherited Project role
        if scope_type == "Flow" and scope_id:
            flow = await get_flow_by_id(db, scope_id)
            if flow and flow.folder_id:
                return await self._get_user_role_for_scope(
                    user_id, "Project", flow.folder_id, db
                )

        return None

    async def _role_has_permission(
        self,
        role_id: UUID,
        permission_name: str,
        scope_type: str,
        db: AsyncSession
    ) -> bool:
        """Check if role has a specific permission"""
        stmt = select(RolePermission).where(
            RolePermission.role_id == role_id
        ).join(Permission).where(
            Permission.name == permission_name,
            Permission.scope == scope_type
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def assign_role(
        self,
        user_id: UUID,
        role_name: str,
        scope_type: str,
        scope_id: UUID | None,
        created_by: UUID,
        db: AsyncSession,
        is_immutable: bool = False
    ) -> UserRoleAssignment:
        """Create a new role assignment"""
        # Get role by name
        role = await get_role_by_name(db, role_name)
        if not role:
            raise RBACException(f"Role '{role_name}' not found")

        # Check for duplicate assignment
        existing = await self._get_assignment(user_id, role.id, scope_type, scope_id, db)
        if existing:
            raise RBACException("Role assignment already exists")

        # Create assignment
        assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=role.id,
            scope_type=scope_type,
            scope_id=scope_id,
            is_immutable=is_immutable,
            created_by=created_by
        )

        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)

        return assignment

    async def remove_role(
        self,
        assignment_id: UUID,
        db: AsyncSession
    ) -> None:
        """Remove a role assignment (if not immutable)"""
        assignment = await get_assignment_by_id(db, assignment_id)

        if not assignment:
            raise RBACException("Assignment not found")

        if assignment.is_immutable:
            raise RBACException("Cannot remove immutable assignment (Starter Project Owner)")

        await db.delete(assignment)
        await db.commit()

    async def update_role(
        self,
        assignment_id: UUID,
        new_role_name: str,
        db: AsyncSession
    ) -> UserRoleAssignment:
        """Update an existing role assignment (if not immutable)"""
        assignment = await get_assignment_by_id(db, assignment_id)

        if not assignment:
            raise RBACException("Assignment not found")

        if assignment.is_immutable:
            raise RBACException("Cannot modify immutable assignment (Starter Project Owner)")

        new_role = await get_role_by_name(db, new_role_name)
        if not new_role:
            raise RBACException(f"Role '{new_role_name}' not found")

        assignment.role_id = new_role.id
        await db.commit()
        await db.refresh(assignment)

        return assignment

    async def list_user_assignments(
        self,
        user_id: UUID | None,
        db: AsyncSession
    ) -> list[UserRoleAssignment]:
        """List all role assignments, optionally filtered by user"""
        stmt = select(UserRoleAssignment)

        if user_id:
            stmt = stmt.where(UserRoleAssignment.user_id == user_id)

        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_user_permissions_for_scope(
        self,
        user_id: UUID,
        scope_type: str,
        scope_id: UUID | None,
        db: AsyncSession
    ) -> list[Permission]:
        """Get all permissions a user has for a specific scope"""
        role = await self._get_user_role_for_scope(user_id, scope_type, scope_id, db)

        if not role:
            return []

        stmt = select(Permission).join(RolePermission).where(
            RolePermission.role_id == role.id,
            Permission.scope == scope_type
        )

        result = await db.execute(stmt)
        return result.scalars().all()
```

**Dependency Injection Setup:**
```python
# In src/backend/base/langbuilder/services/deps.py
def get_rbac_service() -> RBACService:
    return service_manager.get(RBACService)

# Type alias
RBACServiceDep = Annotated[RBACService, Depends(get_rbac_service)]
```

**Tech Stack:**
- FastAPI dependency injection
- SQLModel/SQLAlchemy async queries
- Python 3.10+ type hints

**Success Criteria:**
- [ ] `can_access()` method implements all logic from PRD Story 2.1
- [ ] Superuser and Global Admin bypass logic working
- [ ] Flow-to-Project role inheritance working
- [ ] Role assignment CRUD methods implemented
- [ ] Immutability checks prevent modification of Starter Project Owner assignments
- [ ] Service registered in service manager for DI
- [ ] All methods have comprehensive docstrings
- [ ] Code passes `make format_backend` and `make lint`

**PRD Alignment:** Epic 2, Story 2.1; Epic 1, Story 1.3

---

### Task 2.2: Enforce Read Permission on List Flows Endpoint

**Description:** Integrate RBAC checks into the `GET /api/v1/flows` endpoint to filter flows based on user's Read permission.

**Impact Subgraph:**
- **Modified Nodes:**
  - `nl0005`: List Flows Endpoint Handler (`src/backend/base/langbuilder/api/v1/flows.py`)

**Files to Modify:**
```
src/backend/base/langbuilder/api/v1/
└── flows.py
```

**Current Implementation:**
```python
@router.get("/")
async def read_flows(
    current_user: CurrentActiveUser,
    db: DbSession,
    skip: int = 0,
    limit: int = 100
):
    # Current: Returns all flows where user_id == current_user.id OR is_superuser
    if current_user.is_superuser:
        stmt = select(Flow).offset(skip).limit(limit)
    else:
        stmt = select(Flow).where(Flow.user_id == current_user.id).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()
```

**New Implementation with RBAC:**
```python
@router.get("/")
async def read_flows(
    current_user: CurrentActiveUser,
    db: DbSession,
    rbac: RBACServiceDep,
    skip: int = 0,
    limit: int = 100
):
    # 1. Get all flows (or user's flows if not superuser/admin)
    if current_user.is_superuser or await rbac._has_global_admin_role(current_user.id, db):
        stmt = select(Flow).offset(skip).limit(limit)
    else:
        # Get flows where user has explicit role assignment OR inherited via Project
        stmt = (
            select(Flow)
            .outerjoin(
                UserRoleAssignment,
                and_(
                    UserRoleAssignment.scope_id == Flow.id,
                    UserRoleAssignment.scope_type == "Flow",
                    UserRoleAssignment.user_id == current_user.id
                )
            )
            .outerjoin(
                Folder,
                Flow.folder_id == Folder.id
            )
            .outerjoin(
                UserRoleAssignment,
                and_(
                    UserRoleAssignment.scope_id == Folder.id,
                    UserRoleAssignment.scope_type == "Project",
                    UserRoleAssignment.user_id == current_user.id
                ),
                isouter=True
            )
            .where(
                or_(
                    UserRoleAssignment.id.isnot(None),  # Has explicit Flow assignment
                    UserRoleAssignment.id.isnot(None)   # Has inherited Project assignment
                )
            )
            .offset(skip)
            .limit(limit)
        )

    result = await db.execute(stmt)
    flows = result.scalars().all()

    # 2. Filter flows by Read permission
    accessible_flows = []
    for flow in flows:
        if await rbac.can_access(current_user.id, "Read", "Flow", flow.id, db):
            accessible_flows.append(flow)

    return accessible_flows
```

**Performance Optimization:**
Pre-fetch all role assignments in a single query to avoid N+1 queries:
```python
# Option: Batch permission check
async def batch_filter_by_permission(
    user_id: UUID,
    flows: list[Flow],
    permission_name: str,
    rbac: RBACService,
    db: AsyncSession
) -> list[Flow]:
    """Filter flows by permission in a single query"""
    # Pre-fetch all assignments
    flow_ids = [f.id for f in flows]
    assignments = await rbac.get_user_assignments_for_resources(
        user_id, "Flow", flow_ids, db
    )

    # Build lookup map
    assignment_map = {a.scope_id: a for a in assignments}

    # Filter
    accessible = []
    for flow in flows:
        if flow.id in assignment_map:
            # Check if role has permission
            role = assignment_map[flow.id].role
            if await rbac._role_has_permission(role.id, permission_name, "Flow", db):
                accessible.append(flow)

    return accessible
```

**Success Criteria:**
- [ ] Only flows with Read permission are returned
- [ ] Superuser and Global Admin bypass logic working
- [ ] Project-level role inheritance applied correctly
- [ ] Performance: <100ms p95 latency for 100 flows
- [ ] No N+1 query issues (use batch queries or joins)

**PRD Alignment:** Epic 2, Story 2.2

---

### Task 2.3: Enforce Create Permission on Create Flow Endpoint

**Description:** Add RBAC check to `POST /api/v1/flows` to verify user has Create permission on the target Project.

**Impact Subgraph:**
- **Modified Nodes:**
  - `nl0004`: Create Flow Endpoint Handler (`src/backend/base/langbuilder/api/v1/flows.py`)

**Files to Modify:**
```
src/backend/base/langbuilder/api/v1/
└── flows.py
```

**Current Implementation:**
```python
@router.post("/", response_model=FlowRead, status_code=201)
async def create_flow(
    flow: FlowCreate,
    current_user: CurrentActiveUser,
    db: DbSession
):
    # Current: No permission check, creates flow owned by current_user
    new_flow = Flow(**flow.model_dump(), user_id=current_user.id)
    db.add(new_flow)
    await db.commit()
    await db.refresh(new_flow)
    return new_flow
```

**New Implementation with RBAC:**
```python
@router.post("/", response_model=FlowRead, status_code=201)
async def create_flow(
    flow: FlowCreate,
    current_user: CurrentActiveUser,
    db: DbSession,
    rbac: RBACServiceDep
):
    # 1. Check if user has Create permission on the target Project
    if flow.folder_id:
        has_permission = await rbac.can_access(
            current_user.id,
            "Create",
            "Project",
            flow.folder_id,
            db
        )

        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to create flows in this project"
            )

    # 2. Create the flow
    new_flow = Flow(**flow.model_dump(), user_id=current_user.id)
    db.add(new_flow)
    await db.commit()
    await db.refresh(new_flow)

    # 3. Assign Owner role to creating user for this Flow
    await rbac.assign_role(
        user_id=current_user.id,
        role_name="Owner",
        scope_type="Flow",
        scope_id=new_flow.id,
        created_by=current_user.id,
        db=db
    )

    return new_flow
```

**Success Criteria:**
- [ ] Users without Create permission on Project receive 403 error
- [ ] Flows are created successfully when user has permission
- [ ] Creating user automatically assigned Owner role on new Flow
- [ ] Superuser and Global Admin can create flows in any Project

**PRD Alignment:** Epic 2, Story 2.3; Epic 1, Story 1.5

---

### Task 2.4: Enforce Update Permission on Update Flow Endpoint

**Description:** Add RBAC check to `PATCH /api/v1/flows/{flow_id}` to verify user has Update permission.

**Impact Subgraph:**
- **Modified Nodes:**
  - `nl0009`: Update Flow Endpoint Handler (`src/backend/base/langbuilder/api/v1/flows.py`)

**Files to Modify:**
```
src/backend/base/langbuilder/api/v1/
└── flows.py
```

**Implementation:**
```python
@router.patch("/{flow_id}", response_model=FlowRead)
async def update_flow(
    flow_id: UUID,
    flow_update: FlowUpdate,
    current_user: CurrentActiveUser,
    db: DbSession,
    rbac: RBACServiceDep
):
    # 1. Check Update permission
    has_permission = await rbac.can_access(
        current_user.id,
        "Update",
        "Flow",
        flow_id,
        db
    )

    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to update this flow"
        )

    # 2. Update the flow
    flow = await get_flow_by_id(db, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    update_data = flow_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(flow, key, value)

    await db.commit()
    await db.refresh(flow)

    return flow
```

**Success Criteria:**
- [ ] Users without Update permission receive 403 error
- [ ] Users with Editor or Owner role can update flows
- [ ] Viewers cannot update flows
- [ ] Flow import functionality also checks Update permission

**PRD Alignment:** Epic 2, Story 2.4

---

### Task 2.5: Enforce Delete Permission on Delete Flow Endpoint

**Description:** Add RBAC check to `DELETE /api/v1/flows/{flow_id}` to verify user has Delete permission.

**Impact Subgraph:**
- **Modified Nodes:**
  - `nl0010`: Delete Flow Endpoint Handler (`src/backend/base/langbuilder/api/v1/flows.py`)

**Files to Modify:**
```
src/backend/base/langbuilder/api/v1/
└── flows.py
```

**Implementation:**
```python
@router.delete("/{flow_id}", status_code=204)
async def delete_flow(
    flow_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
    rbac: RBACServiceDep
):
    # 1. Check Delete permission
    has_permission = await rbac.can_access(
        current_user.id,
        "Delete",
        "Flow",
        flow_id,
        db
    )

    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete this flow"
        )

    # 2. Delete the flow
    flow = await get_flow_by_id(db, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    await db.delete(flow)
    await db.commit()

    return Response(status_code=204)
```

**Success Criteria:**
- [ ] Only users with Delete permission (Owner, Admin) can delete flows
- [ ] Editors and Viewers receive 403 error when attempting to delete
- [ ] Flow deletion cascades to related UserRoleAssignments

**PRD Alignment:** Epic 2, Story 2.5

---

### Task 2.6: Enforce Permissions on Project (Folder) Endpoints

**Description:** Add RBAC checks to all Project endpoints (`/api/v1/projects/*`) for Create, Read, Update, Delete permissions.

**Impact Subgraph:**
- **Modified Nodes:**
  - `nl0042`: Create Project Endpoint
  - `nl0043`: List Projects Endpoint
  - `nl0044`: Get Project by ID Endpoint
  - `nl0045`: Update Project Endpoint
  - `nl0046`: Delete Project Endpoint

**Files to Modify:**
```
src/backend/base/langbuilder/api/v1/
└── projects.py
```

**Implementation Pattern:**
Same pattern as Flow endpoints:
- **List Projects:** Filter by Read permission
- **Create Project:** All authenticated users can create (Global permission per Story 1.5), auto-assign Owner role
- **Update Project:** Check Update permission
- **Delete Project:** Check Delete permission

**Special Handling for Starter Projects:**
```python
@router.delete("/projects/{project_id}")
async def delete_project(project_id: UUID, ...):
    # Check if this is a Starter Project
    project = await get_folder_by_id(db, project_id)
    if project.is_starter_project:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete Starter Project"
        )

    # ... rest of delete logic ...
```

**Success Criteria:**
- [ ] All 5 Project endpoints have RBAC checks
- [ ] Starter Projects cannot be deleted
- [ ] Owner assignments on Starter Projects are immutable
- [ ] Creating a Project auto-assigns Owner role to creator

**PRD Alignment:** Epic 2, Stories 2.2-2.5; Epic 1, Story 1.4

---

### Task 2.7: Enforce Permissions on Additional Endpoints

**Description:** Add RBAC checks to auxiliary endpoints that access Flows or Projects.

**Impact Subgraph:**
- **Modified Nodes:**
  - `nl0007`: Get Flow by ID Endpoint
  - `nl0012`: Upload Flows Endpoint
  - `nl0061`: Build Flow Endpoint (chat execution)

**Files to Modify:**
```
src/backend/base/langbuilder/api/v1/
├── flows.py          # GET /{flow_id}, POST /upload
└── chat.py           # POST /build/{flow_id}
```

**Endpoints to Secure:**

1. **GET /api/v1/flows/{flow_id}** - Requires Read permission
2. **POST /api/v1/flows/upload** - Requires Create permission on target Project
3. **POST /api/v1/build/{flow_id}** - Requires Read permission (execution = viewing)
4. **GET /api/v1/flows/{flow_id}/download** - Requires Read permission
5. **POST /api/v1/flows/{flow_id}/export** - Requires Read permission

**Implementation Example (Build/Execute Flow):**
```python
@router.post("/build/{flow_id}")
async def build_flow(
    flow_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
    rbac: RBACServiceDep
):
    # Check Read permission (execution requires viewing)
    has_permission = await rbac.can_access(
        current_user.id,
        "Read",
        "Flow",
        flow_id,
        db
    )

    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to execute this flow"
        )

    # ... build and execute flow ...
```

**Success Criteria:**
- [ ] All flow access endpoints check Read permission
- [ ] Upload endpoint checks Create permission on target Project
- [ ] Export/download endpoints check Read permission
- [ ] Build/execute endpoint checks Read permission

**PRD Alignment:** Epic 2, Story 2.2 (Read permission for execution, export, download)

---

## Phase 3: Admin UI - Backend API

**Goal:** Implement backend API endpoints for RBAC management, accessible only to Admin users.

### Task 3.1: Create RBAC Router with Admin Guard

**Description:** Create a new API router (`/api/v1/rbac/*`) with Admin-only access control.

**Impact Subgraph:**
- **New Nodes:**
  - `nl0505`: GET /api/v1/rbac/roles
  - `nl0506`: GET /api/v1/rbac/assignments
  - `nl0507`: POST /api/v1/rbac/assignments
  - `nl0508`: PATCH /api/v1/rbac/assignments/{id}
  - `nl0509`: DELETE /api/v1/rbac/assignments/{id}
  - `nl0510`: GET /api/v1/rbac/check-permission

**Files to Create:**
```
src/backend/base/langbuilder/api/v1/
└── rbac.py
```

**Implementation:**
```python
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from typing import Annotated

from langbuilder.api.v1.users import get_current_active_user, CurrentActiveUser
from langbuilder.services.deps import DbSession, RBACServiceDep
from langbuilder.services.database.models.role.schema import RoleRead
from langbuilder.services.database.models.user_role_assignment.schema import (
    UserRoleAssignmentCreate,
    UserRoleAssignmentRead,
    UserRoleAssignmentUpdate
)

router = APIRouter(prefix="/rbac", tags=["rbac"])

# Admin-only dependency
async def require_admin(current_user: CurrentActiveUser) -> CurrentActiveUser:
    """Ensure current user is an Admin (superuser or Global Admin role)"""
    # Note: This will be enhanced to check Global Admin role in addition to is_superuser
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

AdminUser = Annotated[CurrentActiveUser, Depends(require_admin)]

@router.get("/roles", response_model=list[RoleRead])
async def list_roles(
    admin: AdminUser,
    db: DbSession
):
    """List all available roles"""
    from langbuilder.services.database.models.role.crud import get_all_roles
    return await get_all_roles(db)

@router.get("/assignments", response_model=list[UserRoleAssignmentRead])
async def list_assignments(
    admin: AdminUser,
    db: DbSession,
    rbac: RBACServiceDep,
    user_id: UUID | None = None,
    role_name: str | None = None,
    scope_type: str | None = None
):
    """
    List all role assignments with optional filtering.
    Supports filtering by user, role, and scope type.
    """
    assignments = await rbac.list_user_assignments(user_id, db)

    # Apply filters
    if role_name:
        assignments = [a for a in assignments if a.role.name == role_name]
    if scope_type:
        assignments = [a for a in assignments if a.scope_type == scope_type]

    return assignments

@router.post("/assignments", response_model=UserRoleAssignmentRead, status_code=201)
async def create_assignment(
    assignment: UserRoleAssignmentCreate,
    admin: AdminUser,
    db: DbSession,
    rbac: RBACServiceDep
):
    """
    Create a new role assignment.

    Validates:
    - User exists
    - Role exists
    - Scope resource exists (Flow or Project)
    - No duplicate assignment
    """
    return await rbac.assign_role(
        user_id=assignment.user_id,
        role_name=assignment.role_name,
        scope_type=assignment.scope_type,
        scope_id=assignment.scope_id,
        created_by=admin.id,
        db=db
    )

@router.patch("/assignments/{assignment_id}", response_model=UserRoleAssignmentRead)
async def update_assignment(
    assignment_id: UUID,
    assignment_update: UserRoleAssignmentUpdate,
    admin: AdminUser,
    db: DbSession,
    rbac: RBACServiceDep
):
    """
    Update an existing role assignment (change role only).

    Validates:
    - Assignment exists
    - Assignment is not immutable (Starter Project Owner)
    """
    return await rbac.update_role(
        assignment_id=assignment_id,
        new_role_name=assignment_update.role_name,
        db=db
    )

@router.delete("/assignments/{assignment_id}", status_code=204)
async def delete_assignment(
    assignment_id: UUID,
    admin: AdminUser,
    db: DbSession,
    rbac: RBACServiceDep
):
    """
    Delete a role assignment.

    Validates:
    - Assignment exists
    - Assignment is not immutable (Starter Project Owner)
    """
    await rbac.remove_role(assignment_id, db)
    return Response(status_code=204)

@router.get("/check-permission")
async def check_permission(
    current_user: CurrentActiveUser,
    db: DbSession,
    rbac: RBACServiceDep,
    permission: str,
    scope_type: str,
    scope_id: UUID | None = None
):
    """
    Check if current user has a specific permission.
    Used by frontend to show/hide UI elements.
    """
    has_permission = await rbac.can_access(
        current_user.id,
        permission,
        scope_type,
        scope_id,
        db
    )

    return {"has_permission": has_permission}
```

**Register Router:**
```python
# In src/backend/base/langbuilder/api/router.py
from langbuilder.api.v1 import rbac

api_router.include_router(rbac.router, prefix="/v1")
```

**Tech Stack:**
- FastAPI APIRouter
- Pydantic request/response schemas
- Async endpoint handlers

**Success Criteria:**
- [ ] All 6 RBAC endpoints implemented
- [ ] Admin-only access enforced via dependency
- [ ] Request/response schemas defined and validated
- [ ] Immutability checks prevent modification of Starter Project Owner
- [ ] Router registered in main API router

**PRD Alignment:** Epic 3, Stories 3.2, 3.3, 3.4

---

### Task 3.2: Create Pydantic Schemas for RBAC API

**Description:** Define request and response schemas for RBAC API endpoints.

**Files to Create:**
```
src/backend/base/langbuilder/services/database/models/user_role_assignment/
└── schema.py
```

**Implementation:**
```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class UserRoleAssignmentCreate(BaseModel):
    user_id: UUID
    role_name: str  # "Owner", "Admin", "Editor", "Viewer"
    scope_type: str  # "Flow", "Project", "Global"
    scope_id: UUID | None = None  # Required for Flow/Project, null for Global

class UserRoleAssignmentUpdate(BaseModel):
    role_name: str  # Only field that can be updated

class UserRoleAssignmentRead(BaseModel):
    id: UUID
    user_id: UUID
    role_id: UUID
    role_name: str  # Denormalized for convenience
    scope_type: str
    scope_id: UUID | None
    scope_name: str | None  # Flow/Project name, denormalized
    is_immutable: bool
    created_at: datetime
    created_by: UUID | None

    class Config:
        from_attributes = True

class RoleRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_system_role: bool

    class Config:
        from_attributes = True
```

**Success Criteria:**
- [ ] All schemas defined with correct field types
- [ ] Schemas use Pydantic v2 syntax
- [ ] `from_attributes=True` for ORM models
- [ ] Schemas include validation (e.g., scope_id required when scope_type != "Global")

**PRD Alignment:** Epic 3, API contracts

---

### Task 3.3: Implement Batch Permission Check Endpoint

**Description:** Create an optimized endpoint for frontend to check multiple permissions at once.

**Files to Modify:**
```
src/backend/base/langbuilder/api/v1/
└── rbac.py
```

**Implementation:**
```python
from pydantic import BaseModel

class PermissionCheckRequest(BaseModel):
    checks: list[PermissionCheck]

class PermissionCheck(BaseModel):
    permission: str
    scope_type: str
    scope_id: UUID | None

class PermissionCheckResponse(BaseModel):
    results: dict[str, bool]  # Key: "{permission}:{scope_type}:{scope_id}"

@router.post("/check-permissions", response_model=PermissionCheckResponse)
async def check_permissions(
    request: PermissionCheckRequest,
    current_user: CurrentActiveUser,
    db: DbSession,
    rbac: RBACServiceDep
):
    """
    Batch permission check for multiple resources.
    Used to optimize frontend permission checks.
    """
    results = {}

    for check in request.checks:
        key = f"{check.permission}:{check.scope_type}:{check.scope_id}"
        has_permission = await rbac.can_access(
            current_user.id,
            check.permission,
            check.scope_type,
            check.scope_id,
            db
        )
        results[key] = has_permission

    return PermissionCheckResponse(results=results)
```

**Success Criteria:**
- [ ] Batch endpoint processes multiple permission checks in single request
- [ ] Performance: <100ms for 10 permission checks
- [ ] Response format easy to consume in frontend

**PRD Alignment:** Performance optimization for frontend

---

### Task 3.4: Add Validation for Role Assignments

**Description:** Implement validation logic to ensure role assignments reference valid users and resources.

**Files to Modify:**
```
src/backend/base/langbuilder/services/rbac/
└── service.py
```

**Implementation:**
```python
async def assign_role(
    self,
    user_id: UUID,
    role_name: str,
    scope_type: str,
    scope_id: UUID | None,
    created_by: UUID,
    db: AsyncSession,
    is_immutable: bool = False
) -> UserRoleAssignment:
    # 1. Validate user exists
    user = await get_user_by_id(db, user_id)
    if not user:
        raise RBACException(f"User {user_id} not found")

    # 2. Validate role exists
    role = await get_role_by_name(db, role_name)
    if not role:
        raise RBACException(f"Role '{role_name}' not found")

    # 3. Validate scope resource exists
    if scope_type == "Flow" and scope_id:
        flow = await get_flow_by_id(db, scope_id)
        if not flow:
            raise RBACException(f"Flow {scope_id} not found")
    elif scope_type == "Project" and scope_id:
        project = await get_folder_by_id(db, scope_id)
        if not project:
            raise RBACException(f"Project {scope_id} not found")
    elif scope_type == "Global":
        if scope_id is not None:
            raise RBACException("Global scope should not have scope_id")
    else:
        raise RBACException(f"Invalid scope_type: {scope_type}")

    # 4. Check for duplicate
    existing = await self._get_assignment(user_id, role.id, scope_type, scope_id, db)
    if existing:
        raise RBACException("Role assignment already exists for this user and scope")

    # 5. Create assignment
    # ... rest of implementation ...
```

**Success Criteria:**
- [ ] All assignment operations validate user existence
- [ ] All assignment operations validate resource existence
- [ ] Duplicate assignments prevented
- [ ] Clear error messages returned for validation failures

**PRD Alignment:** Data integrity and error handling

---

### Task 3.5: Add Logging and Audit Trail for Role Changes

**Description:** Add structured logging for all role assignment changes for security audit purposes.

**Files to Modify:**
```
src/backend/base/langbuilder/services/rbac/
└── service.py
```

**Implementation:**
```python
from loguru import logger

async def assign_role(self, ...):
    # ... validation logic ...

    assignment = UserRoleAssignment(...)
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    # Audit log
    logger.info(
        f"RBAC: Role assigned",
        extra={
            "action": "assign_role",
            "user_id": str(user_id),
            "role_name": role_name,
            "scope_type": scope_type,
            "scope_id": str(scope_id) if scope_id else None,
            "created_by": str(created_by),
            "assignment_id": str(assignment.id),
            "is_immutable": is_immutable
        }
    )

    return assignment

async def remove_role(self, assignment_id: UUID, db: AsyncSession):
    assignment = await get_assignment_by_id(db, assignment_id)

    # ... validation and deletion ...

    logger.info(
        f"RBAC: Role removed",
        extra={
            "action": "remove_role",
            "assignment_id": str(assignment_id),
            "user_id": str(assignment.user_id),
            "role_id": str(assignment.role_id),
            "scope_type": assignment.scope_type,
            "scope_id": str(assignment.scope_id) if assignment.scope_id else None
        }
    )
```

**Success Criteria:**
- [ ] All role assignment changes logged with structured data
- [ ] Logs include actor (created_by), action, and target details
- [ ] Logs are searchable and can support compliance audits

**PRD Alignment:** Security and compliance (implied in Epic 5)

---

## Phase 4: Admin UI - Frontend

**Goal:** Build the web-based Admin UI for role assignment management.

### Task 4.1: Create RBACManagementPage Component

**Description:** Create the main RBAC Management page as a new tab in the Admin Page.

**Impact Subgraph:**
- **New Nodes:**
  - `ni0083`: RBACManagementPage (`src/frontend/src/pages/AdminPage/RBACManagementPage/index.tsx`)
- **Modified Nodes:**
  - `ni0001`: AdminPage (`src/frontend/src/pages/AdminPage/index.tsx`)

**Files to Create:**
```
src/frontend/src/pages/AdminPage/
├── RBACManagementPage/
│   ├── index.tsx              # Main component
│   ├── AssignmentListView.tsx # Assignment list table
│   ├── CreateAssignmentModal.tsx  # Modal for creating assignments
│   ├── EditAssignmentModal.tsx    # Modal for editing assignments
│   └── styles.module.css      # Component styles (if needed)
```

**Files to Modify:**
```
src/frontend/src/pages/AdminPage/
└── index.tsx
```

**Implementation (AdminPage Integration):**
```typescript
// src/frontend/src/pages/AdminPage/index.tsx
import { useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import UserManagementPage from "./UserManagementPage";
import RBACManagementPage from "./RBACManagementPage";
import { useAuthStore } from "@/stores/authStore";
import { Navigate } from "react-router-dom";

export default function AdminPage() {
  const { isAdmin } = useAuthStore();
  const [activeTab, setActiveTab] = useState("users");

  // Redirect if not admin
  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="admin-page">
      <h1>Admin Dashboard</h1>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="users">User Management</TabsTrigger>
          <TabsTrigger value="rbac">RBAC Management</TabsTrigger>
        </TabsList>

        <TabsContent value="users">
          <UserManagementPage />
        </TabsContent>

        <TabsContent value="rbac">
          <RBACManagementPage />
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

**Implementation (RBACManagementPage):**
```typescript
// src/frontend/src/pages/AdminPage/RBACManagementPage/index.tsx
import { useState } from "react";
import AssignmentListView from "./AssignmentListView";
import CreateAssignmentModal from "./CreateAssignmentModal";
import { Button } from "@/components/ui/button";
import { PlusIcon } from "@radix-ui/react-icons";

export default function RBACManagementPage() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  return (
    <div className="rbac-management-page">
      <div className="header">
        <h2>Role-Based Access Control</h2>
        <p className="text-muted-foreground">
          Manage role assignments for users across projects and flows
        </p>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          <PlusIcon className="mr-2" />
          New Assignment
        </Button>
      </div>

      <div className="info-banner">
        <InfoIcon />
        <span>
          Project-level assignments are inherited by contained Flows and can be
          overridden by explicit Flow-specific roles.
        </span>
      </div>

      <AssignmentListView onEditAssignment={(id) => {/* Open edit modal */}} />

      <CreateAssignmentModal
        open={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => {
          setIsCreateModalOpen(false);
          // Refresh list
        }}
      />
    </div>
  );
}
```

**Tech Stack:**
- React 18.3
- TypeScript 5.4
- Radix UI components (Tabs, Button, etc.)
- Tailwind CSS for styling

**Success Criteria:**
- [ ] RBAC Management tab appears in Admin Page
- [ ] Tab is only accessible to Admin users
- [ ] Deep link `/admin?tab=rbac` opens RBAC tab directly
- [ ] Non-admin users see "Access Denied" message when accessing deep link
- [ ] Info banner explains Flow role inheritance

**PRD Alignment:** Epic 3, Story 3.1, 3.5

---

### Task 4.2: Implement AssignmentListView Component

**Description:** Create a table view to display all role assignments with filtering and delete functionality.

**Impact Subgraph:**
- **New Nodes:**
  - `ni0084`: AssignmentListView (`src/frontend/src/pages/AdminPage/RBACManagementPage/AssignmentListView.tsx`)

**Files to Create:**
```
src/frontend/src/pages/AdminPage/RBACManagementPage/
└── AssignmentListView.tsx
```

**Implementation:**
```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/controllers/API";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { TrashIcon, PencilIcon } from "@radix-ui/react-icons";
import { useState } from "react";

interface Assignment {
  id: string;
  user_id: string;
  role_name: string;
  scope_type: string;
  scope_id: string | null;
  scope_name: string | null;
  is_immutable: boolean;
  created_at: string;
}

export default function AssignmentListView({ onEditAssignment }) {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({
    user_id: "",
    role_name: "",
    scope_type: ""
  });

  // Fetch assignments
  const { data: assignments, isLoading } = useQuery({
    queryKey: ["rbac-assignments", filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.user_id) params.append("user_id", filters.user_id);
      if (filters.role_name) params.append("role_name", filters.role_name);
      if (filters.scope_type) params.append("scope_type", filters.scope_type);

      const response = await api.get(`/rbac/assignments?${params.toString()}`);
      return response.data as Assignment[];
    }
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (assignmentId: string) => {
      await api.delete(`/rbac/assignments/${assignmentId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rbac-assignments"] });
    }
  });

  const handleDelete = async (assignment: Assignment) => {
    if (assignment.is_immutable) {
      alert("Cannot delete immutable assignment (Starter Project Owner)");
      return;
    }

    if (confirm(`Delete role assignment for ${assignment.role_name}?`)) {
      await deleteMutation.mutateAsync(assignment.id);
    }
  };

  return (
    <div className="assignment-list">
      {/* Filters */}
      <div className="filters">
        <Input
          placeholder="Filter by user..."
          value={filters.user_id}
          onChange={(e) => setFilters({ ...filters, user_id: e.target.value })}
        />
        <Select
          value={filters.role_name}
          onValueChange={(value) => setFilters({ ...filters, role_name: value })}
        >
          <option value="">All Roles</option>
          <option value="Owner">Owner</option>
          <option value="Admin">Admin</option>
          <option value="Editor">Editor</option>
          <option value="Viewer">Viewer</option>
        </Select>
        <Select
          value={filters.scope_type}
          onValueChange={(value) => setFilters({ ...filters, scope_type: value })}
        >
          <option value="">All Scopes</option>
          <option value="Flow">Flow</option>
          <option value="Project">Project</option>
          <option value="Global">Global</option>
        </Select>
      </div>

      {/* Table */}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>User</TableHead>
            <TableHead>Role</TableHead>
            <TableHead>Scope</TableHead>
            <TableHead>Resource</TableHead>
            <TableHead>Created</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow>
              <TableCell colSpan={6}>Loading...</TableCell>
            </TableRow>
          )}
          {assignments?.map((assignment) => (
            <TableRow key={assignment.id}>
              <TableCell>{assignment.user_id}</TableCell>
              <TableCell>
                <span className={`role-badge role-${assignment.role_name.toLowerCase()}`}>
                  {assignment.role_name}
                </span>
              </TableCell>
              <TableCell>{assignment.scope_type}</TableCell>
              <TableCell>{assignment.scope_name || "-"}</TableCell>
              <TableCell>{new Date(assignment.created_at).toLocaleDateString()}</TableCell>
              <TableCell>
                <div className="actions">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onEditAssignment(assignment.id)}
                    disabled={assignment.is_immutable}
                  >
                    <PencilIcon />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(assignment)}
                    disabled={assignment.is_immutable}
                  >
                    <TrashIcon />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
```

**Success Criteria:**
- [ ] Table displays all assignments with user, role, scope, and resource
- [ ] Filters work for user, role, and scope type
- [ ] Delete button disabled for immutable assignments
- [ ] Delete confirmation modal appears before deletion
- [ ] List refreshes after deletion

**PRD Alignment:** Epic 3, Story 3.3, 3.4

---

### Task 4.3: Implement CreateAssignmentModal Component

**Description:** Create a multi-step modal for creating new role assignments.

**Impact Subgraph:**
- **New Nodes:**
  - `ni0085`: CreateAssignmentModal (`src/frontend/src/pages/AdminPage/RBACManagementPage/CreateAssignmentModal.tsx`)

**Files to Create:**
```
src/frontend/src/pages/AdminPage/RBACManagementPage/
└── CreateAssignmentModal.tsx
```

**Implementation:**
```typescript
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/controllers/API";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Label } from "@/components/ui/label";

interface CreateAssignmentModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function CreateAssignmentModal({ open, onClose, onSuccess }: CreateAssignmentModalProps) {
  const queryClient = useQueryClient();
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    user_id: "",
    scope_type: "",
    scope_id: "",
    role_name: ""
  });

  // Fetch users
  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: async () => {
      const response = await api.get("/users");
      return response.data;
    }
  });

  // Fetch projects/flows based on scope type
  const { data: scopeResources } = useQuery({
    queryKey: ["scope-resources", formData.scope_type],
    queryFn: async () => {
      if (!formData.scope_type || formData.scope_type === "Global") return [];

      const endpoint = formData.scope_type === "Project" ? "/folders" : "/flows";
      const response = await api.get(endpoint);
      return response.data;
    },
    enabled: !!formData.scope_type && formData.scope_type !== "Global"
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      await api.post("/rbac/assignments", {
        user_id: data.user_id,
        role_name: data.role_name,
        scope_type: data.scope_type,
        scope_id: data.scope_type === "Global" ? null : data.scope_id
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rbac-assignments"] });
      onSuccess();
      resetForm();
    }
  });

  const resetForm = () => {
    setStep(1);
    setFormData({ user_id: "", scope_type: "", scope_id: "", role_name: "" });
  };

  const handleNext = () => {
    if (step < 4) setStep(step + 1);
  };

  const handleBack = () => {
    if (step > 1) setStep(step - 1);
  };

  const handleSubmit = async () => {
    await createMutation.mutateAsync(formData);
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Role Assignment</DialogTitle>
          <p className="text-sm text-muted-foreground">Step {step} of 4</p>
        </DialogHeader>

        <div className="form-content">
          {step === 1 && (
            <div className="form-step">
              <Label>Select User</Label>
              <Select
                value={formData.user_id}
                onValueChange={(value) => setFormData({ ...formData, user_id: value })}
              >
                <option value="">Choose a user...</option>
                {users?.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.username}
                  </option>
                ))}
              </Select>
            </div>
          )}

          {step === 2 && (
            <div className="form-step">
              <Label>Select Scope Type</Label>
              <Select
                value={formData.scope_type}
                onValueChange={(value) => setFormData({ ...formData, scope_type: value, scope_id: "" })}
              >
                <option value="">Choose a scope...</option>
                <option value="Global">Global (Admin only)</option>
                <option value="Project">Project</option>
                <option value="Flow">Flow</option>
              </Select>
            </div>
          )}

          {step === 3 && formData.scope_type !== "Global" && (
            <div className="form-step">
              <Label>Select {formData.scope_type}</Label>
              <Select
                value={formData.scope_id}
                onValueChange={(value) => setFormData({ ...formData, scope_id: value })}
              >
                <option value="">Choose a {formData.scope_type.toLowerCase()}...</option>
                {scopeResources?.map((resource) => (
                  <option key={resource.id} value={resource.id}>
                    {resource.name}
                  </option>
                ))}
              </Select>
            </div>
          )}

          {(step === 3 && formData.scope_type === "Global") || step === 4 && (
            <div className="form-step">
              <Label>Select Role</Label>
              <Select
                value={formData.role_name}
                onValueChange={(value) => setFormData({ ...formData, role_name: value })}
              >
                <option value="">Choose a role...</option>
                {formData.scope_type === "Global" ? (
                  <option value="Admin">Admin</option>
                ) : (
                  <>
                    <option value="Owner">Owner</option>
                    <option value="Editor">Editor</option>
                    <option value="Viewer">Viewer</option>
                  </>
                )}
              </Select>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={handleBack} disabled={step === 1}>
            Back
          </Button>
          {step < 4 ? (
            <Button onClick={handleNext} disabled={!canProceed()}>
              Next
            </Button>
          ) : (
            <Button onClick={handleSubmit} disabled={!formData.role_name}>
              Create Assignment
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

**Success Criteria:**
- [ ] Modal guides user through 4-step workflow: User → Scope → Resource → Role
- [ ] Global scope skips resource selection step
- [ ] Only Admin role available for Global scope
- [ ] Form validation prevents proceeding without selections
- [ ] Assignment created successfully on submit

**PRD Alignment:** Epic 3, Story 3.2

---

### Task 4.4: Create RBACGuard Component and usePermission Hook

**Description:** Create reusable components and hooks for permission-based UI rendering.

**Impact Subgraph:**
- **New Nodes:**
  - `ni0086`: RBACGuard (`src/frontend/src/components/authorization/RBACGuard.tsx`)
  - `ni0087`: usePermission (`src/frontend/src/hooks/usePermission.ts`)

**Files to Create:**
```
src/frontend/src/components/authorization/
└── RBACGuard.tsx

src/frontend/src/hooks/
└── usePermission.ts
```

**Implementation (usePermission Hook):**
```typescript
// src/frontend/src/hooks/usePermission.ts
import { useQuery } from "@tanstack/react-query";
import { api } from "@/controllers/API";

export interface PermissionCheck {
  permission: string;  // "Create", "Read", "Update", "Delete"
  scope_type: string;  // "Flow", "Project"
  scope_id: string | null;
}

export function usePermission(check: PermissionCheck) {
  return useQuery({
    queryKey: ["permission", check.permission, check.scope_type, check.scope_id],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append("permission", check.permission);
      params.append("scope_type", check.scope_type);
      if (check.scope_id) params.append("scope_id", check.scope_id);

      const response = await api.get(`/rbac/check-permission?${params.toString()}`);
      return response.data.has_permission as boolean;
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
}

export function useBatchPermissions(checks: PermissionCheck[]) {
  return useQuery({
    queryKey: ["permissions-batch", checks],
    queryFn: async () => {
      const response = await api.post("/rbac/check-permissions", { checks });
      return response.data.results as Record<string, boolean>;
    },
    staleTime: 5 * 60 * 1000,
  });
}
```

**Implementation (RBACGuard Component):**
```typescript
// src/frontend/src/components/authorization/RBACGuard.tsx
import { usePermission, PermissionCheck } from "@/hooks/usePermission";
import { ReactNode } from "react";

interface RBACGuardProps {
  check: PermissionCheck;
  children: ReactNode;
  fallback?: ReactNode;
  hideWhenDenied?: boolean;
}

export default function RBACGuard({
  check,
  children,
  fallback = null,
  hideWhenDenied = true
}: RBACGuardProps) {
  const { data: hasPermission, isLoading } = usePermission(check);

  if (isLoading) {
    return <div className="loading-spinner" />;
  }

  if (!hasPermission) {
    return hideWhenDenied ? null : fallback;
  }

  return <>{children}</>;
}
```

**Usage Example:**
```typescript
// In FlowPage component
import RBACGuard from "@/components/authorization/RBACGuard";

function FlowPage({ flowId }) {
  return (
    <div>
      <h1>Flow Editor</h1>

      {/* Show delete button only if user has Delete permission */}
      <RBACGuard check={{ permission: "Delete", scope_type: "Flow", scope_id: flowId }}>
        <Button onClick={handleDelete}>Delete Flow</Button>
      </RBACGuard>

      {/* Disable save button if user lacks Update permission */}
      <RBACGuard
        check={{ permission: "Update", scope_type: "Flow", scope_id: flowId }}
        fallback={<Button disabled>Save (Read-only)</Button>}
        hideWhenDenied={false}
      >
        <Button onClick={handleSave}>Save</Button>
      </RBACGuard>
    </div>
  );
}
```

**Tech Stack:**
- React hooks (custom hooks)
- TanStack Query for caching
- TypeScript

**Success Criteria:**
- [ ] `usePermission` hook fetches and caches permission checks
- [ ] `RBACGuard` component hides/shows UI elements based on permissions
- [ ] Permission checks cached for 5 minutes to reduce API calls
- [ ] Components are reusable across the application

**PRD Alignment:** Epic 2, Stories 2.2-2.5 (UI enforcement)

---

### Task 4.5: Integrate RBAC Guards into Existing UI Components

**Description:** Update existing UI components to use RBAC guards for permission-based rendering.

**Impact Subgraph:**
- **Modified Nodes:**
  - `ni0006`: CollectionPage (Main Page) - Hide/disable create buttons
  - `ni0009`: FlowPage - Read-only mode, hide delete button

**Files to Modify:**
```
src/frontend/src/pages/MainPage/
└── pages/main-page.tsx

src/frontend/src/pages/FlowPage/
└── index.tsx
```

**Implementation (Main Page - Flow List):**
```typescript
// src/frontend/src/pages/MainPage/pages/main-page.tsx
import RBACGuard from "@/components/authorization/RBACGuard";

function FlowListItem({ flow, project }) {
  return (
    <div className="flow-item">
      <h3>{flow.name}</h3>

      <div className="actions">
        {/* Delete button - only show if user has Delete permission */}
        <RBACGuard check={{ permission: "Delete", scope_type: "Flow", scope_id: flow.id }}>
          <Button onClick={() => handleDelete(flow.id)}>
            <TrashIcon />
          </Button>
        </RBACGuard>

        {/* Edit button - only show if user has Update permission */}
        <RBACGuard check={{ permission: "Update", scope_type: "Flow", scope_id: flow.id }}>
          <Button onClick={() => navigate(`/flow/${flow.id}`)}>
            <PencilIcon />
          </Button>
        </RBACGuard>
      </div>
    </div>
  );
}

function ProjectHeader({ project }) {
  return (
    <div className="project-header">
      <h2>{project.name}</h2>

      {/* Create Flow button - only show if user has Create permission on Project */}
      <RBACGuard check={{ permission: "Create", scope_type: "Project", scope_id: project.id }}>
        <Button onClick={() => handleCreateFlow(project.id)}>
          <PlusIcon /> New Flow
        </Button>
      </RBACGuard>
    </div>
  );
}
```

**Implementation (Flow Editor - Read-only Mode):**
```typescript
// src/frontend/src/pages/FlowPage/index.tsx
import { usePermission } from "@/hooks/usePermission";
import RBACGuard from "@/components/authorization/RBACGuard";

function FlowPage({ flowId }) {
  const { data: canUpdate } = usePermission({
    permission: "Update",
    scope_type: "Flow",
    scope_id: flowId
  });

  // Set editor to read-only mode if user lacks Update permission
  const isReadOnly = !canUpdate;

  return (
    <div className="flow-page">
      <FlowEditor flowId={flowId} readOnly={isReadOnly} />

      <div className="toolbar">
        {/* Save button */}
        <RBACGuard
          check={{ permission: "Update", scope_type: "Flow", scope_id: flowId }}
          fallback={<Button disabled>Read-only</Button>}
          hideWhenDenied={false}
        >
          <Button onClick={handleSave}>Save</Button>
        </RBACGuard>

        {/* Delete button */}
        <RBACGuard check={{ permission: "Delete", scope_type: "Flow", scope_id: flowId }}>
          <Button variant="destructive" onClick={handleDelete}>Delete Flow</Button>
        </RBACGuard>
      </div>
    </div>
  );
}
```

**Success Criteria:**
- [ ] Create Flow button hidden when user lacks Create permission on Project
- [ ] Delete Flow button hidden when user lacks Delete permission
- [ ] Flow editor loads in read-only mode when user lacks Update permission
- [ ] Edit/Save buttons disabled in read-only mode
- [ ] All permission checks use cached results (no excessive API calls)

**PRD Alignment:** Epic 2, Stories 2.2-2.5 (UI enforcement)

---

## Phase 5: Testing, Performance & Documentation

**Goal:** Comprehensive testing, performance optimization, and documentation.

### Task 5.1: Write Unit Tests for RBACService

**Description:** Create comprehensive unit tests for all RBACService methods.

**Files to Create:**
```
src/backend/tests/unit/services/rbac/
├── __init__.py
├── test_rbac_service.py
└── test_can_access.py
```

**Implementation:**
```python
import pytest
from uuid import uuid4
from langbuilder.services.rbac.service import RBACService
from langbuilder.services.database.models.user.model import User
from langbuilder.services.database.models.role.model import Role
from langbuilder.services.database.models.permission.model import Permission
from langbuilder.services.database.models.user_role_assignment.model import UserRoleAssignment

@pytest.mark.asyncio
class TestRBACService:
    @pytest.fixture
    async def rbac_service(self):
        return RBACService()

    @pytest.fixture
    async def setup_data(self, db_session):
        """Create test users, roles, and permissions"""
        # Create test user
        user = User(username="testuser", password="hashed")
        db_session.add(user)

        # Create roles and permissions
        viewer_role = Role(name="Viewer", is_system_role=True)
        editor_role = Role(name="Editor", is_system_role=True)
        owner_role = Role(name="Owner", is_system_role=True)
        db_session.add_all([viewer_role, editor_role, owner_role])

        read_perm = Permission(name="Read", scope="Flow")
        update_perm = Permission(name="Update", scope="Flow")
        db_session.add_all([read_perm, update_perm])

        await db_session.commit()

        return {
            "user": user,
            "viewer_role": viewer_role,
            "editor_role": editor_role,
            "owner_role": owner_role,
            "read_perm": read_perm,
            "update_perm": update_perm
        }

    async def test_superuser_bypass(self, rbac_service, db_session, setup_data):
        """Test that superuser bypasses all permission checks"""
        user = setup_data["user"]
        user.is_superuser = True
        await db_session.commit()

        flow_id = uuid4()

        # Superuser should have all permissions
        assert await rbac_service.can_access(user.id, "Delete", "Flow", flow_id, db_session) is True
        assert await rbac_service.can_access(user.id, "Update", "Flow", flow_id, db_session) is True
        assert await rbac_service.can_access(user.id, "Read", "Flow", flow_id, db_session) is True

    async def test_viewer_role_permissions(self, rbac_service, db_session, setup_data):
        """Test that Viewer role only has Read permission"""
        user = setup_data["user"]
        viewer_role = setup_data["viewer_role"]
        flow_id = uuid4()

        # Assign Viewer role
        assignment = UserRoleAssignment(
            user_id=user.id,
            role_id=viewer_role.id,
            scope_type="Flow",
            scope_id=flow_id
        )
        db_session.add(assignment)
        await db_session.commit()

        # Viewer should have Read permission
        assert await rbac_service.can_access(user.id, "Read", "Flow", flow_id, db_session) is True

        # Viewer should NOT have Update or Delete
        assert await rbac_service.can_access(user.id, "Update", "Flow", flow_id, db_session) is False
        assert await rbac_service.can_access(user.id, "Delete", "Flow", flow_id, db_session) is False

    async def test_flow_inherits_project_role(self, rbac_service, db_session, setup_data):
        """Test that Flow inherits role from containing Project"""
        user = setup_data["user"]
        editor_role = setup_data["editor_role"]

        # Create project and flow
        project = Folder(name="Test Project", user_id=user.id)
        db_session.add(project)
        await db_session.commit()

        flow = Flow(name="Test Flow", user_id=user.id, folder_id=project.id)
        db_session.add(flow)
        await db_session.commit()

        # Assign Editor role at Project level
        assignment = UserRoleAssignment(
            user_id=user.id,
            role_id=editor_role.id,
            scope_type="Project",
            scope_id=project.id
        )
        db_session.add(assignment)
        await db_session.commit()

        # User should inherit Editor permissions on Flow
        assert await rbac_service.can_access(user.id, "Read", "Flow", flow.id, db_session) is True
        assert await rbac_service.can_access(user.id, "Update", "Flow", flow.id, db_session) is True
        assert await rbac_service.can_access(user.id, "Delete", "Flow", flow.id, db_session) is False

    async def test_flow_specific_role_overrides_project_role(self, rbac_service, db_session, setup_data):
        """Test that explicit Flow role overrides inherited Project role"""
        user = setup_data["user"]
        editor_role = setup_data["editor_role"]
        viewer_role = setup_data["viewer_role"]

        # Create project and flow
        project = Folder(name="Test Project", user_id=user.id)
        flow = Flow(name="Test Flow", user_id=user.id, folder_id=project.id)
        db_session.add_all([project, flow])
        await db_session.commit()

        # Assign Editor role at Project level
        project_assignment = UserRoleAssignment(
            user_id=user.id,
            role_id=editor_role.id,
            scope_type="Project",
            scope_id=project.id
        )

        # Assign Viewer role at Flow level (override)
        flow_assignment = UserRoleAssignment(
            user_id=user.id,
            role_id=viewer_role.id,
            scope_type="Flow",
            scope_id=flow.id
        )

        db_session.add_all([project_assignment, flow_assignment])
        await db_session.commit()

        # Flow-specific Viewer role should override Project Editor role
        assert await rbac_service.can_access(user.id, "Read", "Flow", flow.id, db_session) is True
        assert await rbac_service.can_access(user.id, "Update", "Flow", flow.id, db_session) is False

    async def test_cannot_modify_immutable_assignment(self, rbac_service, db_session, setup_data):
        """Test that immutable assignments cannot be modified or deleted"""
        user = setup_data["user"]
        owner_role = setup_data["owner_role"]

        # Create Starter Project with immutable Owner assignment
        project = Folder(name="Starter Project", user_id=user.id, is_starter_project=True)
        db_session.add(project)
        await db_session.commit()

        assignment = UserRoleAssignment(
            user_id=user.id,
            role_id=owner_role.id,
            scope_type="Project",
            scope_id=project.id,
            is_immutable=True
        )
        db_session.add(assignment)
        await db_session.commit()

        # Attempt to remove immutable assignment
        with pytest.raises(RBACException, match="Cannot remove immutable assignment"):
            await rbac_service.remove_role(assignment.id, db_session)

        # Attempt to update immutable assignment
        with pytest.raises(RBACException, match="Cannot modify immutable assignment"):
            await rbac_service.update_role(assignment.id, "Editor", db_session)
```

**Test Coverage Goals:**
- [ ] All RBACService methods covered
- [ ] Superuser bypass logic
- [ ] Global Admin bypass logic
- [ ] Role inheritance (Project → Flow)
- [ ] Role override (explicit Flow role overrides Project role)
- [ ] Immutability checks
- [ ] Permission mapping correctness
- [ ] Edge cases (no role, missing resource, etc.)

**Success Criteria:**
- [ ] All unit tests pass
- [ ] Code coverage >90% for RBACService
- [ ] Tests run in <5 seconds

**PRD Alignment:** Quality assurance

---

### Task 5.2: Write Integration Tests for RBAC API Endpoints

**Description:** Create integration tests for all RBAC API endpoints, covering Gherkin scenarios from PRD.

**Impact Subgraph:**
- **New Nodes:**
  - Tests for Epic 1, 2, 3 acceptance criteria

**Files to Create:**
```
src/backend/tests/integration/rbac/
├── __init__.py
├── test_core_entities.py           # Epic 1, Story 1.1
├── test_default_roles.py            # Epic 1, Story 1.2
├── test_role_assignment.py          # Epic 1, Story 1.3
├── test_immutable_assignment.py     # Epic 1, Story 1.4
├── test_project_creation.py         # Epic 1, Story 1.5
├── test_role_inheritance.py         # Epic 1, Story 1.6
├── test_can_access.py               # Epic 2, Story 2.1
├── test_read_permission.py          # Epic 2, Story 2.2
├── test_create_permission.py        # Epic 2, Story 2.3
├── test_update_permission.py        # Epic 2, Story 2.4
├── test_delete_permission.py        # Epic 2, Story 2.5
└── test_rbac_api.py                 # Epic 3, Stories 3.1-3.4
```

**Implementation Example (Epic 1, Story 1.1 - Core Entities):**
```python
# tests/integration/rbac/test_core_entities.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
class TestCoreRBACEntities:
    """
    Gherkin Scenario: Defining the Core RBAC Entities
    Given the persistence layer is available
    When the system is initialized
    Then the four base permissions (Create, Read, Update, Delete) should be defined
    And the two entity scopes (Flow, Project) should be defined
    And the data model should establish the relationship between permissions and scopes
    """

    async def test_core_permissions_exist(self, client: AsyncClient, admin_headers):
        """Verify that all 8 permissions (4 actions x 2 scopes) exist"""
        response = await client.get("/api/v1/rbac/permissions", headers=admin_headers)
        assert response.status_code == 200

        permissions = response.json()
        assert len(permissions) == 8

        # Verify all combinations exist
        expected = [
            ("Create", "Flow"),
            ("Read", "Flow"),
            ("Update", "Flow"),
            ("Delete", "Flow"),
            ("Create", "Project"),
            ("Read", "Project"),
            ("Update", "Project"),
            ("Delete", "Project"),
        ]

        actual = [(p["name"], p["scope"]) for p in permissions]
        assert set(expected) == set(actual)

    async def test_core_roles_exist(self, client: AsyncClient, admin_headers):
        """Verify that all 4 default roles exist"""
        response = await client.get("/api/v1/rbac/roles", headers=admin_headers)
        assert response.status_code == 200

        roles = response.json()
        role_names = [r["name"] for r in roles]

        assert "Viewer" in role_names
        assert "Editor" in role_names
        assert "Owner" in role_names
        assert "Admin" in role_names
```

**Implementation Example (Epic 2, Story 2.2 - Read Permission):**
```python
# tests/integration/rbac/test_read_permission.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
class TestReadPermission:
    """
    Gherkin Scenario: UI Filtering and Read Access Enforcement
    Given a user loads the Project or Flow list view
    When the user lacks the Read/View permission for an entity
    Then that entity should not be displayed in the list view
    """

    async def test_list_flows_filtered_by_read_permission(self, client: AsyncClient, db_session):
        """Users should only see flows they have Read permission for"""
        # Setup: Create 3 flows
        # - Flow A: User has Owner role (should see)
        # - Flow B: User has Viewer role (should see)
        # - Flow C: User has no role (should NOT see)

        user = await create_test_user(db_session, "testuser")
        user_headers = await get_user_headers(client, "testuser")

        flow_a = await create_test_flow(db_session, "Flow A", user.id)
        flow_b = await create_test_flow(db_session, "Flow B", user.id)
        flow_c = await create_test_flow(db_session, "Flow C", user.id)

        # Assign Owner role to Flow A
        await assign_role(db_session, user.id, "Owner", "Flow", flow_a.id)

        # Assign Viewer role to Flow B
        await assign_role(db_session, user.id, "Viewer", "Flow", flow_b.id)

        # No role for Flow C

        # Test: List flows
        response = await client.get("/api/v1/flows", headers=user_headers)
        assert response.status_code == 200

        flows = response.json()
        flow_ids = [f["id"] for f in flows]

        # Should see Flow A and B (has Read permission)
        assert str(flow_a.id) in flow_ids
        assert str(flow_b.id) in flow_ids

        # Should NOT see Flow C (no permission)
        assert str(flow_c.id) not in flow_ids
```

**Success Criteria:**
- [ ] All Gherkin scenarios from PRD Epics 1-3 covered
- [ ] Tests cover positive and negative cases
- [ ] Tests verify immutability constraints
- [ ] Tests verify role inheritance logic
- [ ] All tests pass consistently

**PRD Alignment:** All epics (comprehensive validation)

---

### Task 5.3: Performance Testing and Optimization

**Description:** Verify RBAC system meets performance requirements from Epic 5.

**PRD Performance Requirements:**
- `can_access()` latency: <50ms p95
- Assignment creation latency: <200ms p95
- Editor load time (with RBAC checks): <2.5s p95

**Files to Create:**
```
src/backend/tests/performance/
├── __init__.py
├── test_can_access_latency.py
├── test_assignment_latency.py
└── test_batch_permission_check.py
```

**Implementation:**
```python
import pytest
import time
from statistics import quantiles

@pytest.mark.performance
@pytest.mark.asyncio
class TestRBACPerformance:
    async def test_can_access_latency(self, rbac_service, db_session, setup_data):
        """
        Gherkin Scenario: Latency for CanAccess Check
        Given the authorization service (AuthService) is running at 50% average load
        When the AuthService.CanAccess method is called
        Then the check must return a response in less than 50 milliseconds (p95)
        """
        user = setup_data["user"]
        flow_id = uuid4()

        # Warm up
        for _ in range(10):
            await rbac_service.can_access(user.id, "Read", "Flow", flow_id, db_session)

        # Measure 1000 calls
        latencies = []
        for _ in range(1000):
            start = time.perf_counter()
            await rbac_service.can_access(user.id, "Read", "Flow", flow_id, db_session)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms

        # Calculate p95
        p95 = quantiles(latencies, n=20)[18]  # 95th percentile

        print(f"can_access p95 latency: {p95:.2f}ms")
        assert p95 < 50, f"p95 latency {p95:.2f}ms exceeds 50ms requirement"

    async def test_assignment_creation_latency(self, rbac_service, db_session, setup_data):
        """
        Gherkin Scenario: Latency for Assignment Creation
        Given an Admin executes an assignment update/create via the API
        When the Core Role Assignment Logic is executed
        Then the API response time should be less than 200 milliseconds (p95)
        """
        admin = setup_data["user"]

        # Measure 100 assignment creations
        latencies = []
        for i in range(100):
            user = User(username=f"testuser{i}", password="hashed")
            db_session.add(user)
            await db_session.commit()

            flow_id = uuid4()

            start = time.perf_counter()
            await rbac_service.assign_role(
                user_id=user.id,
                role_name="Viewer",
                scope_type="Flow",
                scope_id=flow_id,
                created_by=admin.id,
                db=db_session
            )
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        p95 = quantiles(latencies, n=20)[18]

        print(f"assign_role p95 latency: {p95:.2f}ms")
        assert p95 < 200, f"p95 latency {p95:.2f}ms exceeds 200ms requirement"
```

**Optimization Strategies:**
1. **Database Indexing:**
   - Composite index on `(user_id, scope_type, scope_id)` in UserRoleAssignment
   - Index on `(role_id, permission_id)` in RolePermission

2. **Query Optimization:**
   - Use JOINs instead of N+1 queries
   - Batch permission checks in single query

3. **Caching:**
   - Cache role-permission mappings (rarely change)
   - Cache user role assignments (invalidate on change)

**Success Criteria:**
- [ ] `can_access()` p95 latency <50ms
- [ ] Assignment creation p95 latency <200ms
- [ ] Batch permission check processes 10 checks in <100ms
- [ ] Database queries optimized (no N+1 issues)

**PRD Alignment:** Epic 5, Stories 5.1, 5.3

---

### Task 5.4: Update Documentation and Migration Guide

**Description:** Create comprehensive documentation for RBAC system and migration guide for existing deployments.

**Files to Create:**
```
docs/
├── rbac/
│   ├── README.md              # RBAC overview
│   ├── getting-started.md     # Quick start guide
│   ├── admin-guide.md         # Admin UI user guide
│   ├── api-reference.md       # RBAC API documentation
│   ├── migration-guide.md     # Upgrading existing deployments
│   └── architecture.md        # Technical deep-dive
```

**Content Outline:**

**README.md:**
- What is RBAC in LangBuilder?
- Key concepts: Roles, Permissions, Scopes
- Default roles and their capabilities
- Quick examples

**getting-started.md:**
- Enabling RBAC in a new installation
- Creating your first role assignment
- Understanding role inheritance
- Common use cases

**admin-guide.md:**
- Accessing the RBAC Management UI
- Creating role assignments
- Filtering and searching assignments
- Understanding immutable assignments
- Best practices

**api-reference.md:**
- All RBAC API endpoints with request/response examples
- Authentication requirements
- Error codes and troubleshooting

**migration-guide.md:**
```markdown
# RBAC Migration Guide

## Overview

This guide helps you upgrade an existing LangBuilder deployment to include RBAC.

## Prerequisites

- LangBuilder v1.4.x or earlier
- Database backup completed
- Scheduled maintenance window (estimated 15 minutes for 1000 flows)

## Migration Steps

### Step 1: Backup Database

```bash
# SQLite
cp langbuilder.db langbuilder.db.backup

# PostgreSQL
pg_dump langbuilder > langbuilder_backup.sql
```

### Step 2: Update LangBuilder

```bash
# Pull latest version
git pull origin main

# Install dependencies
make install_backend
make install_frontend
```

### Step 3: Run Database Migrations

```bash
# Apply RBAC migrations
make alembic-upgrade

# Verify migrations
make alembic-current
```

This will:
- Create 4 new tables: Role, Permission, RolePermission, UserRoleAssignment
- Add `is_starter_project` column to Folder table
- Seed default roles and permissions
- Backfill Owner role assignments for existing users

### Step 4: Verify Data Migration

```bash
# Check that all existing users have Owner roles
uv run python scripts/verify_rbac_migration.py
```

Expected output:
```
✓ 4 default roles created
✓ 8 permissions created
✓ 150 users migrated
✓ 300 Projects have Owner assignments
✓ 1200 Flows have Owner assignments
```

### Step 5: Test RBAC Functionality

1. Log in as a regular user (non-superuser)
2. Verify you can see your own Projects and Flows
3. Verify you cannot see other users' Projects/Flows (unless explicitly granted access)
4. Log in as admin (superuser)
5. Navigate to Admin Page → RBAC Management tab
6. Create a test role assignment
7. Verify the assignment works correctly

### Step 6: (Optional) Assign Roles for Shared Resources

If you have shared Projects or Flows that should be accessible to multiple users:

1. Navigate to RBAC Management
2. For each shared resource, create role assignments:
   - Assign "Viewer" role for read-only access
   - Assign "Editor" role for read-write access
   - Assign "Owner" role for full control

## Rollback Procedure

If you encounter issues:

```bash
# Rollback migrations
make alembic-downgrade

# Restore database backup
# SQLite
cp langbuilder.db.backup langbuilder.db

# PostgreSQL
psql langbuilder < langbuilder_backup.sql
```

## Backward Compatibility

The RBAC system is designed to be backward compatible:
- Existing `is_superuser` users remain admins
- All existing users receive Owner roles on their existing Projects/Flows
- No functionality is removed

## Troubleshooting

### Issue: Users cannot access their existing flows

**Solution:** Run the backfill script manually:
```bash
uv run python scripts/backfill_owner_assignments.py
```

### Issue: Admin UI shows "Access Denied"

**Solution:** Verify user has `is_superuser=True`:
```sql
SELECT id, username, is_superuser FROM user WHERE username = 'your_username';
```

## Support

For issues or questions, please:
- Check the [RBAC FAQ](./faq.md)
- Open an issue on GitHub
- Contact support@langbuilder.io
```

**architecture.md:**
- Data model diagrams
- Permission check flow diagrams
- Role inheritance algorithm
- Performance considerations

**Success Criteria:**
- [ ] All documentation files created
- [ ] Migration guide tested with existing deployment
- [ ] API reference complete with examples
- [ ] Architecture diagrams included
- [ ] Documentation reviewed and approved

**PRD Alignment:** User enablement and adoption

---

## Success Metrics

### Functional Completeness

- [ ] All 27 tasks completed
- [ ] All PRD stories (Epic 1-3, 5) implemented
- [ ] All Gherkin acceptance criteria passing

### Code Quality

- [ ] All code passes `make format_backend`
- [ ] All code passes `make lint` (mypy type checking)
- [ ] Unit test coverage >90%
- [ ] Integration test coverage >80%

### Performance

- [ ] `can_access()` p95 latency <50ms
- [ ] Assignment creation p95 latency <200ms
- [ ] Editor load time <2.5s p95

### User Experience

- [ ] Admin UI is intuitive and discoverable
- [ ] Permission-based UI elements hide/show correctly
- [ ] Error messages are clear and actionable
- [ ] Documentation is comprehensive

### Security

- [ ] All endpoints secured with RBAC checks
- [ ] Immutability constraints enforced
- [ ] Audit logging in place
- [ ] No permission bypass vulnerabilities

---

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing (unit, integration, E2E)
- [ ] Performance benchmarks met
- [ ] Database migrations tested (upgrade and rollback)
- [ ] Documentation complete
- [ ] Code review completed
- [ ] Security review completed

### Deployment

- [ ] Database backup created
- [ ] Maintenance window scheduled
- [ ] Migrations applied
- [ ] Data backfill completed
- [ ] Smoke tests passed
- [ ] Rollback plan ready

### Post-Deployment

- [ ] Monitor error rates
- [ ] Monitor API latency (especially `can_access()`)
- [ ] Verify user access patterns
- [ ] Collect user feedback
- [ ] Address any issues

---

## Appendix A: Database Schema Diagram

```
┌──────────────────┐
│      User        │
│                  │
│ - id (PK)        │◄──────┐
│ - username       │       │
│ - is_superuser   │       │
└──────────────────┘       │
                           │
┌──────────────────┐       │
│      Role        │       │
│                  │       │
│ - id (PK)        │       │
│ - name           │       │
│ - is_system_role │       │
└──────────────────┘       │
         ▲                 │
         │                 │
         │                 │
┌────────┴─────────┐       │
│ RolePermission   │       │
│                  │       │
│ - role_id (FK)   │       │
│ - permission_id  │       │
└──────────────────┘       │
         │                 │
         ▼                 │
┌──────────────────┐       │
│   Permission     │       │
│                  │       │
│ - id (PK)        │       │
│ - name           │       │
│ - scope          │       │
└──────────────────┘       │
                           │
┌──────────────────────────┴──┐
│  UserRoleAssignment         │
│                             │
│ - id (PK)                   │
│ - user_id (FK)              │
│ - role_id (FK)              │
│ - scope_type                │
│ - scope_id (FK)             │
│ - is_immutable              │
│ - created_by (FK)           │
└─────────────────────────────┘
         │
         │ (scope_id references)
         ▼
┌──────────────────┐      ┌──────────────────┐
│      Flow        │      │     Folder       │
│                  │      │    (Project)     │
│ - id (PK)        │      │                  │
│ - name           │      │ - id (PK)        │
│ - user_id (FK)   │      │ - name           │
│ - folder_id (FK) │──────│ - user_id (FK)   │
│                  │      │ - is_starter_proj│
└──────────────────┘      └──────────────────┘
```

---

## Appendix B: Permission Matrix

| Role | Flow Permissions | Project Permissions | Notes |
|------|-----------------|---------------------|-------|
| **Viewer** | Read | Read | Can view, execute, export, download flows |
| **Editor** | Create, Read, Update | Create, Read, Update | Can create/edit but not delete |
| **Owner** | Create, Read, Update, Delete | Create, Read, Update, Delete | Full control over owned resources |
| **Admin** | Create, Read, Update, Delete (Global) | Create, Read, Update, Delete (Global) | Full control over all resources |

**Permission Definitions:**
- **Create**: Create new flows in a project
- **Read**: View, execute, save, export, download flows/projects
- **Update**: Edit, import flows/projects
- **Delete**: Delete flows/projects

---

## Appendix C: Tech Stack Summary

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Backend** |
| Runtime | Python | 3.10-3.13 | Core runtime |
| Web Framework | FastAPI | Latest | Async HTTP server |
| ORM | SQLModel | Latest | Database ORM |
| Migrations | Alembic | Latest | Schema versioning |
| Validation | Pydantic | 2.x | Data validation |
| **Frontend** |
| UI Framework | React | 18.3.1 | Component library |
| Language | TypeScript | 5.4.5 | Type safety |
| State Management | Zustand | 4.5.2 | Client state |
| Server State | TanStack Query | 5.49.2 | API caching |
| UI Components | Radix UI | Latest | Accessible primitives |
| Styling | Tailwind CSS | 3.4.4 | Utility CSS |
| **Database** |
| Development | SQLite | - | Local database |
| Production | PostgreSQL | Latest | Production database |
| **Testing** |
| Unit Tests | pytest | Latest | Python testing |
| Async Tests | pytest-asyncio | Latest | Async test support |
| Frontend Tests | Jest/Vitest | Latest | JS/TS testing |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-07 | Implementation Planner | Initial plan created |

---

**End of Implementation Plan**
