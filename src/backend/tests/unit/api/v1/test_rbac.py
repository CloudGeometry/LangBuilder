"""Unit tests for RBAC API endpoints.

This module tests all RBAC management endpoints including:
- GET /api/v1/rbac/roles - List all roles
- GET /api/v1/rbac/assignments - List role assignments
- POST /api/v1/rbac/assignments - Create role assignment
- PATCH /api/v1/rbac/assignments/{id} - Update role assignment
- DELETE /api/v1/rbac/assignments/{id} - Delete role assignment
- GET /api/v1/rbac/check-permission - Check user permission
"""

import pytest
from fastapi import status
from httpx import AsyncClient
from langbuilder.services.database.models.folder.model import Folder
from langbuilder.services.database.models.role.crud import get_role_by_name
from langbuilder.services.database.models.user.model import UserRead
from langbuilder.services.database.models.user_role_assignment.crud import (
    create_user_role_assignment,
    get_user_role_assignment_by_id,
)
from langbuilder.services.database.models.user_role_assignment.model import UserRoleAssignmentCreate
from sqlmodel.ext.asyncio.session import AsyncSession


@pytest.mark.asyncio
class TestListRoles:
    """Test GET /api/v1/rbac/roles endpoint."""

    async def test_list_roles_as_superuser(self, client: AsyncClient, logged_in_headers_super_user):
        """Test listing all roles as a superuser."""
        response = await client.get("api/v1/rbac/roles", headers=logged_in_headers_super_user)
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert isinstance(result, list), "The result must be a list"
        assert len(result) > 0, "Should return at least one role"

        # Check role structure
        role = result[0]
        assert "id" in role, "Role must have 'id' field"
        assert "name" in role, "Role must have 'name' field"
        assert "description" in role, "Role must have 'description' field"
        assert "is_system_role" in role, "Role must have 'is_system_role' field"
        assert "created_at" in role, "Role must have 'created_at' field"

        # Verify expected roles exist
        role_names = {r["name"] for r in result}
        assert "Admin" in role_names, "Admin role should exist"
        assert "Owner" in role_names, "Owner role should exist"
        assert "Editor" in role_names, "Editor role should exist"
        assert "Viewer" in role_names, "Viewer role should exist"

    async def test_list_roles_as_regular_user_fails(self, client: AsyncClient, logged_in_headers):
        """Test listing roles as a regular user should fail."""
        response = await client.get("api/v1/rbac/roles", headers=logged_in_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Admin access required"

    async def test_list_roles_unauthenticated_fails(self, client: AsyncClient):
        """Test listing roles without authentication should fail."""
        response = await client.get("api/v1/rbac/roles")
        # Returns 403 because the endpoint first checks admin access
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestListAssignments:
    """Test GET /api/v1/rbac/assignments endpoint."""

    async def test_list_assignments_as_superuser(
        self, client: AsyncClient, logged_in_headers_super_user, session: AsyncSession, active_user: UserRead
    ):
        """Test listing all assignments as a superuser."""
        # Create a test assignment
        role = await get_role_by_name(session, "Viewer")
        assignment_data = UserRoleAssignmentCreate(
            user_id=active_user.id,
            role_id=role.id,
            scope_type="Global",
            scope_id=None,
        )
        await create_user_role_assignment(session, assignment_data)

        response = await client.get("api/v1/rbac/assignments", headers=logged_in_headers_super_user)
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert isinstance(result, list), "The result must be a list"

        # Check assignment structure
        if len(result) > 0:
            assignment = result[0]
            assert "id" in assignment, "Assignment must have 'id' field"
            assert "user_id" in assignment, "Assignment must have 'user_id' field"
            assert "role_id" in assignment, "Assignment must have 'role_id' field"
            assert "scope_type" in assignment, "Assignment must have 'scope_type' field"
            assert "scope_id" in assignment, "Assignment must have 'scope_id' field"
            assert "is_immutable" in assignment, "Assignment must have 'is_immutable' field"
            assert "created_at" in assignment, "Assignment must have 'created_at' field"
            assert "created_by" in assignment, "Assignment must have 'created_by' field"
            assert "role" in assignment, "Assignment must have 'role' relationship"

            # Check role details
            role_data = assignment["role"]
            assert "id" in role_data, "Role must have 'id' field"
            assert "name" in role_data, "Role must have 'name' field"

    async def test_list_assignments_filter_by_user(
        self,
        client: AsyncClient,
        logged_in_headers_super_user,
        session: AsyncSession,
        active_user: UserRead,
        super_user: UserRead,  # noqa: ARG002
    ):
        """Test filtering assignments by user_id."""
        # Create assignments for two different users
        viewer_role = await get_role_by_name(session, "Viewer")

        assignment1 = UserRoleAssignmentCreate(
            user_id=active_user.id,
            role_id=viewer_role.id,
            scope_type="Global",
            scope_id=None,
        )
        await create_user_role_assignment(session, assignment1)

        response = await client.get(
            f"api/v1/rbac/assignments?user_id={active_user.id}", headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert isinstance(result, list), "The result must be a list"

        # All assignments should be for active_user
        for assignment in result:
            assert assignment["user_id"] == str(active_user.id), "All assignments should be for the filtered user"

    async def test_list_assignments_filter_by_role_name(
        self, client: AsyncClient, logged_in_headers_super_user, session: AsyncSession, active_user: UserRead
    ):
        """Test filtering assignments by role_name."""
        # Create assignments with different roles
        viewer_role = await get_role_by_name(session, "Viewer")

        assignment1 = UserRoleAssignmentCreate(
            user_id=active_user.id,
            role_id=viewer_role.id,
            scope_type="Global",
            scope_id=None,
        )
        await create_user_role_assignment(session, assignment1)

        response = await client.get("api/v1/rbac/assignments?role_name=Viewer", headers=logged_in_headers_super_user)
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert isinstance(result, list), "The result must be a list"

        # All assignments should have role name "Viewer"
        for assignment in result:
            assert assignment["role"]["name"] == "Viewer", "All assignments should be for the filtered role"

    async def test_list_assignments_filter_by_scope_type(
        self, client: AsyncClient, logged_in_headers_super_user, session: AsyncSession, active_user: UserRead
    ):
        """Test filtering assignments by scope_type."""
        viewer_role = await get_role_by_name(session, "Viewer")

        assignment1 = UserRoleAssignmentCreate(
            user_id=active_user.id,
            role_id=viewer_role.id,
            scope_type="Global",
            scope_id=None,
        )
        await create_user_role_assignment(session, assignment1)

        response = await client.get("api/v1/rbac/assignments?scope_type=Global", headers=logged_in_headers_super_user)
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert isinstance(result, list), "The result must be a list"

        # All assignments should have scope_type "Global"
        for assignment in result:
            assert assignment["scope_type"] == "Global", "All assignments should be for the filtered scope type"

    async def test_list_assignments_as_regular_user_fails(self, client: AsyncClient, logged_in_headers):
        """Test listing assignments as a regular user should fail."""
        response = await client.get("api/v1/rbac/assignments", headers=logged_in_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Admin access required"


@pytest.mark.asyncio
class TestCreateAssignment:
    """Test POST /api/v1/rbac/assignments endpoint."""

    async def test_create_assignment_global_scope(
        self, client: AsyncClient, logged_in_headers_super_user, session: AsyncSession, active_user: UserRead
    ):
        """Test creating a global scope assignment."""
        viewer_role = await get_role_by_name(session, "Viewer")

        assignment_data = {
            "user_id": str(active_user.id),
            "role_id": str(viewer_role.id),
            "role_name": "Viewer",
            "scope_type": "Global",
            "scope_id": None,
        }

        response = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_201_CREATED

        result = response.json()
        assert result["user_id"] == str(active_user.id)
        assert result["role"]["name"] == "Viewer"
        assert result["scope_type"] == "Global"
        assert result["scope_id"] is None
        assert result["is_immutable"] is False

    async def test_create_assignment_project_scope(
        self,
        client: AsyncClient,
        logged_in_headers_super_user,
        session: AsyncSession,
        active_user: UserRead,
        default_folder: Folder,
    ):
        """Test creating a project scope assignment."""
        editor_role = await get_role_by_name(session, "Editor")

        assignment_data = {
            "user_id": str(active_user.id),
            "role_id": str(editor_role.id),
            "role_name": "Editor",
            "scope_type": "Project",
            "scope_id": str(default_folder.id),
        }

        response = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_201_CREATED

        result = response.json()
        assert result["user_id"] == str(active_user.id)
        assert result["role"]["name"] == "Editor"
        assert result["scope_type"] == "Project"
        assert result["scope_id"] == str(default_folder.id)

    async def test_create_duplicate_assignment_fails(
        self, client: AsyncClient, logged_in_headers_super_user, session: AsyncSession, active_user: UserRead
    ):
        """Test creating a duplicate assignment should fail."""
        viewer_role = await get_role_by_name(session, "Viewer")

        assignment_data = {
            "user_id": str(active_user.id),
            "role_id": str(viewer_role.id),
            "role_name": "Viewer",
            "scope_type": "Global",
            "scope_id": None,
        }

        # Create first assignment
        response1 = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Try to create duplicate
        response2 = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assert response2.status_code == status.HTTP_400_BAD_REQUEST

    async def test_create_assignment_invalid_role_fails(
        self, client: AsyncClient, logged_in_headers_super_user, active_user: UserRead
    ):
        """Test creating assignment with invalid role should fail."""
        assignment_data = {
            "user_id": str(active_user.id),
            "role_id": "00000000-0000-0000-0000-000000000000",
            "role_name": "NonExistentRole",
            "scope_type": "Global",
            "scope_id": None,
        }

        response = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_create_assignment_as_regular_user_fails(
        self, client: AsyncClient, logged_in_headers, session: AsyncSession, active_user: UserRead
    ):
        """Test creating assignment as regular user should fail."""
        viewer_role = await get_role_by_name(session, "Viewer")

        assignment_data = {
            "user_id": str(active_user.id),
            "role_id": str(viewer_role.id),
            "role_name": "Viewer",
            "scope_type": "Global",
            "scope_id": None,
        }

        response = await client.post("api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Admin access required"


@pytest.mark.asyncio
class TestUpdateAssignment:
    """Test PATCH /api/v1/rbac/assignments/{id} endpoint."""

    async def test_update_assignment_role(
        self, client: AsyncClient, logged_in_headers_super_user, session: AsyncSession, active_user: UserRead
    ):
        """Test updating an assignment's role."""
        # Create initial assignment with Viewer role
        viewer_role = await get_role_by_name(session, "Viewer")
        assignment_data = UserRoleAssignmentCreate(
            user_id=active_user.id,
            role_id=viewer_role.id,
            scope_type="Global",
            scope_id=None,
        )
        assignment = await create_user_role_assignment(session, assignment_data)

        # Update to Editor role
        update_data = {"role_name": "Editor"}

        response = await client.patch(
            f"api/v1/rbac/assignments/{assignment.id}", json=update_data, headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert result["id"] == str(assignment.id)
        assert result["role"]["name"] == "Editor"
        assert result["user_id"] == str(active_user.id)

    async def test_update_immutable_assignment_fails(
        self,
        client: AsyncClient,
        logged_in_headers_super_user,
        session: AsyncSession,
        active_user: UserRead,
        super_user: UserRead,  # noqa: ARG002
    ):
        """Test updating an immutable assignment should fail."""
        # Create immutable assignment
        owner_role = await get_role_by_name(session, "Owner")
        assignment_data = UserRoleAssignmentCreate(
            user_id=active_user.id,
            role_id=owner_role.id,
            scope_type="Global",
            scope_id=None,
        )
        assignment = await create_user_role_assignment(session, assignment_data)

        # Fetch it again to update it
        from langbuilder.services.database.models.user_role_assignment.crud import get_user_role_assignment_by_id

        fetched_assignment = await get_user_role_assignment_by_id(session, assignment.id)
        fetched_assignment.is_immutable = True
        session.add(fetched_assignment)
        await session.commit()
        await session.refresh(fetched_assignment)

        # Try to update
        update_data = {"role_name": "Editor"}

        response = await client.patch(
            f"api/v1/rbac/assignments/{assignment.id}", json=update_data, headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_update_nonexistent_assignment_fails(self, client: AsyncClient, logged_in_headers_super_user):
        """Test updating a non-existent assignment should fail."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        update_data = {"role_name": "Editor"}

        response = await client.patch(
            f"api/v1/rbac/assignments/{fake_id}", json=update_data, headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_assignment_invalid_role_fails(
        self, client: AsyncClient, logged_in_headers_super_user, session: AsyncSession, active_user: UserRead
    ):
        """Test updating to an invalid role should fail."""
        viewer_role = await get_role_by_name(session, "Viewer")
        assignment_data = UserRoleAssignmentCreate(
            user_id=active_user.id,
            role_id=viewer_role.id,
            scope_type="Global",
            scope_id=None,
        )
        assignment = await create_user_role_assignment(session, assignment_data)

        update_data = {"role_name": "NonExistentRole"}

        response = await client.patch(
            f"api/v1/rbac/assignments/{assignment.id}", json=update_data, headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_assignment_as_regular_user_fails(
        self, client: AsyncClient, logged_in_headers, session: AsyncSession, active_user: UserRead
    ):
        """Test updating assignment as regular user should fail."""
        viewer_role = await get_role_by_name(session, "Viewer")
        assignment_data = UserRoleAssignmentCreate(
            user_id=active_user.id,
            role_id=viewer_role.id,
            scope_type="Global",
            scope_id=None,
        )
        assignment = await create_user_role_assignment(session, assignment_data)

        update_data = {"role_name": "Editor"}

        response = await client.patch(
            f"api/v1/rbac/assignments/{assignment.id}", json=update_data, headers=logged_in_headers
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestDeleteAssignment:
    """Test DELETE /api/v1/rbac/assignments/{id} endpoint."""

    async def test_delete_assignment(
        self, client: AsyncClient, logged_in_headers_super_user, session: AsyncSession, active_user: UserRead
    ):
        """Test deleting an assignment."""
        viewer_role = await get_role_by_name(session, "Viewer")
        assignment_data = UserRoleAssignmentCreate(
            user_id=active_user.id,
            role_id=viewer_role.id,
            scope_type="Global",
            scope_id=None,
        )
        assignment = await create_user_role_assignment(session, assignment_data)

        response = await client.delete(f"api/v1/rbac/assignments/{assignment.id}", headers=logged_in_headers_super_user)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify assignment was deleted
        deleted_assignment = await get_user_role_assignment_by_id(session, assignment.id)
        assert deleted_assignment is None

    async def test_delete_immutable_assignment_fails(
        self, client: AsyncClient, logged_in_headers_super_user, session: AsyncSession, active_user: UserRead
    ):
        """Test deleting an immutable assignment should fail."""
        owner_role = await get_role_by_name(session, "Owner")
        assignment_data = UserRoleAssignmentCreate(
            user_id=active_user.id,
            role_id=owner_role.id,
            scope_type="Global",
            scope_id=None,
        )
        assignment = await create_user_role_assignment(session, assignment_data)

        # Fetch it again to update it
        fetched_assignment = await get_user_role_assignment_by_id(session, assignment.id)
        fetched_assignment.is_immutable = True
        session.add(fetched_assignment)
        await session.commit()
        await session.refresh(fetched_assignment)

        response = await client.delete(f"api/v1/rbac/assignments/{assignment.id}", headers=logged_in_headers_super_user)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_delete_nonexistent_assignment_fails(self, client: AsyncClient, logged_in_headers_super_user):
        """Test deleting a non-existent assignment should fail."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await client.delete(f"api/v1/rbac/assignments/{fake_id}", headers=logged_in_headers_super_user)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_assignment_as_regular_user_fails(
        self, client: AsyncClient, logged_in_headers, session: AsyncSession, active_user: UserRead
    ):
        """Test deleting assignment as regular user should fail."""
        viewer_role = await get_role_by_name(session, "Viewer")
        assignment_data = UserRoleAssignmentCreate(
            user_id=active_user.id,
            role_id=viewer_role.id,
            scope_type="Global",
            scope_id=None,
        )
        assignment = await create_user_role_assignment(session, assignment_data)

        response = await client.delete(f"api/v1/rbac/assignments/{assignment.id}", headers=logged_in_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestCheckPermission:
    """Test GET /api/v1/rbac/check-permission endpoint."""

    async def test_check_permission_superuser_always_has_permission(
        self, client: AsyncClient, logged_in_headers_super_user
    ):
        """Test that superusers always have permission."""
        response = await client.get(
            "api/v1/rbac/check-permission?permission=Update&scope_type=Global", headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert result["has_permission"] is True

    async def test_check_permission_user_without_role_denied(self, client: AsyncClient, logged_in_headers):
        """Test that users without a role are denied permission."""
        response = await client.get(
            "api/v1/rbac/check-permission?permission=Update&scope_type=Global", headers=logged_in_headers
        )
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert result["has_permission"] is False

    async def test_check_permission_user_with_role_granted(
        self, client: AsyncClient, logged_in_headers, session: AsyncSession, active_user: UserRead
    ):
        """Test that users with appropriate role are granted permission."""
        # Assign Global Admin role to user
        admin_role = await get_role_by_name(session, "Admin")
        assignment_data = UserRoleAssignmentCreate(
            user_id=active_user.id,
            role_id=admin_role.id,
            scope_type="Global",
            scope_id=None,
        )
        await create_user_role_assignment(session, assignment_data)

        response = await client.get(
            "api/v1/rbac/check-permission?permission=Update&scope_type=Global", headers=logged_in_headers
        )
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert result["has_permission"] is True

    async def test_check_permission_with_scope_id(
        self,
        client: AsyncClient,
        logged_in_headers,
        session: AsyncSession,
        active_user: UserRead,
        default_folder: Folder,
    ):
        """Test permission check with specific scope_id."""
        # Assign Editor role for specific project
        editor_role = await get_role_by_name(session, "Editor")
        assignment_data = UserRoleAssignmentCreate(
            user_id=active_user.id,
            role_id=editor_role.id,
            scope_type="Project",
            scope_id=default_folder.id,
        )
        await create_user_role_assignment(session, assignment_data)

        response = await client.get(
            f"api/v1/rbac/check-permission?permission=Update&scope_type=Project&scope_id={default_folder.id}",
            headers=logged_in_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert result["has_permission"] is True

    async def test_check_permission_unauthenticated_fails(self, client: AsyncClient):
        """Test checking permission without authentication should fail."""
        response = await client.get("api/v1/rbac/check-permission?permission=Update&scope_type=Global")
        # Returns 403 because check-permission requires authentication
        assert response.status_code == status.HTTP_403_FORBIDDEN
