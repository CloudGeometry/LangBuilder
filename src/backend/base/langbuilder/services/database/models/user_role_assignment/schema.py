"""Pydantic schemas for RBAC API endpoints.

This module defines request and response schemas for user role assignments,
including denormalized fields (role_name, scope_name) for better frontend usability.

Schema Organization:
--------------------
This module contains API-specific Pydantic schemas that are separate from the ORM schemas
defined in model.py. This separation exists due to a naming conflict and different purposes:

- model.py: SQLModel schemas for database operations (ORM layer)
  - Used for database table mapping, relationships, and ORM queries
  - Inherit from SQLModel and UserRoleAssignmentBase
  - Focus on database structure and constraints

- schema.py: Pydantic schemas for API requests/responses (API layer)
  - Used for FastAPI endpoint request/response models
  - Inherit from pure Pydantic BaseModel
  - Include denormalized fields (role_name, scope_name) to reduce frontend API calls
  - Include additional validation rules for cross-field dependencies
  - Optimized for API documentation generation and client consumption

Naming Conflict Resolution:
---------------------------
Both model.py and schema.py define schemas with the same names:
- UserRoleAssignmentCreate
- UserRoleAssignmentRead
- UserRoleAssignmentUpdate

To resolve this conflict, __init__.py uses aliased imports for the schema.py versions:
- UserRoleAssignmentCreateSchema (from schema.py)
- UserRoleAssignmentReadSchema (from schema.py)
- UserRoleAssignmentUpdateSchema (from schema.py)

The model.py versions retain their original names for backward compatibility.

Usage:
------
For FastAPI endpoint request/response models, import the API schemas:
    from langbuilder.services.database.models.user_role_assignment.schema import (
        UserRoleAssignmentCreate,
        UserRoleAssignmentRead,
        PermissionCheckRequest,
    )

Or use the aliased versions from __init__.py to avoid confusion:
    from langbuilder.services.database.models.user_role_assignment import (
        UserRoleAssignmentCreateSchema,
        UserRoleAssignmentReadSchema,
    )
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class UserRoleAssignmentCreate(BaseModel):
    """Schema for creating a role assignment. Uses role_name instead of role_id for API convenience."""

    user_id: UUID = Field(description="ID of the user to assign the role to")
    role_name: str = Field(description="Role name (e.g., 'Owner', 'Admin', 'Editor', 'Viewer')")
    scope_type: str = Field(description="Scope type: 'Flow', 'Project', or 'Global'")
    scope_id: UUID | None = Field(default=None, description="Required for Flow/Project scopes, null for Global")

    @field_validator("scope_id", mode="after")
    @classmethod
    def validate_scope_id(cls, v: UUID | None, info) -> UUID | None:
        """Validate that scope_id is provided when scope_type is Flow or Project."""
        scope_type = info.data.get("scope_type")
        if scope_type in ("Flow", "Project") and v is None:
            msg = f"scope_id required for scope_type='{scope_type}'"
            raise ValueError(msg)
        if scope_type == "Global" and v is not None:
            msg = "scope_id must be None for scope_type='Global'"
            raise ValueError(msg)
        return v

    @field_validator("scope_type")
    @classmethod
    def validate_scope_type(cls, v: str) -> str:
        """Validate scope_type is one of the allowed values."""
        allowed_values = {"Flow", "Project", "Global"}
        if v not in allowed_values:
            msg = f"scope_type must be one of {allowed_values}"
            raise ValueError(msg)
        return v

    @field_validator("role_name")
    @classmethod
    def validate_role_name(cls, v: str) -> str:
        """Validate role_name is not empty."""
        if not v or not v.strip():
            msg = "role_name cannot be empty"
            raise ValueError(msg)
        return v.strip()


class UserRoleAssignmentUpdate(BaseModel):
    """Schema for updating a role assignment. Only the role can be updated via PATCH."""

    role_name: str = Field(description="New role name to assign")

    @field_validator("role_name")
    @classmethod
    def validate_role_name(cls, v: str) -> str:
        """Validate role_name is not empty."""
        if not v or not v.strip():
            msg = "role_name cannot be empty"
            raise ValueError(msg)
        return v.strip()


class UserRoleAssignmentRead(BaseModel):
    """Schema for reading a role assignment with denormalized fields.

    Includes role_name and scope_name for frontend convenience,
    avoiding the need for additional API calls to resolve these values.
    """

    id: UUID = Field(description="Unique identifier for the role assignment")
    user_id: UUID = Field(description="ID of the user with this role assignment")
    role_id: UUID = Field(description="ID of the assigned role")
    role_name: str = Field(description="Name of the assigned role (denormalized)")
    scope_type: str = Field(description="Scope type: 'Flow', 'Project', or 'Global'")
    scope_id: UUID | None = Field(default=None, description="ID of the scoped resource (Flow/Project)")
    scope_name: str | None = Field(default=None, description="Name of the scoped resource (denormalized)")
    is_immutable: bool = Field(description="Whether this assignment can be modified or deleted")
    created_at: datetime = Field(description="Timestamp when the assignment was created")
    created_by: UUID | None = Field(default=None, description="ID of the user who created this assignment")

    class Config:
        from_attributes = True


class RoleRead(BaseModel):
    """Schema for reading role information."""

    id: UUID = Field(description="Unique identifier for the role")
    name: str = Field(description="Role name")
    description: str | None = Field(default=None, description="Role description")
    is_system_role: bool = Field(description="Whether this is a system-managed role")

    class Config:
        from_attributes = True


class PermissionCheck(BaseModel):
    """Schema for checking a single permission."""

    action: str = Field(description="Action to check (e.g., 'read', 'write', 'delete')")
    resource_type: str = Field(description="Resource type (e.g., 'Flow', 'Project')")
    resource_id: UUID | None = Field(default=None, description="Specific resource ID, if applicable")


MAX_PERMISSION_CHECKS = 100


class PermissionCheckRequest(BaseModel):
    """Schema for batch permission check request."""

    checks: list[PermissionCheck] = Field(description="List of permissions to check")

    @field_validator("checks")
    @classmethod
    def validate_checks_not_empty(cls, v: list[PermissionCheck]) -> list[PermissionCheck]:
        """Validate that checks list is not empty."""
        if not v:
            msg = "checks list cannot be empty"
            raise ValueError(msg)
        if len(v) > MAX_PERMISSION_CHECKS:
            msg = f"Cannot check more than {MAX_PERMISSION_CHECKS} permissions at once"
            raise ValueError(msg)
        return v


class PermissionCheckResult(BaseModel):
    """Schema for a single permission check result."""

    action: str = Field(description="Action that was checked")
    resource_type: str = Field(description="Resource type that was checked")
    resource_id: UUID | None = Field(default=None, description="Specific resource ID, if applicable")
    allowed: bool = Field(description="Whether the action is allowed")


class PermissionCheckResponse(BaseModel):
    """Schema for batch permission check response."""

    results: list[PermissionCheckResult] = Field(description="Results for each permission check")
