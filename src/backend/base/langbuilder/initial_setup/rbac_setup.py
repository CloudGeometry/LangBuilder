"""RBAC Seed Data Initialization Script.

This module provides functionality to populate the database with predefined RBAC
roles, permissions, and role-permission mappings. It runs during application startup
if RBAC tables are empty and is idempotent (safe to run multiple times).

Predefined Roles (per PRD 1.2):
- Admin: All permissions on all scopes (global assignment)
- Owner: Create, Read, Update, Delete on assigned scope
- Editor: Create, Read, Update (no Delete) on assigned scope
- Viewer: Read only on assigned scope

Predefined Permissions (per PRD 1.1, 1.2):
- Create (Flow, Project)
- Read (Flow, Project)
- Update (Flow, Project)
- Delete (Flow, Project)

Special Permission Rules (per PRD 1.2):
- Read permission enables: Flow execution, saving, exporting, downloading
- Update permission enables: Flow/Project import
"""

from loguru import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from langbuilder.services.database.models.rbac.permission import (
    Permission,
    PermissionAction,
    PermissionCreate,
    PermissionScope,
)
from langbuilder.services.database.models.rbac.role import Role, RoleCreate
from langbuilder.services.database.models.rbac.role_permission import RolePermission

# Predefined permission definitions (4 CRUD actions × 2 entity types = 8 permissions)
# Note: Permissions are uniquely identified by (action, scope) enum combination
PERMISSIONS = [
    # Flow permissions
    PermissionCreate(
        action=PermissionAction.CREATE,
        scope=PermissionScope.FLOW,
        description="Create new flows",
    ),
    PermissionCreate(
        action=PermissionAction.READ,
        scope=PermissionScope.FLOW,
        description="Read flows (enables execution, saving, exporting, downloading)",
    ),
    PermissionCreate(
        action=PermissionAction.UPDATE,
        scope=PermissionScope.FLOW,
        description="Update existing flows (enables import)",
    ),
    PermissionCreate(
        action=PermissionAction.DELETE,
        scope=PermissionScope.FLOW,
        description="Delete flows",
    ),
    # Project permissions
    PermissionCreate(
        action=PermissionAction.CREATE,
        scope=PermissionScope.PROJECT,
        description="Create new projects",
    ),
    PermissionCreate(
        action=PermissionAction.READ,
        scope=PermissionScope.PROJECT,
        description="Read projects",
    ),
    PermissionCreate(
        action=PermissionAction.UPDATE,
        scope=PermissionScope.PROJECT,
        description="Update existing projects (enables import)",
    ),
    PermissionCreate(
        action=PermissionAction.DELETE,
        scope=PermissionScope.PROJECT,
        description="Delete projects",
    ),
]

# Predefined role definitions
ROLES = [
    RoleCreate(
        name="Admin",
        description="Full administrative access with all permissions globally",
        is_system=True,
    ),
    RoleCreate(
        name="Owner",
        description="Complete control over assigned resources (all CRUD operations)",
        is_system=True,
    ),
    RoleCreate(
        name="Editor",
        description="Can create, read, and update assigned resources (no delete)",
        is_system=True,
    ),
    RoleCreate(
        name="Viewer",
        description="Read-only access to assigned resources",
        is_system=True,
    ),
]

# Role-permission mappings (per PRD 1.2)
# Maps role names to permission (action, scope) enum tuples
ROLE_PERMISSION_MAPPINGS = {
    "Admin": [
        (PermissionAction.CREATE, PermissionScope.FLOW),
        (PermissionAction.READ, PermissionScope.FLOW),
        (PermissionAction.UPDATE, PermissionScope.FLOW),
        (PermissionAction.DELETE, PermissionScope.FLOW),
        (PermissionAction.CREATE, PermissionScope.PROJECT),
        (PermissionAction.READ, PermissionScope.PROJECT),
        (PermissionAction.UPDATE, PermissionScope.PROJECT),
        (PermissionAction.DELETE, PermissionScope.PROJECT),
    ],  # All permissions on both Flow and Project
    "Owner": [
        (PermissionAction.CREATE, PermissionScope.FLOW),
        (PermissionAction.READ, PermissionScope.FLOW),
        (PermissionAction.UPDATE, PermissionScope.FLOW),
        (PermissionAction.DELETE, PermissionScope.FLOW),
        (PermissionAction.CREATE, PermissionScope.PROJECT),
        (PermissionAction.READ, PermissionScope.PROJECT),
        (PermissionAction.UPDATE, PermissionScope.PROJECT),
        (PermissionAction.DELETE, PermissionScope.PROJECT),
    ],  # All permissions on both Flow and Project
    "Editor": [
        (PermissionAction.CREATE, PermissionScope.FLOW),
        (PermissionAction.READ, PermissionScope.FLOW),
        (PermissionAction.UPDATE, PermissionScope.FLOW),
        (PermissionAction.CREATE, PermissionScope.PROJECT),
        (PermissionAction.READ, PermissionScope.PROJECT),
        (PermissionAction.UPDATE, PermissionScope.PROJECT),
    ],  # No Delete permission
    "Viewer": [
        (PermissionAction.READ, PermissionScope.FLOW),
        (PermissionAction.READ, PermissionScope.PROJECT),
    ],  # Read-only permission
}


