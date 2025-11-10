"""Comprehensive unit tests for RBAC enforcement on additional endpoints (Task 2.7).

This test module focuses on RBAC permission checking for:
1. GET /api/v1/flows/{flow_id} - Read Flow by ID
2. POST /api/v1/flows/upload - Upload flows to a Project
3. POST /api/v1/build/{flow_id}/flow - Build/Execute a Flow

As specified in Phase 2, Task 2.7 of the RBAC implementation plan.
"""

import io
import json
from uuid import UUID

import pytest
from httpx import AsyncClient
from langbuilder.services.auth.utils import get_password_hash
from langbuilder.services.database.models.flow.model import Flow
from langbuilder.services.database.models.folder.model import Folder
from langbuilder.services.database.models.permission.crud import create_permission
from langbuilder.services.database.models.permission.model import Permission, PermissionCreate
from langbuilder.services.database.models.role.crud import create_role
from langbuilder.services.database.models.role.model import Role, RoleCreate
from langbuilder.services.database.models.role_permission.model import RolePermission
from langbuilder.services.database.models.user.model import User
from langbuilder.services.database.models.user_role_assignment.crud import create_user_role_assignment
from langbuilder.services.database.models.user_role_assignment.model import UserRoleAssignmentCreate
from langbuilder.services.deps import get_db_service
from sqlmodel import select

# ==================== Fixtures ====================


@pytest.fixture
async def test_user(client):  # noqa: ARG001
    """Create a test user (flow owner)."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        user = User(
            username="test_user",
            password=get_password_hash("password"),
            is_active=True,
            is_superuser=False,
        )
        stmt = select(User).where(User.username == user.username)
        if existing_user := (await session.exec(stmt)).first():
            return existing_user
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def viewer_user(client):  # noqa: ARG001
    """Create a viewer user."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        user = User(
            username="viewer_user",
            password=get_password_hash("password"),
            is_active=True,
            is_superuser=False,
        )
        stmt = select(User).where(User.username == user.username)
        if existing_user := (await session.exec(stmt)).first():
            return existing_user
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def editor_user(client):  # noqa: ARG001
    """Create an editor user."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        user = User(
            username="editor_user",
            password=get_password_hash("password"),
            is_active=True,
            is_superuser=False,
        )
        stmt = select(User).where(User.username == user.username)
        if existing_user := (await session.exec(stmt)).first():
            return existing_user
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def unauthorized_user(client):  # noqa: ARG001
    """Create a user with no permissions."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        user = User(
            username="unauthorized_user",
            password=get_password_hash("password"),
            is_active=True,
            is_superuser=False,
        )
        stmt = select(User).where(User.username == user.username)
        if existing_user := (await session.exec(stmt)).first():
            return existing_user
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def viewer_role(client):  # noqa: ARG001
    """Create a Viewer role."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        stmt = select(Role).where(Role.name == "Viewer")
        if existing_role := (await session.exec(stmt)).first():
            return existing_role
        role_data = RoleCreate(name="Viewer", description="Read-only access")
        return await create_role(session, role_data)


@pytest.fixture
async def editor_role(client):  # noqa: ARG001
    """Create an Editor role."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        stmt = select(Role).where(Role.name == "Editor")
        if existing_role := (await session.exec(stmt)).first():
            return existing_role
        role_data = RoleCreate(name="Editor", description="Can edit resources")
        return await create_role(session, role_data)


@pytest.fixture
async def owner_role(client):  # noqa: ARG001
    """Create an Owner role."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        stmt = select(Role).where(Role.name == "Owner")
        if existing_role := (await session.exec(stmt)).first():
            return existing_role
        role_data = RoleCreate(name="Owner", description="Full access to owned resources")
        return await create_role(session, role_data)


@pytest.fixture
async def flow_read_permission(client):  # noqa: ARG001
    """Create Read permission for Flow scope."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        stmt = select(Permission).where(Permission.name == "Read", Permission.scope == "Flow")
        if existing_perm := (await session.exec(stmt)).first():
            return existing_perm
        perm_data = PermissionCreate(name="Read", scope="Flow", description="View flows")
        return await create_permission(session, perm_data)


