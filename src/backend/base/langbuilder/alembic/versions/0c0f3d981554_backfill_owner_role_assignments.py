"""Backfill Owner role assignments for existing resources

Revision ID: 0c0f3d981554
Revises: e562793da031
Create Date: 2025-11-08 20:00:00.000000

This data migration assigns Owner roles to existing users for their:
- Projects (Folders) - assigns Owner role with scope_type='Project'
- Standalone Flows - assigns Owner role with scope_type='Flow' for flows not in projects
- Marks Starter Projects with is_immutable=True
"""
from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '0c0f3d981554'
down_revision: Union[str, None] = 'e562793da031'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfill Owner role assignments for existing Projects and Flows."""
    conn = op.get_bind()

    # Get Owner role ID
    result = conn.execute(text("SELECT id FROM role WHERE name = 'Owner'"))
    owner_role_row = result.fetchone()

    if not owner_role_row:
        # If Owner role doesn't exist, skip this migration
        # This can happen if RBAC seed hasn't run yet
        print("WARNING: Owner role not found. Skipping role assignment backfill.")
        print("Please run RBAC seed script before running this migration.")
        return

    owner_role_id = str(owner_role_row[0])

    # Mark Starter Projects with is_immutable=True
    # Starter Projects are folders with name='Starter Projects' and user_id IS NULL
    conn.execute(text("""
        UPDATE folder
        SET is_starter_project = 1
        WHERE name = 'Starter Projects'
        AND user_id IS NULL
    """))

    # Assign Owner role to all users for their existing Projects (Folders)
    # Use INSERT OR IGNORE to handle potential duplicates (idempotent)
    # For SQLite, we use INSERT OR IGNORE
    # For PostgreSQL, we would use INSERT ... ON CONFLICT DO NOTHING
    conn.execute(text(f"""
        INSERT OR IGNORE INTO userroleassignment (id, user_id, role_id, scope_type, scope_id, is_immutable, created_at)
        SELECT
            lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)),2) || '-' ||
                  substr('89ab',abs(random()) % 4 + 1, 1) || substr(hex(randomblob(2)),2) || '-' || hex(randomblob(6))),
            f.user_id,
            '{owner_role_id}',
            'Project',
            f.id,
            f.is_starter_project,
            datetime('now')
        FROM folder f
        WHERE f.user_id IS NOT NULL
    """))

    # Assign Owner role to all users for their existing standalone Flows
    # Only for flows NOT in a project (folder_id IS NULL)
    conn.execute(text(f"""
        INSERT OR IGNORE INTO userroleassignment (id, user_id, role_id, scope_type, scope_id, is_immutable, created_at)
        SELECT
            lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)),2) || '-' ||
                  substr('89ab',abs(random()) % 4 + 1, 1) || substr(hex(randomblob(2)),2) || '-' || hex(randomblob(6))),
            fl.user_id,
            '{owner_role_id}',
            'Flow',
            fl.id,
            0,
            datetime('now')
        FROM flow fl
        WHERE fl.user_id IS NOT NULL
        AND fl.folder_id IS NULL
    """))

    print("Successfully backfilled Owner role assignments for existing resources")


def downgrade() -> None:
    """Remove backfilled Owner role assignments.

    This is a data migration downgrade - it removes role assignments
    that were created by the upgrade() function. This is safe because
    these assignments can be recreated by re-running the upgrade.
    """
    conn = op.get_bind()

    # Get Owner role ID
    result = conn.execute(text("SELECT id FROM role WHERE name = 'Owner'"))
    owner_role_row = result.fetchone()

    if not owner_role_row:
        # Nothing to clean up if Owner role doesn't exist
        return

    owner_role_id = str(owner_role_row[0])

    # Remove Project-level Owner assignments
    # We only remove assignments where created_by is NULL (system-created)
    # to avoid deleting user-created role assignments
    conn.execute(text(f"""
        DELETE FROM userroleassignment
        WHERE role_id = '{owner_role_id}'
        AND scope_type = 'Project'
        AND created_by IS NULL
    """))

    # Remove Flow-level Owner assignments for standalone flows
    conn.execute(text(f"""
        DELETE FROM userroleassignment
        WHERE role_id = '{owner_role_id}'
        AND scope_type = 'Flow'
        AND created_by IS NULL
    """))

    # Revert is_starter_project flag
    conn.execute(text("""
        UPDATE folder
        SET is_starter_project = 0
        WHERE name = 'Starter Projects'
        AND user_id IS NULL
    """))

    print("Successfully removed backfilled Owner role assignments")
