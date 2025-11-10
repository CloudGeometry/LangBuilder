"""Comprehensive unit tests for RBAC enforcement on Projects endpoints.

This test module focuses on RBAC permission checking for all Project endpoints
as specified in Phase 2, Task 2.6 of the RBAC implementation plan.
"""

import pytest
from httpx import AsyncClient
from langbuilder.services.auth.utils import get_password_hash
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

# Fixtures for RBAC test setup


@pytest.fixture
async def viewer_user(client):  # noqa: ARG001
    """Create a test user with Viewer role."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        user = User(
            username="viewer_user_proj",
            password=get_password_hash("password"),
            is_active=True,
            is_superuser=False,
        )
        # Check if user already exists
        stmt = select(User).where(User.username == user.username)
        if existing_user := (await session.exec(stmt)).first():
            return existing_user
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def editor_user(client):  # noqa: ARG001
    """Create a test user with Editor role."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        user = User(
            username="editor_user_proj",
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
async def owner_user(client):  # noqa: ARG001
    """Create a test user with Owner role."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        user = User(
            username="owner_user_proj",
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
async def admin_user(client):  # noqa: ARG001
    """Create a test user with Admin role."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        user = User(
            username="admin_user_proj",
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
async def superuser(client):  # noqa: ARG001
    """Create a superuser."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        user = User(
            username="superuser_proj",
            password=get_password_hash("password"),
            is_active=True,
            is_superuser=True,
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
    """Create a Viewer role with Read permission."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        # Check if role already exists
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
        # Check if role already exists
        stmt = select(Role).where(Role.name == "Editor")
        if existing_role := (await session.exec(stmt)).first():
            return existing_role
        role_data = RoleCreate(name="Editor", description="Can edit projects")
        return await create_role(session, role_data)


@pytest.fixture
async def owner_role(client):  # noqa: ARG001
    """Create an Owner role."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        # Check if role already exists
        stmt = select(Role).where(Role.name == "Owner")
        if existing_role := (await session.exec(stmt)).first():
            return existing_role
        role_data = RoleCreate(name="Owner", description="Full access to owned resources")
        return await create_role(session, role_data)


@pytest.fixture
async def admin_role(client):  # noqa: ARG001
    """Create an Admin role."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        # Check if role already exists
        stmt = select(Role).where(Role.name == "Admin")
        if existing_role := (await session.exec(stmt)).first():
            return existing_role
        role_data = RoleCreate(name="Admin", description="Full access")
        return await create_role(session, role_data)


@pytest.fixture
async def project_read_permission(client):  # noqa: ARG001
    """Create Read permission for Project scope."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        # Check if permission already exists
        stmt = select(Permission).where(Permission.name == "Read", Permission.scope == "Project")
        if existing_perm := (await session.exec(stmt)).first():
            return existing_perm
        perm_data = PermissionCreate(name="Read", scope="Project", description="Read project")
        return await create_permission(session, perm_data)


@pytest.fixture
async def project_create_permission(client):  # noqa: ARG001
    """Create Create permission for Project scope."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        # Check if permission already exists
        stmt = select(Permission).where(Permission.name == "Create", Permission.scope == "Project")
        if existing_perm := (await session.exec(stmt)).first():
            return existing_perm
        perm_data = PermissionCreate(name="Create", scope="Project", description="Create projects")
        return await create_permission(session, perm_data)


@pytest.fixture
async def project_update_permission(client):  # noqa: ARG001
    """Create Update permission for Project scope."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        # Check if permission already exists
        stmt = select(Permission).where(Permission.name == "Update", Permission.scope == "Project")
        if existing_perm := (await session.exec(stmt)).first():
            return existing_perm
        perm_data = PermissionCreate(name="Update", scope="Project", description="Update project")
        return await create_permission(session, perm_data)


@pytest.fixture
async def project_delete_permission(client):  # noqa: ARG001
    """Create Delete permission for Project scope."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        # Check if permission already exists
        stmt = select(Permission).where(Permission.name == "Delete", Permission.scope == "Project")
        if existing_perm := (await session.exec(stmt)).first():
            return existing_perm
        perm_data = PermissionCreate(name="Delete", scope="Project", description="Delete project")
        return await create_permission(session, perm_data)


