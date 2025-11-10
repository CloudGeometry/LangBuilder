"""Custom exceptions for RBAC service."""

from fastapi import HTTPException, status


class RBACException(HTTPException):
    """Base exception for RBAC-related errors."""

    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
        """Initialize RBACException.

        Args:
            detail: Error message detail
            status_code: HTTP status code (default: 400 Bad Request)
        """
        super().__init__(status_code=status_code, detail=detail)


class RoleNotFoundException(RBACException):
    """Raised when a role is not found."""

    def __init__(self, role_name: str) -> None:
        """Initialize RoleNotFoundException.

        Args:
            role_name: Name of the role that was not found
        """
        super().__init__(
            detail=f"Role '{role_name}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class AssignmentNotFoundException(RBACException):
    """Raised when a role assignment is not found."""

    def __init__(self, assignment_id: str) -> None:
        """Initialize AssignmentNotFoundException.

        Args:
            assignment_id: ID of the assignment that was not found
        """
        super().__init__(
            detail=f"Assignment '{assignment_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class DuplicateAssignmentException(RBACException):
    """Raised when attempting to create a duplicate role assignment."""

    def __init__(self) -> None:
        """Initialize DuplicateAssignmentException."""
        super().__init__(
            detail="Role assignment already exists",
            status_code=status.HTTP_409_CONFLICT,
        )


class ImmutableAssignmentException(RBACException):
    """Raised when attempting to modify or delete an immutable assignment."""

    def __init__(self, operation: str = "modify") -> None:
        """Initialize ImmutableAssignmentException.

        Args:
            operation: Operation being attempted (e.g., "modify", "remove")
        """
        super().__init__(
            detail=f"Cannot {operation} immutable assignment (Starter Project Owner)",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class PermissionDeniedException(RBACException):
    """Raised when a user does not have permission to perform an action."""

    def __init__(self, action: str, resource: str) -> None:
        """Initialize PermissionDeniedException.

        Args:
            action: Action being attempted
            resource: Resource being accessed
        """
        super().__init__(
            detail=f"Permission denied: Cannot {action} {resource}",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class UserNotFoundException(RBACException):
    """Raised when a user is not found."""

    def __init__(self, user_id: str) -> None:
        """Initialize UserNotFoundException.

        Args:
            user_id: ID of the user that was not found
        """
        super().__init__(
            detail=f"User '{user_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ResourceNotFoundException(RBACException):
    """Raised when a resource (Flow or Project) is not found."""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        """Initialize ResourceNotFoundException.

        Args:
            resource_type: Type of resource (e.g., "Flow", "Project")
            resource_id: ID of the resource that was not found
        """
        super().__init__(
            detail=f"{resource_type} '{resource_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class InvalidScopeException(RBACException):
    """Raised when an invalid scope type or scope_id is provided."""

    def __init__(self, detail: str) -> None:
        """Initialize InvalidScopeException.

        Args:
            detail: Detailed error message explaining the invalid scope
        """
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