@pytest.fixture
async def flow_update_permission(client):  # noqa: ARG001
    """Create Update permission for Flow scope."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        stmt = select(Permission).where(Permission.name == "Update", Permission.scope == "Flow")
        if existing_perm := (await session.exec(stmt)).first():
            return existing_perm
        perm_data = PermissionCreate(name="Update", scope="Flow", description="Update flows")
        return await create_permission(session, perm_data)


@pytest.fixture
async def project_update_permission(client):  # noqa: ARG001
    """Create Update permission for Project scope."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        stmt = select(Permission).where(Permission.name == "Update", Permission.scope == "Project")
        if existing_perm := (await session.exec(stmt)).first():
            return existing_perm
        perm_data = PermissionCreate(name="Update", scope="Project", description="Update project")
        return await create_permission(session, perm_data)


@pytest.fixture
async def setup_viewer_role_permissions(
    client,  # noqa: ARG001
    viewer_role,
    flow_read_permission,
):
    """Set up Viewer role with Read permission only."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        stmt = select(RolePermission).where(
            RolePermission.role_id == viewer_role.id,
            RolePermission.permission_id == flow_read_permission.id,
        )
        if not (await session.exec(stmt)).first():
            role_perm = RolePermission(
                role_id=viewer_role.id,
                permission_id=flow_read_permission.id,
            )
            session.add(role_perm)
            await session.commit()
        return viewer_role


@pytest.fixture
async def setup_editor_role_permissions(
    client,  # noqa: ARG001
    editor_role,
    flow_read_permission,
    flow_update_permission,
    project_update_permission,
):
    """Set up Editor role with Read and Update permissions."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        # Add Read permission for Flow
        stmt_read = select(RolePermission).where(
            RolePermission.role_id == editor_role.id,
            RolePermission.permission_id == flow_read_permission.id,
        )
        if not (await session.exec(stmt_read)).first():
            session.add(RolePermission(role_id=editor_role.id, permission_id=flow_read_permission.id))

        # Add Update permission for Flow
        stmt_update_flow = select(RolePermission).where(
            RolePermission.role_id == editor_role.id,
            RolePermission.permission_id == flow_update_permission.id,
        )
        if not (await session.exec(stmt_update_flow)).first():
            session.add(RolePermission(role_id=editor_role.id, permission_id=flow_update_permission.id))

        # Add Update permission for Project
        stmt_update_project = select(RolePermission).where(
            RolePermission.role_id == editor_role.id,
            RolePermission.permission_id == project_update_permission.id,
        )
        if not (await session.exec(stmt_update_project)).first():
            session.add(RolePermission(role_id=editor_role.id, permission_id=project_update_permission.id))

        await session.commit()
        return editor_role


@pytest.fixture
async def test_folder(client, test_user):  # noqa: ARG001
    """Create a test folder (project)."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        folder = Folder(name="Test Project", user_id=test_user.id)
        session.add(folder)
        await session.commit()
        await session.refresh(folder)
        return folder


@pytest.fixture
async def test_flow(client, test_user, test_folder):  # noqa: ARG001
    """Create a test flow."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        flow = Flow(
            name="Test Flow",
            data={},
            user_id=test_user.id,
            folder_id=test_folder.id,
        )
        session.add(flow)
        await session.commit()
        await session.refresh(flow)
        return flow


# ==================== GET /flows/{flow_id} Tests ====================


@pytest.mark.asyncio
async def test_read_flow_with_permission(
    client: AsyncClient,
    test_flow,
    viewer_user,
    viewer_role,
    setup_viewer_role_permissions,  # noqa: ARG001
    owner_role,  # noqa: ARG001
):
    """Test that users with Read permission can view a flow."""
    # Assign Viewer role to user for the flow
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=viewer_user.id,
            role_id=viewer_role.id,
            scope_type="Flow",
            scope_id=test_flow.id,
            created_by=viewer_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as viewer
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to read the flow
    response = await client.get(f"api/v1/flows/{test_flow.id}", headers=headers)

    assert response.status_code == 200
    flow_data = response.json()
    assert flow_data["id"] == str(test_flow.id)
    assert flow_data["name"] == "Test Flow"


