"""Comprehensive unit tests for RBAC data migration script.

This test suite validates the migrate_existing_users_to_rbac function which
migrates existing users, flows, and projects to RBAC role assignments.

Tests cover:
- Superuser global Admin assignment creation
- Regular user Owner assignments for flows
- Regular user Owner assignments for projects
- Starter Project immutability marking
- Idempotency (safe to run multiple times)
- Dry-run mode
- Error handling and rollback
- Edge cases (users without resources, missing roles)

Tests follow the pattern: `async with session_getter(get_db_service()) as session:`
and leverage the conftest.py automatic test database isolation.
"""

from langbuilder.scripts.migrate_rbac_data import migrate_existing_users_to_rbac
from langbuilder.services.database.models.flow.model import Flow
from langbuilder.services.database.models.folder.model import Folder
from langbuilder.services.database.models.rbac.permission import Permission, PermissionAction, PermissionScope
from langbuilder.services.database.models.rbac.role import Role
from langbuilder.services.database.models.rbac.role_permission import RolePermission
from langbuilder.services.database.models.rbac.user_role_assignment import UserRoleAssignment
from langbuilder.services.database.models.user.model import User
from langbuilder.services.database.utils import session_getter
from langbuilder.services.deps import get_db_service
from sqlmodel import select

# ==============================================================================
# Test Fixtures and Helpers
# ==============================================================================


async def create_test_roles_and_permissions(session):
    """Create test roles and permissions for migration tests.

    This helper creates the Admin and Owner roles with their permissions,
    which are prerequisites for the migration script.
    """
    # Create permissions
    flow_create = Permission(action=PermissionAction.CREATE, scope=PermissionScope.FLOW, description="Create flows")
    flow_read = Permission(action=PermissionAction.READ, scope=PermissionScope.FLOW, description="Read flows")
    flow_update = Permission(action=PermissionAction.UPDATE, scope=PermissionScope.FLOW, description="Update flows")
    flow_delete = Permission(action=PermissionAction.DELETE, scope=PermissionScope.FLOW, description="Delete flows")
    project_create = Permission(
        action=PermissionAction.CREATE, scope=PermissionScope.PROJECT, description="Create projects"
    )
    project_read = Permission(action=PermissionAction.READ, scope=PermissionScope.PROJECT, description="Read projects")
    project_update = Permission(
        action=PermissionAction.UPDATE, scope=PermissionScope.PROJECT, description="Update projects"
    )
    project_delete = Permission(
        action=PermissionAction.DELETE, scope=PermissionScope.PROJECT, description="Delete projects"
    )

    session.add_all(
        [flow_create, flow_read, flow_update, flow_delete, project_create, project_read, project_update, project_delete]
    )
    await session.commit()

    # Create roles
    admin_role = Role(name="Admin", description="Admin role", is_system=True, is_global=True)
    owner_role = Role(name="Owner", description="Owner role", is_system=True, is_global=False)
    session.add_all([admin_role, owner_role])
    await session.commit()

    # Create role-permission mappings
    for role in [admin_role, owner_role]:
        for perm in [
            flow_create,
            flow_read,
            flow_update,
            flow_delete,
            project_create,
            project_read,
            project_update,
            project_delete,
        ]:
            role_perm = RolePermission(role_id=role.id, permission_id=perm.id)
            session.add(role_perm)
    await session.commit()

    return admin_role, owner_role


async def create_test_user(session, username: str, is_superuser: bool = False) -> User:
    """Create a test user."""
    user = User(username=username, password="hashed_password", is_active=True, is_superuser=is_superuser)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_test_flow(session, user: User, name: str) -> Flow:
    """Create a test flow owned by a user."""
    flow = Flow(name=name, description=f"Test flow: {name}", user_id=user.id, data={})
    session.add(flow)
    await session.commit()
    await session.refresh(flow)
    return flow


