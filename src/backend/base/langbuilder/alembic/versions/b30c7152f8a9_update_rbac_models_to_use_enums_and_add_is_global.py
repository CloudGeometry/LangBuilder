"""update_rbac_models_to_use_enums_and_add_is_global

Revision ID: b30c7152f8a9
Revises: a20a7041e437
Create Date: 2025-11-05 00:00:00.000000

This migration:
1. Converts Permission model to use enum-based action and scope fields
2. Adds is_global field to Role model
3. Updates unique constraint on Permission to composite (action, scope)

Changes:
- Permission.name -> Permission.action (enum: create, read, update, delete)
- Permission.scope_type -> Permission.scope (enum: flow, project)
- Added Permission unique constraint on (action, scope)
- Added Role.is_global field (Boolean, default False)
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b30c7152f8a9"
down_revision: str | None = "a20a7041e437"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # Step 1: Add new columns to permission table
    with op.batch_alter_table("permission", schema=None) as batch_op:
        # Add new action and scope columns
        batch_op.add_column(sa.Column("action", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
        batch_op.add_column(sa.Column("scope", sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    # Step 2: Migrate data from old columns to new columns
    # This is a data migration based on the old string format
    # Map old name values to new action enum values
    conn.execute(
        sa.text("""
        UPDATE permission
        SET action = CASE
            WHEN LOWER(name) LIKE '%create%' THEN 'create'
            WHEN LOWER(name) LIKE '%read%' THEN 'read'
            WHEN LOWER(name) LIKE '%update%' THEN 'update'
            WHEN LOWER(name) LIKE '%delete%' THEN 'delete'
            ELSE 'read'
        END,
        scope = CASE
            WHEN LOWER(scope_type) LIKE '%flow%' THEN 'flow'
            WHEN LOWER(scope_type) LIKE '%project%' THEN 'project'
            ELSE 'flow'
        END
    """)
    )

    # Step 3: Make new columns non-nullable now that data is migrated
    with op.batch_alter_table("permission", schema=None) as batch_op:
        # Drop old unique index on name
        batch_op.drop_index("ix_permission_name")
        batch_op.drop_index("ix_permission_scope_type")

        # Make new columns non-nullable
        batch_op.alter_column("action", nullable=False)
        batch_op.alter_column("scope", nullable=False)

        # Drop old columns
        batch_op.drop_column("name")
        batch_op.drop_column("scope_type")

        # Create new indexes
        batch_op.create_index("ix_permission_action", ["action"], unique=False)
        batch_op.create_index("ix_permission_scope", ["scope"], unique=False)

    # Step 4: Add unique constraint on (action, scope)
    with op.batch_alter_table("permission", schema=None) as batch_op:
        batch_op.create_unique_constraint("unique_action_scope", ["action", "scope"])

    # Step 5: Add is_global field to role table
    with op.batch_alter_table("role", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_global", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    conn = op.get_bind()

    # Step 1: Remove is_global field from role table
    with op.batch_alter_table("role", schema=None) as batch_op:
        batch_op.drop_column("is_global")

    # Step 2: Add back old columns to permission table
    with op.batch_alter_table("permission", schema=None) as batch_op:
        # Drop new unique constraint
        batch_op.drop_constraint("unique_action_scope", type_="unique")

        # Drop new indexes
        batch_op.drop_index("ix_permission_scope")
        batch_op.drop_index("ix_permission_action")

        # Add back old columns
        batch_op.add_column(sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
        batch_op.add_column(sa.Column("scope_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    # Step 3: Migrate data back from new columns to old columns
    conn.execute(
        sa.text("""
        UPDATE permission
        SET name = CASE action
            WHEN 'create' THEN 'Create'
            WHEN 'read' THEN 'Read'
            WHEN 'update' THEN 'Update'
            WHEN 'delete' THEN 'Delete'
            ELSE 'Read'
        END,
        scope_type = CASE scope
            WHEN 'flow' THEN 'Flow'
            WHEN 'project' THEN 'Project'
            ELSE 'Flow'
        END
    """)
    )

    # Step 4: Make old columns non-nullable and drop new columns
    with op.batch_alter_table("permission", schema=None) as batch_op:
        # Make old columns non-nullable
        batch_op.alter_column("name", nullable=False)
        batch_op.alter_column("scope_type", nullable=False)

        # Drop new columns
        batch_op.drop_column("scope")
        batch_op.drop_column("action")

        # Recreate old indexes
        batch_op.create_index("ix_permission_name", ["name"], unique=True)
        batch_op.create_index("ix_permission_scope_type", ["scope_type"], unique=False)
