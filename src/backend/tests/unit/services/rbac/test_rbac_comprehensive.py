"""Comprehensive edge case tests for RBACService (Task 5.1)."""

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
from langbuilder.services.database.models.user_role_assignment.model import UserRoleAssignment
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
        username="testuser_comprehensive",
        password=get_password_hash("password"),
        is_active=True,
        is_superuser=False,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
async def second_user(async_session: AsyncSession):
    """Create a second test user."""
    user = User(
        username="seconduser_comprehensive",
        password=get_password_hash("password"),
        is_active=True,
        is_superuser=False,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
async def viewer_role(async_session: AsyncSession):
    """Create a Viewer role."""
    role_data = RoleCreate(name="ViewerComp", description="Read-only access")
    return await create_role(async_session, role_data)


@pytest.fixture
async def editor_role(async_session: AsyncSession):
    """Create an Editor role."""
    role_data = RoleCreate(name="EditorComp", description="Can edit")
    return await create_role(async_session, role_data)


@pytest.fixture
async def owner_role(async_session: AsyncSession):
    """Create an Owner role."""
    role_data = RoleCreate(name="OwnerComp", description="Full control")
    return await create_role(async_session, role_data)


@pytest.fixture
async def flow_read_permission(async_session: AsyncSession):
    """Create Read permission for Flow scope."""
    perm_data = PermissionCreate(name="ReadComp", scope="Flow", description="Read flow")
    return await create_permission(async_session, perm_data)


@pytest.fixture
async def flow_update_permission(async_session: AsyncSession):
    """Create Update permission for Flow scope."""
    perm_data = PermissionCreate(name="UpdateComp", scope="Flow", description="Update flow")
    return await create_permission(async_session, perm_data)


@pytest.fixture
async def flow_delete_permission(async_session: AsyncSession):
    """Create Delete permission for Flow scope."""
    perm_data = PermissionCreate(name="DeleteComp", scope="Flow", description="Delete flow")
    return await create_permission(async_session, perm_data)


@pytest.fixture
async def project_read_permission(async_session: AsyncSession):
    """Create Read permission for Project scope."""
    perm_data = PermissionCreate(name="ReadCompProj", scope="Project", description="Read project")
    return await create_permission(async_session, perm_data)


@pytest.fixture
async def test_folder(async_session: AsyncSession, test_user):
    """Create a test folder (project)."""
    folder = Folder(
        name="Test Comprehensive Project",
        user_id=test_user.id,
    )
    async_session.add(folder)
    await async_session.commit()
    await async_session.refresh(folder)
    return folder


@pytest.fixture
async def test_flow_with_folder(async_session: AsyncSession, test_user, test_folder):
    """Create a test flow with a folder."""
    flow = Flow(
        name="Test Comprehensive Flow",
        user_id=test_user.id,
        folder_id=test_folder.id,
        data={},
    )
    async_session.add(flow)
    await async_session.commit()
    await async_session.refresh(flow)
    return flow


@pytest.fixture
async def test_flow_without_folder(async_session: AsyncSession, test_user):
    """Create a test flow without a folder."""
    flow = Flow(
        name="Test Orphan Flow",
        user_id=test_user.id,
        folder_id=None,
        data={},
    )
    async_session.add(flow)
    await async_session.commit()
    await async_session.refresh(flow)
    return flow


# Test edge case: Flow without folder (no inheritance possible)


@pytest.mark.asyncio
async def test_can_access_flow_without_folder_no_inheritance(
    rbac_service, async_session, test_user, viewer_role, test_flow_without_folder, flow_read_permission
):
    """Test that a Flow without folder_id does not inherit any permissions."""
    # Link permission to role
    role_perm = RolePermission(role_id=viewer_role.id, permission_id=flow_read_permission.id)
    async_session.add(role_perm)
    await async_session.commit()

    # Assign role at Project level (but flow has no folder)
    assignment = UserRoleAssignment(
        user_id=test_user.id,
        role_id=viewer_role.id,
        scope_type="Project",
        scope_id=uuid4(),  # Random project that doesn't exist
        created_by=test_user.id,
    )
    async_session.add(assignment)
    await async_session.commit()

    # Check Flow permission (should NOT inherit because flow.folder_id is None)
    result = await rbac_service.can_access(
        user_id=test_user.id,
        permission_name="ReadComp",
        scope_type="Flow",
        scope_id=test_flow_without_folder.id,
        db=async_session,
    )
    assert result is False


# Test explicit Flow role overrides Project role


@pytest.mark.asyncio
async def test_explicit_flow_role_overrides_project_inheritance(
    rbac_service,
    async_session,
    test_user,
    viewer_role,
    editor_role,
    test_flow_with_folder,
    test_folder,
    flow_read_permission,
    flow_update_permission,
):
    """Test that explicit Flow-level role takes precedence over inherited Project-level role."""
    # Link permissions to roles
    viewer_perm = RolePermission(role_id=viewer_role.id, permission_id=flow_read_permission.id)
    editor_perm_read = RolePermission(role_id=editor_role.id, permission_id=flow_read_permission.id)
    editor_perm_update = RolePermission(role_id=editor_role.id, permission_id=flow_update_permission.id)
    async_session.add_all([viewer_perm, editor_perm_read, editor_perm_update])
    await async_session.commit()

    # Assign Editor role at Project level
    project_assignment = UserRoleAssignment(
        user_id=test_user.id,
        role_id=editor_role.id,
        scope_type="Project",
        scope_id=test_folder.id,
        created_by=test_user.id,
    )
    async_session.add(project_assignment)
    await async_session.commit()

    # Assign Viewer role at Flow level (explicit override)
    flow_assignment = UserRoleAssignment(
        user_id=test_user.id,
        role_id=viewer_role.id,
        scope_type="Flow",
        scope_id=test_flow_with_folder.id,
        created_by=test_user.id,
    )
    async_session.add(flow_assignment)
    await async_session.commit()

    # Check permissions: should have Viewer permissions (Read only), not Editor
    read_result = await rbac_service.can_access(
        user_id=test_user.id,
        permission_name="ReadComp",
        scope_type="Flow",
        scope_id=test_flow_with_folder.id,
        db=async_session,
    )
    assert read_result is True

    # Should NOT have Update permission (Viewer doesn't have it)
    update_result = await rbac_service.can_access(
        user_id=test_user.id,
        permission_name="UpdateComp",
        scope_type="Flow",
        scope_id=test_flow_with_folder.id,
        db=async_session,
    )
    assert update_result is False


# Test multiple users with different roles on same resource


@pytest.mark.asyncio
async def test_multiple_users_different_roles_same_flow(
    rbac_service,
    async_session,
    test_user,
    second_user,
    viewer_role,
    editor_role,
    test_flow_with_folder,
    flow_read_permission,
    flow_update_permission,
):
    """Test that different users can have different roles on the same Flow."""
    # Link permissions to roles
    viewer_perm = RolePermission(role_id=viewer_role.id, permission_id=flow_read_permission.id)
    editor_perm_read = RolePermission(role_id=editor_role.id, permission_id=flow_read_permission.id)
    editor_perm_update = RolePermission(role_id=editor_role.id, permission_id=flow_update_permission.id)
    async_session.add_all([viewer_perm, editor_perm_read, editor_perm_update])
    await async_session.commit()

    # Assign Viewer role to test_user
    viewer_assignment = UserRoleAssignment(
        user_id=test_user.id,
        role_id=viewer_role.id,
        scope_type="Flow",
        scope_id=test_flow_with_folder.id,
        created_by=test_user.id,
    )
    async_session.add(viewer_assignment)
    await async_session.commit()

    # Assign Editor role to second_user
    editor_assignment = UserRoleAssignment(
        user_id=second_user.id,
        role_id=editor_role.id,
        scope_type="Flow",
        scope_id=test_flow_with_folder.id,
        created_by=second_user.id,
    )
    async_session.add(editor_assignment)
    await async_session.commit()

    # test_user should have Read but not Update
    test_user_read = await rbac_service.can_access(
        user_id=test_user.id,
        permission_name="ReadComp",
        scope_type="Flow",
        scope_id=test_flow_with_folder.id,
        db=async_session,
    )
    assert test_user_read is True

    test_user_update = await rbac_service.can_access(
        user_id=test_user.id,
        permission_name="UpdateComp",
        scope_type="Flow",
        scope_id=test_flow_with_folder.id,
        db=async_session,
    )
    assert test_user_update is False

    # second_user should have both Read and Update
    second_user_read = await rbac_service.can_access(
        user_id=second_user.id,
        permission_name="ReadComp",
        scope_type="Flow",
        scope_id=test_flow_with_folder.id,
        db=async_session,
    )
    assert second_user_read is True

    second_user_update = await rbac_service.can_access(
        user_id=second_user.id,
        permission_name="UpdateComp",
        scope_type="Flow",
        scope_id=test_flow_with_folder.id,
        db=async_session,
    )
    assert second_user_update is True


# Test Project-level permissions for Project scope


@pytest.mark.asyncio
async def test_project_level_permission_check(
    rbac_service, async_session, test_user, viewer_role, test_folder, project_read_permission
):
    """Test permission check directly at Project scope."""
    # Link permission to role
    role_perm = RolePermission(role_id=viewer_role.id, permission_id=project_read_permission.id)
    async_session.add(role_perm)
    await async_session.commit()

    # Assign role at Project level
    assignment = UserRoleAssignment(
        user_id=test_user.id,
        role_id=viewer_role.id,
        scope_type="Project",
        scope_id=test_folder.id,
        created_by=test_user.id,
    )
    async_session.add(assignment)
    await async_session.commit()

    # Check Project permission
    result = await rbac_service.can_access(
        user_id=test_user.id,
        permission_name="ReadCompProj",
        scope_type="Project",
        scope_id=test_folder.id,
        db=async_session,
    )
    assert result is True


# Test list_user_assignments with role relationship loaded


@pytest.mark.asyncio
async def test_list_user_assignments_loads_role_relationship(
    rbac_service, async_session, test_user, viewer_role, test_folder
):
    """Test that list_user_assignments loads role relationship correctly."""
    # Create assignment
    await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="ViewerComp",
        scope_type="Project",
        scope_id=test_folder.id,
        created_by=test_user.id,
        db=async_session,
    )

    # Get assignments
    assignments = await rbac_service.list_user_assignments(user_id=test_user.id, db=async_session)

    # Verify role relationship is loaded
    assert len(assignments) == 1
    assert assignments[0].role is not None
    assert assignments[0].role.name == "ViewerComp"
    assert assignments[0].role.id == viewer_role.id


