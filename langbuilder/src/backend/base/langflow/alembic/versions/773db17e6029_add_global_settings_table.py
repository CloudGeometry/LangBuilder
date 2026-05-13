"""add global_settings table

Revision ID: 773db17e6029
Revises: 59a272d6669a
Create Date: 2026-03-16

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "773db17e6029"  # pragma: allowlist secret
down_revision: str | None = "59a272d6669a"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "global_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("key", sa.VARCHAR(length=100), nullable=False),
        sa.Column("value", sa.TEXT(), nullable=False),
        sa.Column("is_encrypted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index("ix_global_settings_key", "global_settings", ["key"])


def downgrade() -> None:
    op.drop_index("ix_global_settings_key", table_name="global_settings")
    op.drop_table("global_settings")
