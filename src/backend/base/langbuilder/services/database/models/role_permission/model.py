from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from langbuilder.services.database.models.permission.model import Permission
    from langbuilder.services.database.models.role.model import Role


class RolePermissionBase(SQLModel):
    role_id: UUID = Field(foreign_key="role.id", index=True)
    permission_id: UUID = Field(foreign_key="permission.id", index=True)


class RolePermission(RolePermissionBase, table=True):  # type: ignore[call-arg]
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    role: "Role" = Relationship(back_populates="role_permissions")
    permission: "Permission" = Relationship(back_populates="role_permissions")

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="unique_role_permission"),
        Index("idx_role_permission_lookup", "role_id", "permission_id"),
    )


class RolePermissionCreate(RolePermissionBase):
    pass


class RolePermissionRead(RolePermissionBase):
    id: UUID
    created_at: datetime


class RolePermissionUpdate(SQLModel):
    role_id: UUID | None = None
    permission_id: UUID | None = None
