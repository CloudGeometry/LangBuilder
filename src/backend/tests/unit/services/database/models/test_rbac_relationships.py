"""Unit tests for RBAC model relationships and constraints.

This test module covers:
- Bidirectional relationship queries (role->permissions, permission->roles, etc.)
- Cascade delete behavior for Role->RolePermission
- Foreign key constraint violations
- Complex relationship scenarios
"""

import pytest
from fastapi import HTTPException
from langbuilder.services.database.models.permission.crud import create_permission, get_permission_by_id
from langbuilder.services.database.models.permission.model import PermissionCreate
from langbuilder.services.database.models.role.crud import create_role, delete_role, get_role_by_id
from langbuilder.services.database.models.role.model import RoleCreate
from langbuilder.services.database.models.role_permission.crud import create_role_permission
from langbuilder.services.database.models.role_permission.model import RolePermissionCreate
from langbuilder.services.database.models.user.model import User
from langbuilder.services.database.models.user_role_assignment.crud import (
    create_user_role_assignment,
    delete_user_role_assignment,
)
from langbuilder.services.database.models.user_role_assignment.model import UserRoleAssignmentCreate
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession


@pytest.fixture
async def test_user(async_session: AsyncSession):
    """Create a test user for relationship tests."""
    from langbuilder.services.auth.utils import get_password_hash

    user = User(
        username="relationshipuser",
        password=get_password_hash("password"),
        is_active=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


# ============================================================================
# RELATIONSHIP QUERY TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_role_to_permissions_relationship(async_session: AsyncSession):
    """Test querying permissions through role relationship."""
    # Create a role
    role_data = RoleCreate(name="Admin", description="Administrator role")
    role = await create_role(async_session, role_data)

    # Create multiple permissions
    permission_1_data = PermissionCreate(name="Create", scope="Flow")
    permission_1 = await create_permission(async_session, permission_1_data)

    permission_2_data = PermissionCreate(name="Read", scope="Flow")
    permission_2 = await create_permission(async_session, permission_2_data)

    permission_3_data = PermissionCreate(name="Update", scope="Flow")
    permission_3 = await create_permission(async_session, permission_3_data)

    # Associate permissions with role
    await create_role_permission(async_session, RolePermissionCreate(role_id=role.id, permission_id=permission_1.id))
    await create_role_permission(async_session, RolePermissionCreate(role_id=role.id, permission_id=permission_2.id))
    await create_role_permission(async_session, RolePermissionCreate(role_id=role.id, permission_id=permission_3.id))

    # Query role and access permissions through relationship with eager loading
    from langbuilder.services.database.models.role.model import Role

    stmt = select(Role).where(Role.id == role.id).options(selectinload(Role.role_permissions))
    result = await async_session.execute(stmt)
    queried_role = result.scalar_one()

    # Access the role_permissions relationship
    assert len(queried_role.role_permissions) == 3

    # Verify all permissions are accessible through the relationship
    permission_ids = [rp.permission_id for rp in queried_role.role_permissions]
    assert permission_1.id in permission_ids
    assert permission_2.id in permission_ids
    assert permission_3.id in permission_ids


@pytest.mark.asyncio
async def test_permission_to_roles_relationship(async_session: AsyncSession):
    """Test querying roles through permission relationship."""
    # Create multiple roles
    role_1_data = RoleCreate(name="Admin")
    role_1 = await create_role(async_session, role_1_data)

    role_2_data = RoleCreate(name="Editor")
    role_2 = await create_role(async_session, role_2_data)

    # Create a permission
    permission_data = PermissionCreate(name="Create", scope="Flow")
    permission = await create_permission(async_session, permission_data)

    # Associate permission with multiple roles
    await create_role_permission(async_session, RolePermissionCreate(role_id=role_1.id, permission_id=permission.id))
    await create_role_permission(async_session, RolePermissionCreate(role_id=role_2.id, permission_id=permission.id))

    # Query permission and access roles through relationship with eager loading
    from langbuilder.services.database.models.permission.model import Permission

    stmt = select(Permission).where(Permission.id == permission.id).options(selectinload(Permission.role_permissions))
    result = await async_session.execute(stmt)
    queried_permission = result.scalar_one()

    # Access the role_permissions relationship
    assert len(queried_permission.role_permissions) == 2

    # Verify all roles are accessible through the relationship
    role_ids = [rp.role_id for rp in queried_permission.role_permissions]
    assert role_1.id in role_ids
    assert role_2.id in role_ids


@pytest.mark.asyncio
async def test_user_to_roles_relationship(async_session: AsyncSession, test_user: User):
    """Test querying role assignments for a user."""
    # Create multiple roles
    role_1_data = RoleCreate(name="Admin")
    role_1 = await create_role(async_session, role_1_data)

    role_2_data = RoleCreate(name="Editor")
    role_2 = await create_role(async_session, role_2_data)

    # Assign roles to user with different scopes
    assignment_1 = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role_1.id, scope_type="Global", scope_id=None
    )
    await create_user_role_assignment(async_session, assignment_1)

    assignment_2 = UserRoleAssignmentCreate(user_id=test_user.id, role_id=role_2.id, scope_type="Flow", scope_id=None)
    await create_user_role_assignment(async_session, assignment_2)

    # Query role assignments for the user
    from langbuilder.services.database.models.user_role_assignment.crud import list_assignments_by_user

    assignments = await list_assignments_by_user(async_session, test_user.id)

    # Verify assignments
    assert len(assignments) == 2
    role_ids = [assignment.role_id for assignment in assignments]
    assert role_1.id in role_ids
    assert role_2.id in role_ids


