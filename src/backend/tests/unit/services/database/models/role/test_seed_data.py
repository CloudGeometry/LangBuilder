"""Unit tests for RBAC seed data functionality."""

import pytest
from langbuilder.services.database.models.permission.crud import (
    get_permission_by_name_and_scope,
    list_permissions,
)
from langbuilder.services.database.models.role.crud import get_role_by_name, list_roles
from langbuilder.services.database.models.role.model import Role
from langbuilder.services.database.models.role.seed_data import (
    DEFAULT_PERMISSIONS,
    DEFAULT_ROLES,
    ROLE_PERMISSION_MAPPINGS,
    seed_rbac_data,
)
from langbuilder.services.database.models.role_permission.model import RolePermission
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession


async def get_role_with_permissions(db: AsyncSession, role_name: str) -> Role | None:
    """Get a role by name with eagerly loaded permissions."""
    stmt = (
        select(Role)
        .where(Role.name == role_name)
        .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
    )
    result = await db.exec(stmt)
    return result.first()


@pytest.mark.asyncio
async def test_seed_rbac_data_creates_all_permissions(async_session: AsyncSession):
    """Test that seed_rbac_data creates all 8 default permissions."""
    result = await seed_rbac_data(async_session)

    assert result["permissions_created"] == 8, "Should create 8 permissions"

    # Verify all permissions exist
    permissions = await list_permissions(async_session)
    assert len(permissions) == 8, "Should have 8 permissions in database"

    # Verify permission names and scopes
    expected_perms = {(p["name"], p["scope"]) for p in DEFAULT_PERMISSIONS}
    actual_perms = {(p.name, p.scope) for p in permissions}
    assert expected_perms == actual_perms, "All default permissions should be created"


@pytest.mark.asyncio
async def test_seed_rbac_data_creates_all_roles(async_session: AsyncSession):
    """Test that seed_rbac_data creates all 4 default roles."""
    result = await seed_rbac_data(async_session)

    assert result["roles_created"] == 4, "Should create 4 roles"

    # Verify all roles exist
    roles = await list_roles(async_session)
    assert len(roles) == 4, "Should have 4 roles in database"

    # Verify role names
    expected_names = {r["name"] for r in DEFAULT_ROLES}
    actual_names = {r.name for r in roles}
    assert expected_names == actual_names, "All default roles should be created"


@pytest.mark.asyncio
async def test_seed_rbac_data_all_roles_are_system_roles(async_session: AsyncSession):
    """Test that all seeded roles have is_system_role=True."""
    await seed_rbac_data(async_session)

    roles = await list_roles(async_session)
    for role in roles:
        assert role.is_system_role is True, f"Role {role.name} should be a system role"


@pytest.mark.asyncio
async def test_seed_rbac_data_creates_role_permission_mappings(async_session: AsyncSession):
    """Test that seed_rbac_data creates all role-permission mappings."""
    result = await seed_rbac_data(async_session)

    # Should create mappings for all 4 roles
    total_expected_mappings = sum(len(perms) for perms in ROLE_PERMISSION_MAPPINGS.values())
    assert result["mappings_created"] == total_expected_mappings, f"Should create {total_expected_mappings} mappings"

    # Verify each role has correct permissions
    viewer = await get_role_with_permissions(async_session, "Viewer")
    assert viewer is not None
    assert len(viewer.role_permissions) == 2, "Viewer should have 2 permissions"

    editor = await get_role_with_permissions(async_session, "Editor")
    assert editor is not None
    assert len(editor.role_permissions) == 6, "Editor should have 6 permissions"

    owner = await get_role_with_permissions(async_session, "Owner")
    assert owner is not None
    assert len(owner.role_permissions) == 8, "Owner should have 8 permissions"

    admin = await get_role_with_permissions(async_session, "Admin")
    assert admin is not None
    assert len(admin.role_permissions) == 8, "Admin should have 8 permissions"


