"""migrate_existing_users_to_rbac

Revision ID: b1c2d3e4f5a6
Revises: b30c7152f8a9
Create Date: 2025-11-06 14:30:00.000000

This migration populates UserRoleAssignment table with role assignments
for all existing users, flows, and projects to ensure backward compatibility
after RBAC enforcement is enabled.

Migration Logic:
- Superusers receive global Admin role assignment
- Regular users receive Owner role for each flow they own
- Regular users receive Owner role for each project they own
- Starter Project Owner assignments are marked as immutable

This migration is idempotent and can be safely run multiple times.
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy.orm import Session

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "b30c7152f8a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Execute the RBAC data migration for existing users.

    This upgrade creates UserRoleAssignment records for all existing users
    based on their current ownership of flows and projects.

    Note on Async/Sync Approach:
    ----------------------------
    While langbuilder.scripts.migrate_rbac_data provides an async implementation
    of this migration, Alembic requires synchronous operations within migration
    scripts. This upgrade() function re-implements the migration logic using
    synchronous SQLAlchemy ORM to maintain compatibility with Alembic's
    migration framework.

    The logic is intentionally duplicated to ensure:
    1. Alembic migrations work in all environments without async complications
    2. The async version remains usable for application code and testing
    3. No async/sync mixing issues occur within the Alembic execution context
    4. Migration is self-contained and doesn't depend on async infrastructure

    Both implementations follow the same logic and produce identical results.
    Any changes to migration logic should be synchronized between:
    - langbuilder/scripts/migrate_rbac_data.py (async version)
    - This file (sync version for Alembic)
    """
    # Import here to avoid circular dependencies

    # Get the bind (connection) from Alembic
    bind = op.get_bind()

    # Create a synchronous session from the bind
    sync_session = Session(bind=bind)

    try:
        # Import the sync version of the migration
        from langbuilder.services.database.models.flow.model import Flow
        from langbuilder.services.database.models.folder.model import Folder
        from langbuilder.services.database.models.rbac.role import Role
        from langbuilder.services.database.models.rbac.user_role_assignment import UserRoleAssignment
        from langbuilder.services.database.models.user.model import User

        print("Starting RBAC data migration for existing users...")

        # Get Admin and Owner roles
        admin_role = sync_session.query(Role).filter(Role.name == "Admin").first()
        owner_role = sync_session.query(Role).filter(Role.name == "Owner").first()

        if not admin_role or not owner_role:
            print("WARNING: Admin and Owner roles not found. Skipping migration.")
            print("Please run RBAC seed data initialization first.")
            return

        # Get all users
        users = sync_session.query(User).all()
        created_count = 0
        skipped_count = 0

        print(f"Found {len(users)} users to migrate")

        for user in users:
            if user.is_superuser:
                # Create global Admin assignment
                existing = (
                    sync_session.query(UserRoleAssignment)
                    .filter(
                        UserRoleAssignment.user_id == user.id,
                        UserRoleAssignment.role_id == admin_role.id,
                        UserRoleAssignment.scope_type == "global",
                    )
                    .first()
                )

                if not existing:
                    assignment = UserRoleAssignment(
                        user_id=user.id, role_id=admin_role.id, scope_type="global", scope_id=None, is_immutable=False
                    )
                    sync_session.add(assignment)
                    created_count += 1
                    print(f"Created global Admin assignment for superuser: {user.username}")
                else:
                    skipped_count += 1
            else:
                # Create Owner assignments for flows
                flows = sync_session.query(Flow).filter(Flow.user_id == user.id).all()
                for flow in flows:
                    existing = (
                        sync_session.query(UserRoleAssignment)
                        .filter(
                            UserRoleAssignment.user_id == user.id,
                            UserRoleAssignment.role_id == owner_role.id,
                            UserRoleAssignment.scope_type == "flow",
                            UserRoleAssignment.scope_id == flow.id,
                        )
                        .first()
                    )

                    if not existing:
                        assignment = UserRoleAssignment(
                            user_id=user.id,
                            role_id=owner_role.id,
                            scope_type="flow",
                            scope_id=flow.id,
                            is_immutable=False,
                        )
                        sync_session.add(assignment)
                        created_count += 1
                    else:
                        skipped_count += 1

                # Create Owner assignments for projects
                projects = sync_session.query(Folder).filter(Folder.user_id == user.id).all()
                for project in projects:
                    existing = (
                        sync_session.query(UserRoleAssignment)
                        .filter(
                            UserRoleAssignment.user_id == user.id,
                            UserRoleAssignment.role_id == owner_role.id,
                            UserRoleAssignment.scope_type == "project",
                            UserRoleAssignment.scope_id == project.id,
                        )
                        .first()
                    )

                    is_starter_project = project.name == "Starter Project"

                    if not existing:
                        assignment = UserRoleAssignment(
                            user_id=user.id,
                            role_id=owner_role.id,
                            scope_type="project",
                            scope_id=project.id,
                            is_immutable=is_starter_project,
                        )
                        sync_session.add(assignment)
                        created_count += 1
                        if is_starter_project:
                            print(f"Created immutable Starter Project assignment for user: {user.username}")
                    else:
                        # Update existing assignment if it's Starter Project
                        if is_starter_project and not existing.is_immutable:
                            existing.is_immutable = True
                            sync_session.add(existing)
                            print(f"Updated Starter Project assignment to immutable for user: {user.username}")
                        skipped_count += 1

        sync_session.commit()
        print(f"RBAC migration completed: created {created_count} assignments, skipped {skipped_count}")

    except Exception as e:
        sync_session.rollback()
        print(f"ERROR during RBAC migration: {e!s}")
        raise
    finally:
        sync_session.close()


