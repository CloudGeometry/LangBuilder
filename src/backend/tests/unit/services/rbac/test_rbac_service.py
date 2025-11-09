"""Comprehensive unit tests for RBACService."""

from uuid import uuid4

import pytest
from langbuilder.services.auth.utils import get_password_hash
from langbuilder.services.database.models.flow.model import Flow
from langbuilder.services.database.models.folder.model import Folder
from langbuilder.services.database.models.permission.crud import create_permission
from langbuilder.services.database.models.permission.model import PermissionCreate
from langbuilder.services.database.models.role.crud import create_role
from langbuilder.services.database.models.role.model import RoleCreate
from langbuilder.services.database.models.role_permission.model import RolePermission
from langbuilder.services.database.models.user.model import User
from langbuilder.services.database.models.user_role_assignment.crud import create_user_role_assignment
from langbuilder.services.database.models.user_role_assignment.model import UserRoleAssignmentCreate
from langbuilder.services.rbac.exceptions import (
    AssignmentNotFoundException,
    DuplicateAssignmentException,
    ImmutableAssignmentException,
    RoleNotFoundException,
)
from langbuilder.services.rbac.service import RBACService
from sqlmodel.ext.asyncio.session import AsyncSession


@pytest.fixture
async def rbac_service():
    """Create an RBACService instance."""
    return RBACService()


@pytest.fixture
async def test_user(async_session: AsyncSession):
    """Create a test user."""
    user = User(
        username="testuser",
        password=get_password_hash("password"),
        is_active=True,
        is_superuser=False,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
async def superuser(async_session: AsyncSession):
    """Create a superuser."""
    user = User(
        username="superuser",
        password=get_password_hash("password"),
        is_active=True,
        is_superuser=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
async def test_role(async_session: AsyncSession):
    """Create a test role."""
    role_data = RoleCreate(name="Editor", description="Can edit flows")
    return await create_role(async_session, role_data)


@pytest.fixture
async def admin_role(async_session: AsyncSession):
    """Create an Admin role."""
    role_data = RoleCreate(name="Admin", description="Full access")
    return await create_role(async_session, role_data)


@pytest.fixture
async def viewer_role(async_session: AsyncSession):
    """Create a Viewer role."""
    role_data = RoleCreate(name="Viewer", description="Read-only access")
    return await create_role(async_session, role_data)


@pytest.fixture
async def flow_read_permission(async_session: AsyncSession):
    """Create Read permission for Flow scope."""
    perm_data = PermissionCreate(name="Read", scope="Flow", description="Read flow")
    return await create_permission(async_session, perm_data)


@pytest.fixture
async def flow_update_permission(async_session: AsyncSession):
    """Create Update permission for Flow scope."""
    perm_data = PermissionCreate(name="Update", scope="Flow", description="Update flow")
    return await create_permission(async_session, perm_data)


@pytest.fixture
async def project_read_permission(async_session: AsyncSession):
    """Create Read permission for Project scope."""
    perm_data = PermissionCreate(name="Read", scope="Project", description="Read project")
    return await create_permission(async_session, perm_data)


@pytest.fixture
async def test_folder(async_session: AsyncSession, test_user):
    """Create a test folder (project)."""
    folder = Folder(
        name="Test Project",
        user_id=test_user.id,
    )
    async_session.add(folder)
    await async_session.commit()
    await async_session.refresh(folder)
    return folder


@pytest.fixture
async def test_flow(async_session: AsyncSession, test_user, test_folder):
    """Create a test flow."""
    flow = Flow(
        name="Test Flow",
        user_id=test_user.id,
        folder_id=test_folder.id,
        data={},
    )
    async_session.add(flow)
    await async_session.commit()
    await async_session.refresh(flow)
    return flow


# Test can_access method


@pytest.mark.asyncio
async def test_can_access_superuser_bypass(rbac_service, async_session, superuser):
    """Test that superusers bypass all permission checks."""
    result = await rbac_service.can_access(
        user_id=superuser.id,
        permission_name="Delete",
        scope_type="Flow",
        scope_id=uuid4(),
        db=async_session,
    )
    assert result is True


@pytest.mark.asyncio
async def test_can_access_global_admin_bypass(
    rbac_service, async_session, test_user, admin_role, flow_read_permission  # noqa: ARG001
):
    """Test that Global Admin role bypasses permission checks."""
    # Assign Global Admin role
    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id,
        role_id=admin_role.id,
        scope_type="Global",
        scope_id=None,
    )
    await create_user_role_assignment(async_session, assignment_data)

    result = await rbac_service.can_access(
        user_id=test_user.id,
        permission_name="Delete",
        scope_type="Flow",
        scope_id=uuid4(),
        db=async_session,
    )
    assert result is True


@pytest.mark.asyncio
async def test_can_access_with_flow_permission(
    rbac_service, async_session, test_user, test_role, test_flow, flow_read_permission
):
    """Test permission check with explicit Flow-level role assignment."""
    # Link permission to role
    role_perm = RolePermission(role_id=test_role.id, permission_id=flow_read_permission.id)
    async_session.add(role_perm)
    await async_session.commit()

    # Assign role to user for specific flow
    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id,
        role_id=test_role.id,
        scope_type="Flow",
        scope_id=test_flow.id,
    )
    await create_user_role_assignment(async_session, assignment_data)

    result = await rbac_service.can_access(
        user_id=test_user.id,
        permission_name="Read",
        scope_type="Flow",
        scope_id=test_flow.id,
        db=async_session,
    )
    assert result is True