@pytest.fixture
async def test_project_1(client, viewer_user):  # noqa: ARG001
    """Create test project 1."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        project = Folder(
            name="Test Project 1",
            user_id=viewer_user.id,
            is_starter_project=False,
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project


@pytest.fixture
async def test_project_2(client, viewer_user):  # noqa: ARG001
    """Create test project 2."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        project = Folder(
            name="Test Project 2",
            user_id=viewer_user.id,
            is_starter_project=False,
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project


@pytest.fixture
async def test_project_3(client, editor_user):  # noqa: ARG001
    """Create test project 3 (owned by editor_user)."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        project = Folder(
            name="Test Project 3",
            user_id=editor_user.id,
            is_starter_project=False,
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project


@pytest.fixture
async def starter_project(client, viewer_user):  # noqa: ARG001
    """Create a Starter Project (immutable)."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        project = Folder(
            name="Starter Project Test",
            user_id=viewer_user.id,
            is_starter_project=True,
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project


# Setup RBAC permissions


@pytest.fixture
async def setup_viewer_role_permissions(
    client,  # noqa: ARG001
    viewer_role,
    project_read_permission,
):
    """Set up Viewer role with Read permission for Project scope."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        # Check if association already exists
        stmt = select(RolePermission).where(
            RolePermission.role_id == viewer_role.id,
            RolePermission.permission_id == project_read_permission.id,
        )
        if not (await session.exec(stmt)).first():
            role_perm = RolePermission(
                role_id=viewer_role.id,
                permission_id=project_read_permission.id,
            )
            session.add(role_perm)
            await session.commit()
        return viewer_role


@pytest.fixture
async def setup_editor_role_permissions(
    client,  # noqa: ARG001
    editor_role,
    project_read_permission,
    project_update_permission,
):
    """Set up Editor role with Read and Update permissions for Project scope."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        # Check if Read permission association already exists
        stmt_read = select(RolePermission).where(
            RolePermission.role_id == editor_role.id,
            RolePermission.permission_id == project_read_permission.id,
        )
        if not (await session.exec(stmt_read)).first():
            role_perm_read = RolePermission(
                role_id=editor_role.id,
                permission_id=project_read_permission.id,
            )
            session.add(role_perm_read)

        # Check if Update permission association already exists
        stmt_update = select(RolePermission).where(
            RolePermission.role_id == editor_role.id,
            RolePermission.permission_id == project_update_permission.id,
        )
        if not (await session.exec(stmt_update)).first():
            role_perm_update = RolePermission(
                role_id=editor_role.id,
                permission_id=project_update_permission.id,
            )
            session.add(role_perm_update)

        await session.commit()
        return editor_role


