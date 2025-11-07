from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

if TYPE_CHECKING:
    from langbuilder.services.database.models.rbac.permission import Permission
    from langbuilder.services.database.models.rbac.role import Role


class RolePermission(SQLModel, table=True):
    """Junction table representing the many-to-many relationship between roles and permissions.

    This table defines which permissions each role has. For example:
    - Viewer role has only Read permission
    - Owner role has all CRUD permissions (Create, Read, Update, Delete)
    - Editor role has Create, Read, and Update permissions

    The composite unique constraint ensures that each role-permission pair
    can only be assigned once.
    """

    __tablename__ = "role_permission"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    role_id: UUID = Field(foreign_key="role.id", index=True)
    permission_id: UUID = Field(foreign_key="permission.id", index=True)

    # Relationships - using TYPE_CHECKING to avoid circular imports
    role: "Role" = Relationship(
        back_populates="role_permissions",
        sa_relationship_kwargs={"lazy": "select"},
    )
    permission: "Permission" = Relationship(
        back_populates="role_permissions",
        sa_relationship_kwargs={"lazy": "select"},
    )

    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="unique_role_permission"),)


class RolePermissionCreate(SQLModel):
    """Schema for creating a new role-permission association."""

    role_id: UUID
    permission_id: UUID


class RolePermissionRead(SQLModel):
    """Schema for reading role-permission association data."""

    id: UUID
    role_id: UUID
    permission_id: UUID


class RolePermissionUpdate(SQLModel):
    """Schema for updating a role-permission association.

    Note: In practice, role-permission associations are typically deleted and
    recreated rather than updated, but this schema is provided for completeness.
    """

    role_id: UUID | None = None
    permission_id: UUID | None = None
