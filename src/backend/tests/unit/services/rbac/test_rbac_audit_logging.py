"""Unit tests for RBAC Service audit logging functionality."""

from unittest.mock import patch

import pytest
from langbuilder.services.auth.utils import get_password_hash
from langbuilder.services.database.models.folder.model import Folder
from langbuilder.services.database.models.role.crud import create_role
from langbuilder.services.database.models.role.model import RoleCreate
from langbuilder.services.database.models.user.model import User
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
async def admin_user(async_session: AsyncSession):
    """Create an admin user."""
    user = User(
        username="adminuser",
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
    role_data = RoleCreate(name="Editor", description="Can edit flows")
    return await create_role(async_session, role_data)


@pytest.fixture
async def viewer_role(async_session: AsyncSession):
    """Create a Viewer role."""
    role_data = RoleCreate(name="Viewer", description="Read-only access")
    return await create_role(async_session, role_data)


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


# Test audit logging for assign_role


@pytest.mark.asyncio
async def test_assign_role_logs_audit_trail(rbac_service, async_session, test_user, admin_user, test_role):
    """Test that assign_role logs structured audit data."""
    with patch("langbuilder.services.rbac.service.logger") as mock_logger:
        assignment = await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="Editor",
            scope_type="Global",
            scope_id=None,
            created_by=admin_user.id,
            db=async_session,
        )

        # Verify logger.info was called
        mock_logger.info.assert_called_once()

        # Get the call arguments
        call_args = mock_logger.info.call_args

        # Verify the message
        assert call_args[0][0] == "RBAC: Role assigned"

        # Verify the extra data
        extra_data = call_args[1]["extra"]
        assert extra_data["action"] == "assign_role"
        assert extra_data["user_id"] == str(test_user.id)
        assert extra_data["role_name"] == "Editor"
        assert extra_data["role_id"] == str(test_role.id)
        assert extra_data["scope_type"] == "Global"
        assert extra_data["scope_id"] is None
        assert extra_data["created_by"] == str(admin_user.id)
        assert extra_data["assignment_id"] == str(assignment.id)
        assert extra_data["is_immutable"] is False


@pytest.mark.asyncio
async def test_assign_role_logs_with_project_scope(
    rbac_service,
    async_session,
    test_user,
    admin_user,
    test_role,  # noqa: ARG001
    test_folder,
):
    """Test that assign_role logs correct scope_id for Project scope."""
    with patch("langbuilder.services.rbac.service.logger") as mock_logger:
        assignment = await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="Editor",
            scope_type="Project",
            scope_id=test_folder.id,
            created_by=admin_user.id,
            db=async_session,
        )

        # Verify the extra data includes scope_id
        call_args = mock_logger.info.call_args
        extra_data = call_args[1]["extra"]
        assert extra_data["scope_type"] == "Project"
        assert extra_data["scope_id"] == str(test_folder.id)
        assert extra_data["assignment_id"] == str(assignment.id)


@pytest.mark.asyncio
async def test_assign_role_logs_immutable_flag(rbac_service, async_session, test_user, admin_user, test_role):  # noqa: ARG001
    """Test that assign_role logs is_immutable flag correctly."""
    with patch("langbuilder.services.rbac.service.logger") as mock_logger:
        assignment = await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="Editor",
            scope_type="Global",
            scope_id=None,
            created_by=admin_user.id,
            db=async_session,
            is_immutable=True,
        )

        # Verify is_immutable is logged correctly
        call_args = mock_logger.info.call_args
        extra_data = call_args[1]["extra"]
        assert extra_data["is_immutable"] is True
        assert extra_data["assignment_id"] == str(assignment.id)


# Test audit logging for remove_role


@pytest.mark.asyncio
async def test_remove_role_logs_audit_trail(rbac_service, async_session, test_user, admin_user, test_role):
    """Test that remove_role logs structured audit data."""
    # First create an assignment
    assignment = await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Editor",
        scope_type="Global",
        scope_id=None,
        created_by=admin_user.id,
        db=async_session,
    )

    with patch("langbuilder.services.rbac.service.logger") as mock_logger:
        await rbac_service.remove_role(assignment.id, db=async_session)

        # Verify logger.info was called
        mock_logger.info.assert_called_once()

        # Get the call arguments
        call_args = mock_logger.info.call_args

        # Verify the message
        assert call_args[0][0] == "RBAC: Role removed"

        # Verify the extra data
        extra_data = call_args[1]["extra"]
        assert extra_data["action"] == "remove_role"
        assert extra_data["assignment_id"] == str(assignment.id)
        assert extra_data["user_id"] == str(test_user.id)
        assert extra_data["role_id"] == str(test_role.id)
        assert extra_data["scope_type"] == "Global"
        assert extra_data["scope_id"] is None