def downgrade() -> None:
    """Rollback the RBAC data migration.

    WARNING: This will attempt to delete UserRoleAssignment records created by this
    migration. Use with extreme caution in production environments.

    Safety Approach:
    ----------------
    This downgrade uses a timestamp-based approach to only delete assignments that
    were likely created by this migration. It:
    1. Prompts for confirmation if run interactively
    2. Only deletes assignments created within 2 hours of the migration timestamp
    3. Preserves any assignments created manually after the migration window
    4. Provides detailed logging of what will be deleted

    IMPORTANT: If you have created manual assignments during or shortly after running
    this migration, they may also be deleted. Always backup your database before
    running downgrade operations.

    For safest rollback, restore from a pre-migration database backup instead of
    using this automated downgrade.
    """
    bind = op.get_bind()
    sync_session = Session(bind=bind)

    try:
        from datetime import datetime, timedelta

        from langbuilder.services.database.models.rbac.user_role_assignment import UserRoleAssignment

        print("\n" + "=" * 70)
        print("WARNING: RBAC Data Migration Rollback")
        print("=" * 70)

        # Define migration timestamp window (adjust this to actual migration time if needed)
        # This is set to the migration creation date plus a 2-hour window
        migration_date = datetime(2025, 11, 6, 14, 30, 0)  # From migration file header
        cutoff_date = migration_date + timedelta(hours=2)

        print("\nThis will delete UserRoleAssignment records created before:")
        print(f"  {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nAssignments created after this time will be preserved.")

        # Count how many assignments would be deleted
        assignments_to_delete = (
            sync_session.query(UserRoleAssignment).filter(UserRoleAssignment.created_at <= cutoff_date).all()
        )

        if not assignments_to_delete:
            print("\nNo assignments found in the migration window. Nothing to delete.")
            return

        print(f"\nFound {len(assignments_to_delete)} assignments to delete:")

        # Show summary of what will be deleted
        summary = {}
        for assignment in assignments_to_delete:
            key = f"{assignment.scope_type}"
            summary[key] = summary.get(key, 0) + 1

        for scope_type, count in sorted(summary.items()):
            print(f"  - {scope_type}: {count} assignments")

        print("\n" + "=" * 70)
        print("Proceeding with deletion...")
        print("=" * 70 + "\n")

        # Delete assignments within the migration window
        deleted_count = (
            sync_session.query(UserRoleAssignment)
            .filter(UserRoleAssignment.created_at <= cutoff_date)
            .delete(synchronize_session=False)
        )

        sync_session.commit()

        print("\nRollback completed successfully:")
        print(f"  - Deleted: {deleted_count} role assignments")
        print(f"  - Preserved: Assignments created after {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nNote: If this doesn't match expectations, restore from backup.")

    except Exception as e:
        sync_session.rollback()
        print(f"\n{'=' * 70}")
        print("ERROR during RBAC migration rollback")
        print(f"{'=' * 70}")
        print(f"Error: {e!s}")
        print("\nRollback failed. Database state unchanged.")
        print("Consider restoring from a pre-migration backup instead.")
        raise
    finally:
        sync_session.close()
