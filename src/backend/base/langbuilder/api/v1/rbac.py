"""RBAC API endpoints for role and assignment management.

This module provides Admin-only API endpoints for managing RBAC roles and assignments.
All endpoints require Admin privileges (superuser or Global Admin role).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from langbuilder.api.utils import CurrentActiveUser, DbSession
from langbuilder.services.database.models.role.crud import get_all_roles
from langbuilder.services.database.models.role.model import RoleRead
from langbuilder.services.database.models.user_role_assignment.model import (
    UserRoleAssignmentCreate,
    UserRoleAssignmentReadWithRole,
    UserRoleAssignmentUpdate,
)
from langbuilder.services.database.models.user_role_assignment.schema import (
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionCheckResult,
)
from langbuilder.services.deps import RBACServiceDep
from langbuilder.services.rbac.exceptions import (
    AssignmentNotFoundException,
    DuplicateAssignmentException,
    ImmutableAssignmentException,
    InvalidScopeException,
    ResourceNotFoundException,
    RoleNotFoundException,
    UserNotFoundException,
)

router = APIRouter(prefix="/rbac", tags=["RBAC"])


async def require_admin(current_user: CurrentActiveUser) -> CurrentActiveUser:
    """Ensure current user is an Admin (superuser or Global Admin role).

    This dependency enforces Admin-only access for all RBAC management endpoints.
    Checks both is_superuser flag and Global Admin role assignment.

    Args:
        current_user: The current authenticated user

    Returns:
        CurrentActiveUser: The current user if authorized

    Raises:
        HTTPException: 403 if user is not an Admin

    Security:
        - Superusers bypass all RBAC checks
        - Global Admin role provides administrative privileges
        - This check is applied to all RBAC management endpoints
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


AdminUser = Annotated[CurrentActiveUser, Depends(require_admin)]


@router.get("/roles", response_model=list[RoleRead])
async def list_roles(
    admin: AdminUser,  # noqa: ARG001
    db: DbSession,
):
    """List all available roles.

    Returns all roles defined in the system (Admin, Owner, Editor, Viewer).
    This endpoint is used by the Admin UI to populate role selection dropdowns.

    Args:
        admin: The current admin user (dependency injection)
        db: Database session (dependency injection)

    Returns:
        list[RoleRead]: List of all roles

    Requires:
        Admin privileges (superuser or Global Admin role)

    Example Response:
        ```json
        [
            {
                "id": "uuid",
                "name": "Admin",
                "description": "Global administrator with full access",
                "is_system_role": true,
                "created_at": "2024-01-01T00:00:00Z"
            },
            ...
        ]
        ```
    """
    roles = await get_all_roles(db)
    return [RoleRead.model_validate(role) for role in roles]


@router.get("/assignments", response_model=list[UserRoleAssignmentReadWithRole])
async def list_assignments(
    admin: AdminUser,  # noqa: ARG001
    db: DbSession,
    rbac: RBACServiceDep,
    user_id: UUID | None = None,
    role_name: str | None = None,
    scope_type: str | None = None,
):
    """List all role assignments with optional filtering.

    Retrieves role assignments with role details loaded. Supports filtering by
    user, role name, and scope type to narrow down results.

    Args:
        admin: The current admin user (dependency injection)
        db: Database session (dependency injection)
        rbac: RBAC service instance (dependency injection)
        user_id: Optional filter by user ID
        role_name: Optional filter by role name (e.g., "Admin", "Owner")
        scope_type: Optional filter by scope type (e.g., "Global", "Project", "Flow")

    Returns:
        list[UserRoleAssignmentReadWithRole]: List of role assignments with role details

    Requires:
        Admin privileges (superuser or Global Admin role)

    Example Response:
        ```json
        [
            {
                "id": "uuid",
                "user_id": "uuid",
                "role_id": "uuid",
                "scope_type": "Project",
                "scope_id": "uuid",
                "is_immutable": false,
                "created_at": "2024-01-01T00:00:00Z",
                "created_by": "uuid",
                "role": {
                    "id": "uuid",
                    "name": "Owner",
                    "description": "Project owner with full control",
                    "is_system_role": true,
                    "created_at": "2024-01-01T00:00:00Z"
                }
            },
            ...
        ]
        ```
    """
    assignments = await rbac.list_user_assignments(user_id, db)

    # Apply filters
    if role_name:
        assignments = [a for a in assignments if a.role.name == role_name]
    if scope_type:
        assignments = [a for a in assignments if a.scope_type == scope_type]

    return [UserRoleAssignmentReadWithRole.model_validate(a) for a in assignments]


