"""Unit tests for Flow and Folder RBAC relationship implementations.

This test module covers:
- Flow to UserRoleAssignment relationship
- Folder to UserRoleAssignment relationship
- Folder is_starter_project field
- Querying role assignments through Flow and Folder models
- Backward compatibility with existing models
"""

import pytest
from langbuilder.services.database.models.flow.model import Flow
from langbuilder.services.database.models.folder.model import Folder
from langbuilder.services.database.models.role.crud import create_role
from langbuilder.services.database.models.role.model import RoleCreate
from langbuilder.services.database.models.user.model import User
from langbuilder.services.database.models.user_role_assignment.crud import (
    create_user_role_assignment,
    list_assignments_by_scope,
)
from langbuilder.services.database.models.user_role_assignment.model import UserRoleAssignmentCreate
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession


@pytest.fixture
async def test_user(async_session: AsyncSession):
    """Create a test user for relationship tests."""
    from langbuilder.services.auth.utils import get_password_hash

    user = User(
        username="flowfolderuser",
        password=get_password_hash("password"),
        is_active=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
async def test_flow(async_session: AsyncSession, test_user: User):
    """Create a test flow for relationship tests."""
    flow_data = {
        "name": "Test Flow",
        "description": "Test flow for RBAC relationships",
        "data": {"nodes": [], "edges": []},
        "user_id": test_user.id,
    }
    flow = Flow(**flow_data)
    async_session.add(flow)
    await async_session.commit()
    await async_session.refresh(flow)
    return flow


@pytest.fixture
async def test_folder(async_session: AsyncSession, test_user: User):
    """Create a test folder for relationship tests."""
    folder = Folder(
        name="Test Project",
        description="Test project for RBAC relationships",
        user_id=test_user.id,
    )
    async_session.add(folder)
    await async_session.commit()
    await async_session.refresh(folder)
    return folder


# ============================================================================
# FLOW RBAC RELATIONSHIP TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_flow_role_assignments_relationship_empty(async_session: AsyncSession, test_flow: Flow):
    """Test that Flow has role_assignments relationship and it starts empty."""
    # Query flow with eager loading
    stmt = select(Flow).where(Flow.id == test_flow.id).options(selectinload(Flow.role_assignments))
    result = await async_session.execute(stmt)
    flow = result.scalar_one()

    # Verify role_assignments relationship exists and is empty
    assert hasattr(flow, "role_assignments")
    assert isinstance(flow.role_assignments, list)
    assert len(flow.role_assignments) == 0


@pytest.mark.asyncio
async def test_flow_role_assignments_with_assignments(async_session: AsyncSession, test_flow: Flow, test_user: User):
    """Test querying role assignments through Flow relationship."""
    # Create roles
    viewer_role = await create_role(async_session, RoleCreate(name="Viewer"))
    editor_role = await create_role(async_session, RoleCreate(name="Editor"))

    # Assign roles to user for this specific flow
    assignment_1 = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=viewer_role.id, scope_type="Flow", scope_id=test_flow.id
    )
    await create_user_role_assignment(async_session, assignment_1)

    assignment_2 = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=editor_role.id, scope_type="Flow", scope_id=test_flow.id
    )
    await create_user_role_assignment(async_session, assignment_2)

    # Query flow with eager loading of role assignments
    stmt = select(Flow).where(Flow.id == test_flow.id).options(selectinload(Flow.role_assignments))
    result = await async_session.execute(stmt)
    flow = result.scalar_one()

    # Verify role assignments are accessible through relationship
    assert len(flow.role_assignments) == 2

    # Verify the assignments have correct scope_type and scope_id
    for assignment in flow.role_assignments:
        assert assignment.scope_type == "Flow"
        assert assignment.scope_id == test_flow.id
        assert assignment.user_id == test_user.id

    # Verify specific roles are present
    role_ids = [assignment.role_id for assignment in flow.role_assignments]
    assert viewer_role.id in role_ids
    assert editor_role.id in role_ids


