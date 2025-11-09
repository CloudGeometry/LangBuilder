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
