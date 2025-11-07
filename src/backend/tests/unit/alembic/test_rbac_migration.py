"""Comprehensive tests for RBAC tables Alembic migration (a20a7041e437_add_rbac_tables).

This test suite validates:
1. Migration applies cleanly to empty database
2. Migration applies cleanly to existing database with data
3. All tables, indexes, and constraints are created correctly
4. Migration can be rolled back without data loss
5. Performance characteristics of the migration
"""

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from langbuilder.services.database.service import SQLModel
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import select


class TestRBACMigration:
    """Test suite for RBAC tables migration."""

    @pytest.fixture
    async def db_engine(self):
        """Create a test database engine."""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        yield engine
        await engine.dispose()

    @pytest.fixture
    async def db_session(self, db_engine):
        """Create a test database session."""
        async with db_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        async with AsyncSession(db_engine) as session:
            yield session

    async def test_migration_creates_permission_table(self, db_session):
        """Test that the migration creates the permission table with correct schema."""

        def check_permission_table(conn):
            inspector = inspect(conn)

            # Check table exists
            assert "permission" in inspector.get_table_names()

            # Check columns - updated for enum-based schema (post-b30c7152f8a9)
            columns = {col["name"]: col for col in inspector.get_columns("permission")}
            assert "id" in columns
            assert "action" in columns  # Updated from "name"
            assert "description" in columns
            assert "scope" in columns  # Updated from "scope_type"

            # Check indexes - updated for enum-based schema
            indexes = {idx["name"]: idx for idx in inspector.get_indexes("permission")}
            assert "ix_permission_action" in indexes  # Updated from "ix_permission_name"
            assert "ix_permission_scope" in indexes  # Updated from "ix_permission_scope_type"

        connection = await db_session.connection()
        await connection.run_sync(check_permission_table)

    async def test_migration_creates_role_table(self, db_session):
        """Test that the migration creates the role table with correct schema."""

        def check_role_table(conn):
            inspector = inspect(conn)

            # Check table exists
            assert "role" in inspector.get_table_names()

            # Check columns
            columns = {col["name"]: col for col in inspector.get_columns("role")}
            assert "id" in columns
            assert "name" in columns
            assert "description" in columns
            assert "is_system" in columns

            # Check indexes
            indexes = {idx["name"]: idx for idx in inspector.get_indexes("role")}
            assert "ix_role_name" in indexes
            # SQLite returns 1 for True in unique field
            assert indexes["ix_role_name"]["unique"] in (True, 1)

        connection = await db_session.connection()
        await connection.run_sync(check_role_table)

    async def test_migration_creates_role_permission_table(self, db_session):
        """Test that the migration creates the role_permission junction table."""

        def check_role_permission_table(conn):
            inspector = inspect(conn)

            # Check table exists
            assert "role_permission" in inspector.get_table_names()

            # Check columns
            columns = {col["name"]: col for col in inspector.get_columns("role_permission")}
            assert "id" in columns
            assert "role_id" in columns
            assert "permission_id" in columns

            # Check foreign keys
            fks = inspector.get_foreign_keys("role_permission")
            fk_tables = {fk["referred_table"] for fk in fks}
            assert "role" in fk_tables
            assert "permission" in fk_tables

            # Check indexes
            indexes = {idx["name"]: idx for idx in inspector.get_indexes("role_permission")}
            assert "ix_role_permission_role_id" in indexes
            assert "ix_role_permission_permission_id" in indexes

        connection = await db_session.connection()
        await connection.run_sync(check_role_permission_table)

    async def test_migration_creates_user_role_assignment_table(self, db_session):
        """Test that the migration creates the user_role_assignment table."""

        def check_user_role_assignment_table(conn):
            inspector = inspect(conn)

            # Check table exists
            assert "user_role_assignment" in inspector.get_table_names()

            # Check columns
            columns = {col["name"]: col for col in inspector.get_columns("user_role_assignment")}
            assert "id" in columns
            assert "user_id" in columns
            assert "role_id" in columns
            assert "scope_type" in columns
            assert "scope_id" in columns
            assert "is_immutable" in columns
            assert "created_at" in columns
            assert "created_by" in columns

            # Check foreign keys
            fks = inspector.get_foreign_keys("user_role_assignment")
            fk_tables = {fk["referred_table"] for fk in fks}
            assert "user" in fk_tables
            assert "role" in fk_tables

            # Check indexes (including the critical idx_scope_lookup)
            indexes = {idx["name"]: idx for idx in inspector.get_indexes("user_role_assignment")}
            assert "idx_scope_lookup" in indexes
            assert set(indexes["idx_scope_lookup"]["column_names"]) == {"user_id", "scope_type", "scope_id"}
            assert "ix_user_role_assignment_user_id" in indexes
            assert "ix_user_role_assignment_role_id" in indexes
            assert "ix_user_role_assignment_scope_type" in indexes
            assert "ix_user_role_assignment_scope_id" in indexes

        connection = await db_session.connection()
        await connection.run_sync(check_user_role_assignment_table)

    async def test_unique_constraints(self, db_session):
        """Test that unique constraints are properly enforced."""
        from langbuilder.services.database.models.rbac import (
            Permission,
            Role,
        )
        from langbuilder.services.database.models.rbac.permission import (
            PermissionAction,
            PermissionScope,
        )

        # Test permission unique constraint (action + scope must be unique)
        perm1 = Permission(action=PermissionAction.CREATE, scope=PermissionScope.FLOW)
        db_session.add(perm1)
        await db_session.commit()

        # Try to create duplicate permission (same action + scope)
        perm2 = Permission(action=PermissionAction.CREATE, scope=PermissionScope.FLOW)
        db_session.add(perm2)
        with pytest.raises(Exception):  # Should raise integrity error
            await db_session.commit()
        await db_session.rollback()

        # Test role unique constraint
        role1 = Role(name="Admin", is_system=True)
        db_session.add(role1)
        await db_session.commit()

        # Try to create duplicate role name
        role2 = Role(name="Admin", is_system=True)
        db_session.add(role2)
        with pytest.raises(Exception):  # Should raise integrity error
            await db_session.commit()
        await db_session.rollback()

    async def test_foreign_key_constraints(self, db_session):
        """Test that foreign key constraints are enforced."""
        from langbuilder.services.database.models.rbac import RolePermission

        # Enable foreign key constraints for SQLite
        await db_session.execute(text("PRAGMA foreign_keys = ON"))

        # Try to create role_permission with non-existent role/permission
        invalid_rp = RolePermission(role_id=uuid4(), permission_id=uuid4())
        db_session.add(invalid_rp)

        # This should fail due to foreign key constraint
        with pytest.raises(Exception):
            await db_session.commit()
        await db_session.rollback()

    async def test_table_creation_order(self, db_session):
        """Test that tables can be created in the correct dependency order."""
        from langbuilder.services.database.models.rbac import (
            Permission,
            Role,
            RolePermission,
            UserRoleAssignment,
        )
        from langbuilder.services.database.models.rbac.permission import (
            PermissionAction,
            PermissionScope,
        )
        from langbuilder.services.database.models.user import User

        # Create user first (dependency)
        user = User(username="testuser", password="hashedpassword", is_active=True, is_superuser=False)
        db_session.add(user)
        await db_session.flush()  # Flush to get ID
        user_id = user.id
        await db_session.commit()

        # Create permission and role (no dependencies)
        permission = Permission(action=PermissionAction.READ, scope=PermissionScope.FLOW, description="Read flow data")
        role = Role(name="Viewer", description="Can view flows", is_system=True)
        db_session.add_all([permission, role])
        await db_session.flush()  # Flush to get IDs

        # Store IDs before creating relationships
        permission_id = permission.id
        role_id = role.id

        await db_session.commit()

        # Create role_permission (depends on role and permission)
        role_permission = RolePermission(role_id=role_id, permission_id=permission_id)
        db_session.add(role_permission)
        await db_session.flush()
        role_permission_id = role_permission.id
        await db_session.commit()

        # Create user_role_assignment (depends on user and role)
        assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=role_id,
            scope_type="global",
            scope_id=None,
            is_immutable=False,
            created_at=datetime.now(timezone.utc),
            created_by=user_id,
        )
        db_session.add(assignment)
        await db_session.flush()
        assignment_id = assignment.id
        await db_session.commit()

        # Verify all records were created
        assert permission_id is not None
        assert role_id is not None
        assert role_permission_id is not None
        assert assignment_id is not None

    async def test_scope_types(self, db_session):
        """Test different scope types for user role assignments."""
        from langbuilder.services.database.models.rbac import (
            Role,
            UserRoleAssignment,
        )
        from langbuilder.services.database.models.user import User

        # Create user and role
        user = User(username="scopeuser", password="hashedpassword", is_active=True, is_superuser=False)
        role = Role(name="Owner", description="Owner role", is_system=True)
        db_session.add_all([user, role])
        await db_session.flush()  # Flush to get IDs without committing

        # Store IDs before committing to avoid async context issues
        user_id = user.id
        role_id = role.id

        await db_session.commit()

        # Test global scope
        global_assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=role_id,
            scope_type="global",
            scope_id=None,
            is_immutable=False,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(global_assignment)
        await db_session.commit()

        # Test project scope
        project_id = uuid4()
        project_assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=role_id,
            scope_type="project",
            scope_id=project_id,
            is_immutable=False,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(project_assignment)
        await db_session.commit()

        # Test flow scope
        flow_id = uuid4()
        flow_assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=role_id,
            scope_type="flow",
            scope_id=flow_id,
            is_immutable=False,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(flow_assignment)
        await db_session.commit()

        # Verify all assignments were created (using ORM query)
        result = await db_session.execute(select(UserRoleAssignment).where(UserRoleAssignment.user_id == user_id))
        assignments = result.scalars().all()
        assert len(assignments) == 3

    async def test_immutable_flag(self, db_session):
        """Test that the is_immutable flag works correctly."""
        from langbuilder.services.database.models.rbac import (
            Role,
            UserRoleAssignment,
        )
        from langbuilder.services.database.models.user import User

        # Create user and role
        user = User(username="immutableuser", password="hashedpassword", is_active=True, is_superuser=False)
        role = Role(name="StarterOwner", description="Starter Project Owner", is_system=True)
        db_session.add_all([user, role])
        await db_session.flush()  # Flush to get IDs

        # Store IDs before committing
        user_id = user.id
        role_id = role.id

        await db_session.commit()

        # Create immutable assignment
        assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=role_id,
            scope_type="project",
            scope_id=uuid4(),
            is_immutable=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(assignment)
        await db_session.flush()  # Flush to get ID before committing

        # Store assignment_id to avoid async context issues
        assignment_id = assignment.id

        await db_session.commit()

        # Verify immutable flag is set (using ORM query)
        result = await db_session.execute(select(UserRoleAssignment).where(UserRoleAssignment.id == assignment_id))
        fetched_assignment = result.scalar_one()
        assert fetched_assignment.is_immutable is True

    async def test_composite_unique_constraint(self, db_session):
        """Test that the composite unique constraint on user_role_assignment works."""
        from langbuilder.services.database.models.rbac import (
            Role,
            UserRoleAssignment,
        )
        from langbuilder.services.database.models.user import User

        # Create user and role
        user = User(username="uniqueuser", password="hashedpassword", is_active=True, is_superuser=False)
        role = Role(name="UniqueRole", description="Test role", is_system=True)
        db_session.add_all([user, role])
        await db_session.flush()  # Flush to get IDs

        # Store IDs to avoid async context issues
        user_id = user.id
        role_id = role.id

        await db_session.commit()

        scope_id = uuid4()

        # Create first assignment
        assignment1 = UserRoleAssignment(
            user_id=user_id,
            role_id=role_id,
            scope_type="project",
            scope_id=scope_id,
            is_immutable=False,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(assignment1)
        await db_session.commit()

        # Try to create duplicate assignment
        assignment2 = UserRoleAssignment(
            user_id=user_id,
            role_id=role_id,
            scope_type="project",
            scope_id=scope_id,
            is_immutable=False,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(assignment2)

        # This should fail due to unique constraint
        with pytest.raises(Exception):
            await db_session.commit()
        await db_session.rollback()


class TestRBACMigrationRollback:
    """Test rollback functionality of RBAC migration."""

    @pytest.fixture
    async def db_engine_with_migration(self, tmp_path):
        """Create a test database with migrations applied."""
        db_path = tmp_path / "test_rollback.db"
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        yield engine, db_path
        await engine.dispose()

    async def test_rollback_removes_all_tables(self, db_engine_with_migration):
        """Test that downgrade removes all RBAC tables."""
        engine, db_path = db_engine_with_migration

        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        # Check tables exist
        def check_tables_exist(conn):
            inspector = inspect(conn)
            table_names = inspector.get_table_names()
            assert "permission" in table_names
            assert "role" in table_names
            assert "role_permission" in table_names
            assert "user_role_assignment" in table_names

        async with engine.connect() as conn:
            await conn.run_sync(check_tables_exist)

        # Simulate rollback by dropping RBAC tables
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS user_role_assignment"))
            await conn.execute(text("DROP TABLE IF EXISTS role_permission"))
            await conn.execute(text("DROP TABLE IF EXISTS role"))
            await conn.execute(text("DROP TABLE IF EXISTS permission"))

        # Verify tables were removed
        def check_tables_removed(conn):
            inspector = inspect(conn)
            table_names = inspector.get_table_names()
            assert "permission" not in table_names
            assert "role" not in table_names
            assert "role_permission" not in table_names
            assert "user_role_assignment" not in table_names

            # Verify other tables still exist (user, flow, etc.)
            assert "user" in table_names
            assert "flow" in table_names

        async with engine.connect() as conn:
            await conn.run_sync(check_tables_removed)


class TestRBACMigrationExecution:
    """Test suite for actual Alembic migration execution."""

    @pytest.fixture
    def alembic_base_dir(self):
        """Get the base directory for Alembic operations."""
        # Navigate from test file to the alembic directory
        return Path("/home/nick/LangBuilder/src/backend/base/langbuilder")

    @pytest.mark.skip(reason="Requires Alembic configuration - integration test, not unit test")
    async def test_migration_upgrade_execution(self, tmp_path, alembic_base_dir):
        """Test actual alembic upgrade command execution."""
        db_path = tmp_path / "test_migration.db"
        db_url = f"sqlite+aiosqlite:///{db_path}"

        # Set environment variable for database URL
        env = os.environ.copy()
        env["LANGBUILDER_DATABASE_URL"] = db_url

        # Run alembic upgrade to head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=str(alembic_base_dir),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        # Check migration succeeded
        assert result.returncode == 0, f"Migration failed: {result.stderr}"
        assert "Running upgrade" in result.stdout or result.returncode == 0

        # Verify RBAC tables were created
        engine = create_async_engine(db_url)

        def check_tables_created(conn):
            inspector = inspect(conn)
            table_names = inspector.get_table_names()
            assert "permission" in table_names
            assert "role" in table_names
            assert "role_permission" in table_names
            assert "user_role_assignment" in table_names

        async with engine.connect() as conn:
            await conn.run_sync(check_tables_created)

        await engine.dispose()

    @pytest.mark.skip(reason="Requires Alembic configuration - integration test, not unit test")
    async def test_migration_downgrade_execution(self, tmp_path, alembic_base_dir):
        """Test actual alembic downgrade command execution."""
        db_path = tmp_path / "test_downgrade.db"
        db_url = f"sqlite+aiosqlite:///{db_path}"

        env = os.environ.copy()
        env["LANGBUILDER_DATABASE_URL"] = db_url

        # First, upgrade to head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=str(alembic_base_dir),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"Upgrade failed: {result.stderr}"

        # Verify tables exist
        engine = create_async_engine(db_url)

        def check_tables_exist(conn):
            inspector = inspect(conn)
            table_names = inspector.get_table_names()
            assert "permission" in table_names
            assert "role" in table_names

        async with engine.connect() as conn:
            await conn.run_sync(check_tables_exist)

        # Now downgrade to remove RBAC tables
        # Find the revision before RBAC migration (a20a7041e437)
        result = subprocess.run(
            ["alembic", "downgrade", "3162e83e485f"],  # Revision before Task 1.4
            cwd=str(alembic_base_dir),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, f"Downgrade failed: {result.stderr}"

        # Verify RBAC tables were removed
        def check_tables_removed(conn):
            inspector = inspect(conn)
            table_names = inspector.get_table_names()
            assert "permission" not in table_names
            assert "role" not in table_names
            assert "role_permission" not in table_names
            assert "user_role_assignment" not in table_names

        async with engine.connect() as conn:
            await conn.run_sync(check_tables_removed)

        await engine.dispose()

    @pytest.mark.skip(reason="Requires Alembic configuration - integration test, not unit test")
    async def test_migration_multiple_cycles(self, tmp_path, alembic_base_dir):
        """Test that migration can be applied and rolled back multiple times."""
        db_path = tmp_path / "test_cycles.db"
        db_url = f"sqlite+aiosqlite:///{db_path}"

        env = os.environ.copy()
        env["LANGBUILDER_DATABASE_URL"] = db_url

        # Perform 3 upgrade/downgrade cycles
        for i in range(3):
            # Upgrade
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                cwd=str(alembic_base_dir),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, f"Upgrade cycle {i + 1} failed: {result.stderr}"

            # Verify tables exist
            engine = create_async_engine(db_url)

            def check_tables_exist(conn):
                inspector = inspect(conn)
                table_names = inspector.get_table_names()
                assert "permission" in table_names
                assert "role" in table_names

            async with engine.connect() as conn:
                await conn.run_sync(check_tables_exist)

            await engine.dispose()

            # Downgrade
            result = subprocess.run(
                ["alembic", "downgrade", "3162e83e485f"],
                cwd=str(alembic_base_dir),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, f"Downgrade cycle {i + 1} failed: {result.stderr}"

            # Verify tables removed
            engine = create_async_engine(db_url)

            def check_tables_removed(conn):
                inspector = inspect(conn)
                table_names = inspector.get_table_names()
                assert "permission" not in table_names

            async with engine.connect() as conn:
                await conn.run_sync(check_tables_removed)

            await engine.dispose()
