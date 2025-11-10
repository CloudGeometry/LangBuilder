from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import Index, UniqueConstraint
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
        Index("idx_user_role_assignment_lookup", "user_id", "scope_type", "scope_id"),
        Index("idx_user_role_assignment_user", "user_id"),
        Index("idx_user_role_assignment_scope", "scope_type", "scope_id"),
    )


class UserRoleAssignmentCreate(SQLModel):
    """Schema for creating a role assignment. Uses role_name instead of role_id for API convenience."""

    user_id: UUID
    role_name: str  # Role name instead of role_id for easier API usage
    scope_type: str
    scope_id: UUID | None = None
    created_by: UUID | None = None


class UserRoleAssignmentRead(UserRoleAssignmentBase):
    id: UUID
    created_at: datetime
    created_by: UUID | None


class UserRoleAssignmentReadWithRole(SQLModel):
    """UserRoleAssignment read schema with role relationship loaded."""

    id: UUID
    user_id: UUID
    role_id: UUID
    scope_type: str
    scope_id: UUID | None
    is_immutable: bool
    created_at: datetime
    created_by: UUID | None
    role: "RoleRead"  # Include role details

    class Config:
        from_attributes = True


# Import RoleRead for type checking
if TYPE_CHECKING:
    from langbuilder.services.database.models.role.model import RoleRead


class UserRoleAssignmentUpdate(SQLModel):
    """Schema for updating a role assignment. Uses role_name for changing the role."""

    role_name: str  # Only role can be updated via PATCH
