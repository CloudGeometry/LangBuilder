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
from langbuilder.services.database.models.user.model import UserRead
from langbuilder.services.database.models.user_role_assignment.crud import get_user_role_assignment_by_id
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
        self,
        client: AsyncClient,
        logged_in_headers_super_user,
        session: AsyncSession,  # noqa: ARG002
        active_user: UserRead,
    ):
        """Test listing all assignments as a superuser."""
        # Create a test assignment via API
        assignment_data = {
            "user_id": str(active_user.id),
            "role_name": "Viewer",
            "scope_type": "Global",
            "scope_id": None,
        }
        await client.post("api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user)

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
        session: AsyncSession,  # noqa: ARG002
        active_user: UserRead,
        super_user: UserRead,  # noqa: ARG002
    ):
        """Test filtering assignments by user_id."""
        # Create assignment via API
        assignment_data = {
            "user_id": str(active_user.id),
            "role_name": "Viewer",
            "scope_type": "Global",
            "scope_id": None,
        }
        await client.post("api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user)

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
        self,
        client: AsyncClient,
        logged_in_headers_super_user,
        session: AsyncSession,  # noqa: ARG002
        active_user: UserRead,
    ):
        """Test filtering assignments by role_name."""
        # Create assignment via API
        assignment_data = {
            "user_id": str(active_user.id),
            "role_name": "Viewer",
            "scope_type": "Global",
            "scope_id": None,
        }
        await client.post("api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user)

        response = await client.get("api/v1/rbac/assignments?role_name=Viewer", headers=logged_in_headers_super_user)
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert isinstance(result, list), "The result must be a list"

        # All assignments should have role name "Viewer"
        for assignment in result:
            assert assignment["role"]["name"] == "Viewer", "All assignments should be for the filtered role"

    async def test_list_assignments_filter_by_scope_type(
        self,
        client: AsyncClient,
        logged_in_headers_super_user,
        session: AsyncSession,  # noqa: ARG002
        active_user: UserRead,
    ):
        """Test filtering assignments by scope_type."""
        # Create assignment via API
        assignment_data = {
            "user_id": str(active_user.id),
            "role_name": "Viewer",
            "scope_type": "Global",
            "scope_id": None,
        }
        await client.post("api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user)

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
        self,
        client: AsyncClient,
        logged_in_headers_super_user,
        session: AsyncSession,  # noqa: ARG002
        active_user: UserRead,
    ):
        """Test creating a global scope assignment."""
        assignment_data = {
            "user_id": str(active_user.id),
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
        session: AsyncSession,  # noqa: ARG002
        active_user: UserRead,
        default_folder: Folder,
    ):
        """Test creating a project scope assignment."""
        assignment_data = {
            "user_id": str(active_user.id),
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
        self,
        client: AsyncClient,
        logged_in_headers_super_user,
        session: AsyncSession,  # noqa: ARG002
        active_user: UserRead,
    ):
        """Test creating a duplicate assignment should fail."""
        assignment_data = {
            "user_id": str(active_user.id),
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
            "role_name": "NonExistentRole",
            "scope_type": "Global",
            "scope_id": None,
        }

        response = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_create_assignment_as_regular_user_fails(
        self,
        client: AsyncClient,
        logged_in_headers,
        session: AsyncSession,  # noqa: ARG002
        active_user: UserRead,
    ):
        """Test creating assignment as regular user should fail."""
        assignment_data = {
            "user_id": str(active_user.id),
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
        self,
        client: AsyncClient,
        logged_in_headers_super_user,
        session: AsyncSession,  # noqa: ARG002
        active_user: UserRead,
    ):
        """Test updating an assignment's role."""
        # Create initial assignment with Viewer role via API
        assignment_data = {
            "user_id": str(active_user.id),
            "role_name": "Viewer",
            "scope_type": "Global",
            "scope_id": None,
        }
        create_response = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assignment = create_response.json()

        # Update to Editor role
        update_data = {"role_name": "Editor"}

        response = await client.patch(
            f"api/v1/rbac/assignments/{assignment['id']}", json=update_data, headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert result["id"] == assignment["id"]
        assert result["role"]["name"] == "Editor"
        assert result["user_id"] == str(active_user.id)

    async def test_update_immutable_assignment_fails(
        self,
        client: AsyncClient,
        logged_in_headers_super_user,
        session: AsyncSession,  # noqa: ARG002
        active_user: UserRead,
        super_user: UserRead,  # noqa: ARG002
    ):
        """Test updating an immutable assignment should fail."""
        # Create assignment via API
        assignment_data = {
            "user_id": str(active_user.id),
            "role_name": "Owner",
            "scope_type": "Global",
            "scope_id": None,
        }
        create_response = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assert create_response.status_code == 201, f"Failed to create assignment: {create_response.json()}"
        assignment = create_response.json()

        # Mark as immutable using direct DB access
        from uuid import UUID

        from langbuilder.services.database.models.user_role_assignment.crud import get_user_role_assignment_by_id
        from langbuilder.services.deps import get_db_service

        # Use a fresh session to see data committed by API
        db_manager = get_db_service()
        async with db_manager.with_session() as fresh_session:
            fetched_assignment = await get_user_role_assignment_by_id(fresh_session, UUID(assignment["id"]))
            assert fetched_assignment is not None, f"Assignment {assignment['id']} not found in database"
            fetched_assignment.is_immutable = True
            fresh_session.add(fetched_assignment)
            await fresh_session.commit()

        # Try to update
        update_data = {"role_name": "Editor"}

        response = await client.patch(
            f"api/v1/rbac/assignments/{assignment['id']}", json=update_data, headers=logged_in_headers_super_user
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
        self,
        client: AsyncClient,
        logged_in_headers_super_user,
        session: AsyncSession,  # noqa: ARG002
        active_user: UserRead,
    ):
        """Test updating to an invalid role should fail."""
        # Create assignment via API
        assignment_data = {
            "user_id": str(active_user.id),
            "role_name": "Viewer",
            "scope_type": "Global",
            "scope_id": None,
        }
        create_response = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assignment = create_response.json()

        update_data = {"role_name": "NonExistentRole"}

        response = await client.patch(
            f"api/v1/rbac/assignments/{assignment['id']}", json=update_data, headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_assignment_as_regular_user_fails(
        self,
        client: AsyncClient,
        logged_in_headers,
        logged_in_headers_super_user,
        session: AsyncSession,  # noqa: ARG002
        active_user: UserRead,
        super_user: UserRead,  # noqa: ARG002
    ):
        """Test updating assignment as regular user should fail."""
        # Create assignment via API (needs super user)
        assignment_data = {
            "user_id": str(active_user.id),
            "role_name": "Viewer",
            "scope_type": "Global",
            "scope_id": None,
        }
        create_response = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assert create_response.status_code == 201, f"Failed to create assignment: {create_response.json()}"
        assignment = create_response.json()

        update_data = {"role_name": "Editor"}

        response = await client.patch(
            f"api/v1/rbac/assignments/{assignment['id']}", json=update_data, headers=logged_in_headers
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestDeleteAssignment:
    """Test DELETE /api/v1/rbac/assignments/{id} endpoint."""

    async def test_delete_assignment(
        self, client: AsyncClient, logged_in_headers_super_user, session: AsyncSession, active_user: UserRead
    ):
        """Test deleting an assignment."""
        # Create assignment via API
        assignment_data = {
            "user_id": str(active_user.id),
            "role_name": "Viewer",
            "scope_type": "Global",
            "scope_id": None,
        }
        create_response = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assignment = create_response.json()

        response = await client.delete(
            f"api/v1/rbac/assignments/{assignment['id']}", headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify assignment was deleted by trying to fetch it
        from uuid import UUID

        deleted_assignment = await get_user_role_assignment_by_id(session, UUID(assignment["id"]))
        assert deleted_assignment is None

    async def test_delete_immutable_assignment_fails(
        self,
        client: AsyncClient,
        logged_in_headers_super_user,
        session: AsyncSession,  # noqa: ARG002
        active_user: UserRead,
    ):
        """Test deleting an immutable assignment should fail."""
        # Create assignment via API
        assignment_data = {
            "user_id": str(active_user.id),
            "role_name": "Owner",
            "scope_type": "Global",
            "scope_id": None,
        }
        create_response = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assignment = create_response.json()

        # Mark as immutable using direct DB access
        from uuid import UUID

        from langbuilder.services.deps import get_db_service

        # Use a fresh session to see data committed by API
        db_manager = get_db_service()
        async with db_manager.with_session() as fresh_session:
            fetched_assignment = await get_user_role_assignment_by_id(fresh_session, UUID(assignment["id"]))
            assert fetched_assignment is not None, f"Assignment {assignment['id']} not found in database"
            fetched_assignment.is_immutable = True
            fresh_session.add(fetched_assignment)
            await fresh_session.commit()

        response = await client.delete(
            f"api/v1/rbac/assignments/{assignment['id']}", headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_delete_nonexistent_assignment_fails(self, client: AsyncClient, logged_in_headers_super_user):
        """Test deleting a non-existent assignment should fail."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await client.delete(f"api/v1/rbac/assignments/{fake_id}", headers=logged_in_headers_super_user)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_assignment_as_regular_user_fails(
        self,
        client: AsyncClient,
        logged_in_headers,
        logged_in_headers_super_user,
        session: AsyncSession,  # noqa: ARG002
        active_user: UserRead,
        super_user: UserRead,  # noqa: ARG002
    ):
        """Test deleting assignment as regular user should fail."""
        # Create assignment via API (needs super user)
        assignment_data = {
            "user_id": str(active_user.id),
            "role_name": "Viewer",
            "scope_type": "Global",
            "scope_id": None,
        }
        create_response = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assert create_response.status_code == 201, f"Failed to create assignment: {create_response.json()}"
        assignment = create_response.json()

        response = await client.delete(f"api/v1/rbac/assignments/{assignment['id']}", headers=logged_in_headers)
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
        self,
        client: AsyncClient,
        logged_in_headers,
        logged_in_headers_super_user,
        session: AsyncSession,
        active_user: UserRead,
        super_user: UserRead,  # noqa: ARG002
    ):
        """Test that users with appropriate role are granted permission."""
        # Assign Global Admin role to user via API
        assignment_data = {
            "user_id": str(active_user.id),
            "role_name": "Admin",
            "scope_type": "Global",
            "scope_id": None,
        }
        create_response = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assert create_response.status_code == 201, f"Failed to create assignment: {create_response.json()}"

        # Expire session to ensure permission check sees the new assignment
        session.expire_all()

        response = await client.get(
            "api/v1/rbac/check-permission?permission=Update&scope_type=Global", headers=logged_in_headers
        )
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert result["has_permission"] is True, f"Expected permission check to return True, got {result}"

    async def test_check_permission_with_scope_id(
        self,
        client: AsyncClient,
        logged_in_headers,
        logged_in_headers_super_user,
        session: AsyncSession,
        active_user: UserRead,
        super_user: UserRead,  # noqa: ARG002
        default_folder: Folder,
    ):
        """Test permission check with specific scope_id."""
        # Assign Editor role for specific project via API
        assignment_data = {
            "user_id": str(active_user.id),
            "role_name": "Editor",
            "scope_type": "Project",
            "scope_id": str(default_folder.id),
        }
        create_response = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assert create_response.status_code == 201, f"Failed to create assignment: {create_response.json()}"

        # Expire session to ensure permission check sees the new assignment
        session.expire_all()

        response = await client.get(
            f"api/v1/rbac/check-permission?permission=Update&scope_type=Project&scope_id={default_folder.id}",
            headers=logged_in_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert result["has_permission"] is True, f"Expected permission check to return True, got {result}"

    async def test_check_permission_unauthenticated_fails(self, client: AsyncClient):
        """Test checking permission without authentication should fail."""
        response = await client.get("api/v1/rbac/check-permission?permission=Update&scope_type=Global")
        # Returns 403 because check-permission requires authentication
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestCheckPermissionsBatch:
    """Test POST /api/v1/rbac/check-permissions endpoint."""

    async def test_check_permissions_batch_success(
        self,
        client: AsyncClient,
        logged_in_headers,
        logged_in_headers_super_user,
        session: AsyncSession,
        active_user: UserRead,
        super_user: UserRead,  # noqa: ARG002
        default_folder: Folder,
    ):
        """Test batch permission check with multiple permissions."""
        # Assign Editor role for specific project
        assignment_data = {
            "user_id": str(active_user.id),
            "role_name": "Editor",
            "scope_type": "Project",
            "scope_id": str(default_folder.id),
        }
        create_response = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assert create_response.status_code == 201, f"Failed to create assignment: {create_response.json()}"

        # Expire session to ensure permission check sees the new assignment
        session.expire_all()

        # Batch check multiple permissions
        check_request = {
            "checks": [
                {"action": "Read", "resource_type": "Project", "resource_id": str(default_folder.id)},
                {"action": "Update", "resource_type": "Project", "resource_id": str(default_folder.id)},
                {"action": "Delete", "resource_type": "Project", "resource_id": str(default_folder.id)},
            ]
        }

        response = await client.post("api/v1/rbac/check-permissions", json=check_request, headers=logged_in_headers)
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert "results" in result, "Response must have 'results' field"
        assert len(result["results"]) == 3, "Should return results for all 3 checks"

        # Check structure of results
        for check_result in result["results"]:
            assert "action" in check_result, "Result must have 'action' field"
            assert "resource_type" in check_result, "Result must have 'resource_type' field"
            assert "resource_id" in check_result, "Result must have 'resource_id' field"
            assert "allowed" in check_result, "Result must have 'allowed' field"
            assert isinstance(check_result["allowed"], bool), "allowed must be boolean"

        # Verify specific permissions
        results_by_action = {r["action"]: r for r in result["results"]}

        # Editor has Read permission on Project
        assert results_by_action["Read"]["allowed"] is True, "Editor should have Read permission"

        # Editor has Update permission on Project
        assert results_by_action["Update"]["allowed"] is True, "Editor should have Update permission"

        # Editor does NOT have Delete permission on Project
        assert results_by_action["Delete"]["allowed"] is False, "Editor should not have Delete permission"

    async def test_check_permissions_batch_superuser_always_allowed(
        self,
        client: AsyncClient,
        logged_in_headers_super_user,
        default_folder: Folder,
    ):
        """Test that superusers have all permissions in batch check."""
        check_request = {
            "checks": [
                {"action": "Update", "resource_type": "Project", "resource_id": str(default_folder.id)},
                {"action": "Delete", "resource_type": "Global", "resource_id": None},
                {"action": "Create", "resource_type": "Flow", "resource_id": str(default_folder.id)},
            ]
        }

        response = await client.post(
            "api/v1/rbac/check-permissions", json=check_request, headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert len(result["results"]) == 3, "Should return results for all 3 checks"

        # All permissions should be allowed for superuser
        for check_result in result["results"]:
            assert check_result["allowed"] is True, (
                f"Superuser should have all permissions, but {check_result['action']} was denied"
            )

    async def test_check_permissions_batch_no_permissions(
        self,
        client: AsyncClient,
        logged_in_headers,
        default_folder: Folder,
    ):
        """Test batch check for user with no role assignments."""
        check_request = {
            "checks": [
                {"action": "Update", "resource_type": "Project", "resource_id": str(default_folder.id)},
                {"action": "Delete", "resource_type": "Global", "resource_id": None},
                {"action": "Read", "resource_type": "Flow", "resource_id": str(default_folder.id)},
            ]
        }

        response = await client.post("api/v1/rbac/check-permissions", json=check_request, headers=logged_in_headers)
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert len(result["results"]) == 3, "Should return results for all 3 checks"

        # All permissions should be denied for user without role
        for check_result in result["results"]:
            assert check_result["allowed"] is False, (
                f"User without role should have no permissions, but {check_result['action']} was allowed"
            )

    async def test_check_permissions_batch_empty_list_fails(self, client: AsyncClient, logged_in_headers):
        """Test batch check with empty checks list should fail validation."""
        check_request = {"checks": []}

        response = await client.post("api/v1/rbac/check-permissions", json=check_request, headers=logged_in_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, "Empty checks list should fail validation"

    async def test_check_permissions_batch_exceeds_max_limit_fails(self, client: AsyncClient, logged_in_headers):
        """Test batch check exceeding 100 checks should fail validation."""
        # Create 101 checks (exceeds MAX_PERMISSION_CHECKS = 100)
        check_request = {
            "checks": [{"action": "Read", "resource_type": "Global", "resource_id": None} for _ in range(101)]
        }

        response = await client.post("api/v1/rbac/check-permissions", json=check_request, headers=logged_in_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, (
            "Exceeding max checks should fail validation"
        )

    async def test_check_permissions_batch_single_check(self, client: AsyncClient, logged_in_headers_super_user):
        """Test batch check with single permission (edge case)."""
        check_request = {"checks": [{"action": "Update", "resource_type": "Global", "resource_id": None}]}

        response = await client.post(
            "api/v1/rbac/check-permissions", json=check_request, headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert len(result["results"]) == 1, "Should return result for single check"
        assert result["results"][0]["allowed"] is True, "Superuser should have permission"

    async def test_check_permissions_batch_max_checks(
        self,
        client: AsyncClient,
        logged_in_headers_super_user,
    ):
        """Test batch check with exactly 100 checks (max allowed)."""
        # Create exactly 100 checks
        check_request = {
            "checks": [{"action": "Read", "resource_type": "Global", "resource_id": None} for _ in range(100)]
        }

        response = await client.post(
            "api/v1/rbac/check-permissions", json=check_request, headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert len(result["results"]) == 100, "Should return results for all 100 checks"

    async def test_check_permissions_batch_mixed_resource_types(
        self,
        client: AsyncClient,
        logged_in_headers,
        logged_in_headers_super_user,
        session: AsyncSession,
        active_user: UserRead,
        super_user: UserRead,  # noqa: ARG002
        default_folder: Folder,
    ):
        """Test batch check with different resource types and scopes."""
        # Assign Global Admin role
        assignment_data = {
            "user_id": str(active_user.id),
            "role_name": "Admin",
            "scope_type": "Global",
            "scope_id": None,
        }
        create_response = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assert create_response.status_code == 201, f"Failed to create assignment: {create_response.json()}"

        # Expire session to ensure permission check sees the new assignment
        session.expire_all()

        check_request = {
            "checks": [
                {"action": "Create", "resource_type": "Global", "resource_id": None},
                {"action": "Update", "resource_type": "Project", "resource_id": str(default_folder.id)},
                {"action": "Delete", "resource_type": "Flow", "resource_id": str(default_folder.id)},
            ]
        }

        response = await client.post("api/v1/rbac/check-permissions", json=check_request, headers=logged_in_headers)
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert len(result["results"]) == 3, "Should return results for all 3 checks"

        # Global Admin should have all permissions
        for check_result in result["results"]:
            assert check_result["allowed"] is True, (
                f"Global Admin should have all permissions, but {check_result['action']} was denied"
            )

    async def test_check_permissions_batch_preserves_request_order(
        self,
        client: AsyncClient,
        logged_in_headers_super_user,
    ):
        """Test that batch check preserves the order of requests in results."""
        check_request = {
            "checks": [
                {"action": "Delete", "resource_type": "Global", "resource_id": None},
                {"action": "Create", "resource_type": "Project", "resource_id": None},
                {"action": "Update", "resource_type": "Flow", "resource_id": None},
                {"action": "Read", "resource_type": "Global", "resource_id": None},
            ]
        }

        response = await client.post(
            "api/v1/rbac/check-permissions", json=check_request, headers=logged_in_headers_super_user
        )
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert len(result["results"]) == 4, "Should return results for all 4 checks"

        # Verify order is preserved
        expected_actions = ["Delete", "Create", "Update", "Read"]
        expected_resource_types = ["Global", "Project", "Flow", "Global"]

        for i, check_result in enumerate(result["results"]):
            assert check_result["action"] == expected_actions[i], f"Result {i} should have action {expected_actions[i]}"
            assert check_result["resource_type"] == expected_resource_types[i], (
                f"Result {i} should have resource_type {expected_resource_types[i]}"
            )

    async def test_check_permissions_batch_unauthenticated_fails(self, client: AsyncClient):
        """Test batch permission check without authentication should fail."""
        check_request = {"checks": [{"action": "Update", "resource_type": "Global", "resource_id": None}]}

        response = await client.post("api/v1/rbac/check-permissions", json=check_request)
        # Returns 403 because check-permissions requires authentication
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_check_permissions_batch_with_viewer_role(
        self,
        client: AsyncClient,
        logged_in_headers,
        logged_in_headers_super_user,
        session: AsyncSession,
        active_user: UserRead,
        super_user: UserRead,  # noqa: ARG002
        default_folder: Folder,
    ):
        """Test batch check for user with Viewer role (read-only)."""
        # Assign Viewer role for specific project
        assignment_data = {
            "user_id": str(active_user.id),
            "role_name": "Viewer",
            "scope_type": "Project",
            "scope_id": str(default_folder.id),
        }
        create_response = await client.post(
            "api/v1/rbac/assignments", json=assignment_data, headers=logged_in_headers_super_user
        )
        assert create_response.status_code == 201, f"Failed to create assignment: {create_response.json()}"

        # Expire session to ensure permission check sees the new assignment
        session.expire_all()

        check_request = {
            "checks": [
                {"action": "Read", "resource_type": "Project", "resource_id": str(default_folder.id)},
                {"action": "Update", "resource_type": "Project", "resource_id": str(default_folder.id)},
                {"action": "Delete", "resource_type": "Project", "resource_id": str(default_folder.id)},
            ]
        }

        response = await client.post("api/v1/rbac/check-permissions", json=check_request, headers=logged_in_headers)
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert len(result["results"]) == 3, "Should return results for all 3 checks"

        results_by_action = {r["action"]: r for r in result["results"]}

        # Viewer has Read permission
        assert results_by_action["Read"]["allowed"] is True, "Viewer should have Read permission"

        # Viewer does not have Update permission
        assert results_by_action["Update"]["allowed"] is False, "Viewer should not have Update permission"

        # Viewer does not have Delete permission
        assert results_by_action["Delete"]["allowed"] is False, "Viewer should not have Delete permission"
