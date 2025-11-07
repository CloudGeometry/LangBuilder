"""UserRoleAssignment model for RBAC."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Index, Relationship, SQLModel, UniqueConstraint

if TYPE_CHECKING:
    from langbuilder.services.database.models.rbac.role import Role
    from langbuilder.services.database.models.user.model import User


class UserRoleAssignment(SQLModel, table=True):
    """UserRoleAssignment model representing the assignment of roles to users for specific scopes.

    This is the core assignment table that drives all permission checks. It supports
    polymorphic scope relationships (global, project, flow) and includes immutability
    tracking for Starter Project Owner assignments.

    Attributes:
        id: Unique identifier for the assignment
        user_id: Foreign key to the User model
        role_id: Foreign key to the Role model
        scope_type: Type of scope ("global", "project", "flow")
        scope_id: Optional ID of the scoped entity (None for global scope)
        is_immutable: Flag to prevent deletion (for Starter Project Owner assignments)
        created_at: Timestamp when the assignment was created
        created_by: Optional user ID who created the assignment

    Relationships:
        user: The user who has this role assignment
        role: The role assigned to the user

    Constraints:
        - Unique constraint on (user_id, role_id, scope_type, scope_id) to prevent duplicates
        - Composite index on (user_id, scope_type, scope_id) for efficient permission lookups
    """

    __tablename__ = "user_role_assignment"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    role_id: UUID = Field(foreign_key="role.id", index=True)

    # Polymorphic scope
    scope_type: str = Field(index=True)  # "global", "project", "flow"
    scope_id: UUID | None = Field(default=None, nullable=True, index=True)

    # Immutability tracking (for Starter Project Owner)
    is_immutable: bool = Field(default=False)

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: UUID | None = Field(default=None, foreign_key="user.id", nullable=True)

    # Relationships
    user: "User" = Relationship(
        back_populates="role_assignments",
        sa_relationship_kwargs={
            "foreign_keys": "[UserRoleAssignment.user_id]",
            "lazy": "select",
        },
    )
    role: "Role" = Relationship(
        back_populates="user_assignments",
        sa_relationship_kwargs={"lazy": "select"},
    )

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "scope_type", "scope_id", name="unique_user_role_scope"),
        Index("idx_scope_lookup", "user_id", "scope_type", "scope_id"),
    )


class UserRoleAssignmentCreate(SQLModel):
    """Schema for creating a new user role assignment."""

    user_id: UUID
    role_id: UUID
    scope_type: str = Field(min_length=1, max_length=50)
    scope_id: UUID | None = Field(default=None)
    is_immutable: bool = Field(default=False)
    created_by: UUID | None = Field(default=None)


class UserRoleAssignmentRead(SQLModel):
    """Schema for reading user role assignment data."""

    id: UUID
    user_id: UUID
    role_id: UUID
    scope_type: str
    scope_id: UUID | None
    is_immutable: bool
    created_at: datetime
    created_by: UUID | None


class UserRoleAssignmentUpdate(SQLModel):
    """Schema for updating an existing user role assignment.

    Note: Most fields should not be updated after creation. This schema is provided
    for completeness, but typical usage would be to delete and recreate assignments
    rather than update them. The is_immutable flag should prevent updates to
    immutable assignments.
    """

    user_id: UUID | None = None
    role_id: UUID | None = None
    scope_type: str | None = Field(default=None, min_length=1, max_length=50)
    scope_id: UUID | None = None
    is_immutable: bool | None = None
    created_by: UUID | None = None