@pytest.mark.asyncio
async def test_flow_role_assignments_filtered_by_scope(async_session: AsyncSession, test_user: User):
    """Test that Flow only shows assignments for its specific scope (not other flows or projects)."""
    # Create two flows
    flow1 = Flow(
        name="Flow 1", description="First flow", data={"nodes": [], "edges": []}, user_id=test_user.id
    )
    flow2 = Flow(
        name="Flow 2", description="Second flow", data={"nodes": [], "edges": []}, user_id=test_user.id
    )
    async_session.add(flow1)
    async_session.add(flow2)
    await async_session.commit()
    await async_session.refresh(flow1)
    await async_session.refresh(flow2)

    # Create a role
    role = await create_role(async_session, RoleCreate(name="Editor"))

    # Assign role to user for flow1 only
    assignment = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Flow", scope_id=flow1.id
    )
    await create_user_role_assignment(async_session, assignment)

    # Query flow1 with role assignments
    stmt = select(Flow).where(Flow.id == flow1.id).options(selectinload(Flow.role_assignments))
    result = await async_session.execute(stmt)
    queried_flow1 = result.scalar_one()

    # Query flow2 with role assignments
    stmt = select(Flow).where(Flow.id == flow2.id).options(selectinload(Flow.role_assignments))
    result = await async_session.execute(stmt)
    queried_flow2 = result.scalar_one()

    # Verify flow1 has the assignment, flow2 doesn't
    assert len(queried_flow1.role_assignments) == 1
    assert queried_flow1.role_assignments[0].scope_id == flow1.id

    assert len(queried_flow2.role_assignments) == 0


@pytest.mark.asyncio
async def test_flow_role_assignments_not_include_project_scope(
    async_session: AsyncSession, test_flow: Flow, test_user: User
):
    """Test that Flow role_assignments only include Flow scope, not Project scope."""
    # Create a folder (project)
    folder = Folder(name="Test Project", user_id=test_user.id)
    async_session.add(folder)
    await async_session.commit()
    await async_session.refresh(folder)

    # Create roles
    flow_role = await create_role(async_session, RoleCreate(name="FlowEditor"))
    project_role = await create_role(async_session, RoleCreate(name="ProjectAdmin"))

    # Assign Flow role to the flow
    flow_assignment = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=flow_role.id, scope_type="Flow", scope_id=test_flow.id
    )
    await create_user_role_assignment(async_session, flow_assignment)

    # Assign Project role to the project
    project_assignment = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=project_role.id, scope_type="Project", scope_id=folder.id
    )
    await create_user_role_assignment(async_session, project_assignment)

    # Query flow with role assignments
    stmt = select(Flow).where(Flow.id == test_flow.id).options(selectinload(Flow.role_assignments))
    result = await async_session.execute(stmt)
    flow = result.scalar_one()

    # Verify flow only has Flow scope assignments, not Project scope
    assert len(flow.role_assignments) == 1
    assert flow.role_assignments[0].scope_type == "Flow"
    assert flow.role_assignments[0].scope_id == test_flow.id
    assert flow.role_assignments[0].role_id == flow_role.id


# ============================================================================
# FOLDER RBAC RELATIONSHIP TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_folder_role_assignments_relationship_empty(async_session: AsyncSession, test_folder: Folder):
    """Test that Folder has role_assignments relationship and it starts empty."""
    # Query folder with eager loading
    stmt = select(Folder).where(Folder.id == test_folder.id).options(selectinload(Folder.role_assignments))
    result = await async_session.execute(stmt)
    folder = result.scalar_one()

    # Verify role_assignments relationship exists and is empty
    assert hasattr(folder, "role_assignments")
    assert isinstance(folder.role_assignments, list)
    assert len(folder.role_assignments) == 0


@pytest.mark.asyncio
async def test_folder_role_assignments_with_assignments(
    async_session: AsyncSession, test_folder: Folder, test_user: User
):
    """Test querying role assignments through Folder relationship."""
    # Create roles
    owner_role = await create_role(async_session, RoleCreate(name="Owner"))
    admin_role = await create_role(async_session, RoleCreate(name="Admin"))

    # Assign roles to user for this specific project
    assignment_1 = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=owner_role.id, scope_type="Project", scope_id=test_folder.id
    )
    await create_user_role_assignment(async_session, assignment_1)

    assignment_2 = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=admin_role.id, scope_type="Project", scope_id=test_folder.id
    )
    await create_user_role_assignment(async_session, assignment_2)

    # Query folder with eager loading of role assignments
    stmt = select(Folder).where(Folder.id == test_folder.id).options(selectinload(Folder.role_assignments))
    result = await async_session.execute(stmt)
    folder = result.scalar_one()

    # Verify role assignments are accessible through relationship
    assert len(folder.role_assignments) == 2

    # Verify the assignments have correct scope_type and scope_id
    for assignment in folder.role_assignments:
        assert assignment.scope_type == "Project"
        assert assignment.scope_id == test_folder.id
        assert assignment.user_id == test_user.id

    # Verify specific roles are present
    role_ids = [assignment.role_id for assignment in folder.role_assignments]
    assert owner_role.id in role_ids
    assert admin_role.id in role_ids


