"""Unit tests for user role assignment Pydantic schemas.

Tests cover validation rules, field constraints, and edge cases for all schema classes.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from langbuilder.services.database.models.user_role_assignment.schema import (
    MAX_PERMISSION_CHECKS,
    PermissionCheck,
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionCheckResult,
    RoleRead,
    UserRoleAssignmentCreate,
    UserRoleAssignmentRead,
    UserRoleAssignmentUpdate,
)
from pydantic import ValidationError


class TestUserRoleAssignmentCreate:
    """Test UserRoleAssignmentCreate schema validation."""

    def test_create_valid_flow_scope(self):
        """Test creating a valid role assignment with Flow scope."""
        user_id = uuid4()
        scope_id = uuid4()
        data = UserRoleAssignmentCreate(
            user_id=user_id,
            role_name="Editor",
            scope_type="Flow",
            scope_id=scope_id,
        )

        assert data.user_id == user_id
        assert data.role_name == "Editor"
        assert data.scope_type == "Flow"
        assert data.scope_id == scope_id

    def test_create_valid_project_scope(self):
        """Test creating a valid role assignment with Project scope."""
        user_id = uuid4()
        scope_id = uuid4()
        data = UserRoleAssignmentCreate(
            user_id=user_id,
            role_name="Admin",
            scope_type="Project",
            scope_id=scope_id,
        )

        assert data.user_id == user_id
        assert data.role_name == "Admin"
        assert data.scope_type == "Project"
        assert data.scope_id == scope_id

    def test_create_valid_global_scope(self):
        """Test creating a valid role assignment with Global scope."""
        user_id = uuid4()
        data = UserRoleAssignmentCreate(
            user_id=user_id,
            role_name="Owner",
            scope_type="Global",
            scope_id=None,
        )

        assert data.user_id == user_id
        assert data.role_name == "Owner"
        assert data.scope_type == "Global"
        assert data.scope_id is None

    def test_create_global_scope_without_scope_id(self):
        """Test creating Global scope without explicitly setting scope_id."""
        user_id = uuid4()
        data = UserRoleAssignmentCreate(
            user_id=user_id,
            role_name="Viewer",
            scope_type="Global",
        )

        assert data.scope_id is None

    def test_create_flow_scope_requires_scope_id(self):
        """Test that Flow scope requires scope_id."""
        user_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            UserRoleAssignmentCreate(
                user_id=user_id,
                role_name="Editor",
                scope_type="Flow",
                scope_id=None,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("scope_id",)
        assert "scope_id required for scope_type='Flow'" in errors[0]["msg"]

    def test_create_project_scope_requires_scope_id(self):
        """Test that Project scope requires scope_id."""
        user_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            UserRoleAssignmentCreate(
                user_id=user_id,
                role_name="Admin",
                scope_type="Project",
                scope_id=None,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("scope_id",)
        assert "scope_id required for scope_type='Project'" in errors[0]["msg"]

    def test_create_global_scope_rejects_scope_id(self):
        """Test that Global scope rejects non-null scope_id."""
        user_id = uuid4()
        scope_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            UserRoleAssignmentCreate(
                user_id=user_id,
                role_name="Owner",
                scope_type="Global",
                scope_id=scope_id,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("scope_id",)
        assert "scope_id must be None for scope_type='Global'" in errors[0]["msg"]

    def test_create_invalid_scope_type(self):
        """Test that invalid scope_type is rejected."""
        user_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            UserRoleAssignmentCreate(
                user_id=user_id,
                role_name="Editor",
                scope_type="InvalidScope",
                scope_id=None,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("scope_type",)
        assert "must be one of" in errors[0]["msg"]

    def test_create_empty_role_name(self):
        """Test that empty role_name is rejected."""
        user_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            UserRoleAssignmentCreate(
                user_id=user_id,
                role_name="",
                scope_type="Global",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("role_name",)
        assert "cannot be empty" in errors[0]["msg"]

    def test_create_whitespace_role_name(self):
        """Test that whitespace-only role_name is rejected."""
        user_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            UserRoleAssignmentCreate(
                user_id=user_id,
                role_name="   ",
                scope_type="Global",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("role_name",)
        assert "cannot be empty" in errors[0]["msg"]

    def test_create_role_name_trimming(self):
        """Test that role_name is trimmed of whitespace."""
        user_id = uuid4()
        data = UserRoleAssignmentCreate(
            user_id=user_id,
            role_name="  Editor  ",
            scope_type="Global",
        )

        assert data.role_name == "Editor"

    def test_create_missing_required_fields(self):
        """Test that missing required fields raise validation errors."""
        with pytest.raises(ValidationError) as exc_info:
            UserRoleAssignmentCreate()

        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}
        assert "user_id" in error_fields
        assert "role_name" in error_fields
        assert "scope_type" in error_fields


class TestUserRoleAssignmentUpdate:
    """Test UserRoleAssignmentUpdate schema validation."""

    def test_update_valid_role_name(self):
        """Test updating with a valid role_name."""
        data = UserRoleAssignmentUpdate(role_name="NewRole")

        assert data.role_name == "NewRole"

    def test_update_empty_role_name(self):
        """Test that empty role_name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UserRoleAssignmentUpdate(role_name="")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("role_name",)
        assert "cannot be empty" in errors[0]["msg"]

    def test_update_whitespace_role_name(self):
        """Test that whitespace-only role_name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UserRoleAssignmentUpdate(role_name="   ")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("role_name",)
        assert "cannot be empty" in errors[0]["msg"]

    def test_update_role_name_trimming(self):
        """Test that role_name is trimmed of whitespace."""
        data = UserRoleAssignmentUpdate(role_name="  Admin  ")

        assert data.role_name == "Admin"

    def test_update_missing_role_name(self):
        """Test that missing role_name raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            UserRoleAssignmentUpdate()

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("role_name",)


