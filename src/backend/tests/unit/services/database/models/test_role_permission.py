import pytest
from fastapi import HTTPException
from langbuilder.services.database.models.permission.crud import create_permission
from langbuilder.services.database.models.permission.model import PermissionCreate
from langbuilder.services.database.models.role.crud import create_role
from langbuilder.services.database.models.role.model import RoleCreate
from langbuilder.services.database.models.role_permission.crud import (
    create_role_permission,
    delete_role_permission,
    delete_role_permission_by_ids,
    get_role_permission,
    get_role_permission_by_id,
    list_permissions_by_role,
    list_role_permissions,
    list_roles_by_permission,
    update_role_permission,
)
from langbuilder.services.database.models.role_permission.model import (
    RolePermissionCreate,
    RolePermissionUpdate,
)
from sqlmodel.ext.asyncio.session import AsyncSession


@pytest.mark.asyncio
async def test_create_role_permission(async_session: AsyncSession):
    """Test creating a new role-permission association."""
    role_data = RoleCreate(name="Admin")
    role = await create_role(async_session, role_data)

    permission_data = PermissionCreate(name="Create", scope="Flow")
    permission = await create_permission(async_session, permission_data)

    role_permission_data = RolePermissionCreate(role_id=role.id, permission_id=permission.id)
    role_permission = await create_role_permission(async_session, role_permission_data)

    assert role_permission.id is not None
    assert role_permission.role_id == role.id
    assert role_permission.permission_id == permission.id
    assert role_permission.created_at is not None


@pytest.mark.asyncio
async def test_create_duplicate_role_permission(async_session: AsyncSession):
    """Test creating a duplicate role-permission association fails."""
    role_data = RoleCreate(name="Admin")
    role = await create_role(async_session, role_data)

    permission_data = PermissionCreate(name="Create", scope="Flow")
    permission = await create_permission(async_session, permission_data)

    role_permission_data = RolePermissionCreate(role_id=role.id, permission_id=permission.id)
    await create_role_permission(async_session, role_permission_data)

    with pytest.raises(HTTPException) as exc_info:
        await create_role_permission(async_session, role_permission_data)

    assert exc_info.value.status_code == 400
    assert "already exists" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_role_permission_by_id(async_session: AsyncSession):
    """Test getting a role-permission by ID."""
    role_data = RoleCreate(name="Editor")
    role = await create_role(async_session, role_data)

    permission_data = PermissionCreate(name="Read", scope="Flow")
    permission = await create_permission(async_session, permission_data)

    role_permission_data = RolePermissionCreate(role_id=role.id, permission_id=permission.id)
    created_role_permission = await create_role_permission(async_session, role_permission_data)

    role_permission = await get_role_permission_by_id(async_session, created_role_permission.id)

    assert role_permission is not None
    assert role_permission.id == created_role_permission.id


@pytest.mark.asyncio
async def test_get_role_permission_by_id_not_found(async_session: AsyncSession):
    """Test getting a non-existent role-permission returns None."""
    from uuid import uuid4

    role_permission = await get_role_permission_by_id(async_session, uuid4())
    assert role_permission is None


@pytest.mark.asyncio
async def test_get_role_permission(async_session: AsyncSession):
    """Test getting a role-permission by role_id and permission_id."""
    role_data = RoleCreate(name="Admin")
    role = await create_role(async_session, role_data)

    permission_data = PermissionCreate(name="Update", scope="Flow")
    permission = await create_permission(async_session, permission_data)

    role_permission_data = RolePermissionCreate(role_id=role.id, permission_id=permission.id)
    await create_role_permission(async_session, role_permission_data)

    role_permission = await get_role_permission(async_session, role.id, permission.id)

    assert role_permission is not None
    assert role_permission.role_id == role.id
    assert role_permission.permission_id == permission.id


@pytest.mark.asyncio
async def test_list_role_permissions(async_session: AsyncSession):
    """Test listing all role-permissions."""
    role_data_1 = RoleCreate(name="Admin")
    role_1 = await create_role(async_session, role_data_1)

    role_data_2 = RoleCreate(name="Editor")
    role_2 = await create_role(async_session, role_data_2)

    permission_data_1 = PermissionCreate(name="Create", scope="Flow")
    permission_1 = await create_permission(async_session, permission_data_1)

    permission_data_2 = PermissionCreate(name="Read", scope="Flow")
    permission_2 = await create_permission(async_session, permission_data_2)

    await create_role_permission(async_session, RolePermissionCreate(role_id=role_1.id, permission_id=permission_1.id))
    await create_role_permission(async_session, RolePermissionCreate(role_id=role_1.id, permission_id=permission_2.id))
    await create_role_permission(async_session, RolePermissionCreate(role_id=role_2.id, permission_id=permission_1.id))

    role_permissions = await list_role_permissions(async_session)

    assert len(role_permissions) == 3