@pytest.mark.asyncio
async def test_seed_rbac_data_viewer_has_read_only_permissions(async_session: AsyncSession):
    """Test that Viewer role has only Read permissions."""
    await seed_rbac_data(async_session)

    viewer = await get_role_with_permissions(async_session, "Viewer")
    assert viewer is not None

    permission_names = {rp.permission.name for rp in viewer.role_permissions}
    assert permission_names == {"Read"}, "Viewer should only have Read permissions"

    permission_scopes = {rp.permission.scope for rp in viewer.role_permissions}
    assert permission_scopes == {"Flow", "Project"}, "Viewer should have Read for both Flow and Project"


@pytest.mark.asyncio
async def test_seed_rbac_data_editor_has_cru_permissions(async_session: AsyncSession):
    """Test that Editor role has Create, Read, Update permissions (no Delete)."""
    await seed_rbac_data(async_session)

    editor = await get_role_with_permissions(async_session, "Editor")
    assert editor is not None

    permission_names = {rp.permission.name for rp in editor.role_permissions}
    assert permission_names == {"Create", "Read", "Update"}, "Editor should have Create, Read, Update permissions"
    assert "Delete" not in permission_names, "Editor should not have Delete permission"


@pytest.mark.asyncio
async def test_seed_rbac_data_owner_has_all_permissions(async_session: AsyncSession):
    """Test that Owner role has all CRUD permissions."""
    await seed_rbac_data(async_session)

    owner = await get_role_with_permissions(async_session, "Owner")
    assert owner is not None

    permission_names = {rp.permission.name for rp in owner.role_permissions}
    assert permission_names == {
        "Create",
        "Read",
        "Update",
        "Delete",
    }, "Owner should have all CRUD permissions"

    # Verify both scopes
    permission_scopes = {rp.permission.scope for rp in owner.role_permissions}
    assert permission_scopes == {"Flow", "Project"}, "Owner should have permissions for both scopes"


@pytest.mark.asyncio
async def test_seed_rbac_data_admin_has_all_permissions(async_session: AsyncSession):
    """Test that Admin role has all CRUD permissions."""
    await seed_rbac_data(async_session)

    admin = await get_role_with_permissions(async_session, "Admin")
    assert admin is not None

    permission_names = {rp.permission.name for rp in admin.role_permissions}
    assert permission_names == {
        "Create",
        "Read",
        "Update",
        "Delete",
    }, "Admin should have all CRUD permissions"

    # Verify both scopes
    permission_scopes = {rp.permission.scope for rp in admin.role_permissions}
    assert permission_scopes == {"Flow", "Project"}, "Admin should have permissions for both scopes"


@pytest.mark.asyncio
async def test_seed_rbac_data_is_idempotent(async_session: AsyncSession):
    """Test that seed_rbac_data can be run multiple times safely."""
    # First run - should create everything
    result1 = await seed_rbac_data(async_session)
    assert result1["permissions_created"] == 8
    assert result1["roles_created"] == 4
    assert result1["mappings_created"] > 0

    # Second run - should not create anything (idempotent)
    result2 = await seed_rbac_data(async_session)
    assert result2["permissions_created"] == 0, "Should not create duplicate permissions"
    assert result2["roles_created"] == 0, "Should not create duplicate roles"
    assert result2["mappings_created"] == 0, "Should not create duplicate mappings"

    # Verify counts are still correct
    permissions = await list_permissions(async_session)
    assert len(permissions) == 8, "Should still have exactly 8 permissions"

    roles = await list_roles(async_session)
    assert len(roles) == 4, "Should still have exactly 4 roles"


@pytest.mark.asyncio
async def test_seed_rbac_data_permissions_have_descriptions(async_session: AsyncSession):
    """Test that all seeded permissions have descriptions."""
    await seed_rbac_data(async_session)

    permissions = await list_permissions(async_session)
    for perm in permissions:
        assert perm.description is not None, f"Permission {perm.name}:{perm.scope} should have a description"
        assert len(perm.description) > 0, f"Permission {perm.name}:{perm.scope} description should not be empty"


@pytest.mark.asyncio
async def test_seed_rbac_data_roles_have_descriptions(async_session: AsyncSession):
    """Test that all seeded roles have descriptions."""
    await seed_rbac_data(async_session)

    roles = await list_roles(async_session)
    for role in roles:
        assert role.description is not None, f"Role {role.name} should have a description"
        assert len(role.description) > 0, f"Role {role.name} description should not be empty"


