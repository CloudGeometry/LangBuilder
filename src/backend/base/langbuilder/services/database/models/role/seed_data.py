"""Seed data for RBAC system initialization.

This module provides default roles and permissions for the LangBuilder RBAC system.
It defines 4 system roles (Viewer, Editor, Owner, Admin) and 8 permissions across
Flow and Project scopes.
"""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from langbuilder.services.database.models.permission.crud import (
    create_permission,
    get_permission_by_name_and_scope,
)
from langbuilder.services.database.models.permission.model import PermissionCreate
from langbuilder.services.database.models.role.crud import create_role, get_role_by_name
from langbuilder.services.database.models.role.model import RoleCreate
from langbuilder.services.database.models.role_permission.model import RolePermission

# Default permissions (4 actions x 2 scopes = 8 total)
DEFAULT_PERMISSIONS = [
    {"name": "Create", "scope": "Flow", "description": "Create new flows within a project"},
    {"name": "Read", "scope": "Flow", "description": "View/execute/export/download flows"},
    {"name": "Update", "scope": "Flow", "description": "Edit/import flows"},
    {"name": "Delete", "scope": "Flow", "description": "Delete flows"},
    {"name": "Create", "scope": "Project", "description": "Create new projects"},
    {"name": "Read", "scope": "Project", "description": "View projects"},
    {"name": "Update", "scope": "Project", "description": "Edit/import projects"},
    {"name": "Delete", "scope": "Project", "description": "Delete projects"},
]

# Default roles (4 system roles)
DEFAULT_ROLES = [
    {"name": "Viewer", "description": "Read-only access to resources", "is_system_role": True},
    {"name": "Editor", "description": "Create, read, and update access to resources", "is_system_role": True},
    {"name": "Owner", "description": "Full access to owned resources", "is_system_role": True},
    {"name": "Admin", "description": "Global administrator with full access", "is_system_role": True},
]

# Role to permission mappings
ROLE_PERMISSION_MAPPINGS = {
    "Viewer": [("Read", "Flow"), ("Read", "Project")],
    "Editor": [
        ("Create", "Flow"),
        ("Read", "Flow"),
        ("Update", "Flow"),
        ("Create", "Project"),
        ("Read", "Project"),
        ("Update", "Project"),
    ],
    "Owner": [
        ("Create", "Flow"),
        ("Read", "Flow"),
        ("Update", "Flow"),
        ("Delete", "Flow"),
        ("Create", "Project"),
        ("Read", "Project"),
        ("Update", "Project"),
        ("Delete", "Project"),
    ],
    "Admin": [
        ("Create", "Flow"),
        ("Read", "Flow"),
        ("Update", "Flow"),
        ("Delete", "Flow"),
        ("Create", "Project"),
        ("Read", "Project"),
        ("Update", "Project"),
        ("Delete", "Project"),
    ],
}


async def seed_rbac_data(db: AsyncSession) -> dict[str, int]:
    """Seed the database with default RBAC roles and permissions.

    This function is idempotent - it can be run multiple times safely.
    It will only create permissions and roles that don't already exist.

    Args:
        db: Async database session

    Returns:
        Dictionary with counts of created permissions, roles, and mappings:
        {
            "permissions_created": int,
            "roles_created": int,
            "mappings_created": int
        }
    """
    permissions_created = 0
    roles_created = 0
    mappings_created = 0

    # 1. Create permissions (idempotent - skip if already exists)
    for perm_data in DEFAULT_PERMISSIONS:
        existing = await get_permission_by_name_and_scope(db, perm_data["name"], perm_data["scope"])
        if not existing:
            perm = PermissionCreate(**perm_data)
            await create_permission(db, perm)
            permissions_created += 1

    # 2. Create roles (idempotent - skip if already exists)
    roles_map = {}
    for role_data in DEFAULT_ROLES:
        existing = await get_role_by_name(db, role_data["name"])
        if existing:
            roles_map[role_data["name"]] = existing
        else:
            role = RoleCreate(**role_data)
            created_role = await create_role(db, role)
            roles_map[role_data["name"]] = created_role
            roles_created += 1

    # 3. Map permissions to roles (idempotent - skip if mapping already exists)
    for role_name, perm_list in ROLE_PERMISSION_MAPPINGS.items():
        role = roles_map[role_name]
        for action, scope in perm_list:
            perm = await get_permission_by_name_and_scope(db, action, scope)
            if not perm:
                continue

            # Check if mapping already exists using a query
            stmt = select(RolePermission).where(
                RolePermission.role_id == role.id, RolePermission.permission_id == perm.id
            )
            result = await db.exec(stmt)
            existing_mapping = result.first()

            if not existing_mapping:
                role_perm = RolePermission(role_id=role.id, permission_id=perm.id)
                db.add(role_perm)
                mappings_created += 1

    await db.commit()

    return {
        "permissions_created": permissions_created,
        "roles_created": roles_created,
        "mappings_created": mappings_created,
    }