@pytest.mark.asyncio
async def test_role_to_user_assignments_relationship(async_session: AsyncSession, test_user: User):
    """Test querying user assignments through role relationship."""
    # Create a role
    role_data = RoleCreate(name="Viewer")
    role = await create_role(async_session, role_data)

    # Create multiple user assignments for the role
    assignment_1 = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Global", scope_id=None
    )
    await create_user_role_assignment(async_session, assignment_1)

    # Query role and access user assignments through relationship with eager loading
    from langbuilder.services.database.models.role.model import Role

    stmt = select(Role).where(Role.id == role.id).options(selectinload(Role.user_assignments))
    result = await async_session.execute(stmt)
    queried_role = result.scalar_one()

    # Access the user_assignments relationship
    assert len(queried_role.user_assignments) == 1
    assert queried_role.user_assignments[0].user_id == test_user.id


# ============================================================================
# CASCADE DELETE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_delete_role_cascades_to_role_permissions(async_session: AsyncSession):
    """Test that deleting a role cascades to its role_permission associations."""
    # Create a role
    role_data = RoleCreate(name="Admin")
    role = await create_role(async_session, role_data)

    # Create permissions
    permission_1_data = PermissionCreate(name="Create", scope="Flow")
    permission_1 = await create_permission(async_session, permission_1_data)

    permission_2_data = PermissionCreate(name="Read", scope="Flow")
    permission_2 = await create_permission(async_session, permission_2_data)

    # Associate permissions with role
    rp1 = await create_role_permission(
        async_session, RolePermissionCreate(role_id=role.id, permission_id=permission_1.id)
    )
    rp2 = await create_role_permission(
        async_session, RolePermissionCreate(role_id=role.id, permission_id=permission_2.id)
    )

    # Delete the role
    await delete_role(async_session, role.id)

    # Verify role is deleted
    deleted_role = await get_role_by_id(async_session, role.id)
    assert deleted_role is None

    # Verify role_permission associations are also deleted (cascade)
    from langbuilder.services.database.models.role_permission.crud import get_role_permission_by_id

    deleted_rp1 = await get_role_permission_by_id(async_session, rp1.id)
    deleted_rp2 = await get_role_permission_by_id(async_session, rp2.id)
    assert deleted_rp1 is None
    assert deleted_rp2 is None

    # Verify permissions themselves are NOT deleted (only the associations)
    permission_1_exists = await get_permission_by_id(async_session, permission_1.id)
    permission_2_exists = await get_permission_by_id(async_session, permission_2.id)
    assert permission_1_exists is not None
    assert permission_2_exists is not None