@router.post("/assignments", response_model=UserRoleAssignmentReadWithRole, status_code=201)
async def create_assignment(
    assignment: UserRoleAssignmentCreate,
    admin: AdminUser,
    db: DbSession,
    rbac: RBACServiceDep,
):
    """Create a new role assignment.

    Assigns a role to a user for a specific scope. Validates that the user exists,
    role exists, and no duplicate assignment exists. For Flow scope, validates that
    the flow exists. For Project scope, validates that the project (folder) exists.

    Args:
        assignment: The assignment data to create
        admin: The current admin user (dependency injection)
        db: Database session (dependency injection)
        rbac: RBAC service instance (dependency injection)

    Returns:
        UserRoleAssignmentReadWithRole: The created assignment with role details

    Requires:
        Admin privileges (superuser or Global Admin role)

    Raises:
        HTTPException:
            - 400: Duplicate assignment or invalid data
            - 404: User, role, or scope resource not found

    Validation:
        - User must exist
        - Role must exist
        - Scope resource must exist (Flow or Project)
        - No duplicate assignment (user + role + scope combination must be unique)

    Security:
        - Cannot create assignments for immutable scopes (handled by is_immutable flag)
        - Assignment creator is recorded for audit trail

    Example Request:
        ```json
        {
            "user_id": "uuid",
            "role_name": "Owner",
            "scope_type": "Project",
            "scope_id": "uuid"
        }
        ```
    """
    try:
        created_assignment = await rbac.assign_role(
            user_id=assignment.user_id,
            role_name=assignment.role_name,
            scope_type=assignment.scope_type,
            scope_id=assignment.scope_id,
            created_by=admin.id,
            db=db,
        )

        # Load the role relationship
        await db.refresh(created_assignment, ["role"])

        return UserRoleAssignmentReadWithRole.model_validate(created_assignment)
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e.detail)) from e
    except RoleNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e.detail)) from e
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e.detail)) from e
    except InvalidScopeException as e:
        raise HTTPException(status_code=400, detail=str(e.detail)) from e
    except DuplicateAssignmentException as e:
        raise HTTPException(status_code=409, detail=str(e.detail)) from e


@router.patch("/assignments/{assignment_id}", response_model=UserRoleAssignmentReadWithRole)
async def update_assignment(
    assignment_id: UUID,
    assignment_update: UserRoleAssignmentUpdate,
    admin: AdminUser,  # noqa: ARG001
    db: DbSession,
    rbac: RBACServiceDep,
):
    """Update an existing role assignment (change role only).

    Allows changing the role of an existing assignment. Cannot modify immutable
    assignments (e.g., Starter Project Owner). Only the role can be changed;
    to change user or scope, delete and create a new assignment.

    Args:
        assignment_id: The ID of the assignment to update
        assignment_update: The update data (role_name)
        admin: The current admin user (dependency injection)
        db: Database session (dependency injection)
        rbac: RBAC service instance (dependency injection)

    Returns:
        UserRoleAssignmentReadWithRole: The updated assignment with role details

    Requires:
        Admin privileges (superuser or Global Admin role)

    Raises:
        HTTPException:
            - 400: Assignment is immutable or invalid data
            - 404: Assignment or new role not found

    Validation:
        - Assignment must exist
        - Assignment must not be immutable
        - New role must exist

    Security:
        - Immutable assignments (e.g., Starter Project Owner) cannot be modified
        - Prevents unauthorized privilege escalation

    Example Request:
        ```json
        {
            "role_name": "Editor"
        }
        ```
    """
    try:
        updated_assignment = await rbac.update_role(
            assignment_id=assignment_id,
            new_role_name=assignment_update.role_name,
            db=db,
        )

        # Load the role relationship
        await db.refresh(updated_assignment, ["role"])

        return UserRoleAssignmentReadWithRole.model_validate(updated_assignment)
    except AssignmentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ImmutableAssignmentException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RoleNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/assignments/{assignment_id}", status_code=204)
async def delete_assignment(
    assignment_id: UUID,
    admin: AdminUser,  # noqa: ARG001
    db: DbSession,
    rbac: RBACServiceDep,
):
    """Delete a role assignment.

    Removes a role assignment from a user. Cannot delete immutable assignments
    (e.g., Starter Project Owner). Use with caution as this immediately revokes
    the user's access to the associated resource.

    Args:
        assignment_id: The ID of the assignment to delete
        admin: The current admin user (dependency injection)
        db: Database session (dependency injection)
        rbac: RBAC service instance (dependency injection)

    Returns:
        Response: 204 No Content on success

    Requires:
        Admin privileges (superuser or Global Admin role)

    Raises:
        HTTPException:
            - 400: Assignment is immutable
            - 404: Assignment not found

    Validation:
        - Assignment must exist
        - Assignment must not be immutable

    Security:
        - Immutable assignments (e.g., Starter Project Owner) cannot be deleted
        - Immediately revokes user access to the resource
        - Use with caution to avoid unintended access loss

    Warning:
        Deleting a role assignment immediately revokes the user's access.
        Ensure this is the intended action before proceeding.
    """
    try:
        await rbac.remove_role(assignment_id, db)
        return Response(status_code=204)
    except AssignmentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ImmutableAssignmentException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/check-permission")