@pytest.mark.asyncio
async def test_folder_role_assignments_filtered_by_scope(async_session: AsyncSession, test_user: User):
    """Test that Folder only shows assignments for its specific scope (not other projects or flows)."""
    # Create two folders
    folder1 = Folder(name="Project 1", description="First project", user_id=test_user.id)
    folder2 = Folder(name="Project 2", description="Second project", user_id=test_user.id)
    async_session.add(folder1)
    async_session.add(folder2)
    await async_session.commit()
    await async_session.refresh(folder1)
    await async_session.refresh(folder2)

    # Create a role
    role = await create_role(async_session, RoleCreate(name="Admin"))

    # Assign role to user for folder1 only
    assignment = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Project", scope_id=folder1.id
    )
    await create_user_role_assignment(async_session, assignment)

    # Query folder1 with role assignments
    stmt = select(Folder).where(Folder.id == folder1.id).options(selectinload(Folder.role_assignments))
    result = await async_session.execute(stmt)
    queried_folder1 = result.scalar_one()

    # Query folder2 with role assignments
    stmt = select(Folder).where(Folder.id == folder2.id).options(selectinload(Folder.role_assignments))
    result = await async_session.execute(stmt)
    queried_folder2 = result.scalar_one()

    # Verify folder1 has the assignment, folder2 doesn't
    assert len(queried_folder1.role_assignments) == 1
    assert queried_folder1.role_assignments[0].scope_id == folder1.id

    assert len(queried_folder2.role_assignments) == 0


@pytest.mark.asyncio
async def test_folder_role_assignments_not_include_flow_scope(
    async_session: AsyncSession, test_folder: Folder, test_user: User
):
    """Test that Folder role_assignments only include Project scope, not Flow scope."""
    # Create a flow
    flow = Flow(
        name="Test Flow",
        description="Test flow",
        data={"nodes": [], "edges": []},
        user_id=test_user.id,
        folder_id=test_folder.id,
    )
    async_session.add(flow)
    await async_session.commit()
    await async_session.refresh(flow)

    # Create roles
    project_role = await create_role(async_session, RoleCreate(name="ProjectAdmin"))
    flow_role = await create_role(async_session, RoleCreate(name="FlowEditor"))

    # Assign Project role to the folder
    project_assignment = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=project_role.id, scope_type="Project", scope_id=test_folder.id
    )
    await create_user_role_assignment(async_session, project_assignment)

    # Assign Flow role to the flow
    flow_assignment = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=flow_role.id, scope_type="Flow", scope_id=flow.id
    )
    await create_user_role_assignment(async_session, flow_assignment)

    # Query folder with role assignments
    stmt = select(Folder).where(Folder.id == test_folder.id).options(selectinload(Folder.role_assignments))
    result = await async_session.execute(stmt)
    folder = result.scalar_one()

    # Verify folder only has Project scope assignments, not Flow scope
    assert len(folder.role_assignments) == 1
    assert folder.role_assignments[0].scope_type == "Project"
    assert folder.role_assignments[0].scope_id == test_folder.id
    assert folder.role_assignments[0].role_id == project_role.id


# ============================================================================
# FOLDER IS_STARTER_PROJECT FIELD TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_folder_is_starter_project_defaults_to_false(async_session: AsyncSession, test_user: User):
    """Test that is_starter_project defaults to False when creating a new Folder."""
    folder = Folder(name="Regular Project", user_id=test_user.id)
    async_session.add(folder)
    await async_session.commit()
    await async_session.refresh(folder)

    # Verify is_starter_project defaults to False
    assert hasattr(folder, "is_starter_project")
    assert folder.is_starter_project is False


@pytest.mark.asyncio
async def test_folder_is_starter_project_can_be_set_true(async_session: AsyncSession, test_user: User):
    """Test that is_starter_project can be set to True."""
    folder = Folder(name="Starter Project", user_id=test_user.id, is_starter_project=True)
    async_session.add(folder)
    await async_session.commit()
    await async_session.refresh(folder)

    # Verify is_starter_project is True
    assert folder.is_starter_project is True


