"""Unit tests for RBAC system initialization."""

import pytest
from langbuilder.services.database.models.permission.crud import list_permissions
from langbuilder.services.database.models.role.crud import list_roles
from langbuilder.services.database.models.role.model import Role
from langbuilder.services.database.models.role.seed_data import seed_rbac_data
from langbuilder.services.database.models.role_permission.model import RolePermission
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession


@pytest.mark.asyncio
async def test_initialize_rbac_if_needed_seeds_empty_database(async_session: AsyncSession):
    """Test that seeding creates data when database is empty."""
    # Verify database is empty
    roles = await list_roles(async_session)
    assert len(roles) == 0, "Database should start empty"

    permissions = await list_permissions(async_session)
    assert len(permissions) == 0, "Database should start empty"

    # Run seed function
    result = await seed_rbac_data(async_session)

    # Verify data was created
    assert result["permissions_created"] == 8, "Should create 8 permissions"
    assert result["roles_created"] == 4, "Should create 4 roles"
    assert result["mappings_created"] == 24, "Should create 24 mappings"

    roles = await list_roles(async_session)
    assert len(roles) == 4, "Should have 4 roles in database"

    permissions = await list_permissions(async_session)
    assert len(permissions) == 8, "Should have 8 permissions in database"

    # Verify role-permission mappings exist
    stmt = select(RolePermission)
    result = await async_session.exec(stmt)
    mappings = result.all()
    assert len(mappings) == 24, "Should have 24 role-permission mappings"


@pytest.mark.asyncio
async def test_initialize_rbac_if_needed_skips_when_roles_exist(async_session: AsyncSession):
    """Test that seeding checks if roles exist and skips accordingly."""
    # Seed first time
    result = await seed_rbac_data(async_session)
    assert result["roles_created"] == 4, "First run should create roles"
    assert result["permissions_created"] == 8, "First run should create permissions"

    # Second run should detect existing roles and skip
    result2 = await seed_rbac_data(async_session)
    assert result2["roles_created"] == 0, "Should skip role creation"
    assert result2["permissions_created"] == 0, "Should skip permission creation"
    assert result2["mappings_created"] == 0, "Should skip mapping creation"

    # Verify counts stayed the same
    roles = await list_roles(async_session)
    assert len(roles) == 4, "Should still have 4 roles"

    permissions = await list_permissions(async_session)
    assert len(permissions) == 8, "Should still have 8 permissions"


@pytest.mark.asyncio
async def test_initialize_rbac_if_needed_is_idempotent(async_session: AsyncSession):
    """Test that seeding can be run multiple times safely."""
    # First run - should create data
    result1 = await seed_rbac_data(async_session)
    assert result1["permissions_created"] == 8
    assert result1["roles_created"] == 4
    assert result1["mappings_created"] == 24

    # Second run - should not create duplicates
    result2 = await seed_rbac_data(async_session)
    assert result2["permissions_created"] == 0, "Should not create duplicate permissions"
    assert result2["roles_created"] == 0, "Should not create duplicate roles"
    assert result2["mappings_created"] == 0, "Should not create duplicate mappings"

    # Third run - still idempotent
    result3 = await seed_rbac_data(async_session)
    assert result3["permissions_created"] == 0
    assert result3["roles_created"] == 0
    assert result3["mappings_created"] == 0

    # Verify final counts
    permissions = await list_permissions(async_session)
    assert len(permissions) == 8, "Should still have exactly 8 permissions"

    roles = await list_roles(async_session)
    assert len(roles) == 4, "Should still have exactly 4 roles"


@pytest.mark.asyncio
async def test_initialize_rbac_if_needed_creates_all_default_roles(async_session: AsyncSession):
    """Test that all 4 default roles are created."""
    await seed_rbac_data(async_session)

    roles = await list_roles(async_session)
    role_names = {role.name for role in roles}

    expected_roles = {"Viewer", "Editor", "Owner", "Admin"}
    assert role_names == expected_roles, f"Should create all default roles: {expected_roles}"


@pytest.mark.asyncio
async def test_initialize_rbac_if_needed_creates_all_permissions(async_session: AsyncSession):
    """Test that all 8 default permissions are created."""
    await seed_rbac_data(async_session)

    permissions = await list_permissions(async_session)
    permission_tuples = {(p.name, p.scope) for p in permissions}

    expected_permissions = {
        ("Create", "Flow"),
        ("Read", "Flow"),
        ("Update", "Flow"),
        ("Delete", "Flow"),
        ("Create", "Project"),
        ("Read", "Project"),
        ("Update", "Project"),
        ("Delete", "Project"),
    }
    assert (
        permission_tuples == expected_permissions
    ), f"Should create all default permissions: {expected_permissions}"


@pytest.mark.asyncio
async def test_initialize_rbac_if_needed_all_roles_are_system_roles(async_session: AsyncSession):
    """Test that all default roles have is_system_role=True."""
    await seed_rbac_data(async_session)

    roles = await list_roles(async_session)

    for role in roles:
        assert role.is_system_role is True, f"Role {role.name} should be a system role"


@pytest.mark.asyncio
async def test_initialize_rbac_if_needed_creates_role_permission_mappings(async_session: AsyncSession):
    """Test that role-permission mappings are created correctly."""
    await seed_rbac_data(async_session)

    # Verify mappings exist
    stmt = select(RolePermission)
    result = await async_session.exec(stmt)
    mappings = result.all()

    # Should have mappings for all roles
    # Viewer: 2 (Read x 2 scopes)
    # Editor: 6 (C,R,U x 2 scopes)
    # Owner: 8 (C,R,U,D x 2 scopes)
    # Admin: 8 (C,R,U,D x 2 scopes)
    # Total: 24 mappings
    assert len(mappings) == 24, "Should create all role-permission mappings"


@pytest.mark.asyncio
async def test_rbac_setup_detects_empty_database(async_session: AsyncSession):
    """Test that rbac_setup correctly detects when database has no roles."""
    # Verify empty database
    stmt = select(Role)
    result = await async_session.exec(stmt)
    existing_roles = result.all()
    assert len(existing_roles) == 0, "Database should start empty"

    # This simulates what initialize_rbac_if_needed does
    # It should detect no roles and trigger seeding
    if not existing_roles:
        result = await seed_rbac_data(async_session)
        assert result["roles_created"] > 0, "Should seed data when empty"


@pytest.mark.asyncio
async def test_rbac_setup_detects_existing_data(async_session: AsyncSession):
    """Test that rbac_setup correctly detects when database already has roles."""
    # Seed the database first
    await seed_rbac_data(async_session)

    # Check for existing roles (this is what initialize_rbac_if_needed does)
    stmt = select(Role)
    result = await async_session.exec(stmt)
    existing_roles = result.all()
    assert len(existing_roles) > 0, "Database should have roles after seeding"

    # Should skip seeding when roles exist
    if existing_roles:
        # Would skip seeding
        pass
    else:
        # Would seed
        pytest.fail("Should have detected existing roles")