@pytest.mark.asyncio
async def test_remove_role_logs_with_project_scope(
    rbac_service,
    async_session,
    test_user,
    admin_user,
    test_role,  # noqa: ARG001
    test_folder,
):
    """Test that remove_role logs correct scope_id for Project scope."""
    # First create a Project-scoped assignment
    assignment = await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Editor",
        scope_type="Project",
        scope_id=test_folder.id,
        created_by=admin_user.id,
        db=async_session,
    )

    with patch("langbuilder.services.rbac.service.logger") as mock_logger:
        await rbac_service.remove_role(assignment.id, db=async_session)

        # Verify the extra data includes scope_id
        call_args = mock_logger.info.call_args
        extra_data = call_args[1]["extra"]
        assert extra_data["scope_type"] == "Project"
        assert extra_data["scope_id"] == str(test_folder.id)


# Test audit logging for update_role


@pytest.mark.asyncio
async def test_update_role_logs_audit_trail(rbac_service, async_session, test_user, admin_user, test_role, viewer_role):
    """Test that update_role logs structured audit data."""
    # First create an assignment
    assignment = await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Editor",
        scope_type="Global",
        scope_id=None,
        created_by=admin_user.id,
        db=async_session,
    )

    with patch("langbuilder.services.rbac.service.logger") as mock_logger:
        updated_assignment = await rbac_service.update_role(
            assignment_id=assignment.id,
            new_role_name="Viewer",
            db=async_session,
        )

        # Verify logger.info was called
        mock_logger.info.assert_called_once()

        # Get the call arguments
        call_args = mock_logger.info.call_args

        # Verify the message
        assert call_args[0][0] == "RBAC: Role updated"

        # Verify the extra data
        extra_data = call_args[1]["extra"]
        assert extra_data["action"] == "update_role"
        assert extra_data["assignment_id"] == str(assignment.id)
        assert extra_data["user_id"] == str(test_user.id)
        assert extra_data["old_role_id"] == str(test_role.id)
        assert extra_data["new_role_id"] == str(viewer_role.id)
        assert extra_data["new_role_name"] == "Viewer"
        assert extra_data["scope_type"] == "Global"
        assert extra_data["scope_id"] is None
        assert updated_assignment.role_id == viewer_role.id


@pytest.mark.asyncio
async def test_update_role_logs_with_project_scope(
    rbac_service, async_session, test_user, admin_user, test_role, viewer_role, test_folder
):
    """Test that update_role logs correct scope_id for Project scope."""
    # First create a Project-scoped assignment
    assignment = await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Editor",
        scope_type="Project",
        scope_id=test_folder.id,
        created_by=admin_user.id,
        db=async_session,
    )

    with patch("langbuilder.services.rbac.service.logger") as mock_logger:
        updated_assignment = await rbac_service.update_role(
            assignment_id=assignment.id,
            new_role_name="Viewer",
            db=async_session,
        )

        # Verify the extra data includes scope_id
        call_args = mock_logger.info.call_args
        extra_data = call_args[1]["extra"]
        assert extra_data["scope_type"] == "Project"
        assert extra_data["scope_id"] == str(test_folder.id)
        assert extra_data["old_role_id"] == str(test_role.id)
        assert extra_data["new_role_id"] == str(viewer_role.id)
        assert updated_assignment.role_id == viewer_role.id


# Test that all required fields are present in audit logs


@pytest.mark.asyncio
async def test_assign_role_audit_log_contains_all_required_fields(
    rbac_service,
    async_session,
    test_user,
    admin_user,
    test_role,  # noqa: ARG001
):
    """Test that assign_role audit log contains all required fields for compliance."""
    with patch("langbuilder.services.rbac.service.logger") as mock_logger:
        await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="Editor",
            scope_type="Global",
            scope_id=None,
            created_by=admin_user.id,
            db=async_session,
        )

        extra_data = mock_logger.info.call_args[1]["extra"]

        # Verify all required fields are present
        required_fields = [
            "action",
            "user_id",
            "role_name",
            "role_id",
            "scope_type",
            "scope_id",
            "created_by",
            "assignment_id",
            "is_immutable",
        ]
        for field in required_fields:
            assert field in extra_data, f"Required field '{field}' missing from audit log"


