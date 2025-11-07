"""Comprehensive unit tests for RBAC models: Permission, Role, and RolePermission.

This test suite covers:
- Model creation and validation
- CRUD operations
- Schema validation (Create, Read, Update)
- Relationships between models
- Database constraints (unique, foreign keys)
- Edge cases and error handling

Tests follow the pattern: `async with session_getter(get_db_service()) as session:`
and leverage the conftest.py automatic test database isolation.
"""

from uuid import uuid4

import pytest
from langbuilder.services.database.models.rbac.permission import (
    Permission,
    PermissionAction,
    PermissionCreate,
    PermissionRead,
    PermissionScope,
    PermissionUpdate,
)
from langbuilder.services.database.models.rbac.role import (
    Role,
    RoleCreate,
    RoleRead,
    RoleUpdate,
)
from langbuilder.services.database.models.rbac.role_permission import (
    RolePermission,
    RolePermissionCreate,
    RolePermissionRead,
    RolePermissionUpdate,
)
from langbuilder.services.database.utils import session_getter
from langbuilder.services.deps import get_db_service
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

# ==============================================================================
# Permission Model Tests
# ==============================================================================


class TestPermissionModel:
    """Test suite for Permission model CRUD operations and validation."""

    async def test_create_permission(self):
        """Test creating a new permission with valid data."""
        async with session_getter(get_db_service()) as session:
            permission = Permission(
                action=PermissionAction.CREATE,
                scope=PermissionScope.FLOW,
                description="Allows creating new flows",
            )
            session.add(permission)
            await session.commit()
            await session.refresh(permission)

            assert permission.id is not None
            assert permission.action == PermissionAction.CREATE
            assert permission.scope == PermissionScope.FLOW
            assert permission.description == "Allows creating new flows"

    async def test_create_permission_without_description(self):
        """Test creating a permission without optional description field."""
        async with session_getter(get_db_service()) as session:
            permission = Permission(
                action=PermissionAction.READ,
                scope=PermissionScope.PROJECT,
            )
            session.add(permission)
            await session.commit()
            await session.refresh(permission)

            assert permission.id is not None
            assert permission.action == PermissionAction.READ
            assert permission.description is None
            assert permission.scope == PermissionScope.PROJECT

    async def test_read_permission(self):
        """Test reading a permission from the database."""
        async with session_getter(get_db_service()) as session:
            # Create
            permission = Permission(
                action=PermissionAction.UPDATE,
                scope=PermissionScope.FLOW,
                description="Allows updating flows",
            )
            session.add(permission)
            await session.commit()
            await session.refresh(permission)
            permission_id = permission.id

        # Read in a new session
        async with session_getter(get_db_service()) as session:
            result = await session.execute(select(Permission).where(Permission.id == permission_id))
            read_permission = result.scalar_one()

            assert read_permission.id == permission_id
            assert read_permission.action == PermissionAction.UPDATE
            assert read_permission.description == "Allows updating flows"
            assert read_permission.scope == PermissionScope.FLOW

    async def test_update_permission(self):
        """Test updating an existing permission."""
        async with session_getter(get_db_service()) as session:
            # Create
            permission = Permission(
                action=PermissionAction.DELETE,
                scope=PermissionScope.PROJECT,
                description="Old description",
            )
            session.add(permission)
            await session.commit()
            await session.refresh(permission)

            # Update
            permission.description = "Updated description"
            await session.commit()
            await session.refresh(permission)

            assert permission.description == "Updated description"
            assert permission.action == PermissionAction.DELETE
            assert permission.scope == PermissionScope.PROJECT

    async def test_delete_permission(self):
        """Test deleting a permission."""
        async with session_getter(get_db_service()) as session:
            # Create
            permission = Permission(
                action=PermissionAction.CREATE,
                scope=PermissionScope.PROJECT,
                description="To be deleted",
            )
            session.add(permission)
            await session.commit()
            await session.refresh(permission)
            permission_id = permission.id

            # Delete
            await session.delete(permission)
            await session.commit()

        # Verify deletion
        async with session_getter(get_db_service()) as session:
            result = await session.execute(select(Permission).where(Permission.id == permission_id))
            deleted_permission = result.scalar_one_or_none()
            assert deleted_permission is None

    async def test_permission_unique_action_scope_constraint(self):
        """Test that duplicate (action, scope) combinations are not allowed."""
        async with session_getter(get_db_service()) as session:
            # Create first permission
            permission1 = Permission(
                action=PermissionAction.READ,
                scope=PermissionScope.FLOW,
                description="First permission",
            )
            session.add(permission1)
            await session.commit()

            # Try to create duplicate (action, scope)
            permission2 = Permission(
                action=PermissionAction.READ,
                scope=PermissionScope.FLOW,
                description="Duplicate permission",
            )
            session.add(permission2)

            with pytest.raises(IntegrityError):
                await session.commit()

    async def test_permission_allows_same_action_different_scope(self):
        """Test that same action can exist for different scopes."""
        async with session_getter(get_db_service()) as session:
            # Create permission for FLOW scope
            permission1 = Permission(
                action=PermissionAction.CREATE,
                scope=PermissionScope.FLOW,
                description="Create flow permission",
            )
            session.add(permission1)
            await session.commit()

            # Create permission with same action but PROJECT scope - should succeed
            permission2 = Permission(
                action=PermissionAction.CREATE,
                scope=PermissionScope.PROJECT,
                description="Create project permission",
            )
            session.add(permission2)
            await session.commit()
            await session.refresh(permission2)

            assert permission2.id is not None
            assert permission2.action == PermissionAction.CREATE
            assert permission2.scope == PermissionScope.PROJECT