@pytest.mark.asyncio
async def test_read_flow_without_permission(
    client: AsyncClient,
    test_flow,
    unauthorized_user,  # noqa: ARG001
    owner_role,  # noqa: ARG001
):
    """Test that users without Read permission get 403 when trying to view a flow."""
    # Login as unauthorized user
    response = await client.post(
        "api/v1/login",
        data={"username": "unauthorized_user", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to read the flow
    response = await client.get(f"api/v1/flows/{test_flow.id}", headers=headers)

    # Should get 403 (not 404) per security pattern
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_read_flow_permission_inherited_from_project(
    client: AsyncClient,
    test_flow,
    test_folder,
    viewer_user,
    viewer_role,
    setup_viewer_role_permissions,  # noqa: ARG001
    owner_role,  # noqa: ARG001
):
    """Test that Read permission can be inherited from Project scope."""
    # Assign Viewer role to user for the PROJECT (not the flow)
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=viewer_user.id,
            role_id=viewer_role.id,
            scope_type="Project",
            scope_id=test_folder.id,
            created_by=viewer_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as viewer
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to read the flow
    response = await client.get(f"api/v1/flows/{test_flow.id}", headers=headers)

    # Should succeed due to inherited permission
    assert response.status_code == 200
    flow_data = response.json()
    assert flow_data["id"] == str(test_flow.id)


@pytest.mark.asyncio
async def test_read_nonexistent_flow_with_permission(
    client: AsyncClient,
    viewer_user,  # noqa: ARG001
    viewer_role,  # noqa: ARG001
    setup_viewer_role_permissions,  # noqa: ARG001
    owner_role,  # noqa: ARG001
):
    """Test that reading non-existent flow returns 403 (not 404) for users without permission."""
    # Login as viewer (but has no permission on this specific fake flow)
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to read a non-existent flow
    fake_flow_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"api/v1/flows/{fake_flow_id}", headers=headers)

    # Should get 403 before checking existence (security pattern)
    assert response.status_code == 403


# ==================== POST /flows/upload Tests ====================


@pytest.mark.asyncio
async def test_upload_flow_with_project_update_permission(
    client: AsyncClient,
    test_folder,
    editor_user,
    editor_role,
    setup_editor_role_permissions,  # noqa: ARG001
    owner_role,  # noqa: ARG001
):
    """Test that users with Update permission on Project can upload flows."""
    # Assign Editor role to user for the project
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=editor_user.id,
            role_id=editor_role.id,
            scope_type="Project",
            scope_id=test_folder.id,
            created_by=editor_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as editor
    response = await client.post(
        "api/v1/login",
        data={"username": "editor_user", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a flow JSON file to upload
    flow_data = {
        "name": "Uploaded Flow",
        "data": {"nodes": [], "edges": []},
    }
    flow_json = json.dumps(flow_data)
    file_content = io.BytesIO(flow_json.encode())

    # Upload the flow
    files = {"file": ("flow.json", file_content, "application/json")}
    response = await client.post(
        f"api/v1/flows/upload/?folder_id={test_folder.id}",
        files=files,
        headers=headers,
    )

    assert response.status_code == 201
    uploaded_flows = response.json()
    assert isinstance(uploaded_flows, list)
    assert len(uploaded_flows) == 1
    assert uploaded_flows[0]["name"] == "Uploaded Flow"
    assert uploaded_flows[0]["folder_id"] == str(test_folder.id)

    # Verify Owner role was assigned to the uploaded flow
    uploaded_flow_id = UUID(uploaded_flows[0]["id"])
    from langbuilder.services.database.models.user_role_assignment.model import UserRoleAssignment

    async with db_manager.with_session() as session:
        assignment_stmt = select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == editor_user.id,
            UserRoleAssignment.scope_type == "Flow",
            UserRoleAssignment.scope_id == uploaded_flow_id,
        )
        assignment = (await session.exec(assignment_stmt)).first()
        assert assignment is not None, "Owner role should be assigned to uploaded flow"


@pytest.mark.asyncio
async def test_upload_flow_without_project_update_permission(
    client: AsyncClient,
    test_folder,
    viewer_user,
    viewer_role,
    setup_viewer_role_permissions,  # noqa: ARG001
    owner_role,  # noqa: ARG001
):
    """Test that users without Update permission on Project cannot upload flows."""
    # Assign Viewer role (no Update permission) to user for the project
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=viewer_user.id,
            role_id=viewer_role.id,
            scope_type="Project",
            scope_id=test_folder.id,
            created_by=viewer_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as viewer
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a flow JSON file to upload
    flow_data = {
        "name": "Unauthorized Upload",
        "data": {},
    }
    flow_json = json.dumps(flow_data)
    file_content = io.BytesIO(flow_json.encode())

    # Try to upload the flow
    files = {"file": ("flow.json", file_content, "application/json")}
    response = await client.post(
        f"api/v1/flows/upload/?folder_id={test_folder.id}",
        files=files,
        headers=headers,
    )

    # Should get 403
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_flow_to_nonexistent_project(
    client: AsyncClient,
    editor_user,  # noqa: ARG001
    owner_role,  # noqa: ARG001
):
    """Test that uploading to non-existent project returns 404."""
    # Login as editor
    response = await client.post(
        "api/v1/login",
        data={"username": "editor_user", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a flow JSON file
    flow_data = {"name": "Test Flow", "data": {}}
    flow_json = json.dumps(flow_data)
    file_content = io.BytesIO(flow_json.encode())

    # Try to upload to non-existent project
    fake_project_id = "00000000-0000-0000-0000-000000000000"
    files = {"file": ("flow.json", file_content, "application/json")}
    response = await client.post(
        f"api/v1/flows/upload/?folder_id={fake_project_id}",
        files=files,
        headers=headers,
    )

    # Should get 404
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_flow_without_folder_id(
    client: AsyncClient,
    test_user,  # noqa: ARG001
    owner_role,  # noqa: ARG001
):
    """Test that uploading without folder_id succeeds (uses default folder)."""
    # Login as test user
    response = await client.post(
        "api/v1/login",
        data={"username": "test_user", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a flow JSON file
    flow_data = {"name": "Default Folder Flow", "data": {}}
    flow_json = json.dumps(flow_data)
    file_content = io.BytesIO(flow_json.encode())

    # Upload without folder_id (no permission check required)
    files = {"file": ("flow.json", file_content, "application/json")}
    response = await client.post(
        "api/v1/flows/upload/",
        files=files,
        headers=headers,
    )

    # Should succeed
    assert response.status_code == 201
    uploaded_flows = response.json()
    assert len(uploaded_flows) == 1
    assert uploaded_flows[0]["name"] == "Default Folder Flow"


@pytest.mark.asyncio
async def test_upload_multiple_flows(
    client: AsyncClient,
    test_folder,
    editor_user,
    editor_role,
    setup_editor_role_permissions,  # noqa: ARG001
    owner_role,  # noqa: ARG001
):
    """Test uploading multiple flows in a single file."""
    # Assign Editor role to user for the project
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=editor_user.id,
            role_id=editor_role.id,
            scope_type="Project",
            scope_id=test_folder.id,
            created_by=editor_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as editor
    response = await client.post(
        "api/v1/login",
        data={"username": "editor_user", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a multi-flow JSON file
    flows_data = {
        "flows": [
            {"name": "Flow 1", "data": {}},
            {"name": "Flow 2", "data": {}},
            {"name": "Flow 3", "data": {}},
        ]
    }
    flow_json = json.dumps(flows_data)
    file_content = io.BytesIO(flow_json.encode())

    # Upload the flows
    files = {"file": ("flows.json", file_content, "application/json")}
    response = await client.post(
        f"api/v1/flows/upload/?folder_id={test_folder.id}",
        files=files,
        headers=headers,
    )

    assert response.status_code == 201
    uploaded_flows = response.json()
    assert len(uploaded_flows) == 3
    assert {flow["name"] for flow in uploaded_flows} == {"Flow 1", "Flow 2", "Flow 3"}


# ==================== POST /build/{flow_id}/flow Tests ====================


@pytest.mark.asyncio
async def test_build_flow_with_read_permission(
    client: AsyncClient,
    test_flow,
    viewer_user,
    viewer_role,
    setup_viewer_role_permissions,  # noqa: ARG001
    owner_role,  # noqa: ARG001
):
    """Test that users with Read permission can execute a flow."""
    # Assign Viewer role to user for the flow
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=viewer_user.id,
            role_id=viewer_role.id,
            scope_type="Flow",
            scope_id=test_flow.id,
            created_by=viewer_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as viewer
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to build the flow
    response = await client.post(
        f"api/v1/build/{test_flow.id}/flow",
        json={},
        headers=headers,
    )

    # Should succeed (return job_id)
    assert response.status_code == 200
    response_data = response.json()
    assert "job_id" in response_data


@pytest.mark.asyncio
async def test_build_flow_without_read_permission(
    client: AsyncClient,
    test_flow,
    unauthorized_user,  # noqa: ARG001
    owner_role,  # noqa: ARG001
):
    """Test that users without Read permission cannot execute a flow."""
    # Login as unauthorized user
    response = await client.post(
        "api/v1/login",
        data={"username": "unauthorized_user", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to build the flow
    response = await client.post(
        f"api/v1/build/{test_flow.id}/flow",
        json={},
        headers=headers,
    )

    # Should get 403 (not 404) per security pattern
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_build_flow_permission_inherited_from_project(
    client: AsyncClient,
    test_flow,
    test_folder,
    viewer_user,
    viewer_role,
    setup_viewer_role_permissions,  # noqa: ARG001
    owner_role,  # noqa: ARG001
):
    """Test that Read permission for execution can be inherited from Project scope."""
    # Assign Viewer role to user for the PROJECT (not the flow)
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=viewer_user.id,
            role_id=viewer_role.id,
            scope_type="Project",
            scope_id=test_folder.id,
            created_by=viewer_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as viewer
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to build the flow
    response = await client.post(
        f"api/v1/build/{test_flow.id}/flow",
        json={},
        headers=headers,
    )

    # Should succeed due to inherited permission
    assert response.status_code == 200
    assert "job_id" in response.json()


@pytest.mark.asyncio
async def test_build_nonexistent_flow(
    client: AsyncClient,
    viewer_user,  # noqa: ARG001
    owner_role,  # noqa: ARG001
):
    """Test that building non-existent flow returns 403 (not 404) for users without permission."""
    # Login as viewer
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to build a non-existent flow
    fake_flow_id = "00000000-0000-0000-0000-000000000000"
    response = await client.post(
        f"api/v1/build/{fake_flow_id}/flow",
        json={},
        headers=headers,
    )

    # Should get 403 before checking existence (security pattern)
    assert response.status_code == 403


# ==================== Edge Cases and Security Tests ====================


@pytest.mark.asyncio
async def test_read_flow_403_before_404_pattern(
    client: AsyncClient,
    unauthorized_user,  # noqa: ARG001
    owner_role,  # noqa: ARG001
):
    """Test that 403 is returned before 404 to prevent information disclosure."""
    # Login as unauthorized user
    response = await client.post(
        "api/v1/login",
        data={"username": "unauthorized_user", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to read a definitely non-existent flow
    fake_flow_id = "99999999-9999-9999-9999-999999999999"
    response = await client.get(f"api/v1/flows/{fake_flow_id}", headers=headers)

    # Should still get 403 (not 404) to prevent enumeration attacks
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_build_flow_403_before_404_pattern(
    client: AsyncClient,
    unauthorized_user,  # noqa: ARG001
    owner_role,  # noqa: ARG001
):
    """Test that 403 is returned before 404 for build endpoint."""
    # Login as unauthorized user
    response = await client.post(
        "api/v1/login",
        data={"username": "unauthorized_user", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to build a definitely non-existent flow
    fake_flow_id = "99999999-9999-9999-9999-999999999999"
    response = await client.post(
        f"api/v1/build/{fake_flow_id}/flow",
        json={},
        headers=headers,
    )

    # Should still get 403 (not 404)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_upload_flow_404_for_nonexistent_project(
    client: AsyncClient,
    editor_user,  # noqa: ARG001
    owner_role,  # noqa: ARG001
):
    """Test that upload returns 404 for non-existent project (not 403)."""
    # Login as editor
    response = await client.post(
        "api/v1/login",
        data={"username": "editor_user", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create flow JSON
    flow_data = {"name": "Test", "data": {}}
    flow_json = json.dumps(flow_data)
    file_content = io.BytesIO(flow_json.encode())

    # Try to upload to non-existent project
    fake_project_id = "99999999-9999-9999-9999-999999999999"
    files = {"file": ("flow.json", file_content, "application/json")}
    response = await client.post(
        f"api/v1/flows/upload/?folder_id={fake_project_id}",
        files=files,
        headers=headers,
    )

    # For upload, we check project existence first, so we get 404
    assert response.status_code == 404