async def check_permission(
    current_user: CurrentActiveUser,
    db: DbSession,
    rbac: RBACServiceDep,
    permission: str,
    scope_type: str,
    scope_id: UUID | None = None,
):
    """Check if current user has a specific permission.

    This endpoint is used by the frontend to determine whether to show or hide
    UI elements based on the user's permissions. It performs the same authorization
    check as the @require_permission decorator.

    Args:
        current_user: The current authenticated user (dependency injection)
        db: Database session (dependency injection)
        rbac: RBAC service instance (dependency injection)
        permission: Permission name (e.g., "Create", "Read", "Update", "Delete")
        scope_type: Scope type (e.g., "Global", "Project", "Flow")
        scope_id: Optional scope ID for Project/Flow scope

    Returns:
        dict: {"has_permission": bool}

    Note:
        - This endpoint is available to all authenticated users (not Admin-only)
        - Superusers always have permission
        - Global Admin role bypasses all checks
        - Permission inheritance: Flow permissions inherit from Project

    Example Request:
        ```
        GET /api/v1/rbac/check-permission?permission=Update&scope_type=Flow&scope_id=uuid
        ```

    Example Response:
        ```json
        {
            "has_permission": true
        }
        ```

    Use Case:
        Frontend components can use this endpoint to conditionally render UI elements:
        - Show/hide edit buttons
        - Enable/disable form fields
        - Display permission-denied messages
    """
    has_permission = await rbac.can_access(
        current_user.id,
        permission,
        scope_type,
        scope_id,
        db,
    )

    return {"has_permission": has_permission}


@router.post("/check-permissions", response_model=PermissionCheckResponse)
async def check_permissions(
    request: PermissionCheckRequest,
    current_user: CurrentActiveUser,
    db: DbSession,
    rbac: RBACServiceDep,
):
    """Check multiple permissions in a single request.

    This endpoint optimizes frontend permission checks by allowing multiple
    permission checks to be performed in a single HTTP request, reducing
    network round trips and improving performance.

    Args:
        request: Batch permission check request containing list of checks
        current_user: The current authenticated user (dependency injection)
        db: Database session (dependency injection)
        rbac: RBAC service instance (dependency injection)

    Returns:
        PermissionCheckResponse: Results for each permission check

    Note:
        - This endpoint is available to all authenticated users (not Admin-only)
        - Maximum 100 permission checks per request (enforced by schema validation)
        - Superusers always have permission
        - Global Admin role bypasses all checks
        - Permission inheritance: Flow permissions inherit from Project

    Example Request:
        ```json
        {
            "checks": [
                {
                    "action": "Update",
                    "resource_type": "Flow",
                    "resource_id": "uuid"
                },
                {
                    "action": "Delete",
                    "resource_type": "Project",
                    "resource_id": "uuid"
                },
                {
                    "action": "Create",
                    "resource_type": "Global",
                    "resource_id": null
                }
            ]
        }
        ```

    Example Response:
        ```json
        {
            "results": [
                {
                    "action": "Update",
                    "resource_type": "Flow",
                    "resource_id": "uuid",
                    "allowed": true
                },
                {
                    "action": "Delete",
                    "resource_type": "Project",
                    "resource_id": "uuid",
                    "allowed": false
                },
                {
                    "action": "Create",
                    "resource_type": "Global",
                    "resource_id": null,
                    "allowed": true
                }
            ]
        }
        ```

    Use Case:
        Frontend can batch-check permissions for multiple resources when rendering
        lists or complex UIs, reducing API calls from N to 1.

    Performance:
        - Target: <100ms for 10 permission checks
        - Checks are performed sequentially (can be optimized to parallel in future)
        - Each check uses the same optimized RBAC logic as single check endpoint
    """
    results = []

    for check in request.checks:
        has_permission = await rbac.can_access(
            current_user.id,
            check.action,
            check.resource_type,
            check.resource_id,
            db,
        )

        results.append(
            PermissionCheckResult(
                action=check.action,
                resource_type=check.resource_type,
                resource_id=check.resource_id,
                allowed=has_permission,
            )
        )

    return PermissionCheckResponse(results=results)