@pytest.mark.asyncio
async def test_list_permissions_by_role(async_session: AsyncSession):
    """Test listing all permissions for a specific role."""
    role_data_1 = RoleCreate(name="Admin")
    role_1 = await create_role(async_session, role_data_1)

    role_data_2 = RoleCreate(name="Editor")
    role_2 = await create_role(async_session, role_data_2)

    permission_data_1 = PermissionCreate(name="Create", scope="Flow")
    permission_1 = await create_permission(async_session, permission_data_1)

    permission_data_2 = PermissionCreate(name="Read", scope="Flow")
    permission_2 = await create_permission(async_session, permission_data_2)

    await create_role_permission(async_session, RolePermissionCreate(role_id=role_1.id, permission_id=permission_1.id))
    await create_role_permission(async_session, RolePermissionCreate(role_id=role_1.id, permission_id=permission_2.id))
    await create_role_permission(async_session, RolePermissionCreate(role_id=role_2.id, permission_id=permission_1.id))

    role_1_permissions = await list_permissions_by_role(async_session, role_1.id)

    assert len(role_1_permissions) == 2
    for role_permission in role_1_permissions:
        assert role_permission.role_id == role_1.id


@pytest.mark.asyncio
async def test_list_roles_by_permission(async_session: AsyncSession):
    """Test listing all roles that have a specific permission."""
    role_data_1 = RoleCreate(name="Admin")
    role_1 = await create_role(async_session, role_data_1)

    role_data_2 = RoleCreate(name="Editor")
    role_2 = await create_role(async_session, role_data_2)

    permission_data_1 = PermissionCreate(name="Create", scope="Flow")
    permission_1 = await create_permission(async_session, permission_data_1)

    permission_data_2 = PermissionCreate(name="Read", scope="Flow")
    permission_2 = await create_permission(async_session, permission_data_2)

    await create_role_permission(async_session, RolePermissionCreate(role_id=role_1.id, permission_id=permission_1.id))
    await create_role_permission(async_session, RolePermissionCreate(role_id=role_1.id, permission_id=permission_2.id))
    await create_role_permission(async_session, RolePermissionCreate(role_id=role_2.id, permission_id=permission_1.id))

    roles_with_permission_1 = await list_roles_by_permission(async_session, permission_1.id)

    assert len(roles_with_permission_1) == 2
    for role_permission in roles_with_permission_1:
        assert role_permission.permission_id == permission_1.id


@pytest.mark.asyncio
async def test_update_role_permission(async_session: AsyncSession):
    """Test updating a role-permission."""
    role_data_1 = RoleCreate(name="Admin")
    role_1 = await create_role(async_session, role_data_1)

    role_data_2 = RoleCreate(name="Editor")
    role_2 = await create_role(async_session, role_data_2)

    permission_data = PermissionCreate(name="Create", scope="Flow")
    permission = await create_permission(async_session, permission_data)

    role_permission_data = RolePermissionCreate(role_id=role_1.id, permission_id=permission.id)
    created_role_permission = await create_role_permission(async_session, role_permission_data)

    role_permission_update = RolePermissionUpdate(role_id=role_2.id)
    updated_role_permission = await update_role_permission(
        async_session, created_role_permission.id, role_permission_update
    )

    assert updated_role_permission.id == created_role_permission.id
    assert updated_role_permission.role_id == role_2.id
    assert updated_role_permission.permission_id == permission.id


@pytest.mark.asyncio
async def test_update_role_permission_not_found(async_session: AsyncSession):
    """Test updating a non-existent role-permission fails."""
    from uuid import uuid4

    role_permission_update = RolePermissionUpdate()

    with pytest.raises(HTTPException) as exc_info:
        await update_role_permission(async_session, uuid4(), role_permission_update)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_role_permission(async_session: AsyncSession):
    """Test deleting a role-permission."""
    role_data = RoleCreate(name="Admin")
    role = await create_role(async_session, role_data)

    permission_data = PermissionCreate(name="Delete", scope="Flow")
    permission = await create_permission(async_session, permission_data)

    role_permission_data = RolePermissionCreate(role_id=role.id, permission_id=permission.id)
    created_role_permission = await create_role_permission(async_session, role_permission_data)

    result = await delete_role_permission(async_session, created_role_permission.id)

    assert result["detail"] == "Role-permission deleted successfully"

    deleted_role_permission = await get_role_permission_by_id(async_session, created_role_permission.id)
    assert deleted_role_permission is None


@pytest.mark.asyncio
async def test_delete_role_permission_not_found(async_session: AsyncSession):
    """Test deleting a non-existent role-permission fails."""
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc_info:
        await delete_role_permission(async_session, uuid4())

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_role_permission_by_ids(async_session: AsyncSession):
    """Test deleting a role-permission by role_id and permission_id."""
    role_data = RoleCreate(name="Admin")
    role = await create_role(async_session, role_data)

    permission_data = PermissionCreate(name="Execute", scope="Flow")
    permission = await create_permission(async_session, permission_data)

    role_permission_data = RolePermissionCreate(role_id=role.id, permission_id=permission.id)
    await create_role_permission(async_session, role_permission_data)

    result = await delete_role_permission_by_ids(async_session, role.id, permission.id)

    assert result["detail"] == "Role-permission deleted successfully"

    deleted_role_permission = await get_role_permission(async_session, role.id, permission.id)
    assert deleted_role_permission is None


@pytest.mark.asyncio
async def test_delete_role_permission_by_ids_not_found(async_session: AsyncSession):
    """Test deleting a non-existent role-permission by IDs fails."""
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc_info:
        await delete_role_permission_by_ids(async_session, uuid4(), uuid4())

    assert exc_info.value.status_code == 404
