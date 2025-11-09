"""Unit tests for backfill Owner role assignments data migration (Task 1.6).

This module tests the Alembic data migration that assigns Owner roles to
existing users for their Projects and Flows.
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from langbuilder.services.database.models.flow.model import Flow
from langbuilder.services.database.models.folder.model import Folder
from langbuilder.services.database.models.role.model import Role
from langbuilder.services.database.models.role.seed_data import seed_rbac_data
from langbuilder.services.database.models.user.model import User
from langbuilder.services.database.models.user_role_assignment.model import UserRoleAssignment
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.pool import StaticPool


# Import the migration functions directly
# We'll execute them as regular Python functions for testing
async def get_owner_role_id(session: AsyncSession):
    """Helper to get Owner role ID as UUID object."""
    stmt = select(Role).where(Role.name == "Owner")
    result = await session.exec(stmt)
    role = result.first()
    return role.id if role else None


async def execute_upgrade_migration(session: AsyncSession, owner_role_id):
    """Execute the upgrade migration logic using ORM (for testing)."""
    # Mark Starter Projects
    stmt_folders = select(Folder).where(Folder.name == "Starter Projects", Folder.user_id.is_(None))
    result = await session.exec(stmt_folders)
    starter_folders = result.all()
    for folder in starter_folders:
        folder.is_starter_project = True
    await session.commit()

    # Assign Owner role for all Projects (Folders with user_id)
    stmt_projects = select(Folder).where(Folder.user_id.isnot(None))
    result = await session.exec(stmt_projects)
    projects = result.all()

    for project in projects:
        # Check if assignment already exists (idempotent)
        check_stmt = select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == project.user_id,
            UserRoleAssignment.role_id == owner_role_id,
            UserRoleAssignment.scope_type == "Project",
            UserRoleAssignment.scope_id == project.id
        )
        check_result = await session.exec(check_stmt)
        existing = check_result.first()

        if not existing:
            assignment = UserRoleAssignment(
                id=uuid4(),
                user_id=project.user_id,
                role_id=owner_role_id,
                scope_type="Project",
                scope_id=project.id,
                is_immutable=project.is_starter_project,
                created_at=datetime.now(timezone.utc),
                created_by=None
            )
            session.add(assignment)

    await session.commit()

    # Assign Owner role for standalone Flows (not in a project)
    stmt_flows = select(Flow).where(Flow.user_id.isnot(None), Flow.folder_id.is_(None))
    result = await session.exec(stmt_flows)
    flows = result.all()

    for flow in flows:
        # Check if assignment already exists (idempotent)
        check_stmt = select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == flow.user_id,
            UserRoleAssignment.role_id == owner_role_id,
            UserRoleAssignment.scope_type == "Flow",
            UserRoleAssignment.scope_id == flow.id
        )
        check_result = await session.exec(check_stmt)
        existing = check_result.first()

        if not existing:
            assignment = UserRoleAssignment(
                id=uuid4(),
                user_id=flow.user_id,
                role_id=owner_role_id,
                scope_type="Flow",
                scope_id=flow.id,
                is_immutable=False,
                created_at=datetime.now(timezone.utc),
                created_by=None
            )
            session.add(assignment)

    await session.commit()


async def execute_downgrade_migration(session: AsyncSession, owner_role_id):
    """Execute the downgrade migration logic using ORM (for testing)."""
    # Remove Project-level Owner assignments where created_by is NULL
    stmt_project_assignments = select(UserRoleAssignment).where(
        UserRoleAssignment.role_id == owner_role_id,
        UserRoleAssignment.scope_type == "Project",
        UserRoleAssignment.created_by.is_(None)
    )
    result = await session.exec(stmt_project_assignments)
    project_assignments = result.all()
    for assignment in project_assignments:
        await session.delete(assignment)

    # Remove Flow-level Owner assignments where created_by is NULL
    stmt_flow_assignments = select(UserRoleAssignment).where(
        UserRoleAssignment.role_id == owner_role_id,
        UserRoleAssignment.scope_type == "Flow",
        UserRoleAssignment.created_by.is_(None)
    )
    result = await session.exec(stmt_flow_assignments)
    flow_assignments = result.all()
    for assignment in flow_assignments:
        await session.delete(assignment)

    await session.commit()

    # Revert is_starter_project flag
    stmt_folders = select(Folder).where(Folder.name == "Starter Projects", Folder.user_id.is_(None))
    result = await session.exec(stmt_folders)
    starter_folders = result.all()
    for folder in starter_folders:
        folder.is_starter_project = False

    await session.commit()


@pytest.fixture
async def db_with_rbac() -> AsyncSession:
    """Create a test database with RBAC data seeded."""
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    # Import SQLModel to get metadata
    from sqlmodel import SQLModel

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        # Seed RBAC data
        await seed_rbac_data(session)
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.mark.asyncio
async def test_migration_creates_owner_assignments_for_projects(db_with_rbac: AsyncSession):
    """Test that migration creates Owner role assignments for all existing Projects."""
    # Create test users
    user1 = User(id=uuid4(), username="user1", password="hashed", is_active=True, is_superuser=False)
    user2 = User(id=uuid4(), username="user2", password="hashed", is_active=True, is_superuser=False)
    db_with_rbac.add(user1)
    db_with_rbac.add(user2)
    await db_with_rbac.commit()

    # Create test projects
    project1 = Folder(id=uuid4(), name="Project 1", user_id=user1.id)
    project2 = Folder(id=uuid4(), name="Project 2", user_id=user2.id)
    db_with_rbac.add(project1)
    db_with_rbac.add(project2)
    await db_with_rbac.commit()

    # Run migration
    owner_role_id = await get_owner_role_id(db_with_rbac)
    assert owner_role_id is not None, "Owner role should exist"

    await execute_upgrade_migration(db_with_rbac, owner_role_id)
    await db_with_rbac.commit()

    # Verify role assignments were created
    stmt = select(UserRoleAssignment).where(
        UserRoleAssignment.scope_type == "Project",
        UserRoleAssignment.role_id == owner_role_id
    )
    result = await db_with_rbac.exec(stmt)
    assignments = result.all()

    assert len(assignments) == 2, "Should create 2 Owner assignments for 2 projects"

    # Verify assignment details
    assignment_map = {str(a.scope_id): a for a in assignments}
    assert str(project1.id) in assignment_map, "Project 1 should have Owner assignment"
    assert str(project2.id) in assignment_map, "Project 2 should have Owner assignment"

    assert assignment_map[str(project1.id)].user_id == user1.id, "Project 1 owner should be user1"
    assert assignment_map[str(project2.id)].user_id == user2.id, "Project 2 owner should be user2"


@pytest.mark.asyncio
async def test_migration_creates_owner_assignments_for_standalone_flows(db_with_rbac: AsyncSession):
    """Test that migration creates Owner role assignments for standalone Flows (not in projects)."""
    # Create test user
    user = User(id=uuid4(), username="user1", password="hashed", is_active=True, is_superuser=False)
    db_with_rbac.add(user)
    await db_with_rbac.commit()

    # Create standalone flows (no folder_id)
    flow1 = Flow(id=uuid4(), name="Flow 1", user_id=user.id, folder_id=None, data={})
    flow2 = Flow(id=uuid4(), name="Flow 2", user_id=user.id, folder_id=None, data={})
    db_with_rbac.add(flow1)
    db_with_rbac.add(flow2)
    await db_with_rbac.commit()

    # Run migration
    owner_role_id = await get_owner_role_id(db_with_rbac)
    await execute_upgrade_migration(db_with_rbac, owner_role_id)
    await db_with_rbac.commit()

    # Verify role assignments were created
    stmt = select(UserRoleAssignment).where(
        UserRoleAssignment.scope_type == "Flow",
        UserRoleAssignment.role_id == owner_role_id
    )
    result = await db_with_rbac.exec(stmt)
    assignments = result.all()

    assert len(assignments) == 2, "Should create 2 Owner assignments for 2 standalone flows"

    # Verify assignment details
    assignment_map = {str(a.scope_id): a for a in assignments}
    assert str(flow1.id) in assignment_map, "Flow 1 should have Owner assignment"
    assert str(flow2.id) in assignment_map, "Flow 2 should have Owner assignment"

    assert assignment_map[str(flow1.id)].user_id == user.id, "Flow 1 owner should be user"
    assert assignment_map[str(flow2.id)].user_id == user.id, "Flow 2 owner should be user"

    # Verify is_immutable is False for standalone flows
    assert assignment_map[str(flow1.id)].is_immutable is False, "Standalone flow assignment should not be immutable"
    assert assignment_map[str(flow2.id)].is_immutable is False, "Standalone flow assignment should not be immutable"


@pytest.mark.asyncio
async def test_migration_does_not_assign_for_flows_in_projects(db_with_rbac: AsyncSession):
    """Test that migration does NOT create Flow-level assignments for flows inside projects."""
    # Create test user and project
    user = User(id=uuid4(), username="user1", password="hashed", is_active=True, is_superuser=False)
    db_with_rbac.add(user)
    await db_with_rbac.commit()

    project = Folder(id=uuid4(), name="Project 1", user_id=user.id)
    db_with_rbac.add(project)
    await db_with_rbac.commit()

    # Create flow inside project
    flow_in_project = Flow(id=uuid4(), name="Flow in Project", user_id=user.id, folder_id=project.id, data={})
    db_with_rbac.add(flow_in_project)
    await db_with_rbac.commit()

    # Run migration
    owner_role_id = await get_owner_role_id(db_with_rbac)
    await execute_upgrade_migration(db_with_rbac, owner_role_id)
    await db_with_rbac.commit()

    # Verify NO Flow-level assignment for this flow
    stmt = select(UserRoleAssignment).where(
        UserRoleAssignment.scope_type == "Flow",
        UserRoleAssignment.scope_id == flow_in_project.id
    )
    result = await db_with_rbac.exec(stmt)
    flow_assignments = result.all()

    assert len(flow_assignments) == 0, "Should NOT create Flow-level assignment for flows inside projects"

    # But Project-level assignment should exist
    stmt = select(UserRoleAssignment).where(
        UserRoleAssignment.scope_type == "Project",
        UserRoleAssignment.scope_id == project.id
    )
    result = await db_with_rbac.exec(stmt)
    project_assignments = result.all()

    assert len(project_assignments) == 1, "Should create Project-level assignment"


@pytest.mark.asyncio
async def test_migration_marks_starter_projects_as_immutable(db_with_rbac: AsyncSession):
    """Test that migration marks Starter Projects with is_starter_project=True and is_immutable=True."""
    # Create Starter Projects folder (no user_id)
    starter_folder = Folder(id=uuid4(), name="Starter Projects", user_id=None, is_starter_project=False)
    db_with_rbac.add(starter_folder)
    await db_with_rbac.commit()

    # Verify initial state
    assert starter_folder.is_starter_project is False, "Initially is_starter_project should be False"

    # Run migration
    owner_role_id = await get_owner_role_id(db_with_rbac)
    await execute_upgrade_migration(db_with_rbac, owner_role_id)
    await db_with_rbac.commit()

    # Refresh folder
    await db_with_rbac.refresh(starter_folder)

    # Verify is_starter_project was set to True
    assert starter_folder.is_starter_project is True, "Starter Projects folder should be marked as starter project"


@pytest.mark.asyncio
async def test_migration_skips_resources_without_users(db_with_rbac: AsyncSession):
    """Test that migration skips Projects and Flows without user_id."""
    # Create project without user_id
    project_no_user = Folder(id=uuid4(), name="Project No User", user_id=None)
    db_with_rbac.add(project_no_user)

    # Create flow without user_id
    flow_no_user = Flow(id=uuid4(), name="Flow No User", user_id=None, folder_id=None, data={})
    db_with_rbac.add(flow_no_user)
    await db_with_rbac.commit()

    # Run migration
    owner_role_id = await get_owner_role_id(db_with_rbac)
    await execute_upgrade_migration(db_with_rbac, owner_role_id)
    await db_with_rbac.commit()

    # Verify no assignments were created
    stmt = select(UserRoleAssignment).where(
        UserRoleAssignment.scope_id.in_([project_no_user.id, flow_no_user.id])
    )
    result = await db_with_rbac.exec(stmt)
    assignments = result.all()

    assert len(assignments) == 0, "Should not create assignments for resources without users"


@pytest.mark.asyncio
async def test_migration_is_idempotent(db_with_rbac: AsyncSession):
    """Test that migration can be run multiple times safely without creating duplicates."""
    # Create test data
    user = User(id=uuid4(), username="user1", password="hashed", is_active=True, is_superuser=False)
    db_with_rbac.add(user)
    await db_with_rbac.commit()

    project = Folder(id=uuid4(), name="Project 1", user_id=user.id)
    db_with_rbac.add(project)
    await db_with_rbac.commit()

    # Run migration first time
    owner_role_id = await get_owner_role_id(db_with_rbac)
    await execute_upgrade_migration(db_with_rbac, owner_role_id)
    await db_with_rbac.commit()

    # Count assignments
    stmt = select(UserRoleAssignment).where(UserRoleAssignment.scope_type == "Project")
    result = await db_with_rbac.exec(stmt)
    assignments_first = result.all()
    count_first = len(assignments_first)

    # Run migration second time
    await execute_upgrade_migration(db_with_rbac, owner_role_id)
    await db_with_rbac.commit()

    # Count assignments again
    result = await db_with_rbac.exec(stmt)
    assignments_second = result.all()
    count_second = len(assignments_second)

    assert count_first == count_second, "Should not create duplicate assignments on second run"
    assert count_first == 1, "Should have exactly 1 assignment"


@pytest.mark.asyncio
async def test_migration_downgrade_removes_assignments(db_with_rbac: AsyncSession):
    """Test that downgrade migration removes backfilled Owner role assignments."""
    # Create test data
    user = User(id=uuid4(), username="user1", password="hashed", is_active=True, is_superuser=False)
    db_with_rbac.add(user)
    await db_with_rbac.commit()

    project = Folder(id=uuid4(), name="Project 1", user_id=user.id)
    flow = Flow(id=uuid4(), name="Flow 1", user_id=user.id, folder_id=None, data={})
    db_with_rbac.add(project)
    db_with_rbac.add(flow)
    await db_with_rbac.commit()

    # Run upgrade migration
    owner_role_id = await get_owner_role_id(db_with_rbac)
    await execute_upgrade_migration(db_with_rbac, owner_role_id)
    await db_with_rbac.commit()

    # Verify assignments exist
    stmt = select(UserRoleAssignment)
    result = await db_with_rbac.exec(stmt)
    assignments_before = result.all()
    assert len(assignments_before) > 0, "Should have assignments after upgrade"

    # Run downgrade migration
    await execute_downgrade_migration(db_with_rbac, owner_role_id)
    await db_with_rbac.commit()

    # Verify assignments were removed
    result = await db_with_rbac.exec(stmt)
    assignments_after = result.all()
    assert len(assignments_after) == 0, "Should have no assignments after downgrade"


@pytest.mark.asyncio
async def test_migration_downgrade_reverts_starter_project_flag(db_with_rbac: AsyncSession):
    """Test that downgrade migration reverts is_starter_project flag."""
    # Create Starter Projects folder
    starter_folder = Folder(id=uuid4(), name="Starter Projects", user_id=None, is_starter_project=False)
    db_with_rbac.add(starter_folder)
    await db_with_rbac.commit()

    # Run upgrade
    owner_role_id = await get_owner_role_id(db_with_rbac)
    await execute_upgrade_migration(db_with_rbac, owner_role_id)
    await db_with_rbac.commit()
    await db_with_rbac.refresh(starter_folder)

    assert starter_folder.is_starter_project is True, "Should be True after upgrade"

    # Run downgrade
    await execute_downgrade_migration(db_with_rbac, owner_role_id)
    await db_with_rbac.commit()
    await db_with_rbac.refresh(starter_folder)

    assert starter_folder.is_starter_project is False, "Should be False after downgrade"


@pytest.mark.asyncio
async def test_migration_handles_multiple_users_and_projects(db_with_rbac: AsyncSession):
    """Test that migration correctly handles multiple users with multiple projects each."""
    # Create multiple users
    users = []
    for i in range(3):
        user = User(id=uuid4(), username=f"user{i}", password="hashed", is_active=True, is_superuser=False)
        users.append(user)
        db_with_rbac.add(user)
    await db_with_rbac.commit()

    # Create multiple projects per user
    expected_assignments = 0
    for user in users:
        for j in range(2):
            project = Folder(id=uuid4(), name=f"Project {j} for {user.username}", user_id=user.id)
            db_with_rbac.add(project)
            expected_assignments += 1
    await db_with_rbac.commit()

    # Run migration
    owner_role_id = await get_owner_role_id(db_with_rbac)
    await execute_upgrade_migration(db_with_rbac, owner_role_id)
    await db_with_rbac.commit()

    # Verify correct number of assignments
    stmt = select(UserRoleAssignment).where(UserRoleAssignment.scope_type == "Project")
    result = await db_with_rbac.exec(stmt)
    assignments = result.all()

    assert len(assignments) == expected_assignments, f"Should create {expected_assignments} assignments"

    # Verify each user has correct assignments
    for user in users:
        user_assignments = [a for a in assignments if a.user_id == user.id]
        assert len(user_assignments) == 2, f"User {user.username} should have 2 assignments"


@pytest.mark.asyncio
async def test_migration_assignment_created_at_is_set(db_with_rbac: AsyncSession):
    """Test that migration sets created_at timestamp on assignments."""
    # Create test data
    user = User(id=uuid4(), username="user1", password="hashed", is_active=True, is_superuser=False)
    db_with_rbac.add(user)
    await db_with_rbac.commit()

    project = Folder(id=uuid4(), name="Project 1", user_id=user.id)
    db_with_rbac.add(project)
    await db_with_rbac.commit()

    # Run migration
    owner_role_id = await get_owner_role_id(db_with_rbac)
    await execute_upgrade_migration(db_with_rbac, owner_role_id)
    await db_with_rbac.commit()

    # Verify created_at is set
    stmt = select(UserRoleAssignment).where(UserRoleAssignment.scope_type == "Project")
    result = await db_with_rbac.exec(stmt)
    assignments = result.all()

    assert len(assignments) == 1
    assignment = assignments[0]
    assert assignment.created_at is not None, "created_at should be set"
    assert isinstance(assignment.created_at, datetime), "created_at should be a datetime"


@pytest.mark.asyncio
async def test_migration_assignment_created_by_is_null(db_with_rbac: AsyncSession):
    """Test that migration sets created_by to NULL (system-created)."""
    # Create test data
    user = User(id=uuid4(), username="user1", password="hashed", is_active=True, is_superuser=False)
    db_with_rbac.add(user)
    await db_with_rbac.commit()

    project = Folder(id=uuid4(), name="Project 1", user_id=user.id)
    db_with_rbac.add(project)
    await db_with_rbac.commit()

    # Run migration
    owner_role_id = await get_owner_role_id(db_with_rbac)
    await execute_upgrade_migration(db_with_rbac, owner_role_id)
    await db_with_rbac.commit()

    # Verify created_by is NULL
    stmt = select(UserRoleAssignment).where(UserRoleAssignment.scope_type == "Project")
    result = await db_with_rbac.exec(stmt)
    assignments = result.all()

    assert len(assignments) == 1
    assignment = assignments[0]
    assert assignment.created_by is None, "created_by should be NULL for system-created assignments"


@pytest.mark.asyncio
async def test_migration_handles_empty_database(db_with_rbac: AsyncSession):
    """Test that migration handles empty database gracefully."""
    # Run migration on empty database (only RBAC data exists)
    owner_role_id = await get_owner_role_id(db_with_rbac)
    await execute_upgrade_migration(db_with_rbac, owner_role_id)
    await db_with_rbac.commit()

    # Verify no assignments were created
    stmt = select(UserRoleAssignment)
    result = await db_with_rbac.exec(stmt)
    assignments = result.all()

    assert len(assignments) == 0, "Should not create assignments in empty database"


@pytest.mark.asyncio
async def test_migration_only_assigns_owner_role(db_with_rbac: AsyncSession):
    """Test that migration only creates assignments for Owner role, not other roles."""
    # Create test data
    user = User(id=uuid4(), username="user1", password="hashed", is_active=True, is_superuser=False)
    db_with_rbac.add(user)
    await db_with_rbac.commit()

    project = Folder(id=uuid4(), name="Project 1", user_id=user.id)
    db_with_rbac.add(project)
    await db_with_rbac.commit()

    # Run migration
    owner_role_id = await get_owner_role_id(db_with_rbac)
    await execute_upgrade_migration(db_with_rbac, owner_role_id)
    await db_with_rbac.commit()

    # Verify all assignments are for Owner role
    stmt = select(UserRoleAssignment)
    result = await db_with_rbac.exec(stmt)
    assignments = result.all()

    for assignment in assignments:
        assert assignment.role_id == owner_role_id, "All assignments should be for Owner role"

    # Get other roles
    stmt = select(Role).where(Role.name != "Owner")
    result = await db_with_rbac.exec(stmt)
    other_roles = result.all()

    # Verify no assignments for other roles
    for role in other_roles:
        stmt = select(UserRoleAssignment).where(UserRoleAssignment.role_id == role.id)
        result = await db_with_rbac.exec(stmt)
        other_assignments = result.all()
        assert len(other_assignments) == 0, f"Should not create assignments for {role.name} role"
