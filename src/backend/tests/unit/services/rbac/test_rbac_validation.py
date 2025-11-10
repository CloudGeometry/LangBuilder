"""Unit tests for RBAC role assignment validation (Task 3.4)."""

from uuid import uuid4

import pytest
from langbuilder.services.auth.utils import get_password_hash
from langbuilder.services.database.models.flow.model import Flow
from langbuilder.services.database.models.folder.model import Folder
from langbuilder.services.database.models.role.crud import create_role
from langbuilder.services.database.models.role.model import RoleCreate
from langbuilder.services.database.models.user.model import User
from langbuilder.services.rbac.exceptions import (
    InvalidScopeException,
    ResourceNotFoundException,
    RoleNotFoundException,
    UserNotFoundException,
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
        username="testuser_validation",
        password=get_password_hash("password"),
        is_active=True,
        is_superuser=False,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
async def test_role(async_session: AsyncSession):
    """Create a test role."""
    role_data = RoleCreate(name="TestRole", description="Test role for validation")
    return await create_role(async_session, role_data)


@pytest.fixture
async def test_folder(async_session: AsyncSession, test_user):
    """Create a test folder (project)."""
    folder = Folder(
        name="Test Validation Project",
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
        name="Test Validation Flow",
        user_id=test_user.id,
        folder_id=test_folder.id,
        data={"nodes": [], "edges": []},
    )
    async_session.add(flow)
    await async_session.commit()
    await async_session.refresh(flow)
    return flow


# Test user validation


@pytest.mark.asyncio
async def test_assign_role_user_not_found(rbac_service, async_session, test_role):  # noqa: ARG001
    """Test that assigning a role to a non-existent user raises UserNotFoundException."""
    non_existent_user_id = uuid4()

    with pytest.raises(UserNotFoundException) as exc_info:
        await rbac_service.assign_role(
            user_id=non_existent_user_id,
            role_name="TestRole",
            scope_type="Global",
            scope_id=None,
            created_by=non_existent_user_id,
            db=async_session,
        )

    assert str(non_existent_user_id) in str(exc_info.value.detail)
    assert exc_info.value.status_code == 404


# Test role validation


@pytest.mark.asyncio
async def test_assign_role_role_not_found(rbac_service, async_session, test_user):
    """Test that assigning a non-existent role raises RoleNotFoundException."""
    with pytest.raises(RoleNotFoundException) as exc_info:
        await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="NonExistentRole",
            scope_type="Global",
            scope_id=None,
            created_by=test_user.id,
            db=async_session,
        )

    assert "NonExistentRole" in str(exc_info.value.detail)
    assert exc_info.value.status_code == 404


# Test Flow scope validation


@pytest.mark.asyncio
async def test_assign_role_flow_scope_without_scope_id(rbac_service, async_session, test_user, test_role):  # noqa: ARG001
    """Test that Flow scope without scope_id raises InvalidScopeException."""
    with pytest.raises(InvalidScopeException) as exc_info:
        await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="TestRole",
            scope_type="Flow",
            scope_id=None,
            created_by=test_user.id,
            db=async_session,
        )

    assert "Flow scope requires scope_id" in str(exc_info.value.detail)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_assign_role_flow_not_found(rbac_service, async_session, test_user, test_role):  # noqa: ARG001
    """Test that assigning a role for a non-existent Flow raises ResourceNotFoundException."""
    non_existent_flow_id = uuid4()

    with pytest.raises(ResourceNotFoundException) as exc_info:
        await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="TestRole",
            scope_type="Flow",
            scope_id=non_existent_flow_id,
            created_by=test_user.id,
            db=async_session,
        )

    assert "Flow" in str(exc_info.value.detail)
    assert str(non_existent_flow_id) in str(exc_info.value.detail)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_assign_role_flow_scope_valid(rbac_service, async_session, test_user, test_role, test_flow):
    """Test that assigning a role for a valid Flow succeeds."""
    assignment = await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="TestRole",
        scope_type="Flow",
        scope_id=test_flow.id,
        created_by=test_user.id,
        db=async_session,
    )

    assert assignment.id is not None
    assert assignment.user_id == test_user.id
    assert assignment.role_id == test_role.id
    assert assignment.scope_type == "Flow"
    assert assignment.scope_id == test_flow.id


# Test Project scope validation


