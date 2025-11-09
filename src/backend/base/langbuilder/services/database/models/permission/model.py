from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from langbuilder.services.database.models.role_permission.model import RolePermission


class PermissionBase(SQLModel):
    name: str = Field(index=True, nullable=False)
    scope: str = Field(index=True, nullable=False)
    description: str | None = Field(default=None)


class Permission(PermissionBase, table=True):  # type: ignore[call-arg]
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    role_permissions: list["RolePermission"] = Relationship(back_populates="permission")

    __table_args__ = (
        UniqueConstraint("name", "scope", name="unique_permission_scope"),
        Index("idx_permission_name_scope", "name", "scope"),
    )


class PermissionCreate(PermissionBase):
    pass


class PermissionRead(PermissionBase):
    id: UUID
    created_at: datetime


class PermissionUpdate(SQLModel):
    name: str | None = None
    scope: str | None = None
    description: str | None = None
