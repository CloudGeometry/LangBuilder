"""Fixtures for unit tests with proper database isolation."""

import os

# Set test database URL BEFORE any langbuilder imports to ensure test isolation
os.environ["LANGBUILDER_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import Mock

import pytest

# Import all models at module level to ensure they're registered with SQLModel metadata
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.pool import StaticPool

# Use a lock to ensure only one test database setup happens at a time
_setup_lock = asyncio.Lock()


class TestDatabaseContext:
    """Context manager for test database isolation."""

    def __init__(self):
        self.engine = None

    async def setup(self):
        """Create a fresh test database."""
        # Create an in-memory database engine with a unique database per test
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )

        # Add event listener to enable foreign keys for every connection
        @event.listens_for(self.engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # Create all tables
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def teardown(self):
        """Clean up the test database."""
        if self.engine:
            # Drop all tables
            async with self.engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.drop_all)

            # Dispose of the engine
            await self.engine.dispose()
            self.engine = None


@pytest.fixture(autouse=True)
async def setup_test_database(monkeypatch, request):
    """Automatically set up an isolated test database for all tests in this directory.

    This fixture:
    1. Creates a fresh in-memory SQLite database for each test
    2. Creates all tables (including RBAC tables)
    3. Monkey-patches session_getter and get_db_service to use the test database
    4. Cleans up after the test completes
    """
    # Clear the service manager cache before each test
    from langbuilder.services.manager import service_manager

    service_manager.factories.clear()
    service_manager.services.clear()

    # Create test database context
    db_context = TestDatabaseContext()
    await db_context.setup()

    # Create a session getter that uses our test engine
    @asynccontextmanager
    async def test_session_getter(db_service=None):
        async with AsyncSession(db_context.engine, expire_on_commit=False) as session:
            yield session

    # Create a mock database service with with_session method
    mock_db_service = Mock()
    mock_db_service.engine = db_context.engine

    # Add with_session method that returns async context manager
    @asynccontextmanager
    async def mock_with_session():
        """Provide async session for test database."""
        async with AsyncSession(db_context.engine, expire_on_commit=False) as session:
            yield session

    mock_db_service.with_session = mock_with_session

    # Monkey-patch get_db_service at the source
    monkeypatch.setattr("langbuilder.services.deps.get_db_service", lambda: mock_db_service)

    # Monkey-patch session_getter to use our test engine
    # Patch it both at the source and where it's imported in the test file
    monkeypatch.setattr("langbuilder.services.database.utils.session_getter", test_session_getter)
    # Also patch in the test module's namespace
    import sys

    if "tests.unit.test_rbac_models" in sys.modules:
        monkeypatch.setattr("tests.unit.test_rbac_models.session_getter", test_session_getter)
    if "tests.unit.test_user_role_assignment" in sys.modules:
        monkeypatch.setattr("tests.unit.test_user_role_assignment.session_getter", test_session_getter)
    if "tests.unit.test_rbac_setup" in sys.modules:
        monkeypatch.setattr("tests.unit.test_rbac_setup.session_getter", test_session_getter)
        monkeypatch.setattr("tests.unit.test_rbac_setup.get_db_service", lambda: mock_db_service)
    if "tests.unit.test_rbac_startup_integration" in sys.modules:
        monkeypatch.setattr("tests.unit.test_rbac_startup_integration.session_getter", test_session_getter)
        monkeypatch.setattr("tests.unit.test_rbac_startup_integration.get_db_service", lambda: mock_db_service)
    if "tests.unit.test_migrate_rbac_data" in sys.modules:
        monkeypatch.setattr("tests.unit.test_migrate_rbac_data.session_getter", test_session_getter)
        monkeypatch.setattr("tests.unit.test_migrate_rbac_data.get_db_service", lambda: mock_db_service)

    # Patch session_scope to use test database
    @asynccontextmanager
    async def test_session_scope():
        """Test version of session_scope using test database."""
        from loguru import logger

        db_service = mock_db_service
        async with db_service.with_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                logger.exception("An error occurred during the session scope.")
                await session.rollback()
                raise

    monkeypatch.setattr("langbuilder.services.deps.session_scope", test_session_scope)

    # Patch in test module namespace
    if "tests.unit.test_rbac_startup_integration" in sys.modules:
        monkeypatch.setattr("tests.unit.test_rbac_startup_integration.session_scope", test_session_scope)

    # Provide the test engine to tests
    yield db_context.engine

    # Clean up after the test
    await db_context.teardown()

    # Clear the service manager cache after the test
    service_manager.factories.clear()
    service_manager.services.clear()


@pytest.fixture
async def clean_db_session(setup_test_database):
    """Provides an isolated database session for tests that explicitly request it.

    This is an alternative to using session_getter for tests that prefer
    direct session injection.
    """
    async with AsyncSession(setup_test_database, expire_on_commit=False) as session:
        yield session