@pytest.mark.asyncio
async def test_can_access_inherited_from_project(
    rbac_service, async_session, test_user, test_role, test_flow, test_folder, flow_read_permission
):
    """Test Flow permission inheritance from Project-level role assignment."""
    # Link permission to role
    role_perm = RolePermission(role_id=test_role.id, permission_id=flow_read_permission.id)
    async_session.add(role_perm)
    await async_session.commit()

    # Assign role to user at Project level (not Flow level)
    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id,
        role_id=test_role.id,
        scope_type="Project",
        scope_id=test_folder.id,
    )
    await create_user_role_assignment(async_session, assignment_data)

    # Check Flow permission (should inherit from Project)
    result = await rbac_service.can_access(
        user_id=test_user.id,
        permission_name="Read",
        scope_type="Flow",
        scope_id=test_flow.id,
        db=async_session,
    )
    assert result is True


@pytest.mark.asyncio
async def test_can_access_no_permission(rbac_service, async_session, test_user, test_flow):
    """Test permission check when user has no role assignment."""
    result = await rbac_service.can_access(
        user_id=test_user.id,
        permission_name="Read",
        scope_type="Flow",
        scope_id=test_flow.id,
        db=async_session,
    )
    assert result is False


@pytest.mark.asyncio
async def test_can_access_wrong_permission(
    rbac_service, async_session, test_user, test_role, test_flow, flow_read_permission
):
    """Test permission check when role lacks required permission."""
    # Link Read permission to role
    role_perm = RolePermission(role_id=test_role.id, permission_id=flow_read_permission.id)
    async_session.add(role_perm)
    await async_session.commit()

    # Assign role to user
    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id,
        role_id=test_role.id,
        scope_type="Flow",
        scope_id=test_flow.id,
    )
    await create_user_role_assignment(async_session, assignment_data)

    # Check for Update permission (role only has Read)
    result = await rbac_service.can_access(
        user_id=test_user.id,
        permission_name="Update",
        scope_type="Flow",
        scope_id=test_flow.id,
        db=async_session,
    )
    assert result is False


# Test assign_role method


@pytest.mark.asyncio
async def test_assign_role_success(rbac_service, async_session, test_user, test_role):
    """Test successful role assignment."""
    flow_id = uuid4()
    assignment = await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Editor",
        scope_type="Flow",
        scope_id=flow_id,
        created_by=test_user.id,
        db=async_session,
    )

    assert assignment.id is not None
    assert assignment.user_id == test_user.id
    assert assignment.role_id == test_role.id
    assert assignment.scope_type == "Flow"
    assert assignment.scope_id == flow_id
    assert assignment.is_immutable is False


@pytest.mark.asyncio
async def test_assign_role_immutable(rbac_service, async_session, test_user, test_role):  # noqa: ARG001
    """Test assigning an immutable role."""
    flow_id = uuid4()
    assignment = await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Editor",
        scope_type="Flow",
        scope_id=flow_id,
        created_by=test_user.id,
        db=async_session,
        is_immutable=True,
    )

    assert assignment.is_immutable is True