@pytest.mark.asyncio
async def test_remove_role_audit_log_contains_all_required_fields(
    rbac_service,
    async_session,
    test_user,
    admin_user,
    test_role,  # noqa: ARG001
):
    """Test that remove_role audit log contains all required fields for compliance."""
    # First create an assignment
    assignment = await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Editor",
        scope_type="Global",
        scope_id=None,
        created_by=admin_user.id,
        db=async_session,
    )

    with patch("langbuilder.services.rbac.service.logger") as mock_logger:
        await rbac_service.remove_role(assignment.id, db=async_session)

        extra_data = mock_logger.info.call_args[1]["extra"]

        # Verify all required fields are present
        required_fields = [
            "action",
            "assignment_id",
            "user_id",
            "role_id",
            "scope_type",
            "scope_id",
        ]
        for field in required_fields:
            assert field in extra_data, f"Required field '{field}' missing from audit log"


@pytest.mark.asyncio
async def test_update_role_audit_log_contains_all_required_fields(
    rbac_service,
    async_session,
    test_user,
    admin_user,
    test_role,  # noqa: ARG001
    viewer_role,  # noqa: ARG001
):
    """Test that update_role audit log contains all required fields for compliance."""
    # First create an assignment
    assignment = await rbac_service.assign_role(
        user_id=test_user.id,
        role_name="Editor",
        scope_type="Global",
        scope_id=None,
        created_by=admin_user.id,
        db=async_session,
    )

    with patch("langbuilder.services.rbac.service.logger") as mock_logger:
        await rbac_service.update_role(
            assignment_id=assignment.id,
            new_role_name="Viewer",
            db=async_session,
        )

        extra_data = mock_logger.info.call_args[1]["extra"]

        # Verify all required fields are present
        required_fields = [
            "action",
            "assignment_id",
            "user_id",
            "old_role_id",
            "new_role_id",
            "new_role_name",
            "scope_type",
            "scope_id",
        ]
        for field in required_fields:
            assert field in extra_data, f"Required field '{field}' missing from audit log"


# Test that UUIDs are properly serialized to strings


@pytest.mark.asyncio
async def test_audit_logs_serialize_uuids_to_strings(rbac_service, async_session, test_user, admin_user, test_role):  # noqa: ARG001
    """Test that all UUID fields are serialized to strings for JSON compatibility."""
    with patch("langbuilder.services.rbac.service.logger") as mock_logger:
        await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="Editor",
            scope_type="Global",
            scope_id=None,
            created_by=admin_user.id,
            db=async_session,
        )

        extra_data = mock_logger.info.call_args[1]["extra"]

        # Verify UUID fields are strings
        assert isinstance(extra_data["user_id"], str)
        assert isinstance(extra_data["role_id"], str)
        assert isinstance(extra_data["created_by"], str)
        assert isinstance(extra_data["assignment_id"], str)

        # Verify they can be parsed back to UUIDs
        from uuid import UUID

        UUID(extra_data["user_id"])
        UUID(extra_data["role_id"])
        UUID(extra_data["created_by"])
        UUID(extra_data["assignment_id"])


# Test edge case: logging when scope_id is None


@pytest.mark.asyncio
async def test_audit_logs_handle_none_scope_id(rbac_service, async_session, test_user, admin_user, test_role):  # noqa: ARG001
    """Test that audit logs correctly handle None scope_id for Global scope."""
    with patch("langbuilder.services.rbac.service.logger") as mock_logger:
        await rbac_service.assign_role(
            user_id=test_user.id,
            role_name="Editor",
            scope_type="Global",
            scope_id=None,
            created_by=admin_user.id,
            db=async_session,
        )

        extra_data = mock_logger.info.call_args[1]["extra"]

        # Verify scope_id is None (not "None" string)
        assert extra_data["scope_id"] is None
        assert extra_data["scope_type"] == "Global"