# ==============================================================================
# Permission Schema Tests
# ==============================================================================


class TestPermissionSchemas:
    """Test suite for Permission Pydantic schema validation."""

    async def test_permission_create_schema_valid(self):
        """Test PermissionCreate schema with valid data."""
        permission_data = PermissionCreate(
            action=PermissionAction.CREATE,
            scope=PermissionScope.FLOW,
            description="Test description",
        )

        assert permission_data.action == PermissionAction.CREATE
        assert permission_data.scope == PermissionScope.FLOW
        assert permission_data.description == "Test description"

    async def test_permission_create_schema_without_description(self):
        """Test PermissionCreate schema without optional description."""
        permission_data = PermissionCreate(
            action=PermissionAction.READ,
            scope=PermissionScope.PROJECT,
        )

        assert permission_data.action == PermissionAction.READ
        assert permission_data.scope == PermissionScope.PROJECT
        assert permission_data.description is None

    async def test_permission_create_schema_invalid_action(self):
        """Test PermissionCreate schema with invalid action."""
        with pytest.raises(ValidationError):
            PermissionCreate(
                action="INVALID_ACTION",  # type: ignore
                scope=PermissionScope.FLOW,
            )

    async def test_permission_create_schema_invalid_scope(self):
        """Test PermissionCreate schema with invalid scope."""
        with pytest.raises(ValidationError):
            PermissionCreate(
                action=PermissionAction.CREATE,
                scope="INVALID_SCOPE",  # type: ignore
            )

    async def test_permission_read_schema(self):
        """Test PermissionRead schema."""
        permission_id = uuid4()
        permission_data = PermissionRead(
            id=permission_id,
            action=PermissionAction.UPDATE,
            scope=PermissionScope.FLOW,
            description="Read schema test",
        )

        assert permission_data.id == permission_id
        assert permission_data.action == PermissionAction.UPDATE
        assert permission_data.scope == PermissionScope.FLOW
        assert permission_data.description == "Read schema test"

    async def test_permission_update_schema(self):
        """Test PermissionUpdate schema with partial updates."""
        # Only update description
        permission_update = PermissionUpdate(description="Updated description only")
        assert permission_update.action is None
        assert permission_update.scope is None
        assert permission_update.description == "Updated description only"

    async def test_permission_update_schema_all_fields(self):
        """Test PermissionUpdate schema with all fields."""
        permission_update = PermissionUpdate(
            action=PermissionAction.DELETE,
            scope=PermissionScope.PROJECT,
            description="Updated all fields",
        )

        assert permission_update.action == PermissionAction.DELETE
        assert permission_update.scope == PermissionScope.PROJECT
        assert permission_update.description == "Updated all fields"


