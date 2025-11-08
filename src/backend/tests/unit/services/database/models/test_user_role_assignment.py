import pytest
from fastapi import HTTPException
from langbuilder.services.auth.utils import get_password_hash
from langbuilder.services.database.models.role.crud import create_role
from langbuilder.services.database.models.role.model import RoleCreate
from langbuilder.services.database.models.user.model import User
from langbuilder.services.database.models.user_role_assignment.crud import (
    create_user_role_assignment,
    delete_user_role_assignment,
    get_user_role_assignment,
    get_user_role_assignment_by_id,
    list_assignments_by_role,
    list_assignments_by_scope,
    list_assignments_by_user,
    list_user_role_assignments,
    update_user_role_assignment,
)
from langbuilder.services.database.models.user_role_assignment.model import (
    UserRoleAssignmentCreate,
    UserRoleAssignmentUpdate,
)
from sqlmodel.ext.asyncio.session import AsyncSession


@pytest.fixture
async def test_user(async_session: AsyncSession):
    """Create a test user."""
    user = User(
        username="testuser",
        password=get_password_hash("password"),
        is_active=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
async def test_user_2(async_session: AsyncSession):
    """Create a second test user."""
    user = User(
        username="testuser2",
        password=get_password_hash("password"),
        is_active=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_create_user_role_assignment(async_session: AsyncSession, test_user: User):
    """Test creating a new user role assignment."""
    role_data = RoleCreate(name="Admin")
    role = await create_role(async_session, role_data)

    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Global", scope_id=None
    )
    assignment = await create_user_role_assignment(async_session, assignment_data)

    assert assignment.id is not None
    assert assignment.user_id == test_user.id
    assert assignment.role_id == role.id
    assert assignment.scope_type == "Global"
    assert assignment.scope_id is None
    assert assignment.is_immutable is False
    assert assignment.created_at is not None


@pytest.mark.asyncio
async def test_create_user_role_assignment_with_scope(async_session: AsyncSession, test_user: User):
    """Test creating a user role assignment with scope."""
    from uuid import uuid4

    role_data = RoleCreate(name="Editor")
    role = await create_role(async_session, role_data)

    flow_id = uuid4()
    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Flow", scope_id=flow_id
    )
    assignment = await create_user_role_assignment(async_session, assignment_data)

    assert assignment.scope_type == "Flow"
    assert assignment.scope_id == flow_id


@pytest.mark.asyncio
async def test_create_duplicate_user_role_assignment(async_session: AsyncSession, test_user: User):
    """Test creating a duplicate user role assignment fails."""
    role_data = RoleCreate(name="Admin")
    role = await create_role(async_session, role_data)

    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Global", scope_id=None
    )
    await create_user_role_assignment(async_session, assignment_data)

    with pytest.raises(HTTPException) as exc_info:
        await create_user_role_assignment(async_session, assignment_data)

    assert exc_info.value.status_code == 400
    assert "already exists" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_immutable_assignment(async_session: AsyncSession, test_user: User):
    """Test creating an immutable user role assignment."""
    role_data = RoleCreate(name="Owner")
    role = await create_role(async_session, role_data)

    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Project", scope_id=None, is_immutable=True
    )
    assignment = await create_user_role_assignment(async_session, assignment_data)

    assert assignment.is_immutable is True


@pytest.mark.asyncio
async def test_get_user_role_assignment_by_id(async_session: AsyncSession, test_user: User):
    """Test getting a user role assignment by ID."""
    role_data = RoleCreate(name="Editor")
    role = await create_role(async_session, role_data)

    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Global", scope_id=None
    )
    created_assignment = await create_user_role_assignment(async_session, assignment_data)

    assignment = await get_user_role_assignment_by_id(async_session, created_assignment.id)

    assert assignment is not None
    assert assignment.id == created_assignment.id


@pytest.mark.asyncio
async def test_get_user_role_assignment_by_id_not_found(async_session: AsyncSession):
    """Test getting a non-existent user role assignment returns None."""
    from uuid import uuid4

    assignment = await get_user_role_assignment_by_id(async_session, uuid4())
    assert assignment is None