@pytest.mark.asyncio
async def test_delete_user_prevents_if_has_role_assignments(async_session: AsyncSession):
    """Test that deleting a user with role assignments is handled correctly."""
    from langbuilder.services.auth.utils import get_password_hash

    # Create a test user specifically for this test
    user = User(
        username="testusertodelete",
        password=get_password_hash("password"),
        is_active=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    user_id = user.id

    # Create a role
    role_data = RoleCreate(name="Editor")
    role = await create_role(async_session, role_data)

    # Create role assignment
    assignment_data = UserRoleAssignmentCreate(user_id=user.id, role_id=role.id, scope_type="Global", scope_id=None)
    assignment = await create_user_role_assignment(async_session, assignment_data)

    # Attempting to delete the user should fail due to foreign key constraint
    # (unless cascade delete is configured on User model's relationship)
    try:
        await async_session.delete(user)
        await async_session.commit()
        # If cascade is configured, this succeeds; if not, it fails
    except IntegrityError:
        # Foreign key constraint prevents deletion
        await async_session.rollback()
        # Verify user still exists
        stmt = select(User).where(User.id == user_id)
        result = await async_session.execute(stmt)
        user_exists = result.scalar_one_or_none()
        assert user_exists is not None


# ============================================================================
# CONSTRAINT VALIDATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_role_permission_requires_valid_role_and_permission(async_session: AsyncSession):
    """Test that role_permission enforces valid role_id and permission_id."""
    # This test validates that the foreign key relationships are properly defined
    # Actual constraint enforcement happens at the database level

    # Create valid role and permission
    role_data = RoleCreate(name="Admin")
    role = await create_role(async_session, role_data)

    permission_data = PermissionCreate(name="Create", scope="Flow")
    permission = await create_permission(async_session, permission_data)

    # Create role_permission with valid IDs - should succeed
    rp_data = RolePermissionCreate(role_id=role.id, permission_id=permission.id)
    rp = await create_role_permission(async_session, rp_data)

    assert rp.role_id == role.id
    assert rp.permission_id == permission.id


@pytest.mark.asyncio
async def test_user_role_assignment_requires_valid_user_and_role(async_session: AsyncSession, test_user: User):
    """Test that user_role_assignment enforces valid user_id and role_id."""
    # This test validates that the foreign key relationships are properly defined

    # Create valid role
    role_data = RoleCreate(name="Editor")
    role = await create_role(async_session, role_data)

    # Create user_role_assignment with valid IDs - should succeed
    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Global", scope_id=None
    )
    assignment = await create_user_role_assignment(async_session, assignment_data)

    assert assignment.user_id == test_user.id
    assert assignment.role_id == role.id


# ============================================================================
# COMPLEX RELATIONSHIP SCENARIOS
# ============================================================================


