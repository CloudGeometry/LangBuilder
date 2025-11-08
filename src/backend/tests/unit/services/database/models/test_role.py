import pytest
from fastapi import HTTPException
from langbuilder.services.database.models.role.crud import (
    create_role,
    delete_role,
    get_role_by_id,
    get_role_by_name,
    list_roles,
    update_role,
)
from langbuilder.services.database.models.role.model import RoleCreate, RoleUpdate
from sqlmodel.ext.asyncio.session import AsyncSession


@pytest.mark.asyncio
async def test_create_role(async_session: AsyncSession):
    """Test creating a new role."""
    role_data = RoleCreate(name="Admin", description="Administrator role", is_system_role=True)
    role = await create_role(async_session, role_data)

    assert role.id is not None
    assert role.name == "Admin"
    assert role.description == "Administrator role"
    assert role.is_system_role is True
    assert role.created_at is not None


@pytest.mark.asyncio
async def test_create_duplicate_role(async_session: AsyncSession):
    """Test creating a role with duplicate name fails."""
    role_data = RoleCreate(name="Admin", description="Administrator role")
    await create_role(async_session, role_data)

    with pytest.raises(HTTPException) as exc_info:
        await create_role(async_session, role_data)

    assert exc_info.value.status_code == 400
    assert "already exists" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_role_by_id(async_session: AsyncSession):
    """Test getting a role by ID."""
    role_data = RoleCreate(name="Editor", description="Editor role")
    created_role = await create_role(async_session, role_data)

    role = await get_role_by_id(async_session, created_role.id)

    assert role is not None
    assert role.id == created_role.id
    assert role.name == "Editor"


@pytest.mark.asyncio
async def test_get_role_by_id_not_found(async_session: AsyncSession):
    """Test getting a non-existent role returns None."""
    from uuid import uuid4

    role = await get_role_by_id(async_session, uuid4())
    assert role is None


@pytest.mark.asyncio
async def test_get_role_by_name(async_session: AsyncSession):
    """Test getting a role by name."""
    role_data = RoleCreate(name="Viewer", description="Viewer role")
    await create_role(async_session, role_data)

    role = await get_role_by_name(async_session, "Viewer")

    assert role is not None
    assert role.name == "Viewer"


@pytest.mark.asyncio
async def test_get_role_by_name_not_found(async_session: AsyncSession):
    """Test getting a non-existent role by name returns None."""
    role = await get_role_by_name(async_session, "NonExistent")
    assert role is None


@pytest.mark.asyncio
async def test_list_roles(async_session: AsyncSession):
    """Test listing all roles."""
    role_data_1 = RoleCreate(name="Admin", description="Administrator role")
    role_data_2 = RoleCreate(name="Editor", description="Editor role")
    role_data_3 = RoleCreate(name="Viewer", description="Viewer role")

    await create_role(async_session, role_data_1)
    await create_role(async_session, role_data_2)
    await create_role(async_session, role_data_3)

    roles = await list_roles(async_session)

    assert len(roles) == 3
    role_names = [role.name for role in roles]
    assert "Admin" in role_names
    assert "Editor" in role_names
    assert "Viewer" in role_names


@pytest.mark.asyncio
async def test_list_roles_with_pagination(async_session: AsyncSession):
    """Test listing roles with pagination."""
    for i in range(5):
        role_data = RoleCreate(name=f"Role{i}", description=f"Role {i}")
        await create_role(async_session, role_data)

    roles = await list_roles(async_session, skip=2, limit=2)

    assert len(roles) == 2


@pytest.mark.asyncio
async def test_update_role(async_session: AsyncSession):
    """Test updating a role."""
    role_data = RoleCreate(name="Admin", description="Administrator role")
    created_role = await create_role(async_session, role_data)

    role_update = RoleUpdate(description="Updated administrator role")
    updated_role = await update_role(async_session, created_role.id, role_update)

    assert updated_role.id == created_role.id
    assert updated_role.name == "Admin"
    assert updated_role.description == "Updated administrator role"


@pytest.mark.asyncio
async def test_update_role_not_found(async_session: AsyncSession):
    """Test updating a non-existent role fails."""
    from uuid import uuid4

    role_update = RoleUpdate(description="Updated")

    with pytest.raises(HTTPException) as exc_info:
        await update_role(async_session, uuid4(), role_update)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_system_role_flag_fails(async_session: AsyncSession):
    """Test that modifying system role flag is not allowed."""
    role_data = RoleCreate(name="Admin", description="Administrator role", is_system_role=True)
    created_role = await create_role(async_session, role_data)

    role_update = RoleUpdate(is_system_role=False)

    with pytest.raises(HTTPException) as exc_info:
        await update_role(async_session, created_role.id, role_update)

    assert exc_info.value.status_code == 400
    assert "system role" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_delete_role(async_session: AsyncSession):
    """Test deleting a role."""
    role_data = RoleCreate(name="Editor", description="Editor role")
    created_role = await create_role(async_session, role_data)

    result = await delete_role(async_session, created_role.id)

    assert result["detail"] == "Role deleted successfully"

    deleted_role = await get_role_by_id(async_session, created_role.id)
    assert deleted_role is None


@pytest.mark.asyncio
async def test_delete_role_not_found(async_session: AsyncSession):
    """Test deleting a non-existent role fails."""
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc_info:
        await delete_role(async_session, uuid4())

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_system_role_fails(async_session: AsyncSession):
    """Test that deleting a system role is not allowed."""
    role_data = RoleCreate(name="Admin", description="Administrator role", is_system_role=True)
    created_role = await create_role(async_session, role_data)

    with pytest.raises(HTTPException) as exc_info:
        await delete_role(async_session, created_role.id)

    assert exc_info.value.status_code == 400
    assert "system role" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_role_model_defaults(async_session: AsyncSession):
    """Test role model with default values."""
    role_data = RoleCreate(name="DefaultRole")
    role = await create_role(async_session, role_data)

    assert role.description is None
    assert role.is_system_role is False