@pytest.mark.asyncio
async def test_get_user_role_assignment(async_session: AsyncSession, test_user: User):
    """Test getting a user role assignment by user_id, role_id, scope_type, and scope_id."""
    role_data = RoleCreate(name="Viewer")
    role = await create_role(async_session, role_data)

    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Global", scope_id=None
    )
    await create_user_role_assignment(async_session, assignment_data)

    assignment = await get_user_role_assignment(async_session, test_user.id, role.id, "Global", None)

    assert assignment is not None
    assert assignment.user_id == test_user.id
    assert assignment.role_id == role.id


@pytest.mark.asyncio
async def test_list_user_role_assignments(async_session: AsyncSession, test_user: User, test_user_2: User):
    """Test listing all user role assignments."""
    role_data_1 = RoleCreate(name="Admin")
    role_1 = await create_role(async_session, role_data_1)

    role_data_2 = RoleCreate(name="Editor")
    role_2 = await create_role(async_session, role_data_2)

    await create_user_role_assignment(
        async_session,
        UserRoleAssignmentCreate(user_id=test_user.id, role_id=role_1.id, scope_type="Global", scope_id=None),
    )
    await create_user_role_assignment(
        async_session,
        UserRoleAssignmentCreate(user_id=test_user.id, role_id=role_2.id, scope_type="Flow", scope_id=None),
    )
    await create_user_role_assignment(
        async_session,
        UserRoleAssignmentCreate(user_id=test_user_2.id, role_id=role_1.id, scope_type="Global", scope_id=None),
    )

    assignments = await list_user_role_assignments(async_session)

    assert len(assignments) == 3


@pytest.mark.asyncio
async def test_list_assignments_by_user(async_session: AsyncSession, test_user: User, test_user_2: User):
    """Test listing all role assignments for a specific user."""
    role_data_1 = RoleCreate(name="Admin")
    role_1 = await create_role(async_session, role_data_1)

    role_data_2 = RoleCreate(name="Editor")
    role_2 = await create_role(async_session, role_data_2)

    await create_user_role_assignment(
        async_session,
        UserRoleAssignmentCreate(user_id=test_user.id, role_id=role_1.id, scope_type="Global", scope_id=None),
    )
    await create_user_role_assignment(
        async_session,
        UserRoleAssignmentCreate(user_id=test_user.id, role_id=role_2.id, scope_type="Flow", scope_id=None),
    )
    await create_user_role_assignment(
        async_session,
        UserRoleAssignmentCreate(user_id=test_user_2.id, role_id=role_1.id, scope_type="Global", scope_id=None),
    )

    user_assignments = await list_assignments_by_user(async_session, test_user.id)

    assert len(user_assignments) == 2
    for assignment in user_assignments:
        assert assignment.user_id == test_user.id


@pytest.mark.asyncio
async def test_list_assignments_by_role(async_session: AsyncSession, test_user: User, test_user_2: User):
    """Test listing all user assignments for a specific role."""
    role_data_1 = RoleCreate(name="Admin")
    role_1 = await create_role(async_session, role_data_1)

    role_data_2 = RoleCreate(name="Editor")
    role_2 = await create_role(async_session, role_data_2)

    await create_user_role_assignment(
        async_session,
        UserRoleAssignmentCreate(user_id=test_user.id, role_id=role_1.id, scope_type="Global", scope_id=None),
    )
    await create_user_role_assignment(
        async_session,
        UserRoleAssignmentCreate(user_id=test_user.id, role_id=role_2.id, scope_type="Flow", scope_id=None),
    )
    await create_user_role_assignment(
        async_session,
        UserRoleAssignmentCreate(user_id=test_user_2.id, role_id=role_1.id, scope_type="Global", scope_id=None),
    )

    role_assignments = await list_assignments_by_role(async_session, role_1.id)

    assert len(role_assignments) == 2
    for assignment in role_assignments:
        assert assignment.role_id == role_1.id


