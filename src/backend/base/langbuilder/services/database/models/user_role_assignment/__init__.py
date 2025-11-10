# Import ORM models and SQLModel schemas from model.py
# These are used for database operations and ORM queries
from .model import (
    UserRoleAssignment,
    UserRoleAssignmentCreate,
    UserRoleAssignmentRead,
    UserRoleAssignmentReadWithRole,
    UserRoleAssignmentUpdate,
)

# Import API-specific Pydantic schemas from schema.py
# These are unique to schema.py and have no naming conflicts
from .schema import (
    PermissionCheck,
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionCheckResult,
    RoleRead,
)

# Import API schemas with aliased names to resolve naming conflicts
# Both model.py and schema.py define UserRoleAssignmentCreate/Read/Update with the same names
# but different implementations (SQLModel vs Pydantic BaseModel)
#
# The aliased imports below provide access to the API-focused Pydantic schemas
# without conflicting with the ORM schemas imported above:
# - UserRoleAssignmentCreateSchema: API request schema with validation and denormalized fields
# - UserRoleAssignmentReadSchema: API response schema with denormalized role_name and scope_name
# - UserRoleAssignmentUpdateSchema: API update schema with validation
#
# Consumers should use the aliased versions when working with API endpoints
# and the non-aliased versions when working with the database/ORM layer
from .schema import UserRoleAssignmentCreate as UserRoleAssignmentCreateSchema
from .schema import UserRoleAssignmentRead as UserRoleAssignmentReadSchema
from .schema import UserRoleAssignmentUpdate as UserRoleAssignmentUpdateSchema

__all__ = [
    "PermissionCheck",
    "PermissionCheckRequest",
    "PermissionCheckResponse",
    "PermissionCheckResult",
    "RoleRead",
    "UserRoleAssignment",
    "UserRoleAssignmentCreate",
    "UserRoleAssignmentCreateSchema",
    "UserRoleAssignmentRead",
    "UserRoleAssignmentReadSchema",
    "UserRoleAssignmentReadWithRole",
    "UserRoleAssignmentUpdate",
    "UserRoleAssignmentUpdateSchema",
]