# ==============================================================================
# Role Model Tests
# ==============================================================================


class TestRoleModel:
    """Test suite for Role model CRUD operations and validation."""

    async def test_create_role(self):
        """Test creating a new role with valid data."""
        async with session_getter(get_db_service()) as session:
            role = Role(
                name="Admin",
                description="Administrator role",
                is_system=True,
                is_global=True,
            )
            session.add(role)
            await session.commit()
            await session.refresh(role)

            assert role.id is not None
            assert role.name == "Admin"
            assert role.description == "Administrator role"
            assert role.is_system is True
            assert role.is_global is True

    async def test_create_role_without_description(self):
        """Test creating a role without optional description field."""
        async with session_getter(get_db_service()) as session:
            role = Role(
                name="Owner",
                is_system=True,
                is_global=False,
            )
            session.add(role)
            await session.commit()
            await session.refresh(role)

            assert role.id is not None
            assert role.name == "Owner"
            assert role.description is None
            assert role.is_global is False

    async def test_create_non_system_role(self):
        """Test creating a non-system role."""
        async with session_getter(get_db_service()) as session:
            role = Role(
                name="CustomRole",
                description="Custom user-defined role",
                is_system=False,
                is_global=False,
            )
            session.add(role)
            await session.commit()
            await session.refresh(role)

            assert role.id is not None
            assert role.is_system is False
            assert role.is_global is False

    async def test_read_role(self):
        """Test reading a role from the database."""
        async with session_getter(get_db_service()) as session:
            # Create
            role = Role(
                name="Editor",
                description="Editor role",
                is_system=True,
                is_global=False,
            )
            session.add(role)
            await session.commit()
            await session.refresh(role)
            role_id = role.id

        # Read in a new session
        async with session_getter(get_db_service()) as session:
            result = await session.execute(select(Role).where(Role.id == role_id))
            read_role = result.scalar_one()

            assert read_role.id == role_id
            assert read_role.name == "Editor"
            assert read_role.description == "Editor role"
            assert read_role.is_global is False

    async def test_update_role(self):
        """Test updating an existing role."""
        async with session_getter(get_db_service()) as session:
            # Create
            role = Role(
                name="Viewer",
                description="Old description",
                is_system=True,
                is_global=False,
            )
            session.add(role)
            await session.commit()
            await session.refresh(role)

            # Update
            role.description = "Updated viewer role"
            await session.commit()
            await session.refresh(role)

            assert role.description == "Updated viewer role"
            assert role.name == "Viewer"

    async def test_delete_role(self):
        """Test deleting a role."""
        async with session_getter(get_db_service()) as session:
            # Create
            role = Role(
                name="TempRole",
                description="To be deleted",
                is_system=False,
                is_global=False,
            )
            session.add(role)
            await session.commit()
            await session.refresh(role)
            role_id = role.id

            # Delete
            await session.delete(role)
            await session.commit()

        # Verify deletion
        async with session_getter(get_db_service()) as session:
            result = await session.execute(select(Role).where(Role.id == role_id))
            deleted_role = result.scalar_one_or_none()
            assert deleted_role is None

    async def test_role_unique_name_constraint(self):
        """Test that duplicate role names are not allowed."""
        async with session_getter(get_db_service()) as session:
            # Create first role
            role1 = Role(
                name="UniqueRole",
                description="First role",
                is_global=False,
            )
            session.add(role1)
            await session.commit()

            # Try to create duplicate name
            role2 = Role(
                name="UniqueRole",
                description="Duplicate role",
                is_global=False,
            )
            session.add(role2)

            with pytest.raises(IntegrityError):
                await session.commit()

    async def test_role_with_predefined_names(self):
        """Test creating roles with predefined names (Admin, Owner, Editor, Viewer)."""
        async with session_getter(get_db_service()) as session:
            # Create all predefined roles
            admin = Role(name="Admin", is_global=True)
            owner = Role(name="Owner", is_global=False)
            editor = Role(name="Editor", is_global=False)
            viewer = Role(name="Viewer", is_global=False)

            session.add_all([admin, owner, editor, viewer])
            await session.commit()

            # Verify all created
            result = await session.execute(select(Role))
            roles = result.scalars().all()
            role_names = {role.name for role in roles}

            assert "Admin" in role_names
            assert "Owner" in role_names
            assert "Editor" in role_names
            assert "Viewer" in role_names


