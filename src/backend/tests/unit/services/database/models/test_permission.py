import pytest
from fastapi import HTTPException
from langbuilder.services.database.models.permission.crud import (
    create_permission,
    delete_permission,
    get_permission_by_id,
    get_permission_by_name_and_scope,
    list_permissions,
    list_permissions_by_scope,
    update_permission,
)
from langbuilder.services.database.models.permission.model import PermissionCreate, PermissionUpdate
from sqlmodel.ext.asyncio.session import AsyncSession


@pytest.mark.asyncio
async def test_create_permission(async_session: AsyncSession):
    """Test creating a new permission."""
    permission_data = PermissionCreate(name="Create", scope="Flow", description="Create flow permission")
    permission = await create_permission(async_session, permission_data)

    assert permission.id is not None
    assert permission.name == "Create"
    assert permission.scope == "Flow"
    assert permission.description == "Create flow permission"
    assert permission.created_at is not None


@pytest.mark.asyncio
async def test_create_duplicate_permission(async_session: AsyncSession):
    """Test creating a permission with duplicate name and scope fails."""
    permission_data = PermissionCreate(name="Create", scope="Flow", description="Create flow permission")
    await create_permission(async_session, permission_data)

    with pytest.raises(HTTPException) as exc_info:
        await create_permission(async_session, permission_data)

    assert exc_info.value.status_code == 400
    assert "already exists" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_permission_same_name_different_scope(async_session: AsyncSession):
    """Test creating permissions with same name but different scopes."""
    permission_data_1 = PermissionCreate(name="Create", scope="Flow")
    permission_data_2 = PermissionCreate(name="Create", scope="Project")

    permission_1 = await create_permission(async_session, permission_data_1)
    permission_2 = await create_permission(async_session, permission_data_2)

    assert permission_1.id != permission_2.id
    assert permission_1.name == permission_2.name
    assert permission_1.scope != permission_2.scope


@pytest.mark.asyncio
async def test_get_permission_by_id(async_session: AsyncSession):
    """Test getting a permission by ID."""
    permission_data = PermissionCreate(name="Read", scope="Flow", description="Read flow permission")
    created_permission = await create_permission(async_session, permission_data)

    permission = await get_permission_by_id(async_session, created_permission.id)

    assert permission is not None
    assert permission.id == created_permission.id
    assert permission.name == "Read"


@pytest.mark.asyncio
async def test_get_permission_by_id_not_found(async_session: AsyncSession):
    """Test getting a non-existent permission returns None."""
    from uuid import uuid4

    permission = await get_permission_by_id(async_session, uuid4())
    assert permission is None


@pytest.mark.asyncio
async def test_get_permission_by_name_and_scope(async_session: AsyncSession):
    """Test getting a permission by name and scope."""
    permission_data = PermissionCreate(name="Update", scope="Flow", description="Update flow permission")
    await create_permission(async_session, permission_data)

    permission = await get_permission_by_name_and_scope(async_session, "Update", "Flow")

    assert permission is not None
    assert permission.name == "Update"
    assert permission.scope == "Flow"


@pytest.mark.asyncio
async def test_get_permission_by_name_and_scope_not_found(async_session: AsyncSession):
    """Test getting a non-existent permission by name and scope returns None."""
    permission = await get_permission_by_name_and_scope(async_session, "NonExistent", "Flow")
    assert permission is None


@pytest.mark.asyncio
async def test_list_permissions(async_session: AsyncSession):
    """Test listing all permissions."""
    permission_data_1 = PermissionCreate(name="Create", scope="Flow")
    permission_data_2 = PermissionCreate(name="Read", scope="Flow")
    permission_data_3 = PermissionCreate(name="Create", scope="Project")

    await create_permission(async_session, permission_data_1)
    await create_permission(async_session, permission_data_2)
    await create_permission(async_session, permission_data_3)

    permissions = await list_permissions(async_session)

    assert len(permissions) == 3


@pytest.mark.asyncio
async def test_list_permissions_with_pagination(async_session: AsyncSession):
    """Test listing permissions with pagination."""
    for i in range(5):
        permission_data = PermissionCreate(name=f"Permission{i}", scope=f"Scope{i}")
        await create_permission(async_session, permission_data)

    permissions = await list_permissions(async_session, skip=2, limit=2)

    assert len(permissions) == 2


@pytest.mark.asyncio
async def test_list_permissions_by_scope(async_session: AsyncSession):
    """Test listing permissions by scope."""
    permission_data_1 = PermissionCreate(name="Create", scope="Flow")
    permission_data_2 = PermissionCreate(name="Read", scope="Flow")
    permission_data_3 = PermissionCreate(name="Create", scope="Project")

    await create_permission(async_session, permission_data_1)
    await create_permission(async_session, permission_data_2)
    await create_permission(async_session, permission_data_3)

    flow_permissions = await list_permissions_by_scope(async_session, "Flow")

    assert len(flow_permissions) == 2
    for permission in flow_permissions:
        assert permission.scope == "Flow"


@pytest.mark.asyncio
async def test_update_permission(async_session: AsyncSession):
    """Test updating a permission."""
    permission_data = PermissionCreate(name="Delete", scope="Flow", description="Delete flow permission")
    created_permission = await create_permission(async_session, permission_data)

    permission_update = PermissionUpdate(description="Updated delete flow permission")
    updated_permission = await update_permission(async_session, created_permission.id, permission_update)

    assert updated_permission.id == created_permission.id
    assert updated_permission.name == "Delete"
    assert updated_permission.description == "Updated delete flow permission"


@pytest.mark.asyncio
async def test_update_permission_not_found(async_session: AsyncSession):
    """Test updating a non-existent permission fails."""
    from uuid import uuid4

    permission_update = PermissionUpdate(description="Updated")

    with pytest.raises(HTTPException) as exc_info:
        await update_permission(async_session, uuid4(), permission_update)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_permission(async_session: AsyncSession):
    """Test deleting a permission."""
    permission_data = PermissionCreate(name="Execute", scope="Flow")
    created_permission = await create_permission(async_session, permission_data)

    result = await delete_permission(async_session, created_permission.id)

    assert result["detail"] == "Permission deleted successfully"

    deleted_permission = await get_permission_by_id(async_session, created_permission.id)
    assert deleted_permission is None


@pytest.mark.asyncio
async def test_delete_permission_not_found(async_session: AsyncSession):
    """Test deleting a non-existent permission fails."""
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc_info:
        await delete_permission(async_session, uuid4())

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_permission_model_defaults(async_session: AsyncSession):
    """Test permission model with default values."""
    permission_data = PermissionCreate(name="View", scope="Flow")
    permission = await create_permission(async_session, permission_data)

    assert permission.description is None