class TestUserRoleAssignmentRead:
    """Test UserRoleAssignmentRead schema."""

    def test_read_complete_assignment(self):
        """Test reading a complete role assignment."""
        assignment_id = uuid4()
        user_id = uuid4()
        role_id = uuid4()
        scope_id = uuid4()
        created_by = uuid4()
        created_at = datetime.now(timezone.utc)

        data = UserRoleAssignmentRead(
            id=assignment_id,
            user_id=user_id,
            role_id=role_id,
            role_name="Editor",
            scope_type="Flow",
            scope_id=scope_id,
            scope_name="My Flow",
            is_immutable=False,
            created_at=created_at,
            created_by=created_by,
        )

        assert data.id == assignment_id
        assert data.user_id == user_id
        assert data.role_id == role_id
        assert data.role_name == "Editor"
        assert data.scope_type == "Flow"
        assert data.scope_id == scope_id
        assert data.scope_name == "My Flow"
        assert data.is_immutable is False
        assert data.created_at == created_at
        assert data.created_by == created_by

    def test_read_global_scope_assignment(self):
        """Test reading a Global scope assignment without scope_id and scope_name."""
        assignment_id = uuid4()
        user_id = uuid4()
        role_id = uuid4()
        created_at = datetime.now(timezone.utc)

        data = UserRoleAssignmentRead(
            id=assignment_id,
            user_id=user_id,
            role_id=role_id,
            role_name="Owner",
            scope_type="Global",
            scope_id=None,
            scope_name=None,
            is_immutable=True,
            created_at=created_at,
            created_by=None,
        )

        assert data.scope_type == "Global"
        assert data.scope_id is None
        assert data.scope_name is None
        assert data.is_immutable is True
        assert data.created_by is None

    def test_read_from_orm_model(self):
        """Test that Config.from_attributes=True works for ORM models."""
        # This test verifies the Config setting but doesn't actually test ORM conversion
        # since that requires a database session
        assert UserRoleAssignmentRead.model_config["from_attributes"] is True


class TestRoleRead:
    """Test RoleRead schema."""

    def test_read_system_role(self):
        """Test reading a system role."""
        role_id = uuid4()
        data = RoleRead(
            id=role_id,
            name="Owner",
            description="System owner role",
            is_system_role=True,
        )

        assert data.id == role_id
        assert data.name == "Owner"
        assert data.description == "System owner role"
        assert data.is_system_role is True

    def test_read_custom_role(self):
        """Test reading a custom role."""
        role_id = uuid4()
        data = RoleRead(
            id=role_id,
            name="CustomRole",
            description=None,
            is_system_role=False,
        )

        assert data.id == role_id
        assert data.name == "CustomRole"
        assert data.description is None
        assert data.is_system_role is False

    def test_read_from_orm_model(self):
        """Test that Config.from_attributes=True works for ORM models."""
        assert RoleRead.model_config["from_attributes"] is True


class TestPermissionCheck:
    """Test PermissionCheck schema."""

    def test_permission_check_with_resource_id(self):
        """Test permission check with specific resource ID."""
        resource_id = uuid4()
        check = PermissionCheck(
            action="read",
            resource_type="Flow",
            resource_id=resource_id,
        )

        assert check.action == "read"
        assert check.resource_type == "Flow"
        assert check.resource_id == resource_id

    def test_permission_check_without_resource_id(self):
        """Test permission check without specific resource ID."""
        check = PermissionCheck(
            action="create",
            resource_type="Project",
            resource_id=None,
        )

        assert check.action == "create"
        assert check.resource_type == "Project"
        assert check.resource_id is None

    def test_permission_check_missing_required_fields(self):
        """Test that missing required fields raise validation errors."""
        with pytest.raises(ValidationError) as exc_info:
            PermissionCheck()

        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}
        assert "action" in error_fields
        assert "resource_type" in error_fields