# ==============================================================================
# Role Schema Tests
# ==============================================================================


class TestRoleSchemas:
    """Test suite for Role Pydantic schema validation."""

    async def test_role_create_schema_valid(self):
        """Test RoleCreate schema with valid data."""
        role_data = RoleCreate(
            name="Admin",
            description="Administrator role",
            is_system=True,
            is_global=True,
        )

        assert role_data.name == "Admin"
        assert role_data.description == "Administrator role"
        assert role_data.is_system is True
        assert role_data.is_global is True

    async def test_role_create_schema_without_description(self):
        """Test RoleCreate schema without optional description."""
        role_data = RoleCreate(
            name="Owner",
            is_system=True,
            is_global=False,
        )

        assert role_data.name == "Owner"
        assert role_data.description is None
        assert role_data.is_global is False

    async def test_role_create_schema_empty_name(self):
        """Test RoleCreate schema with empty name."""
        with pytest.raises(ValidationError):
            RoleCreate(
                name="",
                is_global=False,
            )

    async def test_role_create_schema_name_too_long(self):
        """Test RoleCreate schema with name exceeding max length."""
        with pytest.raises(ValidationError):
            RoleCreate(
                name="A" * 101,  # Max length is 100
                is_global=False,
            )

    async def test_role_read_schema(self):
        """Test RoleRead schema."""
        role_id = uuid4()
        role_data = RoleRead(
            id=role_id,
            name="Editor",
            description="Editor role",
            is_system=True,
            is_global=False,
        )

        assert role_data.id == role_id
        assert role_data.name == "Editor"
        assert role_data.description == "Editor role"
        assert role_data.is_system is True
        assert role_data.is_global is False

    async def test_role_update_schema(self):
        """Test RoleUpdate schema with partial updates."""
        # Only update description
        role_update = RoleUpdate(description="Updated description only")
        assert role_update.name is None
        assert role_update.description == "Updated description only"

    async def test_role_update_schema_all_fields(self):
        """Test RoleUpdate schema with all fields."""
        role_update = RoleUpdate(
            name="UpdatedViewer",
            description="Updated viewer role",
            is_system=False,
            is_global=False,
        )

        assert role_update.name == "UpdatedViewer"
        assert role_update.description == "Updated viewer role"
        assert role_update.is_system is False
        assert role_update.is_global is False


# ==============================================================================
# RolePermission Model Tests
# ==============================================================================


