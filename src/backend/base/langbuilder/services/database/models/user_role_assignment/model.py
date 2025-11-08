from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from langbuilder.services.database.models.role.model import Role
    from langbuilder.services.database.models.user.model import User


class UserRoleAssignmentBase(SQLModel):
    user_id: UUID = Field(foreign_key="user.id", index=True)
    role_id: UUID = Field(foreign_key="role.id", index=True)
    scope_type: str = Field(index=True)
    scope_id: UUID | None = Field(default=None, index=True)
    is_immutable: bool = Field(default=False)


class UserRoleAssignment(UserRoleAssignmentBase, table=True):  # type: ignore[call-arg]
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: UUID | None = Field(default=None, foreign_key="user.id", nullable=True)

    # Relationships
    user: "User" = Relationship(sa_relationship_kwargs={"foreign_keys": "[UserRoleAssignment.user_id]"})
    role: "Role" = Relationship(back_populates="user_assignments")
    creator: Optional["User"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[UserRoleAssignment.created_by]"})

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "scope_type", "scope_id", name="unique_user_role_scope"),
    )


class UserRoleAssignmentCreate(UserRoleAssignmentBase):
    created_by: UUID | None = None


class UserRoleAssignmentRead(UserRoleAssignmentBase):
    id: UUID
    created_at: datetime
    created_by: UUID | None


class UserRoleAssignmentUpdate(SQLModel):
    user_id: UUID | None = None
    role_id: UUID | None = None
    scope_type: str | None = None
    scope_id: UUID | None = None
    is_immutable: bool | None = None
    created_by: UUID | None = None