@pytest.mark.asyncio
async def test_assign_role_not_found(rbac_service, async_session, test_user):
    """Test assigning a non-existent role."""
    with pytest.raises(RoleNotFoundException) as exc_info:
        await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="NonExistentRole",
            scope_type="Flow",
            scope_id=uuid4(),
            created_by=test_user.id,
            db=async_session,
        )
    assert "NonExistentRole" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_assign_role_duplicate(rbac_service, async_session, test_user, test_role):  # noqa: ARG001
    """Test assigning a duplicate role."""
    flow_id = uuid4()

    # First assignment
    await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Editor",
        scope_type="Flow",
        scope_id=flow_id,
        created_by=test_user.id,
        db=async_session,
    )

    # Duplicate assignment
    with pytest.raises(DuplicateAssignmentException):
        await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="Editor",
            scope_type="Flow",
            scope_id=flow_id,
            created_by=test_user.id,
            db=async_session,
        )


# Test remove_role method


@pytest.mark.asyncio
async def test_remove_role_success(rbac_service, async_session, test_user, test_role):  # noqa: ARG001
    """Test successful role removal."""
    flow_id = uuid4()
    assignment = await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Editor",
        scope_type="Flow",
        scope_id=flow_id,
        created_by=test_user.id,
        db=async_session,
    )

    await rbac_service.remove_role(assignment.id, db=async_session)

    # Verify assignment was deleted
    from langbuilder.services.database.models.user_role_assignment.crud import get_user_role_assignment_by_id

    deleted_assignment = await get_user_role_assignment_by_id(async_session, assignment.id)
    assert deleted_assignment is None


@pytest.mark.asyncio
async def test_remove_role_not_found(rbac_service, async_session):
    """Test removing a non-existent role assignment."""
    with pytest.raises(AssignmentNotFoundException):
        await rbac_service.remove_role(uuid4(), db=async_session)


@pytest.mark.asyncio
async def test_remove_role_immutable(rbac_service, async_session, test_user, test_role):  # noqa: ARG001
    """Test removing an immutable role assignment fails."""
    flow_id = uuid4()
    assignment = await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Editor",
        scope_type="Flow",
        scope_id=flow_id,
        created_by=test_user.id,
        db=async_session,
        is_immutable=True,
    )

    with pytest.raises(ImmutableAssignmentException) as exc_info:
        await rbac_service.remove_role(assignment.id, db=async_session)
    assert "remove" in str(exc_info.value.detail).lower()


# Test update_role method


@pytest.mark.asyncio
async def test_update_role_success(rbac_service, async_session, test_user, test_role, viewer_role):  # noqa: ARG001
    """Test successful role update."""
    flow_id = uuid4()
    assignment = await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Editor",
        scope_type="Flow",
        scope_id=flow_id,
        created_by=test_user.id,
        db=async_session,
    )

    updated_assignment = await rbac_service.update_role(
        assignment_id=assignment.id,
        new_role_name="Viewer",
        db=async_session,
    )

    assert updated_assignment.role_id == viewer_role.id


@pytest.mark.asyncio
async def test_update_role_not_found(rbac_service, async_session):
    """Test updating a non-existent role assignment."""
    with pytest.raises(AssignmentNotFoundException):
        await rbac_service.update_role(
            assignment_id=uuid4(),
            new_role_name="Viewer",
            db=async_session,
        )


@pytest.mark.asyncio
async def test_update_role_immutable(rbac_service, async_session, test_user, test_role):  # noqa: ARG001
    """Test updating an immutable role assignment fails."""
    flow_id = uuid4()
    assignment = await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Editor",
        scope_type="Flow",
        scope_id=flow_id,
        created_by=test_user.id,
        db=async_session,
        is_immutable=True,
    )

    with pytest.raises(ImmutableAssignmentException) as exc_info:
        await rbac_service.update_role(
            assignment_id=assignment.id,
            new_role_name="Viewer",
            db=async_session,
        )
    assert "modify" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_update_role_new_role_not_found(rbac_service, async_session, test_user, test_role):  # noqa: ARG001
    """Test updating to a non-existent role."""
    flow_id = uuid4()
    assignment = await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Editor",
        scope_type="Flow",
        scope_id=flow_id,
        created_by=test_user.id,
        db=async_session,
    )

    with pytest.raises(RoleNotFoundException):
        await rbac_service.update_role(
            assignment_id=assignment.id,
            new_role_name="NonExistentRole",
            db=async_session,
        )