@pytest.mark.asyncio
async def test_folder_is_starter_project_can_be_queried(async_session: AsyncSession, test_user: User):
    """Test querying folders by is_starter_project field."""
    # Create a regular project and a starter project
    regular_project = Folder(name="Regular Project", user_id=test_user.id, is_starter_project=False)
    starter_project = Folder(name="Starter Project", user_id=test_user.id, is_starter_project=True)

    async_session.add(regular_project)
    async_session.add(starter_project)
    await async_session.commit()

    # Query only starter projects
    stmt = select(Folder).where(Folder.user_id == test_user.id).where(Folder.is_starter_project == True)
    result = await async_session.execute(stmt)
    starter_folders = result.scalars().all()

    # Verify only the starter project is returned
    assert len(starter_folders) == 1
    assert starter_folders[0].name == "Starter Project"
    assert starter_folders[0].is_starter_project is True


@pytest.mark.asyncio
async def test_folder_is_starter_project_in_base_model(async_session: AsyncSession, test_user: User):
    """Test that is_starter_project is properly inherited from FolderBase."""
    from langbuilder.services.database.models.folder.model import FolderBase

    # Verify is_starter_project is defined in FolderBase
    assert "is_starter_project" in FolderBase.model_fields

    # Create a folder to ensure the field is accessible
    folder = Folder(name="Test Project", user_id=test_user.id)
    assert hasattr(folder, "is_starter_project")


# ============================================================================
# BACKWARD COMPATIBILITY TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_flow_existing_relationships_not_affected(async_session: AsyncSession, test_user: User):
    """Test that existing Flow relationships (user, folder) still work after adding role_assignments."""
    # Create folder and flow
    folder = Folder(name="Test Project", user_id=test_user.id)
    async_session.add(folder)
    await async_session.commit()
    await async_session.refresh(folder)

    flow = Flow(
        name="Test Flow",
        data={"nodes": [], "edges": []},
        user_id=test_user.id,
        folder_id=folder.id,
    )
    async_session.add(flow)
    await async_session.commit()
    await async_session.refresh(flow)

    # Query flow with all relationships
    stmt = (
        select(Flow)
        .where(Flow.id == flow.id)
        .options(selectinload(Flow.user), selectinload(Flow.folder), selectinload(Flow.role_assignments))
    )
    result = await async_session.execute(stmt)
    queried_flow = result.scalar_one()

    # Verify existing relationships still work
    assert queried_flow.user is not None
    assert queried_flow.user.id == test_user.id
    assert queried_flow.folder is not None
    assert queried_flow.folder.id == folder.id

    # Verify new relationship also exists
    assert hasattr(queried_flow, "role_assignments")


@pytest.mark.asyncio
async def test_folder_existing_relationships_not_affected(async_session: AsyncSession, test_user: User):
    """Test that existing Folder relationships (user, flows, children, parent) still work after adding role_assignments."""
    # Create parent and child folders
    parent_folder = Folder(name="Parent Project", user_id=test_user.id)
    async_session.add(parent_folder)
    await async_session.commit()
    await async_session.refresh(parent_folder)

    child_folder = Folder(name="Child Project", user_id=test_user.id, parent_id=parent_folder.id)
    async_session.add(child_folder)
    await async_session.commit()
    await async_session.refresh(child_folder)

    # Create a flow in the folder
    flow = Flow(
        name="Test Flow",
        data={"nodes": [], "edges": []},
        user_id=test_user.id,
        folder_id=child_folder.id,
    )
    async_session.add(flow)
    await async_session.commit()

    # Query folder with all relationships
    stmt = (
        select(Folder)
        .where(Folder.id == child_folder.id)
        .options(
            selectinload(Folder.user),
            selectinload(Folder.flows),
            selectinload(Folder.parent),
            selectinload(Folder.role_assignments),
        )
    )
    result = await async_session.execute(stmt)
    queried_folder = result.scalar_one()

    # Verify existing relationships still work
    assert queried_folder.user is not None
    assert queried_folder.user.id == test_user.id
    assert len(queried_folder.flows) == 1
    assert queried_folder.flows[0].name == "Test Flow"
    assert queried_folder.parent is not None
    assert queried_folder.parent.id == parent_folder.id

    # Verify new relationship also exists
    assert hasattr(queried_folder, "role_assignments")