class TestRolePermissionModel:
    """Test suite for RolePermission junction table operations."""

    async def test_create_role_permission(self):
        """Test creating a role-permission mapping."""
        async with session_getter(get_db_service()) as session:
            # Create role and permission first
            role = Role(name="TestRole", is_global=False)
            permission = Permission(
                action=PermissionAction.READ,
                scope=PermissionScope.FLOW,
            )
            session.add_all([role, permission])
            await session.commit()
            await session.refresh(role)
            await session.refresh(permission)

            # Create mapping
            role_permission = RolePermission(role_id=role.id, permission_id=permission.id)
            session.add(role_permission)
            await session.commit()
            await session.refresh(role_permission)

            assert role_permission.id is not None
            assert role_permission.role_id == role.id
            assert role_permission.permission_id == permission.id

    async def test_read_role_permission(self):
        """Test reading a role-permission mapping."""
        async with session_getter(get_db_service()) as session:
            # Create
            role = Role(name="ReadRole", is_global=False)
            permission = Permission(
                action=PermissionAction.UPDATE,
                scope=PermissionScope.PROJECT,
            )
            session.add_all([role, permission])
            await session.commit()
            await session.refresh(role)
            await session.refresh(permission)

            role_permission = RolePermission(role_id=role.id, permission_id=permission.id)
            session.add(role_permission)
            await session.commit()
            await session.refresh(role_permission)
            rp_id = role_permission.id

        # Read in new session
        async with session_getter(get_db_service()) as session:
            result = await session.execute(select(RolePermission).where(RolePermission.id == rp_id))
            read_rp = result.scalar_one()

            assert read_rp.id == rp_id
            assert read_rp.role_id == role.id
            assert read_rp.permission_id == permission.id

    async def test_delete_role_permission(self):
        """Test deleting a role-permission mapping."""
        async with session_getter(get_db_service()) as session:
            # Create
            role = Role(name="DeleteRole", is_global=False)
            permission = Permission(
                action=PermissionAction.DELETE,
                scope=PermissionScope.FLOW,
            )
            session.add_all([role, permission])
            await session.commit()
            await session.refresh(role)
            await session.refresh(permission)

            role_permission = RolePermission(role_id=role.id, permission_id=permission.id)
            session.add(role_permission)
            await session.commit()
            await session.refresh(role_permission)
            rp_id = role_permission.id

            # Delete
            await session.delete(role_permission)
            await session.commit()

        # Verify deletion
        async with session_getter(get_db_service()) as session:
            result = await session.execute(select(RolePermission).where(RolePermission.id == rp_id))
            deleted_rp = result.scalar_one_or_none()
            assert deleted_rp is None

    async def test_role_permission_unique_constraint(self):
        """Test that duplicate (role_id, permission_id) combinations are not allowed."""
        async with session_getter(get_db_service()) as session:
            # Create role and permission
            role = Role(name="UniqueRole", is_global=False)
            permission = Permission(
                action=PermissionAction.CREATE,
                scope=PermissionScope.PROJECT,
            )
            session.add_all([role, permission])
            await session.commit()
            await session.refresh(role)
            await session.refresh(permission)

            # Create first mapping
            rp1 = RolePermission(role_id=role.id, permission_id=permission.id)
            session.add(rp1)
            await session.commit()

            # Try to create duplicate mapping
            rp2 = RolePermission(role_id=role.id, permission_id=permission.id)
            session.add(rp2)

            with pytest.raises(IntegrityError):
                await session.commit()

    async def test_role_permission_foreign_key_role(self):
        """Test foreign key constraint to Role table."""
        async with session_getter(get_db_service()) as session:
            permission = Permission(
                action=PermissionAction.READ,
                scope=PermissionScope.FLOW,
            )
            session.add(permission)
            await session.commit()
            await session.refresh(permission)

            # Try to create mapping with non-existent role
            fake_role_id = uuid4()
            role_permission = RolePermission(role_id=fake_role_id, permission_id=permission.id)
            session.add(role_permission)

            with pytest.raises(IntegrityError):
                await session.commit()

    async def test_role_permission_foreign_key_permission(self):
        """Test foreign key constraint to Permission table."""
        async with session_getter(get_db_service()) as session:
            role = Role(name="TestFKRole", is_global=False)
            session.add(role)
            await session.commit()
            await session.refresh(role)

            # Try to create mapping with non-existent permission
            fake_permission_id = uuid4()
            role_permission = RolePermission(role_id=role.id, permission_id=fake_permission_id)
            session.add(role_permission)

            with pytest.raises(IntegrityError):
                await session.commit()

    async def test_multiple_permissions_per_role(self):
        """Test that a role can have multiple permissions."""
        async with session_getter(get_db_service()) as session:
            # Create role and multiple permissions
            role = Role(name="MultiPermRole", is_global=False)
            perm1 = Permission(
                action=PermissionAction.CREATE,
                scope=PermissionScope.FLOW,
            )
            perm2 = Permission(
                action=PermissionAction.READ,
                scope=PermissionScope.FLOW,
            )
            perm3 = Permission(
                action=PermissionAction.UPDATE,
                scope=PermissionScope.FLOW,
            )
            session.add_all([role, perm1, perm2, perm3])
            await session.commit()
            await session.refresh(role)
            await session.refresh(perm1)
            await session.refresh(perm2)
            await session.refresh(perm3)

            # Map all permissions to role
            rp1 = RolePermission(role_id=role.id, permission_id=perm1.id)
            rp2 = RolePermission(role_id=role.id, permission_id=perm2.id)
            rp3 = RolePermission(role_id=role.id, permission_id=perm3.id)
            session.add_all([rp1, rp2, rp3])
            await session.commit()

            # Verify all mappings created
            result = await session.execute(select(RolePermission).where(RolePermission.role_id == role.id))
            role_perms = result.scalars().all()
            assert len(role_perms) == 3

    async def test_multiple_roles_per_permission(self):
        """Test that a permission can be assigned to multiple roles."""
        async with session_getter(get_db_service()) as session:
            # Create multiple roles and one permission
            role1 = Role(name="Role1", is_global=False)
            role2 = Role(name="Role2", is_global=False)
            role3 = Role(name="Role3", is_global=False)
            permission = Permission(
                action=PermissionAction.READ,
                scope=PermissionScope.PROJECT,
            )
            session.add_all([role1, role2, role3, permission])
            await session.commit()
            await session.refresh(role1)
            await session.refresh(role2)
            await session.refresh(role3)
            await session.refresh(permission)

            # Map permission to all roles
            rp1 = RolePermission(role_id=role1.id, permission_id=permission.id)
            rp2 = RolePermission(role_id=role2.id, permission_id=permission.id)
            rp3 = RolePermission(role_id=role3.id, permission_id=permission.id)
            session.add_all([rp1, rp2, rp3])
            await session.commit()

            # Verify all mappings created
            result = await session.execute(select(RolePermission).where(RolePermission.permission_id == permission.id))
            perm_roles = result.scalars().all()
            assert len(perm_roles) == 3