# Test list_user_assignments method


@pytest.mark.asyncio
async def test_list_user_assignments_all(rbac_service, async_session, test_user, test_role, viewer_role):  # noqa: ARG001
    """Test listing all role assignments."""
    # Create multiple assignments
    await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Editor",
        scope_type="Flow",
        scope_id=uuid4(),
        created_by=test_user.id,
        db=async_session,
    )
    await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Viewer",
        scope_type="Project",
        scope_id=uuid4(),
        created_by=test_user.id,
        db=async_session,
    )

    assignments = await rbac_service.list_user_assignments(user_id=None, db=async_session)
    assert len(assignments) >= 2


@pytest.mark.asyncio
async def test_list_user_assignments_filtered(rbac_service, async_session, test_user, test_role):  # noqa: ARG001
    """Test listing role assignments filtered by user."""
    # Create assignment for test_user
    await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Editor",
        scope_type="Flow",
        scope_id=uuid4(),
        created_by=test_user.id,
        db=async_session,
    )

    # Create another user and assignment
    other_user = User(
        username="otheruser",
        password=get_password_hash("password"),
        is_active=True,
    )
    async_session.add(other_user)
    await async_session.commit()
    await async_session.refresh(other_user)

    await rbac_service.assign_role(
        user_id=other_user.id,
        role_name="Editor",
        scope_type="Flow",
        scope_id=uuid4(),
        created_by=other_user.id,
        db=async_session,
    )

    # Get assignments only for test_user
    assignments = await rbac_service.list_user_assignments(user_id=test_user.id, db=async_session)
    assert len(assignments) == 1
    assert assignments[0].user_id == test_user.id


# Test get_user_permissions_for_scope method


@pytest.mark.asyncio
async def test_get_user_permissions_for_scope(
    rbac_service, async_session, test_user, test_role, test_flow, flow_read_permission, flow_update_permission
):
    """Test getting user permissions for a specific scope."""
    # Link permissions to role
    role_perm1 = RolePermission(role_id=test_role.id, permission_id=flow_read_permission.id)
    role_perm2 = RolePermission(role_id=test_role.id, permission_id=flow_update_permission.id)
    async_session.add(role_perm1)
    async_session.add(role_perm2)
    await async_session.commit()

    # Assign role to user
    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id,
        role_id=test_role.id,
        scope_type="Flow",
        scope_id=test_flow.id,
    )
    await create_user_role_assignment(async_session, assignment_data)

    # Get permissions
    permissions = await rbac_service.get_user_permissions_for_scope(
        user_id=test_user.id,
        scope_type="Flow",
        scope_id=test_flow.id,
        db=async_session,
    )

    assert len(permissions) == 2
    permission_names = {p.name for p in permissions}
    assert "Read" in permission_names
    assert "Update" in permission_names


@pytest.mark.asyncio
async def test_get_user_permissions_no_role(rbac_service, async_session, test_user, test_flow):
    """Test getting permissions when user has no role."""
    permissions = await rbac_service.get_user_permissions_for_scope(
        user_id=test_user.id,
        scope_type="Flow",
        scope_id=test_flow.id,
        db=async_session,
    )

    assert len(permissions) == 0


@pytest.mark.asyncio
async def test_get_user_permissions_inherited_from_project(
    rbac_service, async_session, test_user, test_role, test_flow, test_folder, flow_read_permission
):
    """Test getting Flow permissions inherited from Project-level assignment."""
    # Link permission to role
    role_perm = RolePermission(role_id=test_role.id, permission_id=flow_read_permission.id)
    async_session.add(role_perm)
    await async_session.commit()

    # Assign role at Project level
    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id,
        role_id=test_role.id,
        scope_type="Project",
        scope_id=test_folder.id,
    )
    await create_user_role_assignment(async_session, assignment_data)

    # Get Flow permissions (should inherit from Project)
    permissions = await rbac_service.get_user_permissions_for_scope(
        user_id=test_user.id,
        scope_type="Flow",
        scope_id=test_flow.id,
        db=async_session,
    )

    assert len(permissions) == 1
    assert permissions[0].name == "Read"
