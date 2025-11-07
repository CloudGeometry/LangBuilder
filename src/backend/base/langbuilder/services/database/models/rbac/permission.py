from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

if TYPE_CHECKING:
    from langbuilder.services.database.models.rbac.role_permission import RolePermission


class PermissionAction(str, Enum):
    """CRUD actions for RBAC permissions."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


class PermissionScope(str, Enum):
    """Entity scopes for RBAC permissions."""

    FLOW = "flow"
    PROJECT = "project"


class Permission(SQLModel, table=True):
    """Permission model representing CRUD actions applicable to Flow and Project entity types.

    Permissions are defined by an action (CREATE, READ, UPDATE, DELETE) and a scope
    (FLOW, PROJECT). Each action+scope combination must be unique.

    Permissions define atomic actions that can be assigned to roles and evaluated
    for access control.
    """

    __tablename__ = "permission"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    action: PermissionAction = Field(index=True)
    scope: PermissionScope = Field(index=True)
    description: str | None = Field(default=None)

    # Relationships
    role_permissions: list["RolePermission"] = Relationship(
        back_populates="permission",
        sa_relationship_kwargs={"lazy": "select"},
    )

    __table_args__ = (UniqueConstraint("action", "scope", name="unique_action_scope"),)


class PermissionCreate(SQLModel):
    """Schema for creating a new permission."""

    action: PermissionAction
    scope: PermissionScope
    description: str | None = Field(default=None, max_length=500)


class PermissionRead(SQLModel):
    """Schema for reading permission data."""

    id: UUID
    action: PermissionAction
    scope: PermissionScope
    description: str | None


class PermissionUpdate(SQLModel):
    """Schema for updating an existing permission."""

    action: PermissionAction | None = None
    scope: PermissionScope | None = None
    description: str | None = Field(default=None, max_length=500)
