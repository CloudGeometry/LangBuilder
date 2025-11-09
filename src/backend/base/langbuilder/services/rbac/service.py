"""RBAC Service for permission checking and role management."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import select

from langbuilder.services.base import Service
from langbuilder.services.database.models.flow.model import Flow
from langbuilder.services.database.models.permission.model import Permission
from langbuilder.services.database.models.role.crud import get_role_by_name
from langbuilder.services.database.models.role.model import Role
from langbuilder.services.database.models.role_permission.model import RolePermission
from langbuilder.services.database.models.user.crud import get_user_by_id
from langbuilder.services.database.models.user_role_assignment.crud import (
    get_user_role_assignment,
    get_user_role_assignment_by_id,
    list_assignments_by_user,
)
from langbuilder.services.database.models.user_role_assignment.model import UserRoleAssignment
from langbuilder.services.rbac.exceptions import (
    AssignmentNotFoundException,
    DuplicateAssignmentException,
    ImmutableAssignmentException,
    RoleNotFoundException,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlmodel.ext.asyncio.session import AsyncSession


class RBACService(Service):
    """Role-Based Access Control service for permission checks and role management."""

    name = "rbac_service"

    async def can_access(
        self,
        user_id: UUID,
        permission_name: str,
        scope_type: str,
        scope_id: UUID | None,
        db: AsyncSession,
    ) -> bool:
        """Core authorization check. Returns True if user has permission.

        Logic:
        1. Check if user is superuser (bypass all checks)
        2. Check if user has Global Admin role (bypass all checks)
        3. For Flow scope:
           - Check for explicit Flow-level role assignment
           - If none, check for inherited Project-level role assignment
        4. For Project scope:
           - Check for explicit Project-level role assignment
        5. Check if role has the required permission

        Args:
            user_id: The user's ID
            permission_name: Permission name (e.g., "Create", "Read", "Update", "Delete")
            scope_type: Scope type (e.g., "Flow", "Project", "Global")
            scope_id: Specific resource ID (None for Global scope)
            db: Database session

        Returns:
            bool: True if user has permission, False otherwise
        """
        # 1. Superuser bypass
        user = await get_user_by_id(db, user_id)
        if user and user.is_superuser:
            return True

        # 2. Global Admin role bypass
        if await self._has_global_admin_role(user_id, db):
            return True

        # 3. Get user's role for the scope
        role = await self._get_user_role_for_scope(user_id, scope_type, scope_id, db)

        if not role:
            return False

        # 4. Check if role has the permission
        return await self._role_has_permission(role.id, permission_name, scope_type, db)

    async def _has_global_admin_role(self, user_id: UUID, db: AsyncSession) -> bool:
        """Check if user has Global Admin role.

        Args:
            user_id: The user's ID
            db: Database session

        Returns:
            bool: True if user has Global Admin role, False otherwise
        """
        stmt = (
            select(UserRoleAssignment)
            .where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.scope_type == "Global",
            )
            .join(Role)
            .where(Role.name == "Admin")
        )

        result = await db.exec(stmt)
        return result.first() is not None

    async def _get_user_role_for_scope(
        self,
        user_id: UUID,
        scope_type: str,
        scope_id: UUID | None,
        db: AsyncSession,
    ) -> Role | None:
        """Get user's role for a specific scope.

        For Flow scope: checks Flow-specific assignment first, then inherited Project assignment.

        Args:
            user_id: The user's ID
            scope_type: Scope type (e.g., "Flow", "Project", "Global")
            scope_id: Specific resource ID (None for Global scope)
            db: Database session

        Returns:
            Role | None: The user's role for the scope, or None if no assignment exists
        """
        # Check for explicit scope assignment
        stmt = (
            select(UserRoleAssignment)
            .where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.scope_type == scope_type,
                UserRoleAssignment.scope_id == scope_id,
            )
            .join(Role)
        )

        result = await db.exec(stmt)
        assignment = result.first()

        if assignment:
            return assignment.role

        # For Flow scope, check inherited Project role
        if scope_type == "Flow" and scope_id:
            flow_stmt = select(Flow).where(Flow.id == scope_id)
            flow_result = await db.exec(flow_stmt)
            flow = flow_result.first()

            if flow and flow.folder_id:
                return await self._get_user_role_for_scope(user_id, "Project", flow.folder_id, db)

        return None

    async def _role_has_permission(
        self,
        role_id: UUID,
        permission_name: str,
        scope_type: str,
        db: AsyncSession,
    ) -> bool:
        """Check if role has a specific permission.

        Args:
            role_id: The role's ID
            permission_name: Permission name (e.g., "Create", "Read")
            scope_type: Scope type (e.g., "Flow", "Project")
            db: Database session

        Returns:
            bool: True if role has the permission, False otherwise
        """
        stmt = (
            select(RolePermission)
            .where(RolePermission.role_id == role_id)
            .join(Permission)
            .where(
                Permission.name == permission_name,
                Permission.scope == scope_type,
            )
        )

        result = await db.exec(stmt)
        return result.first() is not None

    async def assign_role(
        self,
        user_id: UUID,
        role_name: str,
        scope_type: str,
        scope_id: UUID | None,
        created_by: UUID,
        db: AsyncSession,
        is_immutable: bool = False,  # noqa: FBT001, FBT002
    ) -> UserRoleAssignment:
        """Create a new role assignment.

        Args:
            user_id: The user's ID
            role_name: The role name to assign
            scope_type: Scope type (e.g., "Flow", "Project", "Global")
            scope_id: Specific resource ID (None for Global scope)
            created_by: ID of user creating the assignment
            db: Database session
            is_immutable: Whether assignment is immutable (cannot be modified/deleted)

        Returns:
            UserRoleAssignment: The created assignment

        Raises:
            RoleNotFoundException: If role not found
            DuplicateAssignmentException: If assignment already exists
        """
        # Get role by name
        role = await get_role_by_name(db, role_name)
        if not role:
            raise RoleNotFoundException(role_name)

        # Check for duplicate assignment
        existing = await get_user_role_assignment(db, user_id, role.id, scope_type, scope_id)
        if existing:
            raise DuplicateAssignmentException

        # Create assignment
        assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=role.id,
            scope_type=scope_type,
            scope_id=scope_id,
            is_immutable=is_immutable,
            created_by=created_by,
        )

        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)

        return assignment

    async def remove_role(
        self,
        assignment_id: UUID,
        db: AsyncSession,
    ) -> None:
        """Remove a role assignment (if not immutable).

        Args:
            assignment_id: The assignment's ID
            db: Database session

        Raises:
            AssignmentNotFoundException: If assignment not found
            ImmutableAssignmentException: If assignment is immutable
        """
        assignment = await get_user_role_assignment_by_id(db, assignment_id)

        if not assignment:
            raise AssignmentNotFoundException(str(assignment_id))

        if assignment.is_immutable:
            raise ImmutableAssignmentException(operation="remove")

        await db.delete(assignment)
        await db.commit()

    async def update_role(
        self,
        assignment_id: UUID,
        new_role_name: str,
        db: AsyncSession,
    ) -> UserRoleAssignment:
        """Update an existing role assignment (if not immutable).

        Args:
            assignment_id: The assignment's ID
            new_role_name: The new role name
            db: Database session

        Returns:
            UserRoleAssignment: The updated assignment

        Raises:
            AssignmentNotFoundException: If assignment not found
            ImmutableAssignmentException: If assignment is immutable
            RoleNotFoundException: If new role not found
        """
        assignment = await get_user_role_assignment_by_id(db, assignment_id)

        if not assignment:
            raise AssignmentNotFoundException(str(assignment_id))

        if assignment.is_immutable:
            raise ImmutableAssignmentException(operation="modify")

        new_role = await get_role_by_name(db, new_role_name)
        if not new_role:
            raise RoleNotFoundException(new_role_name)

        assignment.role_id = new_role.id
        await db.commit()
        await db.refresh(assignment)

        return assignment

    async def list_user_assignments(
        self,
        user_id: UUID | None,
        db: AsyncSession,
    ) -> list[UserRoleAssignment]:
        """List all role assignments, optionally filtered by user.

        Args:
            user_id: Optional user ID to filter assignments
            db: Database session

        Returns:
            list[UserRoleAssignment]: List of role assignments
        """
        if user_id:
            return await list_assignments_by_user(db, user_id)

        stmt = select(UserRoleAssignment)
        result = await db.exec(stmt)
        return list(result.all())

    async def get_user_permissions_for_scope(
        self,
        user_id: UUID,
        scope_type: str,
        scope_id: UUID | None,
        db: AsyncSession,
    ) -> list[Permission]:
        """Get all permissions a user has for a specific scope.

        Args:
            user_id: The user's ID
            scope_type: Scope type (e.g., "Flow", "Project", "Global")
            scope_id: Specific resource ID (None for Global scope)
            db: Database session

        Returns:
            list[Permission]: List of permissions user has for the scope
        """
        role = await self._get_user_role_for_scope(user_id, scope_type, scope_id, db)

        if not role:
            return []

        stmt = (
            select(Permission)
            .join(RolePermission)
            .where(
                RolePermission.role_id == role.id,
                Permission.scope == scope_type,
            )
        )

        result = await db.exec(stmt)
        return list(result.all())
