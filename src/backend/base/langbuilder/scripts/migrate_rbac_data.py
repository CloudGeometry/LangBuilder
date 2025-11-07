"""Data Migration Script for RBAC User Role Assignments.

This script migrates existing users, flows, and projects to RBAC role assignments.
It ensures backward compatibility by assigning appropriate roles to all existing
users based on their current ownership and permissions.

Migration Logic:
1. Superusers (is_superuser=True) receive global Admin role assignment
2. Regular users receive Owner role for each flow they own (user_id matches flow.user_id)
3. Regular users receive Owner role for each project they own (user_id matches folder.user_id)
4. Starter Project Owner assignments are marked as immutable (is_immutable=True)
5. Script is idempotent (safe to run multiple times)
6. Supports dry-run mode for pre-deployment testing

Usage:
    # As a module function (recommended)
    from langbuilder.scripts.migrate_rbac_data import migrate_existing_users_to_rbac
    result = await migrate_existing_users_to_rbac(session, dry_run=True)

    # As a standalone script
    python -m langbuilder.scripts.migrate_rbac_data --dry-run
"""

from typing import Any

from loguru import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from langbuilder.services.database.models.flow.model import Flow
from langbuilder.services.database.models.folder.model import Folder
from langbuilder.services.database.models.rbac.role import Role
from langbuilder.services.database.models.rbac.user_role_assignment import UserRoleAssignment
from langbuilder.services.database.models.user.model import User


async def migrate_existing_users_to_rbac(session: AsyncSession, dry_run: bool = True) -> dict[str, Any]:
    """Migrate existing users, projects, and flows to RBAC role assignments.

    This function creates UserRoleAssignment records for all existing users:
    - Superusers get global Admin role
    - Regular users get Owner role for their owned flows and projects
    - Starter Project Owner assignments are marked immutable

    Args:
        session: AsyncSession instance for database operations
        dry_run: If True, performs migration without committing changes (default: True)

    Returns:
        Dictionary containing migration results:
        {
            "status": "success" | "dry_run" | "error",
            "created": int,  # Number of assignments created
            "skipped": int,  # Number of assignments already existing
            "errors": list[str],  # Error messages if any
            "details": {
                "superuser_assignments": int,
                "flow_assignments": int,
                "project_assignments": int,
                "immutable_assignments": int
            }
        }

    Raises:
        Exception: If database operations fail critically
    """
    created_count = 0
    skipped_count = 0
    errors: list[str] = []
    details = {"superuser_assignments": 0, "flow_assignments": 0, "project_assignments": 0, "immutable_assignments": 0}

    try:
        logger.debug("Starting RBAC data migration for existing users")

        # Get Admin and Owner roles (must exist from seed data)
        admin_role = await _get_role_by_name(session, "Admin")
        owner_role = await _get_role_by_name(session, "Owner")

        if not admin_role or not owner_role:
            error_msg = "Admin and Owner roles not found. Run RBAC seed data initialization first."
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
                "created": 0,
                "skipped": 0,
                "errors": [error_msg],
                "details": details,
            }

        # Get all users
        users_result = await session.exec(select(User))
        users_list = users_result.all()
        total_users = len(users_list)
        logger.debug(f"Found {total_users} users to migrate")

        # Process each user
        for idx, user in enumerate(users_list, 1):
            # Progress reporting for large datasets (every 100 users)
            if total_users > 100 and idx % 100 == 0:
                logger.info(f"Migration progress: {idx}/{total_users} users processed ({idx * 100 // total_users}%)")
            try:
                if user.is_superuser:
                    # Superusers get global Admin role
                    created, skipped = await _create_superuser_assignment(session, user, admin_role)
                    created_count += created
                    skipped_count += skipped
                    if created:
                        details["superuser_assignments"] += 1
                        logger.debug(f"Created global Admin assignment for superuser {user.username}")
                    else:
                        logger.debug(f"Skipped existing Admin assignment for superuser {user.username}")
                else:
                    # Regular users: Owner of their flows and projects
                    flow_created, flow_skipped = await _create_flow_assignments(session, user, owner_role)
                    created_count += flow_created
                    skipped_count += flow_skipped
                    details["flow_assignments"] += flow_created

                    project_created, project_skipped, immutable_count = await _create_project_assignments(
                        session, user, owner_role
                    )
                    created_count += project_created
                    skipped_count += project_skipped
                    details["project_assignments"] += project_created
                    details["immutable_assignments"] += immutable_count

                    logger.debug(
                        f"User {user.username}: created {flow_created + project_created} assignments, "
                        f"skipped {flow_skipped + project_skipped}, "
                        f"immutable: {immutable_count}"
                    )

            except Exception as e:
                error_msg = f"Error migrating user {user.id} ({user.username}): {e!s}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Log final progress summary
        if total_users > 100:
            logger.info(f"Migration progress: {total_users}/{total_users} users processed (100%)")

        # Commit or rollback based on dry_run flag
        if not dry_run:
            await session.commit()
            logger.info(
                f"RBAC migration completed: created {created_count} assignments, "
                f"skipped {skipped_count}, errors: {len(errors)}"
            )
            return {
                "status": "success",
                "created": created_count,
                "skipped": skipped_count,
                "errors": errors,
                "details": details,
            }
        await session.rollback()
        logger.info(
            f"RBAC migration dry-run completed: would create {created_count} assignments, "
            f"would skip {skipped_count}, errors: {len(errors)}"
        )
        return {
            "status": "dry_run",
            "would_create": created_count,
            "would_skip": skipped_count,
            "errors": errors,
            "details": details,
        }

    except Exception as e:
        await session.rollback()
        error_msg = f"Critical error during RBAC migration: {e!s}"
        logger.exception(error_msg)
        return {
            "status": "error",
            "error": error_msg,
            "created": created_count,
            "skipped": skipped_count,
            "errors": errors + [error_msg],
            "details": details,
        }