# Test get_user_permissions_for_scope returns correct permissions


@pytest.mark.asyncio
async def test_get_user_permissions_returns_all_role_permissions(
    rbac_service,
    async_session,
    test_user,
    editor_role,
    test_flow_with_folder,
    flow_read_permission,
    flow_update_permission,
    flow_delete_permission,  # noqa: ARG001
):
    """Test that get_user_permissions_for_scope returns all permissions for the role."""
    # Link multiple permissions to editor role
    role_perm1 = RolePermission(role_id=editor_role.id, permission_id=flow_read_permission.id)
    role_perm2 = RolePermission(role_id=editor_role.id, permission_id=flow_update_permission.id)
    async_session.add_all([role_perm1, role_perm2])
    await async_session.commit()

    # Assign role
    assignment = UserRoleAssignment(
        user_id=test_user.id,
        role_id=editor_role.id,
        scope_type="Flow",
        scope_id=test_flow_with_folder.id,
        created_by=test_user.id,
    )
    async_session.add(assignment)
    await async_session.commit()

    # Get permissions
    permissions = await rbac_service.get_user_permissions_for_scope(
        user_id=test_user.id,
        scope_type="Flow",
        scope_id=test_flow_with_folder.id,
        db=async_session,
    )

    # Should have exactly 2 permissions (Read and Update)
    assert len(permissions) == 2
    permission_names = {p.name for p in permissions}
    assert "ReadComp" in permission_names
    assert "UpdateComp" in permission_names


