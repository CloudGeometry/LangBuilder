"""RBAC system initialization for LangBuilder.

This module provides initialization logic to set up the RBAC system during
application startup. It ensures default roles and permissions are available.
"""

from loguru import logger
from sqlmodel import select

from langbuilder.services.database.models.role.model import Role
from langbuilder.services.database.models.role.seed_data import seed_rbac_data
from langbuilder.services.deps import session_scope


async def initialize_rbac_if_needed() -> None:
    """Initialize RBAC system with default roles and permissions if needed.

    This function checks if the RBAC system has been initialized by checking
    if any roles exist. If no roles exist, it seeds the database with default
    roles and permissions.

    This function is idempotent and safe to call multiple times.
    """
    async with session_scope() as session:
        # Check if RBAC is already initialized by looking for existing roles
        stmt = select(Role)
        result = await session.exec(stmt)
        existing_roles = result.all()

        if existing_roles:
            logger.debug(f"RBAC already initialized with {len(existing_roles)} roles")
            return

        # Seed the database with default RBAC data
        logger.info("Initializing RBAC system with default roles and permissions")
        result = await seed_rbac_data(session)

        logger.info(
            f"RBAC initialization complete: "
            f"{result['permissions_created']} permissions, "
            f"{result['roles_created']} roles, "
            f"{result['mappings_created']} role-permission mappings created"
        )