@pytest.mark.asyncio
async def test_assign_role_project_scope_without_scope_id(rbac_service, async_session, test_user, test_role):  # noqa: ARG001
    """Test that Project scope without scope_id raises InvalidScopeException."""
    with pytest.raises(InvalidScopeException) as exc_info:
        await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="TestRole",
            scope_type="Project",
            scope_id=None,
            created_by=test_user.id,
            db=async_session,
        )

    assert "Project scope requires scope_id" in str(exc_info.value.detail)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_assign_role_project_not_found(rbac_service, async_session, test_user, test_role):  # noqa: ARG001
    """Test that assigning a role for a non-existent Project raises ResourceNotFoundException."""
    non_existent_project_id = uuid4()

    with pytest.raises(ResourceNotFoundException) as exc_info:
        await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="TestRole",
            scope_type="Project",
            scope_id=non_existent_project_id,
            created_by=test_user.id,
            db=async_session,
        )

    assert "Project" in str(exc_info.value.detail)
    assert str(non_existent_project_id) in str(exc_info.value.detail)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_assign_role_project_scope_valid(rbac_service, async_session, test_user, test_role, test_folder):
    """Test that assigning a role for a valid Project succeeds."""
    assignment = await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="TestRole",
        scope_type="Project",
        scope_id=test_folder.id,
        created_by=test_user.id,
        db=async_session,
    )

    assert assignment.id is not None
    assert assignment.user_id == test_user.id
    assert assignment.role_id == test_role.id
    assert assignment.scope_type == "Project"
    assert assignment.scope_id == test_folder.id


# Test Global scope validation


@pytest.mark.asyncio
async def test_assign_role_global_scope_with_scope_id(rbac_service, async_session, test_user, test_role):  # noqa: ARG001
    """Test that Global scope with scope_id raises InvalidScopeException."""
    with pytest.raises(InvalidScopeException) as exc_info:
        await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="TestRole",
            scope_type="Global",
            scope_id=uuid4(),
            created_by=test_user.id,
            db=async_session,
        )

    assert "Global scope should not have scope_id" in str(exc_info.value.detail)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_assign_role_global_scope_valid(rbac_service, async_session, test_user, test_role):
    """Test that assigning a role for Global scope succeeds."""
    assignment = await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="TestRole",
        scope_type="Global",
        scope_id=None,
        created_by=test_user.id,
        db=async_session,
    )

    assert assignment.id is not None
    assert assignment.user_id == test_user.id
    assert assignment.role_id == test_role.id
    assert assignment.scope_type == "Global"
    assert assignment.scope_id is None


# Test invalid scope type


@pytest.mark.asyncio
async def test_assign_role_invalid_scope_type(rbac_service, async_session, test_user, test_role):  # noqa: ARG001
    """Test that an invalid scope_type raises InvalidScopeException."""
    with pytest.raises(InvalidScopeException) as exc_info:
        await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="TestRole",
            scope_type="InvalidScope",
            scope_id=None,
            created_by=test_user.id,
            db=async_session,
        )

    assert "Invalid scope_type: InvalidScope" in str(exc_info.value.detail)
    assert "Must be 'Flow', 'Project', or 'Global'" in str(exc_info.value.detail)
    assert exc_info.value.status_code == 400


# Test error messages clarity


@pytest.mark.asyncio
async def test_validation_error_messages_are_clear(rbac_service, async_session, test_user, test_role):  # noqa: ARG001
    """Test that validation error messages are clear and informative."""
    # Test User not found
    non_existent_user_id = uuid4()
    with pytest.raises(UserNotFoundException) as exc_info:
        await rbac_service.assign_role(
            user_id=non_existent_user_id,
            role_name="TestRole",
            scope_type="Global",
            scope_id=None,
            created_by=test_user.id,
            db=async_session,
        )
    assert "User" in str(exc_info.value.detail)
    assert "not found" in str(exc_info.value.detail)

    # Test Flow not found
    non_existent_flow_id = uuid4()
    with pytest.raises(ResourceNotFoundException) as exc_info:
        await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="TestRole",
            scope_type="Flow",
            scope_id=non_existent_flow_id,
            created_by=test_user.id,
            db=async_session,
        )
    assert "Flow" in str(exc_info.value.detail)
    assert "not found" in str(exc_info.value.detail)

    # Test Project not found
    non_existent_project_id = uuid4()
    with pytest.raises(ResourceNotFoundException) as exc_info:
        await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="TestRole",
            scope_type="Project",
            scope_id=non_existent_project_id,
            created_by=test_user.id,
            db=async_session,
        )
    assert "Project" in str(exc_info.value.detail)
    assert "not found" in str(exc_info.value.detail)

    # Test invalid scope
    with pytest.raises(InvalidScopeException) as exc_info:
        await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="TestRole",
            scope_type="Global",
            scope_id=uuid4(),
            created_by=test_user.id,
            db=async_session,
        )
    assert "Global scope should not have scope_id" in str(exc_info.value.detail)
