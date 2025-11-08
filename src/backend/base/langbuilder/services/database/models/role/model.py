from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from langbuilder.services.database.models.role_permission.model import RolePermission
    from langbuilder.services.database.models.user_role_assignment.model import UserRoleAssignment


class RoleBase(SQLModel):
    name: str = Field(unique=True, index=True)
    description: str | None = Field(default=None)
    is_system_role: bool = Field(default=False)


class Role(RoleBase, table=True):  # type: ignore[call-arg]
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    role_permissions: list["RolePermission"] = Relationship(
        back_populates="role",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    user_assignments: list["UserRoleAssignment"] = Relationship(back_populates="role")


class RoleCreate(RoleBase):
    pass


class RoleRead(RoleBase):
    id: UUID
    created_at: datetime


class RoleUpdate(SQLModel):
    name: str | None = None
    description: str | None = None
    is_system_role: bool | None = None
