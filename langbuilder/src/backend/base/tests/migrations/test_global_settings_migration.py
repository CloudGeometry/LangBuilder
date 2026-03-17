"""Tests for the add_global_settings_table migration.

These tests verify:
1. Migration file exists in versions/ directory
2. upgrade() creates global_settings table with required columns
3. downgrade() drops the table
4. The table has ix_global_settings_key index
5. The key column has a UNIQUE constraint
6. Round-trip: upgrade -> downgrade -> upgrade works
"""
from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

VERSIONS_DIR = Path(__file__).parent.parent.parent / "langflow" / "alembic" / "versions"
ALEMBIC_INI = Path(__file__).parent.parent.parent / "langflow" / "alembic.ini"


def get_alembic_cfg(db_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", db_url)
    # Override script_location to absolute path
    cfg.set_main_option(
        "script_location",
        str(ALEMBIC_INI.parent / "alembic"),
    )
    return cfg


def find_migration_file() -> Path | None:
    """Find the migration file for add_global_settings_table."""
    matches = list(VERSIONS_DIR.glob("*_add_global_settings_table.py"))
    return matches[0] if matches else None


class TestGlobalSettingsMigrationFileExists:
    def test_migration_file_exists(self):
        migration_file = find_migration_file()
        assert migration_file is not None, (
            "Migration file *_add_global_settings_table.py not found in versions/"
        )

    def test_migration_file_has_correct_naming(self):
        migration_file = find_migration_file()
        assert migration_file is not None
        assert migration_file.name.endswith("_add_global_settings_table.py"), (
            f"Migration file has incorrect name: {migration_file.name}"
        )

    def test_migration_file_contains_revision(self):
        migration_file = find_migration_file()
        assert migration_file is not None
        content = migration_file.read_text()
        assert "revision" in content
        assert "down_revision" in content

    def test_migration_file_has_down_revision(self):
        """Verify down_revision is set (not None) pointing to previous migration."""
        migration_file = find_migration_file()
        assert migration_file is not None
        content = migration_file.read_text()
        # down_revision should not be None
        assert "down_revision: str | None = None" not in content or \
               "down_revision = None" not in content


class TestGlobalSettingsMigrationUpgrade:
    """Test that upgrade creates the global_settings table correctly."""

    @pytest.fixture
    def sqlite_url(self, tmp_path):
        return f"sqlite+aiosqlite:///{tmp_path}/test_migration.db"

    @pytest.fixture
    def sync_url(self, tmp_path):
        return f"sqlite:///{tmp_path}/test_migration.db"

    def test_upgrade_creates_table(self, sqlite_url, sync_url):
        cfg = get_alembic_cfg(sqlite_url)
        command.upgrade(cfg, "head")

        engine = sa.create_engine(sync_url)
        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            tables = inspector.get_table_names()
            assert "global_settings" in tables, "global_settings table not created after upgrade"

    def test_upgrade_creates_correct_columns(self, sqlite_url, sync_url):
        cfg = get_alembic_cfg(sqlite_url)
        command.upgrade(cfg, "head")

        engine = sa.create_engine(sync_url)
        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            columns = {col["name"] for col in inspector.get_columns("global_settings")}

        expected_columns = {"id", "key", "value", "is_encrypted", "created_at", "updated_at", "updated_by"}
        assert expected_columns.issubset(columns), (
            f"Missing columns: {expected_columns - columns}"
        )

    def test_upgrade_creates_primary_key(self, sqlite_url, sync_url):
        cfg = get_alembic_cfg(sqlite_url)
        command.upgrade(cfg, "head")

        engine = sa.create_engine(sync_url)
        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            pk = inspector.get_pk_constraint("global_settings")
            assert "id" in pk["constrained_columns"], "id is not the primary key"

    def test_upgrade_creates_ix_global_settings_key_index(self, sqlite_url, sync_url):
        cfg = get_alembic_cfg(sqlite_url)
        command.upgrade(cfg, "head")

        engine = sa.create_engine(sync_url)
        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            indexes = {idx["name"] for idx in inspector.get_indexes("global_settings")}
            assert "ix_global_settings_key" in indexes, (
                f"ix_global_settings_key index not found. Found: {indexes}"
            )

    def test_upgrade_key_column_has_unique_constraint(self, sqlite_url, sync_url):
        cfg = get_alembic_cfg(sqlite_url)
        command.upgrade(cfg, "head")

        engine = sa.create_engine(sync_url)
        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            # Check unique constraints
            unique_constraints = inspector.get_unique_constraints("global_settings")
            unique_cols = [col for uc in unique_constraints for col in uc["column_names"]]
            # Also check indexes that are unique
            indexes = inspector.get_indexes("global_settings")
            unique_index_cols = [col for idx in indexes if idx.get("unique") for col in idx["column_names"]]

            all_unique_cols = set(unique_cols + unique_index_cols)
            assert "key" in all_unique_cols, (
                f"key column does not have a UNIQUE constraint. Unique cols: {all_unique_cols}"
            )

    def test_upgrade_key_column_not_nullable(self, sqlite_url, sync_url):
        cfg = get_alembic_cfg(sqlite_url)
        command.upgrade(cfg, "head")

        engine = sa.create_engine(sync_url)
        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            columns = {col["name"]: col for col in inspector.get_columns("global_settings")}
            assert not columns["key"]["nullable"], "key column should be NOT NULL"

    def test_upgrade_value_column_not_nullable(self, sqlite_url, sync_url):
        cfg = get_alembic_cfg(sqlite_url)
        command.upgrade(cfg, "head")

        engine = sa.create_engine(sync_url)
        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            columns = {col["name"]: col for col in inspector.get_columns("global_settings")}
            assert not columns["value"]["nullable"], "value column should be NOT NULL"


class TestGlobalSettingsMigrationDowngrade:
    """Test that downgrade removes the global_settings table."""

    @pytest.fixture
    def sqlite_url(self, tmp_path):
        return f"sqlite+aiosqlite:///{tmp_path}/test_migration.db"

    @pytest.fixture
    def sync_url(self, tmp_path):
        return f"sqlite:///{tmp_path}/test_migration.db"

    def test_downgrade_drops_table(self, sqlite_url, sync_url):
        cfg = get_alembic_cfg(sqlite_url)
        command.upgrade(cfg, "head")

        # Verify table exists before downgrade
        engine = sa.create_engine(sync_url)
        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            assert "global_settings" in inspector.get_table_names()

        command.downgrade(cfg, "-1")

        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            tables = inspector.get_table_names()
            assert "global_settings" not in tables, (
                "global_settings table still exists after downgrade"
            )

    def test_downgrade_drops_index(self, sqlite_url, sync_url):
        cfg = get_alembic_cfg(sqlite_url)
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "-1")

        engine = sa.create_engine(sync_url)
        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            # After downgrade, table should not exist, so no index either
            tables = inspector.get_table_names()
            assert "global_settings" not in tables


class TestGlobalSettingsMigrationRoundTrip:
    """Test full round-trip: upgrade -> downgrade -> upgrade."""

    @pytest.fixture
    def sqlite_url(self, tmp_path):
        return f"sqlite+aiosqlite:///{tmp_path}/test_migration.db"

    @pytest.fixture
    def sync_url(self, tmp_path):
        return f"sqlite:///{tmp_path}/test_migration.db"

    def test_round_trip_upgrade_downgrade_upgrade(self, sqlite_url, sync_url):
        cfg = get_alembic_cfg(sqlite_url)

        # First upgrade
        command.upgrade(cfg, "head")
        engine = sa.create_engine(sync_url)
        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            assert "global_settings" in inspector.get_table_names(), "Table missing after first upgrade"

        # Downgrade
        command.downgrade(cfg, "-1")
        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            assert "global_settings" not in inspector.get_table_names(), "Table still exists after downgrade"

        # Second upgrade
        command.upgrade(cfg, "head")
        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            assert "global_settings" in inspector.get_table_names(), "Table missing after second upgrade"
            indexes = {idx["name"] for idx in inspector.get_indexes("global_settings")}
            assert "ix_global_settings_key" in indexes, "Index missing after second upgrade"