@pytest.mark.asyncio
async def test_crud_operations_still_work_for_flow(async_session: AsyncSession, test_user: User):
    """Test that basic CRUD operations for Flow still work after adding RBAC relationships."""
    # Create
    flow = Flow(name="CRUD Test Flow", data={"nodes": [], "edges": []}, user_id=test_user.id)
    async_session.add(flow)
    await async_session.commit()
    await async_session.refresh(flow)
    flow_id = flow.id

    # Read
    stmt = select(Flow).where(Flow.id == flow_id)
    result = await async_session.execute(stmt)
    read_flow = result.scalar_one()
    assert read_flow.name == "CRUD Test Flow"

    # Update
    read_flow.name = "Updated Flow Name"
    async_session.add(read_flow)
    await async_session.commit()

    # Verify update
    stmt = select(Flow).where(Flow.id == flow_id)
    result = await async_session.execute(stmt)
    updated_flow = result.scalar_one()
    assert updated_flow.name == "Updated Flow Name"

    # Delete
    await async_session.delete(updated_flow)
    await async_session.commit()

    # Verify deletion
    stmt = select(Flow).where(Flow.id == flow_id)
    result = await async_session.execute(stmt)
    deleted_flow = result.scalar_one_or_none()
    assert deleted_flow is None


@pytest.mark.asyncio
async def test_crud_operations_still_work_for_folder(async_session: AsyncSession, test_user: User):
    """Test that basic CRUD operations for Folder still work after adding RBAC relationships."""
    # Create
    folder = Folder(name="CRUD Test Project", user_id=test_user.id)
    async_session.add(folder)
    await async_session.commit()
    await async_session.refresh(folder)
    folder_id = folder.id

    # Read
    stmt = select(Folder).where(Folder.id == folder_id)
    result = await async_session.execute(stmt)
    read_folder = result.scalar_one()
    assert read_folder.name == "CRUD Test Project"

    # Update
    read_folder.name = "Updated Project Name"
    read_folder.is_starter_project = True
    async_session.add(read_folder)
    await async_session.commit()

    # Verify update
    stmt = select(Folder).where(Folder.id == folder_id)
    result = await async_session.execute(stmt)
    updated_folder = result.scalar_one()
    assert updated_folder.name == "Updated Project Name"
    assert updated_folder.is_starter_project is True

    # Delete
    await async_session.delete(updated_folder)
    await async_session.commit()

    # Verify deletion
    stmt = select(Folder).where(Folder.id == folder_id)
    result = await async_session.execute(stmt)
    deleted_folder = result.scalar_one_or_none()
    assert deleted_folder is None


# ============================================================================
# INTEGRATION TESTS WITH CRUD OPERATIONS
# ============================================================================


@pytest.mark.asyncio
async def test_list_assignments_by_scope_for_flow(async_session: AsyncSession, test_flow: Flow, test_user: User):
    """Test using CRUD function list_assignments_by_scope for Flow."""
    # Create role and assignment
    role = await create_role(async_session, RoleCreate(name="FlowViewer"))
    assignment = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Flow", scope_id=test_flow.id
    )
    await create_user_role_assignment(async_session, assignment)

    # List assignments by scope
    assignments = await list_assignments_by_scope(async_session, "Flow", test_flow.id)

    # Verify assignment is returned
    assert len(assignments) == 1
    assert assignments[0].scope_type == "Flow"
    assert assignments[0].scope_id == test_flow.id
    assert assignments[0].user_id == test_user.id
    assert assignments[0].role_id == role.id


@pytest.mark.asyncio
async def test_list_assignments_by_scope_for_folder(async_session: AsyncSession, test_folder: Folder, test_user: User):
    """Test using CRUD function list_assignments_by_scope for Folder."""
    # Create role and assignment
    role = await create_role(async_session, RoleCreate(name="ProjectOwner"))
    assignment = UserRoleAssignmentCreate(
        user_id=test_user.id, role_id=role.id, scope_type="Project", scope_id=test_folder.id
    )
    await create_user_role_assignment(async_session, assignment)

    # List assignments by scope
    assignments = await list_assignments_by_scope(async_session, "Project", test_folder.id)

    # Verify assignment is returned
    assert len(assignments) == 1
    assert assignments[0].scope_type == "Project"
    assert assignments[0].scope_id == test_folder.id
    assert assignments[0].user_id == test_user.id
    assert assignments[0].role_id == role.id