@pytest.mark.asyncio
async def test_seed_rbac_data_permission_unique_constraint(async_session: AsyncSession):
    """Test that permissions are unique by (name, scope) combination."""
    await seed_rbac_data(async_session)

    # Verify we can get specific permissions
    create_flow = await get_permission_by_name_and_scope(async_session, "Create", "Flow")
    assert create_flow is not None
    assert create_flow.name == "Create"
    assert create_flow.scope == "Flow"

    create_project = await get_permission_by_name_and_scope(async_session, "Create", "Project")
    assert create_project is not None
    assert create_project.name == "Create"
    assert create_project.scope == "Project"

    # These should be different permissions
    assert create_flow.id != create_project.id, "Create Flow and Create Project should be different permissions"


@pytest.mark.asyncio
async def test_seed_rbac_data_returns_correct_counts(async_session: AsyncSession):
    """Test that seed_rbac_data returns accurate counts."""
    result = await seed_rbac_data(async_session)

    # Verify the result structure
    assert "permissions_created" in result
    assert "roles_created" in result
    assert "mappings_created" in result

    # Verify counts match actual data
    permissions = await list_permissions(async_session)
    assert len(permissions) == result["permissions_created"]

    roles = await list_roles(async_session)
    assert len(roles) == result["roles_created"]


@pytest.mark.asyncio
async def test_seed_rbac_data_partial_seeding(async_session: AsyncSession):
    """Test that seeding works correctly when some data already exists."""
    # Pre-create one permission
    from langbuilder.services.database.models.permission.crud import create_permission
    from langbuilder.services.database.models.permission.model import PermissionCreate

    await create_permission(
        async_session, PermissionCreate(name="Read", scope="Flow", description="Pre-existing permission")
    )

    # Now run seed - should create remaining permissions
    result = await seed_rbac_data(async_session)

    assert result["permissions_created"] == 7, "Should create 7 new permissions (1 already exists)"
    assert result["roles_created"] == 4, "Should create all 4 roles"

    # Verify total is correct
    permissions = await list_permissions(async_session)
    assert len(permissions) == 8, "Should have 8 total permissions"


@pytest.mark.asyncio
async def test_seed_rbac_data_all_permissions_created(async_session: AsyncSession):
    """Test that all expected permissions from DEFAULT_PERMISSIONS are created."""
    await seed_rbac_data(async_session)

    for perm_data in DEFAULT_PERMISSIONS:
        perm = await get_permission_by_name_and_scope(async_session, perm_data["name"], perm_data["scope"])
        assert perm is not None, f"Permission {perm_data['name']}:{perm_data['scope']} should exist"
        assert perm.description == perm_data["description"], "Permission description should match"


@pytest.mark.asyncio
async def test_seed_rbac_data_all_roles_created(async_session: AsyncSession):
    """Test that all expected roles from DEFAULT_ROLES are created."""
    await seed_rbac_data(async_session)

    for role_data in DEFAULT_ROLES:
        role = await get_role_by_name(async_session, role_data["name"])
        assert role is not None, f"Role {role_data['name']} should exist"
        assert role.description == role_data["description"], "Role description should match"
        assert role.is_system_role == role_data["is_system_role"], "Role system flag should match"


@pytest.mark.asyncio
async def test_seed_rbac_data_role_permission_relationships(async_session: AsyncSession):
    """Test that role-permission relationships are correctly established."""
    await seed_rbac_data(async_session)

    for role_name, perm_list in ROLE_PERMISSION_MAPPINGS.items():
        role = await get_role_with_permissions(async_session, role_name)
        assert role is not None, f"Role {role_name} should exist"

        # Get actual permission names from role
        actual_perms = {(rp.permission.name, rp.permission.scope) for rp in role.role_permissions}
        expected_perms = set(perm_list)

        assert (
            actual_perms == expected_perms
        ), f"Role {role_name} should have exact permission set: expected {expected_perms}, got {actual_perms}"