class TestPermissionCheckRequest:
    """Test PermissionCheckRequest schema."""

    def test_permission_check_request_single_check(self):
        """Test permission check request with single check."""
        resource_id = uuid4()
        request = PermissionCheckRequest(
            checks=[
                PermissionCheck(
                    action="read",
                    resource_type="Flow",
                    resource_id=resource_id,
                )
            ]
        )

        assert len(request.checks) == 1
        assert request.checks[0].action == "read"

    def test_permission_check_request_multiple_checks(self):
        """Test permission check request with multiple checks."""
        flow_id = uuid4()
        project_id = uuid4()
        request = PermissionCheckRequest(
            checks=[
                PermissionCheck(action="read", resource_type="Flow", resource_id=flow_id),
                PermissionCheck(action="write", resource_type="Flow", resource_id=flow_id),
                PermissionCheck(action="delete", resource_type="Project", resource_id=project_id),
            ]
        )

        assert len(request.checks) == 3
        assert request.checks[0].action == "read"
        assert request.checks[1].action == "write"
        assert request.checks[2].action == "delete"

    def test_permission_check_request_empty_checks(self):
        """Test that empty checks list is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PermissionCheckRequest(checks=[])

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("checks",)
        assert "cannot be empty" in errors[0]["msg"]

    def test_permission_check_request_too_many_checks(self):
        """Test that more than MAX_PERMISSION_CHECKS is rejected."""
        checks = [
            PermissionCheck(action="read", resource_type="Flow", resource_id=uuid4())
            for _ in range(MAX_PERMISSION_CHECKS + 1)
        ]

        with pytest.raises(ValidationError) as exc_info:
            PermissionCheckRequest(checks=checks)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("checks",)
        assert f"Cannot check more than {MAX_PERMISSION_CHECKS}" in errors[0]["msg"]

    def test_permission_check_request_exactly_max_checks(self):
        """Test that exactly MAX_PERMISSION_CHECKS is allowed."""
        checks = [
            PermissionCheck(action="read", resource_type="Flow", resource_id=uuid4())
            for _ in range(MAX_PERMISSION_CHECKS)
        ]

        request = PermissionCheckRequest(checks=checks)
        assert len(request.checks) == MAX_PERMISSION_CHECKS


class TestPermissionCheckResult:
    """Test PermissionCheckResult schema."""

    def test_permission_check_result_allowed(self):
        """Test permission check result when allowed."""
        resource_id = uuid4()
        result = PermissionCheckResult(
            action="read",
            resource_type="Flow",
            resource_id=resource_id,
            allowed=True,
        )

        assert result.action == "read"
        assert result.resource_type == "Flow"
        assert result.resource_id == resource_id
        assert result.allowed is True

    def test_permission_check_result_denied(self):
        """Test permission check result when denied."""
        resource_id = uuid4()
        result = PermissionCheckResult(
            action="delete",
            resource_type="Project",
            resource_id=resource_id,
            allowed=False,
        )

        assert result.action == "delete"
        assert result.resource_type == "Project"
        assert result.resource_id == resource_id
        assert result.allowed is False

    def test_permission_check_result_without_resource_id(self):
        """Test permission check result without resource_id."""
        result = PermissionCheckResult(
            action="create",
            resource_type="Flow",
            resource_id=None,
            allowed=True,
        )

        assert result.resource_id is None
        assert result.allowed is True


class TestPermissionCheckResponse:
    """Test PermissionCheckResponse schema."""

    def test_permission_check_response_single_result(self):
        """Test permission check response with single result."""
        resource_id = uuid4()
        response = PermissionCheckResponse(
            results=[
                PermissionCheckResult(
                    action="read",
                    resource_type="Flow",
                    resource_id=resource_id,
                    allowed=True,
                )
            ]
        )

        assert len(response.results) == 1
        assert response.results[0].allowed is True

    def test_permission_check_response_multiple_results(self):
        """Test permission check response with multiple results."""
        flow_id = uuid4()
        response = PermissionCheckResponse(
            results=[
                PermissionCheckResult(action="read", resource_type="Flow", resource_id=flow_id, allowed=True),
                PermissionCheckResult(action="write", resource_type="Flow", resource_id=flow_id, allowed=True),
                PermissionCheckResult(action="delete", resource_type="Flow", resource_id=flow_id, allowed=False),
            ]
        )

        assert len(response.results) == 3
        assert response.results[0].allowed is True
        assert response.results[1].allowed is True
        assert response.results[2].allowed is False

    def test_permission_check_response_empty_results(self):
        """Test permission check response with empty results."""
        response = PermissionCheckResponse(results=[])

        assert len(response.results) == 0