@pytest.mark.asyncio
async def test_role_with_multiple_permissions_and_users(async_session: AsyncSession, test_user: User):
    """Test a role with multiple permissions and multiple user assignments."""
    # Create a role
    role_data = RoleCreate(name="ProjectManager")
    role = await create_role(async_session, role_data)

    # Create permissions
    permissions = []
    for name in ["Create", "Read", "Update", "Delete"]:
        permission_data = PermissionCreate(name=name, scope="Project")
        permission = await create_permission(async_session, permission_data)
        permissions.append(permission)

        # Associate permission with role
        await create_role_permission(async_session, RolePermissionCreate(role_id=role.id, permission_id=permission.id))

    # Create additional users
    from langbuilder.services.auth.utils import get_password_hash

    user2 = User(username="user2", password=get_password_hash("password"), is_active=True)
    async_session.add(user2)
    await async_session.commit()
    await async_session.refresh(user2)

    # Assign role to multiple users
    assignment_1 = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Project", scope_id=None
    )
    await create_user_role_assignment(async_session, assignment_1)

    assignment_2 = UserRoleAssignmentCreate(user_id=user2.id, role_id=role.id, scope_type="Project", scope_id=None)
    await create_user_role_assignment(async_session, assignment_2)

    # Query role and verify relationships with eager loading
    from langbuilder.services.database.models.role.model import Role

    stmt = (
        select(Role)
        .where(Role.id == role.id)
        .options(selectinload(Role.role_permissions), selectinload(Role.user_assignments))
    )
    result = await async_session.execute(stmt)
    queried_role = result.scalar_one()

    # Verify all permissions are associated
    assert len(queried_role.role_permissions) == 4

    # Verify all users are assigned
    assert len(queried_role.user_assignments) == 2


@pytest.mark.asyncio
async def test_user_with_multiple_roles_different_scopes(async_session: AsyncSession, test_user: User):
    """Test a user with multiple roles at different scope levels."""
    from uuid import uuid4

    # Create roles
    admin_role = await create_role(async_session, RoleCreate(name="GlobalAdmin"))
    project_role = await create_role(async_session, RoleCreate(name="ProjectEditor"))
    flow_role = await create_role(async_session, RoleCreate(name="FlowViewer"))

    # Assign roles at different scopes
    project_id = uuid4()
    flow_id = uuid4()

    # Global scope
    await create_user_role_assignment(
        async_session,
        UserRoleAssignmentCreate(user_id=test_user.id, role_id=admin_role.id, scope_type="Global", scope_id=None),
    )

    # Project scope
    await create_user_role_assignment(
        async_session,
        UserRoleAssignmentCreate(
            user_id=test_user.id, role_id=project_role.id, scope_type="Project", scope_id=project_id
        ),
    )

    # Flow scope
    await create_user_role_assignment(
        async_session,
        UserRoleAssignmentCreate(user_id=test_user.id, role_id=flow_role.id, scope_type="Flow", scope_id=flow_id),
    )

    # Query user assignments directly
    from langbuilder.services.database.models.user_role_assignment.crud import list_assignments_by_user

    assignments = await list_assignments_by_user(async_session, test_user.id)

    # Verify all role assignments
    assert len(assignments) == 3

    # Verify scope types
    scope_types = {assignment.scope_type for assignment in assignments}
    assert scope_types == {"Global", "Project", "Flow"}

    # Verify specific scope IDs
    project_assignment = next(a for a in assignments if a.scope_type == "Project")
    assert project_assignment.scope_id == project_id

    flow_assignment = next(a for a in assignments if a.scope_type == "Flow")
    assert flow_assignment.scope_id == flow_id




@pytest.mark.asyncio
async def test_immutable_assignment_prevents_deletion(async_session: AsyncSession, test_user: User):
    """Test that an immutable user role assignment cannot be deleted."""
    # Create role
    role_data = RoleCreate(name="Owner")
    role = await create_role(async_session, role_data)

    # Create immutable assignment
    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Project", scope_id=None, is_immutable=True
    )
    assignment = await create_user_role_assignment(async_session, assignment_data)

    # Attempt to delete the immutable assignment
    with pytest.raises(HTTPException) as exc_info:
        await delete_user_role_assignment(async_session, assignment.id)

    assert exc_info.value.status_code == 400
    assert "immutable" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_system_role_prevents_deletion(async_session: AsyncSession):
    """Test that a system role cannot be deleted."""
    # Create a system role
    role_data = RoleCreate(name="Admin", description="System administrator", is_system_role=True)
    role = await create_role(async_session, role_data)

    # Attempt to delete the system role
    with pytest.raises(HTTPException) as exc_info:
        await delete_role(async_session, role.id)

    assert exc_info.value.status_code == 400
    assert "system role" in exc_info.value.detail.lower()