@pytest.mark.asyncio
async def test_list_assignments_by_scope(async_session: AsyncSession, test_user: User, test_user_2: User):
    """Test listing all user role assignments for a specific scope."""
    from uuid import uuid4

    role_data = RoleCreate(name="Admin")
    role = await create_role(async_session, role_data)

    flow_id = uuid4()

    await create_user_role_assignment(
        async_session,
        UserRoleAssignmentCreate(user_id=test_user.id, role_id=role.id, scope_type="Global", scope_id=None),
    )
    await create_user_role_assignment(
        async_session,
        UserRoleAssignmentCreate(user_id=test_user.id, role_id=role.id, scope_type="Flow", scope_id=flow_id),
    )
    await create_user_role_assignment(
        async_session,
        UserRoleAssignmentCreate(user_id=test_user_2.id, role_id=role.id, scope_type="Flow", scope_id=flow_id),
    )

    flow_assignments = await list_assignments_by_scope(async_session, "Flow", flow_id)

    assert len(flow_assignments) == 2
    for assignment in flow_assignments:
        assert assignment.scope_type == "Flow"
        assert assignment.scope_id == flow_id


@pytest.mark.asyncio
async def test_update_user_role_assignment(async_session: AsyncSession, test_user: User):
    """Test updating a user role assignment."""
    role_data_1 = RoleCreate(name="Editor")
    role_1 = await create_role(async_session, role_data_1)

    role_data_2 = RoleCreate(name="Viewer")
    role_2 = await create_role(async_session, role_data_2)

    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role_1.id, scope_type="Global", scope_id=None
    )
    created_assignment = await create_user_role_assignment(async_session, assignment_data)

    assignment_update = UserRoleAssignmentUpdate(role_id=role_2.id)
    updated_assignment = await update_user_role_assignment(async_session, created_assignment.id, assignment_update)

    assert updated_assignment.id == created_assignment.id
    assert updated_assignment.role_id == role_2.id


@pytest.mark.asyncio
async def test_update_user_role_assignment_not_found(async_session: AsyncSession):
    """Test updating a non-existent user role assignment fails."""
    from uuid import uuid4

    assignment_update = UserRoleAssignmentUpdate()

    with pytest.raises(HTTPException) as exc_info:
        await update_user_role_assignment(async_session, uuid4(), assignment_update)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_immutable_assignment_fails(async_session: AsyncSession, test_user: User):
    """Test that updating an immutable assignment is not allowed."""
    role_data = RoleCreate(name="Owner")
    role = await create_role(async_session, role_data)

    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Project", scope_id=None, is_immutable=True
    )
    created_assignment = await create_user_role_assignment(async_session, assignment_data)

    assignment_update = UserRoleAssignmentUpdate(scope_type="Global")

    with pytest.raises(HTTPException) as exc_info:
        await update_user_role_assignment(async_session, created_assignment.id, assignment_update)

    assert exc_info.value.status_code == 400
    assert "immutable" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_delete_user_role_assignment(async_session: AsyncSession, test_user: User):
    """Test deleting a user role assignment."""
    role_data = RoleCreate(name="Editor")
    role = await create_role(async_session, role_data)

    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Global", scope_id=None
    )
    created_assignment = await create_user_role_assignment(async_session, assignment_data)

    result = await delete_user_role_assignment(async_session, created_assignment.id)

    assert result["detail"] == "User role assignment deleted successfully"

    deleted_assignment = await get_user_role_assignment_by_id(async_session, created_assignment.id)
    assert deleted_assignment is None


@pytest.mark.asyncio
async def test_delete_user_role_assignment_not_found(async_session: AsyncSession):
    """Test deleting a non-existent user role assignment fails."""
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc_info:
        await delete_user_role_assignment(async_session, uuid4())

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_immutable_assignment_fails(async_session: AsyncSession, test_user: User):
    """Test that deleting an immutable assignment is not allowed."""
    role_data = RoleCreate(name="Owner")
    role = await create_role(async_session, role_data)

    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Project", scope_id=None, is_immutable=True
    )
    created_assignment = await create_user_role_assignment(async_session, assignment_data)

    with pytest.raises(HTTPException) as exc_info:
        await delete_user_role_assignment(async_session, created_assignment.id)

    assert exc_info.value.status_code == 400
    assert "immutable" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_user_role_assignment_with_creator(async_session: AsyncSession, test_user: User, test_user_2: User):
    """Test creating a user role assignment with creator."""
    role_data = RoleCreate(name="Admin")
    role = await create_role(async_session, role_data)

    assignment_data = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Global", scope_id=None, created_by=test_user_2.id
    )
    assignment = await create_user_role_assignment(async_session, assignment_data)

    assert assignment.created_by == test_user_2.id