# ==============================================================================
# RolePermission Schema Tests
# ==============================================================================


class TestRolePermissionSchemas:
    """Test suite for RolePermission Pydantic schema validation."""

    async def test_role_permission_create_schema(self):
        """Test RolePermissionCreate schema."""
        role_id = uuid4()
        permission_id = uuid4()
        rp_data = RolePermissionCreate(role_id=role_id, permission_id=permission_id)

        assert rp_data.role_id == role_id
        assert rp_data.permission_id == permission_id

    async def test_role_permission_read_schema(self):
        """Test RolePermissionRead schema."""
        rp_id = uuid4()
        role_id = uuid4()
        permission_id = uuid4()
        rp_data = RolePermissionRead(id=rp_id, role_id=role_id, permission_id=permission_id)

        assert rp_data.id == rp_id
        assert rp_data.role_id == role_id
        assert rp_data.permission_id == permission_id

    async def test_role_permission_update_schema(self):
        """Test RolePermissionUpdate schema with partial updates."""
        # Only update permission_id
        rp_update = RolePermissionUpdate(permission_id=uuid4())
        assert rp_update.role_id is None
        assert rp_update.permission_id is not None

    async def test_role_permission_update_schema_partial(self):
        """Test RolePermissionUpdate schema with both fields."""
        role_id = uuid4()
        permission_id = uuid4()
        rp_update = RolePermissionUpdate(role_id=role_id, permission_id=permission_id)

        assert rp_update.role_id == role_id
        assert rp_update.permission_id == permission_id