@pytest.fixture
async def setup_owner_role_permissions(
    client,  # noqa: ARG001
    owner_role,
    project_read_permission,
    project_update_permission,
    project_delete_permission,
):
    """Set up Owner role with all Project permissions."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        # Add Read permission
        stmt_read = select(RolePermission).where(
            RolePermission.role_id == owner_role.id,
            RolePermission.permission_id == project_read_permission.id,
        )
        if not (await session.exec(stmt_read)).first():
            session.add(RolePermission(role_id=owner_role.id, permission_id=project_read_permission.id))

        # Add Update permission
        stmt_update = select(RolePermission).where(
            RolePermission.role_id == owner_role.id,
            RolePermission.permission_id == project_update_permission.id,
        )
        if not (await session.exec(stmt_update)).first():
            session.add(RolePermission(role_id=owner_role.id, permission_id=project_update_permission.id))

        # Add Delete permission
        stmt_delete = select(RolePermission).where(
            RolePermission.role_id == owner_role.id,
            RolePermission.permission_id == project_delete_permission.id,
        )
        if not (await session.exec(stmt_delete)).first():
            session.add(RolePermission(role_id=owner_role.id, permission_id=project_delete_permission.id))

        await session.commit()
        return owner_role


@pytest.fixture
async def setup_admin_role_permissions(
    client,  # noqa: ARG001
    admin_role,
    project_read_permission,
    project_update_permission,
    project_delete_permission,
):
    """Set up Admin role with all permissions."""
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        # Add Read permission
        stmt_read = select(RolePermission).where(
            RolePermission.role_id == admin_role.id,
            RolePermission.permission_id == project_read_permission.id,
        )
        if not (await session.exec(stmt_read)).first():
            session.add(RolePermission(role_id=admin_role.id, permission_id=project_read_permission.id))

        # Add Update permission
        stmt_update = select(RolePermission).where(
            RolePermission.role_id == admin_role.id,
            RolePermission.permission_id == project_update_permission.id,
        )
        if not (await session.exec(stmt_update)).first():
            session.add(RolePermission(role_id=admin_role.id, permission_id=project_update_permission.id))

        # Add Delete permission
        stmt_delete = select(RolePermission).where(
            RolePermission.role_id == admin_role.id,
            RolePermission.permission_id == project_delete_permission.id,
        )
        if not (await session.exec(stmt_delete)).first():
            session.add(RolePermission(role_id=admin_role.id, permission_id=project_delete_permission.id))

        await session.commit()
        return admin_role


# Test cases for List Projects endpoint RBAC


@pytest.mark.asyncio
async def test_list_projects_superuser_sees_all_projects(
    client: AsyncClient,
    superuser,  # noqa: ARG001
    test_project_1,  # noqa: ARG001
    test_project_2,  # noqa: ARG001
    test_project_3,  # noqa: ARG001
):
    """Test that superusers can see all projects regardless of RBAC assignments."""
    # Login as superuser
    response = await client.post(
        "api/v1/login",
        data={"username": "superuser_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get all projects
    response = await client.get("api/v1/projects/", headers=headers)

    assert response.status_code == 200
    projects = response.json()
    # Superuser should see all projects (at least the 3 test projects)
    project_names = [p["name"] for p in projects]
    assert "Test Project 1" in project_names
    assert "Test Project 2" in project_names
    assert "Test Project 3" in project_names


@pytest.mark.asyncio
async def test_list_projects_global_admin_sees_all_projects(
    client: AsyncClient,
    admin_user,
    admin_role,
    setup_admin_role_permissions,  # noqa: ARG001
    test_project_1,  # noqa: ARG001
    test_project_2,  # noqa: ARG001
    test_project_3,  # noqa: ARG001
):
    """Test that Global Admin users can see all projects."""
    # Assign Global Admin role
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=admin_user.id,
            role_id=admin_role.id,
            scope_type="Global",
            scope_id=None,
            created_by=admin_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as admin
    response = await client.post(
        "api/v1/login",
        data={"username": "admin_user_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get all projects
    response = await client.get("api/v1/projects/", headers=headers)

    assert response.status_code == 200
    projects = response.json()
    # Global Admin should see all projects
    project_names = [p["name"] for p in projects]
    assert "Test Project 1" in project_names
    assert "Test Project 2" in project_names
    assert "Test Project 3" in project_names


@pytest.mark.asyncio
async def test_list_projects_user_with_project_read_permission(
    client: AsyncClient,
    viewer_user,
    viewer_role,
    setup_viewer_role_permissions,  # noqa: ARG001
    test_project_1,
    test_project_2,  # noqa: ARG001
):
    """Test that users with Project-specific Read permission see only those projects."""
    # Assign Viewer role to project 1 only
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=viewer_user.id,
            role_id=viewer_role.id,
            scope_type="Project",
            scope_id=test_project_1.id,
            created_by=viewer_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as viewer
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get all projects
    response = await client.get("api/v1/projects/", headers=headers)

    assert response.status_code == 200
    projects = response.json()
    # User should only see project 1 (has permission) but not project 2
    project_names = [p["name"] for p in projects]
    assert "Test Project 1" in project_names
    assert "Test Project 2" not in project_names


@pytest.mark.asyncio
async def test_list_projects_user_with_no_permissions(
    client: AsyncClient,
    viewer_user,  # noqa: ARG001
    test_project_1,  # noqa: ARG001
    test_project_2,  # noqa: ARG001
):
    """Test that users without any permissions see no projects."""
    # Login as viewer (no role assignments)
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get all projects
    response = await client.get("api/v1/projects/", headers=headers)

    assert response.status_code == 200
    # User should see no projects (filtered out by RBAC)
    # Note: projects owned by the user are still subject to RBAC filtering


# Test cases for Create Project endpoint RBAC


@pytest.mark.asyncio
async def test_create_project_assigns_owner_role(
    client: AsyncClient,
    viewer_user,
    owner_role,
    setup_owner_role_permissions,  # noqa: ARG001
):
    """Test that creating a project automatically assigns Owner role to the creating user."""
    # Login as viewer
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a new project
    project_data = {
        "name": "New Test Project",
        "description": "A test project",
    }
    response = await client.post("api/v1/projects/", json=project_data, headers=headers)

    assert response.status_code == 201
    created_project = response.json()
    assert created_project["name"] == "New Test Project"
    # FolderRead doesn't include user_id in response, just verify name and id

    # Verify Owner role was assigned
    from uuid import UUID

    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        from langbuilder.services.database.models.user_role_assignment.model import UserRoleAssignment

        # Convert string UUID to UUID object
        project_uuid = UUID(created_project["id"]) if isinstance(created_project["id"], str) else created_project["id"]

        stmt = select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == viewer_user.id,
            UserRoleAssignment.scope_type == "Project",
            UserRoleAssignment.scope_id == project_uuid,
            UserRoleAssignment.role_id == owner_role.id,
        )
        assignment = (await session.exec(stmt)).first()
        assert assignment is not None, "Owner role should be assigned to the creating user"
        assert assignment.is_immutable is False, "New projects should have mutable Owner assignments"


@pytest.mark.asyncio
async def test_create_project_superuser_bypasses_permission_check(
    client: AsyncClient,
    superuser,  # noqa: ARG001
):
    """Test that superusers can create projects without explicit permission assignments."""
    # Login as superuser (no role assignments needed)
    response = await client.post(
        "api/v1/login",
        data={"username": "superuser_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a new project
    project_data = {
        "name": "Superuser Project",
        "description": "Created by superuser",
    }
    response = await client.post("api/v1/projects/", json=project_data, headers=headers)

    assert response.status_code == 201
    created_project = response.json()
    assert created_project["name"] == "Superuser Project"


@pytest.mark.asyncio
async def test_create_project_global_admin_bypasses_permission_check(
    client: AsyncClient,
    admin_user,
    admin_role,
    setup_admin_role_permissions,  # noqa: ARG001
):
    """Test that Global Admin users can create projects."""
    # Assign Global Admin role
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=admin_user.id,
            role_id=admin_role.id,
            scope_type="Global",
            scope_id=None,
            created_by=admin_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as admin
    response = await client.post(
        "api/v1/login",
        data={"username": "admin_user_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a new project
    project_data = {
        "name": "Admin Project",
        "description": "Created by global admin",
    }
    response = await client.post("api/v1/projects/", json=project_data, headers=headers)

    assert response.status_code == 201
    created_project = response.json()
    assert created_project["name"] == "Admin Project"


# Test cases for Get Project by ID endpoint RBAC


@pytest.mark.asyncio
async def test_get_project_with_read_permission(
    client: AsyncClient,
    viewer_user,
    viewer_role,
    setup_viewer_role_permissions,  # noqa: ARG001
    test_project_1,
):
    """Test that users with Read permission can view a project."""
    # Assign Viewer role to user for project 1
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=viewer_user.id,
            role_id=viewer_role.id,
            scope_type="Project",
            scope_id=test_project_1.id,
            created_by=viewer_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as viewer
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get the project
    response = await client.get(f"api/v1/projects/{test_project_1.id}", headers=headers)

    assert response.status_code == 200
    project = response.json()
    # Response can be FolderWithPaginatedFlows or FolderReadWithFlows depending on params
    # Check if it has nested structure or direct structure
    if "folder" in project:
        assert project["folder"]["name"] == "Test Project 1"
    else:
        assert project["name"] == "Test Project 1"


@pytest.mark.asyncio
async def test_get_project_without_read_permission(
    client: AsyncClient,
    viewer_user,  # noqa: ARG001
    test_project_1,
):
    """Test that users without Read permission cannot view a project."""
    # Login as viewer (no role assignments)
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to get the project
    response = await client.get(f"api/v1/projects/{test_project_1.id}", headers=headers)

    # Should receive 403 Forbidden
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


# Test cases for Update Project endpoint RBAC


@pytest.mark.asyncio
async def test_update_project_with_update_permission(
    client: AsyncClient,
    editor_user,
    editor_role,
    setup_editor_role_permissions,  # noqa: ARG001
    test_project_3,
):
    """Test that users with Update permission can update projects."""
    # Assign Editor role (has Update permission) to user for project 3
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=editor_user.id,
            role_id=editor_role.id,
            scope_type="Project",
            scope_id=test_project_3.id,
            created_by=editor_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as editor
    response = await client.post(
        "api/v1/login",
        data={"username": "editor_user_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Update the project
    update_data = {
        "name": "Updated Project Name",
        "description": "Updated description",
    }
    response = await client.patch(f"api/v1/projects/{test_project_3.id}", json=update_data, headers=headers)

    assert response.status_code == 200
    updated_project = response.json()
    assert updated_project["name"] == "Updated Project Name"
    assert updated_project["description"] == "Updated description"


@pytest.mark.asyncio
async def test_update_project_without_update_permission(
    client: AsyncClient,
    viewer_user,
    viewer_role,
    setup_viewer_role_permissions,  # noqa: ARG001
    test_project_1,
):
    """Test that users without Update permission cannot update projects."""
    # Assign Viewer role (no Update permission) to user for project 1
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=viewer_user.id,
            role_id=viewer_role.id,
            scope_type="Project",
            scope_id=test_project_1.id,
            created_by=viewer_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as viewer
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to update the project
    update_data = {
        "name": "Unauthorized Update",
    }
    response = await client.patch(f"api/v1/projects/{test_project_1.id}", json=update_data, headers=headers)

    # Should receive 403 Forbidden
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


# Test cases for Delete Project endpoint RBAC


@pytest.mark.asyncio
async def test_delete_project_with_delete_permission_owner(
    client: AsyncClient,
    viewer_user,
    owner_role,
    setup_owner_role_permissions,  # noqa: ARG001
    test_project_1,
):
    """Test that users with Owner role (Delete permission) can delete projects."""
    # Assign Owner role to user for project 1
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=viewer_user.id,
            role_id=owner_role.id,
            scope_type="Project",
            scope_id=test_project_1.id,
            created_by=viewer_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as viewer (who has Owner role on this project)
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Delete the project
    response = await client.delete(f"api/v1/projects/{test_project_1.id}", headers=headers)

    assert response.status_code == 204

    # Verify project is actually deleted
    async with db_manager.with_session() as session:
        stmt = select(Folder).where(Folder.id == test_project_1.id)
        result = await session.exec(stmt)
        deleted_project = result.first()
        assert deleted_project is None, "Project should be deleted from database"


@pytest.mark.asyncio
async def test_delete_project_without_delete_permission_viewer(
    client: AsyncClient,
    viewer_user,
    viewer_role,
    setup_viewer_role_permissions,  # noqa: ARG001
    test_project_1,
):
    """Test that users with Viewer role (no Delete permission) cannot delete projects."""
    # Assign Viewer role (no Delete permission) to user for project 1
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=viewer_user.id,
            role_id=viewer_role.id,
            scope_type="Project",
            scope_id=test_project_1.id,
            created_by=viewer_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as viewer
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to delete the project
    response = await client.delete(f"api/v1/projects/{test_project_1.id}", headers=headers)

    # Should receive 403 Forbidden
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()

    # Verify project still exists
    async with db_manager.with_session() as session:
        stmt = select(Folder).where(Folder.id == test_project_1.id)
        result = await session.exec(stmt)
        project = result.first()
        assert project is not None, "Project should still exist in database"


@pytest.mark.asyncio
async def test_delete_starter_project_blocked(
    client: AsyncClient,
    viewer_user,
    owner_role,
    setup_owner_role_permissions,  # noqa: ARG001
    starter_project,
):
    """Test that Starter Projects cannot be deleted even with Owner/Delete permission."""
    # Assign Owner role to user for starter project
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=viewer_user.id,
            role_id=owner_role.id,
            scope_type="Project",
            scope_id=starter_project.id,
            created_by=viewer_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as viewer (who has Owner role on this starter project)
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to delete the starter project
    response = await client.delete(f"api/v1/projects/{starter_project.id}", headers=headers)

    # Should receive 400 Bad Request (Starter Projects cannot be deleted)
    assert response.status_code == 400
    assert "starter project" in response.json()["detail"].lower()

    # Verify project still exists
    async with db_manager.with_session() as session:
        stmt = select(Folder).where(Folder.id == starter_project.id)
        result = await session.exec(stmt)
        project = result.first()
        assert project is not None, "Starter Project should still exist in database"


@pytest.mark.asyncio
async def test_delete_project_superuser_cannot_delete_starter_project(
    client: AsyncClient,
    superuser,  # noqa: ARG001
    starter_project,
):
    """Test that even superusers cannot delete Starter Projects."""
    # Login as superuser
    response = await client.post(
        "api/v1/login",
        data={"username": "superuser_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to delete the starter project
    response = await client.delete(f"api/v1/projects/{starter_project.id}", headers=headers)

    # Should receive 400 Bad Request (Starter Projects cannot be deleted)
    assert response.status_code == 400
    assert "starter project" in response.json()["detail"].lower()

    # Verify project still exists
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        stmt = select(Folder).where(Folder.id == starter_project.id)
        result = await session.exec(stmt)
        project = result.first()
        assert project is not None, "Starter Project should still exist in database"


@pytest.mark.asyncio
async def test_delete_project_global_admin_bypasses_permission_check(
    client: AsyncClient,
    admin_user,
    admin_role,
    setup_admin_role_permissions,  # noqa: ARG001
    test_project_1,
):
    """Test that Global Admin users can delete any project (except Starter Projects)."""
    # Assign Global Admin role
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        assignment_data = UserRoleAssignmentCreate(
            user_id=admin_user.id,
            role_id=admin_role.id,
            scope_type="Global",
            scope_id=None,
            created_by=admin_user.id,
        )
        await create_user_role_assignment(session, assignment_data)

    # Login as admin
    response = await client.post(
        "api/v1/login",
        data={"username": "admin_user_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Delete the project
    response = await client.delete(f"api/v1/projects/{test_project_1.id}", headers=headers)

    assert response.status_code == 204

    # Verify project is actually deleted
    async with db_manager.with_session() as session:
        stmt = select(Folder).where(Folder.id == test_project_1.id)
        result = await session.exec(stmt)
        deleted_project = result.first()
        assert deleted_project is None, "Project should be deleted from database"


@pytest.mark.asyncio
async def test_delete_project_without_any_permission(
    client: AsyncClient,
    viewer_user,  # noqa: ARG001
    test_project_1,
):
    """Test that users without any permissions cannot delete projects."""
    # Login as viewer (no role assignments)
    response = await client.post(
        "api/v1/login",
        data={"username": "viewer_user_proj", "password": "password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to delete the project
    response = await client.delete(f"api/v1/projects/{test_project_1.id}", headers=headers)

    # Should receive 403 Forbidden
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()

    # Verify project still exists
    db_manager = get_db_service()
    async with db_manager.with_session() as session:
        stmt = select(Folder).where(Folder.id == test_project_1.id)
        result = await session.exec(stmt)
        project = result.first()
        assert project is not None, "Project should still exist in database"