async def initialize_rbac_data(session: AsyncSession) -> None:
    """Initialize RBAC data by populating roles, permissions, and role-permission mappings.

    This function is idempotent - it safely checks for existing data before inserting.
    It should be called during application startup to ensure RBAC tables are populated.

    Args:
        session: AsyncSession instance for database operations

    Raises:
        Exception: If database operations fail
    """
    try:
        logger.debug("Starting RBAC data initialization")

        # Check if RBAC data already exists (idempotent check)
        existing_roles_count = await _count_existing_roles(session)
        existing_permissions_count = await _count_existing_permissions(session)

        if existing_roles_count > 0 and existing_permissions_count > 0:
            logger.debug(
                f"RBAC data already initialized (found {existing_roles_count} roles, "
                f"{existing_permissions_count} permissions). Skipping initialization."
            )
            return

        # Step 1: Create permissions
        logger.debug("Creating RBAC permissions")
        permissions_map = await _create_permissions(session)
        logger.debug(f"Created {len(permissions_map)} permissions")

        # Step 2: Create roles
        logger.debug("Creating RBAC roles")
        roles_map = await _create_roles(session)
        logger.debug(f"Created {len(roles_map)} roles")

        # Step 3: Create role-permission mappings
        logger.debug("Creating role-permission mappings")
        mappings_count = await _create_role_permission_mappings(session, roles_map, permissions_map)
        logger.debug(f"Created {mappings_count} role-permission mappings")

        # Commit all changes
        await session.commit()
        logger.info("RBAC data initialization completed successfully")

    except Exception:
        logger.exception("Error during RBAC data initialization")
        await session.rollback()
        raise


async def _count_existing_roles(session: AsyncSession) -> int:
    """Count existing roles in the database."""
    stmt = select(Role)
    result = await session.exec(stmt)
    roles = result.all()
    return len(roles)


async def _count_existing_permissions(session: AsyncSession) -> int:
    """Count existing permissions in the database."""
    stmt = select(Permission)
    result = await session.exec(stmt)
    permissions = result.all()
    return len(permissions)


async def _create_permissions(
    session: AsyncSession,
) -> dict[tuple[PermissionAction, PermissionScope], Permission]:
    """Create all predefined permissions.

    Returns:
        Dictionary mapping (action, scope) enum tuples to Permission instances
    """
    permissions_map: dict[tuple[PermissionAction, PermissionScope], Permission] = {}

    for perm_create in PERMISSIONS:
        # Check if permission already exists
        stmt = select(Permission).where(
            Permission.action == perm_create.action,
            Permission.scope == perm_create.scope,
        )
        result = await session.exec(stmt)
        existing_perm = result.first()

        if existing_perm:
            logger.debug(
                f"Permission '{perm_create.action.value}' for scope '{perm_create.scope.value}' already exists"
            )
            permissions_map[(perm_create.action, perm_create.scope)] = existing_perm
        else:
            # Create new permission
            permission = Permission.model_validate(perm_create, from_attributes=True)
            session.add(permission)
            await session.flush()  # Ensure ID is generated
            permissions_map[(perm_create.action, perm_create.scope)] = permission
            logger.debug(f"Created permission '{perm_create.action.value}' for scope '{perm_create.scope.value}'")

    return permissions_map


async def _create_roles(session: AsyncSession) -> dict[str, Role]:
    """Create all predefined roles.

    Returns:
        Dictionary mapping role names to Role instances
    """
    roles_map: dict[str, Role] = {}

    for role_create in ROLES:
        # Check if role already exists
        stmt = select(Role).where(Role.name == role_create.name)
        result = await session.exec(stmt)
        existing_role = result.first()

        if existing_role:
            logger.debug(f"Role '{role_create.name}' already exists")
            roles_map[role_create.name] = existing_role
        else:
            # Create new role
            role = Role.model_validate(role_create, from_attributes=True)
            session.add(role)
            await session.flush()  # Ensure ID is generated
            roles_map[role_create.name] = role
            logger.debug(f"Created role '{role_create.name}'")

    return roles_map


async def _create_role_permission_mappings(
    session: AsyncSession,
    roles_map: dict[str, Role],
    permissions_map: dict[tuple[PermissionAction, PermissionScope], Permission],
) -> int:
    """Create role-permission mappings based on ROLE_PERMISSION_MAPPINGS.

    Args:
        session: Database session
        roles_map: Dictionary mapping role names to Role instances
        permissions_map: Dictionary mapping (action, scope) enum tuples to Permission instances

    Returns:
        Number of role-permission mappings created
    """
    mappings_created = 0

    for role_name, permission_keys in ROLE_PERMISSION_MAPPINGS.items():
        role = roles_map.get(role_name)
        if not role:
            logger.warning(f"Role '{role_name}' not found in roles_map, skipping mappings")
            continue

        # For each permission key (action, scope) enum tuple, find and map it
        for permission_key in permission_keys:
            permission = permissions_map.get(permission_key)

            if permission:
                if not await _role_permission_exists(session, role.id, permission.id):
                    role_perm = RolePermission(role_id=role.id, permission_id=permission.id)
                    session.add(role_perm)
                    mappings_created += 1
                    action, scope = permission_key
                    logger.debug(f"Mapped role '{role_name}' to permission '{action.value}:{scope.value}'")
            else:
                action, scope = permission_key
                logger.warning(f"Permission '{action.value}:{scope.value}' not found in permissions_map")

    await session.flush()
    return mappings_created


async def _role_permission_exists(session: AsyncSession, role_id, permission_id) -> bool:
    """Check if a role-permission mapping already exists."""
    stmt = select(RolePermission).where(
        RolePermission.role_id == role_id,
        RolePermission.permission_id == permission_id,
    )
    result = await session.exec(stmt)
    return result.first() is not None