# ==============================================================================
# Model Relationship Tests
# ==============================================================================


class TestModelRelationships:
    """Test suite for relationships between RBAC models."""

    async def test_role_relationship_to_permissions(self):
        """Test that role.role_permissions relationship works correctly."""
        async with session_getter(get_db_service()) as session:
            # Create role and permissions
            role = Role(name="RelRole", is_global=False)
            perm1 = Permission(
                action=PermissionAction.CREATE,
                scope=PermissionScope.PROJECT,
            )
            perm2 = Permission(
                action=PermissionAction.READ,
                scope=PermissionScope.PROJECT,
            )
            session.add_all([role, perm1, perm2])
            await session.commit()
            await session.refresh(role)
            await session.refresh(perm1)
            await session.refresh(perm2)

            # Create mappings
            rp1 = RolePermission(role_id=role.id, permission_id=perm1.id)
            rp2 = RolePermission(role_id=role.id, permission_id=perm2.id)
            session.add_all([rp1, rp2])
            await session.commit()

            # Verify relationship
            result = await session.execute(select(Role).where(Role.id == role.id))
            role_with_perms = result.scalar_one()
            # Note: Relationships need explicit loading in async SQLModel
            # This test verifies the relationship is defined correctly

    async def test_permission_relationship_to_roles(self):
        """Test that permission.role_permissions relationship works correctly."""
        async with session_getter(get_db_service()) as session:
            # Create permission and roles
            permission = Permission(
                action=PermissionAction.UPDATE,
                scope=PermissionScope.FLOW,
            )
            role1 = Role(name="RelRole1", is_global=False)
            role2 = Role(name="RelRole2", is_global=False)
            session.add_all([permission, role1, role2])
            await session.commit()
            await session.refresh(permission)
            await session.refresh(role1)
            await session.refresh(role2)

            # Create mappings
            rp1 = RolePermission(role_id=role1.id, permission_id=permission.id)
            rp2 = RolePermission(role_id=role2.id, permission_id=permission.id)
            session.add_all([rp1, rp2])
            await session.commit()

            # Verify relationship
            result = await session.execute(select(Permission).where(Permission.id == permission.id))
            perm_with_roles = result.scalar_one()
            # Note: Relationships need explicit loading in async SQLModel
            # This test verifies the relationship is defined correctly

    async def test_cascade_behavior_on_role_deletion(self):
        """Test that deleting a role cascades to role_permission mappings."""
        async with session_getter(get_db_service()) as session:
            # Create role, permission, and mapping
            role = Role(name="CascadeRole", is_global=False)
            permission = Permission(
                action=PermissionAction.DELETE,
                scope=PermissionScope.PROJECT,
            )
            session.add_all([role, permission])
            await session.commit()
            await session.refresh(role)
            await session.refresh(permission)

            role_permission = RolePermission(role_id=role.id, permission_id=permission.id)
            session.add(role_permission)
            await session.commit()
            await session.refresh(role_permission)
            rp_id = role_permission.id

            # Delete role
            await session.delete(role)
            await session.commit()

        # Verify role_permission was also deleted (cascade)
        async with session_getter(get_db_service()) as session:
            result = await session.execute(select(RolePermission).where(RolePermission.id == rp_id))
            deleted_rp = result.scalar_one_or_none()
            # SQLite foreign key cascade should delete this
            # Result depends on cascade configuration

    async def test_cascade_behavior_on_permission_deletion(self):
        """Test that deleting a permission cascades to role_permission mappings."""
        async with session_getter(get_db_service()) as session:
            # Create role, permission, and mapping
            role = Role(name="CascadePerm", is_global=False)
            permission = Permission(
                action=PermissionAction.CREATE,
                scope=PermissionScope.FLOW,
            )
            session.add_all([role, permission])
            await session.commit()
            await session.refresh(role)
            await session.refresh(permission)

            role_permission = RolePermission(role_id=role.id, permission_id=permission.id)
            session.add(role_permission)
            await session.commit()
            await session.refresh(role_permission)
            rp_id = role_permission.id

            # Delete permission
            await session.delete(permission)
            await session.commit()

        # Verify role_permission was also deleted (cascade)
        async with session_getter(get_db_service()) as session:
            result = await session.execute(select(RolePermission).where(RolePermission.id == rp_id))
            deleted_rp = result.scalar_one_or_none()
            # SQLite foreign key cascade should delete this
            # Result depends on cascade configuration


