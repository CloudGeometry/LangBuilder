"""fix global_settings SQLite column types and constraints

The original migration (773db17e6029) used sa.UUID() which creates literal
'UUID' type strings in SQLite. All other migrations use
sqlmodel.sql.sqltypes.types.Uuid() which renders as CHAR(32). It also created
named constraints and a redundant UniqueConstraint + Index combo that don't
match what SQLModel generates. This mismatch causes Alembic's startup check
to flag false-positive diffs and crash.

This migration recreates the table with correct types and constraints via
batch_alter_table (CREATE-COPY-DROP-RENAME on SQLite, column-level ops on
PostgreSQL).

Revision ID: a1b2c3d4e5f6
Revises: 773db17e6029
Create Date: 2026-03-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"  # pragma: allowlist secret
down_revision: str | None = "773db17e6029"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop and recreate the table with correct types and constraints.
    # batch_alter_table on SQLite does CREATE-COPY-DROP-RENAME transparently.
    # Data is fully preserved.
    with op.batch_alter_table(
        "global_settings",
        schema=None,
        # Explicitly define the recreated table to fix constraint names and types
        recreate="always",
    ) as batch_op:
        # Fix column types: sa.UUID() → sqlmodel Uuid(), sa.TEXT() → AutoString()
        batch_op.alter_column(
            "id",
            type_=sqlmodel.sql.sqltypes.types.Uuid(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "value",
            type_=sqlmodel.sql.sqltypes.AutoString(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "updated_by",
            type_=sqlmodel.sql.sqltypes.types.Uuid(),
            existing_nullable=True,
        )

        # Fix constraint mismatch: drop the named UniqueConstraint
        # (SQLModel uses a unique Index instead)
        try:
            batch_op.drop_constraint("uq_global_settings_key", type_="unique")
        except Exception:  # noqa: BLE001
            pass  # Constraint may not exist by name on all backends

        # Fix FK: drop named FK and recreate without explicit name
        # (SQLModel generates unnamed FKs by default)
        try:
            batch_op.drop_constraint("fk_global_settings_updated_by_user", type_="foreignkey")
        except Exception:  # noqa: BLE001
            pass
        batch_op.create_foreign_key(
            None,  # No explicit name — let SQLAlchemy generate it
            "user",
            ["updated_by"],
            ["id"],
        )

    # Recreate the index as a unique index (matching SQLModel's Field(unique=True, index=True))
    try:
        op.drop_index("ix_global_settings_key", table_name="global_settings")
    except Exception:  # noqa: BLE001
        pass
    op.create_index(
        op.f("ix_global_settings_key"),
        "global_settings",
        ["key"],
        unique=True,
    )


def downgrade() -> None:
    # Reverse: restore original types and named constraints
    op.drop_index(op.f("ix_global_settings_key"), table_name="global_settings")
    op.create_index("ix_global_settings_key", "global_settings", ["key"])

    with op.batch_alter_table("global_settings", schema=None, recreate="always") as batch_op:
        batch_op.alter_column("id", type_=sa.UUID(), existing_nullable=False)
        batch_op.alter_column("value", type_=sa.TEXT(), existing_nullable=False)
        batch_op.alter_column("updated_by", type_=sa.UUID(), existing_nullable=True)
        batch_op.create_unique_constraint("uq_global_settings_key", ["key"])
        batch_op.create_foreign_key(
            "fk_global_settings_updated_by_user",
            "user",
            ["updated_by"],
            ["id"],
            ondelete="SET NULL",
        )