async def _get_role_by_name(session: AsyncSession, name: str) -> Role | None:
    """Fetch a role by name.

    Args:
        session: AsyncSession instance
        name: Role name to fetch

    Returns:
        Role instance if found, None otherwise
    """
    stmt = select(Role).where(Role.name == name)
    result = await session.exec(stmt)
    return result.first()


async def _create_superuser_assignment(session: AsyncSession, user: User, admin_role: Role) -> tuple[int, int]:
    """Create global Admin role assignment for a superuser.

    Args:
        session: AsyncSession instance
        user: User instance
        admin_role: Admin Role instance

    Returns:
        Tuple of (created_count, skipped_count)
    """
    # Check if assignment already exists
    stmt = select(UserRoleAssignment).where(
        UserRoleAssignment.user_id == user.id,
        UserRoleAssignment.role_id == admin_role.id,
        UserRoleAssignment.scope_type == "global",
    )
    result = await session.exec(stmt)
    existing = result.first()

    if existing:
        return (0, 1)  # Skipped

    # Create new assignment
    assignment = UserRoleAssignment(
        user_id=user.id, role_id=admin_role.id, scope_type="global", scope_id=None, is_immutable=False
    )
    session.add(assignment)
    return (1, 0)  # Created


async def _create_flow_assignments(session: AsyncSession, user: User, owner_role: Role) -> tuple[int, int]:
    """Create Owner role assignments for all flows owned by a user.

    Args:
        session: AsyncSession instance
        user: User instance
        owner_role: Owner Role instance

    Returns:
        Tuple of (created_count, skipped_count)
    """
    created = 0
    skipped = 0

    # Get all flows owned by this user
    stmt = select(Flow).where(Flow.user_id == user.id)
    result = await session.exec(stmt)
    flows = result.all()

    for flow in flows:
        # Check if assignment already exists
        assign_stmt = select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user.id,
            UserRoleAssignment.role_id == owner_role.id,
            UserRoleAssignment.scope_type == "flow",
            UserRoleAssignment.scope_id == flow.id,
        )
        assign_result = await session.exec(assign_stmt)
        existing = assign_result.first()

        if existing:
            skipped += 1
            continue

        # Create new assignment
        assignment = UserRoleAssignment(
            user_id=user.id, role_id=owner_role.id, scope_type="flow", scope_id=flow.id, is_immutable=False
        )
        session.add(assignment)
        created += 1

    return (created, skipped)


async def _create_project_assignments(session: AsyncSession, user: User, owner_role: Role) -> tuple[int, int, int]:
    """Create Owner role assignments for all projects (folders) owned by a user.

    Special handling: Starter Project assignments are marked as immutable.

    Args:
        session: AsyncSession instance
        user: User instance
        owner_role: Owner Role instance

    Returns:
        Tuple of (created_count, skipped_count, immutable_count)
    """
    created = 0
    skipped = 0
    immutable_count = 0

    # Get all projects/folders owned by this user
    stmt = select(Folder).where(Folder.user_id == user.id)
    result = await session.exec(stmt)
    projects = result.all()

    for project in projects:
        # Check if assignment already exists
        assign_stmt = select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user.id,
            UserRoleAssignment.role_id == owner_role.id,
            UserRoleAssignment.scope_type == "project",
            UserRoleAssignment.scope_id == project.id,
        )
        assign_result = await session.exec(assign_stmt)
        existing = assign_result.first()

        # Determine if this is the Starter Project (immutable)
        is_starter_project = project.name == "Starter Project"

        if existing:
            # If it's Starter Project and not already immutable, update it
            if is_starter_project and not existing.is_immutable:
                existing.is_immutable = True
                session.add(existing)
                immutable_count += 1
                logger.debug("Updated existing assignment for Starter Project to immutable")
            skipped += 1
            continue

        # Create new assignment
        assignment = UserRoleAssignment(
            user_id=user.id,
            role_id=owner_role.id,
            scope_type="project",
            scope_id=project.id,
            is_immutable=is_starter_project,
        )
        session.add(assignment)
        created += 1
        if is_starter_project:
            immutable_count += 1

    return (created, skipped, immutable_count)


# CLI support for standalone execution
if __name__ == "__main__":
    import argparse
    import asyncio

    from langbuilder.services.database.utils import session_getter
    from langbuilder.services.deps import get_db_service

    parser = argparse.ArgumentParser(description="Migrate existing users to RBAC role assignments")
    parser.add_argument(
        "--commit", action="store_true", help="Commit changes to database (default: dry-run mode for safety)"
    )
    args = parser.parse_args()

    async def main():
        """Execute the migration."""
        async with session_getter(get_db_service()) as session:
            # Invert the flag: dry_run is True unless --commit is specified
            result = await migrate_existing_users_to_rbac(session, dry_run=(not args.commit))
            print("\nMigration Results:")
            print(f"Status: {result['status']}")
            if result["status"] == "dry_run":
                print(f"Would create: {result['would_create']}")
                print(f"Would skip: {result['would_skip']}")
            else:
                print(f"Created: {result.get('created', 0)}")
                print(f"Skipped: {result.get('skipped', 0)}")
            print(f"Errors: {len(result['errors'])}")
            if result["errors"]:
                print("\nError details:")
                for error in result["errors"]:
                    print(f"  - {error}")
            print(f"\nDetails: {result['details']}")

    asyncio.run(main())