async def create_test_project(session, user: User, name: str) -> Folder:
    """Create a test project (folder) owned by a user."""
    project = Folder(name=name, description=f"Test project: {name}", user_id=user.id)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def count_assignments(session, user_id, role_id, scope_type: str, scope_id=None) -> int:
    """Count role assignments matching the criteria."""
    stmt = select(UserRoleAssignment).where(
        UserRoleAssignment.user_id == user_id,
        UserRoleAssignment.role_id == role_id,
        UserRoleAssignment.scope_type == scope_type,
    )
    if scope_id is not None:
        stmt = stmt.where(UserRoleAssignment.scope_id == scope_id)
    result = await session.exec(stmt)
    return len(result.all())


# ==============================================================================
# Migration Tests
# ==============================================================================


class TestMigrateRBACData:
    """Test suite for RBAC data migration script."""

    async def test_migrate_superuser_gets_global_admin_role(self):
        """Test that superusers receive global Admin role assignment."""
        async with session_getter(get_db_service()) as session:
            # Setup: Create roles and a superuser
            admin_role, owner_role = await create_test_roles_and_permissions(session)
            superuser = await create_test_user(session, "admin_user", is_superuser=True)

            # Execute migration
            result = await migrate_existing_users_to_rbac(session, dry_run=False)

            # Verify results
            assert result["status"] == "success"
            assert result["created"] == 1
            assert result["details"]["superuser_assignments"] == 1

            # Verify assignment exists
            count = await count_assignments(session, superuser.id, admin_role.id, "global")
            assert count == 1

    async def test_migrate_regular_user_gets_owner_for_flows(self):
        """Test that regular users receive Owner role for their flows."""
        async with session_getter(get_db_service()) as session:
            # Setup: Create roles, user, and flows
            admin_role, owner_role = await create_test_roles_and_permissions(session)
            user = await create_test_user(session, "regular_user", is_superuser=False)
            flow1 = await create_test_flow(session, user, "Test Flow 1")
            flow2 = await create_test_flow(session, user, "Test Flow 2")

            # Execute migration
            result = await migrate_existing_users_to_rbac(session, dry_run=False)

            # Verify results
            assert result["status"] == "success"
            assert result["created"] == 2
            assert result["details"]["flow_assignments"] == 2

            # Verify assignments exist
            count1 = await count_assignments(session, user.id, owner_role.id, "flow", flow1.id)
            count2 = await count_assignments(session, user.id, owner_role.id, "flow", flow2.id)
            assert count1 == 1
            assert count2 == 1

    async def test_migrate_regular_user_gets_owner_for_projects(self):
        """Test that regular users receive Owner role for their projects."""
        async with session_getter(get_db_service()) as session:
            # Setup: Create roles, user, and projects
            admin_role, owner_role = await create_test_roles_and_permissions(session)
            user = await create_test_user(session, "regular_user", is_superuser=False)
            project1 = await create_test_project(session, user, "Test Project 1")
            project2 = await create_test_project(session, user, "Test Project 2")

            # Execute migration
            result = await migrate_existing_users_to_rbac(session, dry_run=False)

            # Verify results
            assert result["status"] == "success"
            assert result["created"] == 2
            assert result["details"]["project_assignments"] == 2

            # Verify assignments exist
            count1 = await count_assignments(session, user.id, owner_role.id, "project", project1.id)
            count2 = await count_assignments(session, user.id, owner_role.id, "project", project2.id)
            assert count1 == 1
            assert count2 == 1

    async def test_migrate_starter_project_is_immutable(self):
        """Test that Starter Project Owner assignments are marked immutable."""
        async with session_getter(get_db_service()) as session:
            # Setup: Create roles, user, and Starter Project
            admin_role, owner_role = await create_test_roles_and_permissions(session)
            user = await create_test_user(session, "regular_user", is_superuser=False)
            starter_project = await create_test_project(session, user, "Starter Project")

            # Execute migration
            result = await migrate_existing_users_to_rbac(session, dry_run=False)

            # Verify results
            assert result["status"] == "success"
            assert result["created"] == 1
            assert result["details"]["immutable_assignments"] == 1

            # Verify assignment is immutable
            stmt = select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == user.id,
                UserRoleAssignment.role_id == owner_role.id,
                UserRoleAssignment.scope_type == "project",
                UserRoleAssignment.scope_id == starter_project.id,
            )
            result = await session.exec(stmt)
            assignment = result.first()
            assert assignment is not None
            assert assignment.is_immutable is True

    async def test_migrate_mixed_user_types(self):
        """Test migration with both superusers and regular users."""
        async with session_getter(get_db_service()) as session:
            # Setup: Create roles, superuser, and regular user with resources
            admin_role, owner_role = await create_test_roles_and_permissions(session)
            superuser = await create_test_user(session, "admin", is_superuser=True)
            regular_user = await create_test_user(session, "user", is_superuser=False)
            flow = await create_test_flow(session, regular_user, "User Flow")
            project = await create_test_project(session, regular_user, "User Project")

            # Execute migration
            result = await migrate_existing_users_to_rbac(session, dry_run=False)

            # Verify results
            assert result["status"] == "success"
            assert result["created"] == 3  # 1 superuser + 1 flow + 1 project
            assert result["details"]["superuser_assignments"] == 1
            assert result["details"]["flow_assignments"] == 1
            assert result["details"]["project_assignments"] == 1

    async def test_migrate_idempotent_behavior(self):
        """Test that migration is idempotent (safe to run multiple times)."""
        async with session_getter(get_db_service()) as session:
            # Setup: Create roles and user with flow
            admin_role, owner_role = await create_test_roles_and_permissions(session)
            user = await create_test_user(session, "user", is_superuser=False)
            flow = await create_test_flow(session, user, "Test Flow")

            # Execute migration first time
            result1 = await migrate_existing_users_to_rbac(session, dry_run=False)
            assert result1["status"] == "success"
            assert result1["created"] == 1

            # Execute migration second time
            result2 = await migrate_existing_users_to_rbac(session, dry_run=False)
            assert result2["status"] == "success"
            assert result2["created"] == 0  # Nothing new created
            assert result2["skipped"] == 1  # Existing assignment skipped

    async def test_migrate_dry_run_mode(self):
        """Test that dry-run mode does not commit changes."""
        async with session_getter(get_db_service()) as session:
            # Setup: Create roles and user with flow
            admin_role, owner_role = await create_test_roles_and_permissions(session)
            user = await create_test_user(session, "user", is_superuser=False)
            flow = await create_test_flow(session, user, "Test Flow")

            # Store IDs before dry-run (which will rollback)
            user_id = user.id
            owner_role_id = owner_role.id
            flow_id = flow.id

            # Execute migration in dry-run mode
            result = await migrate_existing_users_to_rbac(session, dry_run=True)

            # Verify dry-run results
            assert result["status"] == "dry_run"
            assert result["would_create"] == 1
            assert result["would_skip"] == 0

            # Verify no assignments were actually created
            count = await count_assignments(session, user_id, owner_role_id, "flow", flow_id)
            assert count == 0

    async def test_migrate_user_without_resources(self):
        """Test migration for user with no flows or projects."""
        async with session_getter(get_db_service()) as session:
            # Setup: Create roles and user without resources
            admin_role, owner_role = await create_test_roles_and_permissions(session)
            user = await create_test_user(session, "empty_user", is_superuser=False)

            # Execute migration
            result = await migrate_existing_users_to_rbac(session, dry_run=False)

            # Verify results
            assert result["status"] == "success"
            assert result["created"] == 0  # No assignments created

            # Verify no assignments exist
            stmt = select(UserRoleAssignment).where(UserRoleAssignment.user_id == user.id)
            result = await session.exec(stmt)
            assignments = result.all()
            assert len(assignments) == 0

    async def test_migrate_without_roles_returns_error(self):
        """Test that migration returns error if roles are missing."""
        async with session_getter(get_db_service()) as session:
            # Setup: Create user but NO roles
            user = await create_test_user(session, "user", is_superuser=False)

            # Execute migration
            result = await migrate_existing_users_to_rbac(session, dry_run=False)

            # Verify error results
            assert result["status"] == "error"
            assert "Admin and Owner roles not found" in result["error"]
            assert len(result["errors"]) > 0

    async def test_migrate_updates_existing_starter_project_to_immutable(self):
        """Test that existing Starter Project assignment is updated to immutable."""
        async with session_getter(get_db_service()) as session:
            # Setup: Create roles, user, and Starter Project
            admin_role, owner_role = await create_test_roles_and_permissions(session)
            user = await create_test_user(session, "user", is_superuser=False)
            starter_project = await create_test_project(session, user, "Starter Project")

            # Create assignment without immutable flag
            assignment = UserRoleAssignment(
                user_id=user.id,
                role_id=owner_role.id,
                scope_type="project",
                scope_id=starter_project.id,
                is_immutable=False,
            )
            session.add(assignment)
            await session.commit()

            # Execute migration
            result = await migrate_existing_users_to_rbac(session, dry_run=False)

            # Verify assignment was updated to immutable
            stmt = select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == user.id, UserRoleAssignment.scope_id == starter_project.id
            )
            result = await session.exec(stmt)
            updated_assignment = result.first()
            assert updated_assignment is not None
            assert updated_assignment.is_immutable is True

    async def test_migrate_multiple_users_with_resources(self):
        """Test migration with multiple users each owning multiple resources."""
        async with session_getter(get_db_service()) as session:
            # Setup: Create roles and multiple users with resources
            admin_role, owner_role = await create_test_roles_and_permissions(session)

            user1 = await create_test_user(session, "user1", is_superuser=False)
            flow1 = await create_test_flow(session, user1, "User1 Flow")
            project1 = await create_test_project(session, user1, "User1 Project")

            user2 = await create_test_user(session, "user2", is_superuser=False)
            flow2a = await create_test_flow(session, user2, "User2 Flow A")
            flow2b = await create_test_flow(session, user2, "User2 Flow B")
            project2 = await create_test_project(session, user2, "User2 Project")

            # Execute migration
            result = await migrate_existing_users_to_rbac(session, dry_run=False)

            # Verify results
            assert result["status"] == "success"
            assert result["created"] == 5  # 1+1 for user1, 2+1 for user2
            assert result["details"]["flow_assignments"] == 3
            assert result["details"]["project_assignments"] == 2

    async def test_migrate_no_users_in_database(self):
        """Test migration when no users exist in database."""
        async with session_getter(get_db_service()) as session:
            # Setup: Create roles but no users
            admin_role, owner_role = await create_test_roles_and_permissions(session)

            # Execute migration
            result = await migrate_existing_users_to_rbac(session, dry_run=False)

            # Verify results
            assert result["status"] == "success"
            assert result["created"] == 0
            assert result["skipped"] == 0

    async def test_migrate_assignment_attributes(self):
        """Test that created assignments have correct attributes."""
        async with session_getter(get_db_service()) as session:
            # Setup: Create roles and user with flow
            admin_role, owner_role = await create_test_roles_and_permissions(session)
            user = await create_test_user(session, "user", is_superuser=False)
            flow = await create_test_flow(session, user, "Test Flow")

            # Execute migration
            result = await migrate_existing_users_to_rbac(session, dry_run=False)

            # Verify assignment attributes
            stmt = select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == user.id, UserRoleAssignment.scope_id == flow.id
            )
            result = await session.exec(stmt)
            assignment = result.first()

            assert assignment is not None
            assert assignment.user_id == user.id
            assert assignment.role_id == owner_role.id
            assert assignment.scope_type == "flow"
            assert assignment.scope_id == flow.id
            assert assignment.is_immutable is False
            assert assignment.created_at is not None
            assert assignment.id is not None

    async def test_migrate_superuser_assignment_attributes(self):
        """Test that superuser global Admin assignment has correct attributes."""
        async with session_getter(get_db_service()) as session:
            # Setup: Create roles and superuser
            admin_role, owner_role = await create_test_roles_and_permissions(session)
            superuser = await create_test_user(session, "admin", is_superuser=True)

            # Execute migration
            result = await migrate_existing_users_to_rbac(session, dry_run=False)

            # Verify assignment attributes
            stmt = select(UserRoleAssignment).where(UserRoleAssignment.user_id == superuser.id)
            result = await session.exec(stmt)
            assignment = result.first()

            assert assignment is not None
            assert assignment.user_id == superuser.id
            assert assignment.role_id == admin_role.id
            assert assignment.scope_type == "global"
            assert assignment.scope_id is None
            assert assignment.is_immutable is False
            assert assignment.created_at is not None