# Test superuser with non-existent user ID still returns True


@pytest.mark.asyncio
async def test_superuser_bypass_even_with_no_roles(rbac_service, async_session):
    """Test that superuser bypasses checks even without any role assignments."""
    # Create superuser
    superuser = User(
        username="superuser_comprehensive",
        password=get_password_hash("password"),
        is_active=True,
        is_superuser=True,
    )
    async_session.add(superuser)
    await async_session.commit()
    await async_session.refresh(superuser)

    # Check permission without any role assignments
    result = await rbac_service.can_access(
        user_id=superuser.id,
        permission_name="NonExistentPermission",
        scope_type="Flow",
        scope_id=uuid4(),
        db=async_session,
    )
    assert result is True


# Test can_access with wrong scope type returns False


@pytest.mark.asyncio
async def test_can_access_wrong_scope_type_returns_false(
    rbac_service, async_session, test_user, viewer_role, test_flow_with_folder, flow_read_permission
):
    """Test that checking permission with wrong scope type returns False."""
    # Link permission to role (Flow scope)
    role_perm = RolePermission(role_id=viewer_role.id, permission_id=flow_read_permission.id)
    async_session.add(role_perm)
    await async_session.commit()

    # Assign role at Flow level
    assignment = UserRoleAssignment(
        user_id=test_user.id,
        role_id=viewer_role.id,
        scope_type="Flow",
        scope_id=test_flow_with_folder.id,
        created_by=test_user.id,
    )
    async_session.add(assignment)
    await async_session.commit()

    # Check permission but with Project scope instead of Flow
    result = await rbac_service.can_access(
        user_id=test_user.id,
        permission_name="ReadComp",
        scope_type="Project",
        scope_id=test_flow_with_folder.id,
        db=async_session,
    )
    assert result is False


# Test list_user_assignments when user has no assignments


@pytest.mark.asyncio
async def test_list_user_assignments_empty_for_new_user(rbac_service, async_session, test_user):
    """Test that list_user_assignments returns empty list for user with no assignments."""
    assignments = await rbac_service.list_user_assignments(user_id=test_user.id, db=async_session)
    assert len(assignments) == 0
