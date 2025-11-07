from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from langbuilder.services.database.models.rbac.role_permission import RolePermission
    from langbuilder.services.database.models.rbac.user_role_assignment import UserRoleAssignment


class Role(SQLModel, table=True):
    """Role model representing predefined RBAC roles.

    Roles define permission sets that can be assigned to users. The MVP includes
    four predefined roles:
    - Admin: Global role with full access across all resources (is_global=True)
    - Owner: Scoped role with full CRUD permissions on assigned resources
    - Editor: Scoped role with Create, Read, Update permissions (no Delete)
    - Viewer: Scoped role with Read-only permissions

    Roles (Admin, Owner, Editor, Viewer) are predefined sets of permissions that
    can be assigned to users for access control.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True, index=True)  # "Admin", "Owner", "Editor", "Viewer"
    description: str | None = Field(default=None)
    is_system: bool = Field(default=True)  # Prevents deletion of predefined roles
    is_global: bool = Field(default=False)  # True only for Admin role

    # Relationships
    role_permissions: list["RolePermission"] = Relationship(
        back_populates="role",
        sa_relationship_kwargs={"lazy": "select"},
    )
    user_assignments: list["UserRoleAssignment"] = Relationship(
        back_populates="role",
        sa_relationship_kwargs={"lazy": "select"},
    )


class RoleCreate(SQLModel):
    """Schema for creating a new role."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_system: bool = Field(default=True)
    is_global: bool = Field(default=False)


class RoleRead(SQLModel):
    """Schema for reading role data."""

    id: UUID
    name: str
    description: str | None
    is_system: bool
    is_global: bool


class RoleUpdate(SQLModel):
    """Schema for updating an existing role."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_system: bool | None = None
    is_global: bool | None = None