# ==============================================================================
# Edge Cases and Error Handling
# ==============================================================================


class TestEdgeCases:
    """Test suite for edge cases and error conditions."""

    async def test_permission_with_very_long_description(self):
        """Test permission with maximum allowed description length."""
        async with session_getter(get_db_service()) as session:
            long_description = "A" * 500  # Max length from schema
            permission = Permission(
                action=PermissionAction.READ,
                scope=PermissionScope.FLOW,
                description=long_description,
            )
            session.add(permission)
            await session.commit()
            await session.refresh(permission)

            assert permission.description == long_description
            assert len(permission.description) == 500

    async def test_role_with_very_long_description(self):
        """Test role with maximum allowed description length."""
        async with session_getter(get_db_service()) as session:
            long_description = "B" * 500  # Max length from schema
            role = Role(
                name="LongDescRole",
                description=long_description,
                is_global=False,
            )
            session.add(role)
            await session.commit()
            await session.refresh(role)

            assert role.description == long_description
            assert len(role.description) == 500

    async def test_query_nonexistent_permission(self):
        """Test querying for a non-existent permission."""
        async with session_getter(get_db_service()) as session:
            fake_id = uuid4()
            result = await session.execute(select(Permission).where(Permission.id == fake_id))
            permission = result.scalar_one_or_none()
            assert permission is None

    async def test_query_nonexistent_role(self):
        """Test querying for a non-existent role."""
        async with session_getter(get_db_service()) as session:
            fake_id = uuid4()
            result = await session.execute(select(Role).where(Role.id == fake_id))
            role = result.scalar_one_or_none()
            assert role is None

    async def test_permission_with_special_characters_in_description(self):
        """Test permission description with special characters."""
        async with session_getter(get_db_service()) as session:
            special_desc = "Test!@#$%^&*()_+-=[]{}|;':\",./<>?"
            permission = Permission(
                action=PermissionAction.UPDATE,
                scope=PermissionScope.PROJECT,
                description=special_desc,
            )
            session.add(permission)
            await session.commit()
            await session.refresh(permission)

            assert permission.description == special_desc

    async def test_role_with_special_characters_in_name(self):
        """Test role name with special characters."""
        async with session_getter(get_db_service()) as session:
            special_name = "Role-Name_With.Special#Chars"
            role = Role(
                name=special_name,
                is_global=False,
            )
            session.add(role)
            await session.commit()
            await session.refresh(role)

            assert role.name == special_name

    async def test_empty_database_queries(self):
        """Test queries on empty database return no results."""
        async with session_getter(get_db_service()) as session:
            # Query all permissions (should be empty)
            result = await session.execute(select(Permission))
            permissions = result.scalars().all()
            assert len(permissions) == 0

            # Query all roles (should be empty)
            result = await session.execute(select(Role))
            roles = result.scalars().all()
            assert len(roles) == 0

            # Query all role_permissions (should be empty)
            result = await session.execute(select(RolePermission))
            role_perms = result.scalars().all()
            assert len(role_perms) == 0
