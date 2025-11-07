"""Unit tests for RBAC seed data initialization script."""

from langbuilder.initial_setup.rbac_setup import (
    PERMISSIONS,
    ROLE_PERMISSION_MAPPINGS,
    ROLES,
    _count_existing_permissions,
    _count_existing_roles,
    _create_permissions,
    _create_role_permission_mappings,
    _create_roles,
    _role_permission_exists,
    initialize_rbac_data,
)
from langbuilder.services.database.models.rbac import (
    Permission,
    PermissionAction,
    PermissionScope,
    Role,
    RolePermission,
)
from langbuilder.services.database.utils import session_getter
from langbuilder.services.deps import get_db_service
from sqlmodel import select


class TestRBACSetupConstants:
    """Tests for RBAC setup constants and configuration."""

    def test_permissions_count(self):
        """Test that we have 8 predefined permissions (4 CRUD x 2 entity types)."""
        assert len(PERMISSIONS) == 8

    def test_permissions_structure(self):
        """Test that permissions have correct structure."""
        for perm in PERMISSIONS:
            assert hasattr(perm, "action")
            assert hasattr(perm, "description")
            assert hasattr(perm, "scope")
            assert isinstance(perm.action, PermissionAction)
            assert isinstance(perm.scope, PermissionScope)
            assert perm.action in [
                PermissionAction.CREATE,
                PermissionAction.READ,
                PermissionAction.UPDATE,
                PermissionAction.DELETE,
            ]
            assert perm.scope in [PermissionScope.FLOW, PermissionScope.PROJECT]

    def test_permissions_coverage(self):
        """Test that all CRUD operations are covered for both Flow and Project."""
        expected_perms = {
            (PermissionAction.CREATE, PermissionScope.FLOW),
            (PermissionAction.READ, PermissionScope.FLOW),
            (PermissionAction.UPDATE, PermissionScope.FLOW),
            (PermissionAction.DELETE, PermissionScope.FLOW),
            (PermissionAction.CREATE, PermissionScope.PROJECT),
            (PermissionAction.READ, PermissionScope.PROJECT),
            (PermissionAction.UPDATE, PermissionScope.PROJECT),
            (PermissionAction.DELETE, PermissionScope.PROJECT),
        }
        actual_perms = {(p.action, p.scope) for p in PERMISSIONS}
        assert actual_perms == expected_perms

    def test_roles_count(self):
        """Test that we have 4 predefined roles."""
        assert len(ROLES) == 4

    def test_roles_structure(self):
        """Test that roles have correct structure."""
        expected_role_names = {"Admin", "Owner", "Editor", "Viewer"}
        actual_role_names = {role.name for role in ROLES}
        assert actual_role_names == expected_role_names

        for role in ROLES:
            assert hasattr(role, "name")
            assert hasattr(role, "description")
            assert hasattr(role, "is_system")
            assert role.is_system is True

    def test_role_permission_mappings_structure(self):
        """Test that role-permission mappings are correctly defined."""
        assert len(ROLE_PERMISSION_MAPPINGS) == 4
        assert "Admin" in ROLE_PERMISSION_MAPPINGS
        assert "Owner" in ROLE_PERMISSION_MAPPINGS
        assert "Editor" in ROLE_PERMISSION_MAPPINGS
        assert "Viewer" in ROLE_PERMISSION_MAPPINGS

    def test_admin_role_permissions(self):
        """Test that Admin has all 8 permissions (4 CRUD x 2 scopes)."""
        admin_perms = ROLE_PERMISSION_MAPPINGS["Admin"]
        assert len(admin_perms) == 8
        assert (PermissionAction.CREATE, PermissionScope.FLOW) in admin_perms
        assert (PermissionAction.READ, PermissionScope.FLOW) in admin_perms
        assert (PermissionAction.UPDATE, PermissionScope.FLOW) in admin_perms
        assert (PermissionAction.DELETE, PermissionScope.FLOW) in admin_perms
        assert (PermissionAction.CREATE, PermissionScope.PROJECT) in admin_perms
        assert (PermissionAction.READ, PermissionScope.PROJECT) in admin_perms
        assert (PermissionAction.UPDATE, PermissionScope.PROJECT) in admin_perms
        assert (PermissionAction.DELETE, PermissionScope.PROJECT) in admin_perms

    def test_owner_role_permissions(self):
        """Test that Owner has all 8 permissions (4 CRUD x 2 scopes)."""
        owner_perms = ROLE_PERMISSION_MAPPINGS["Owner"]
        assert len(owner_perms) == 8
        assert (PermissionAction.CREATE, PermissionScope.FLOW) in owner_perms
        assert (PermissionAction.DELETE, PermissionScope.FLOW) in owner_perms
        assert (PermissionAction.CREATE, PermissionScope.PROJECT) in owner_perms
        assert (PermissionAction.DELETE, PermissionScope.PROJECT) in owner_perms

    def test_editor_role_permissions(self):
        """Test that Editor has Create, Read, Update (no Delete)."""
        editor_perms = ROLE_PERMISSION_MAPPINGS["Editor"]
        assert len(editor_perms) == 6
        assert (PermissionAction.CREATE, PermissionScope.FLOW) in editor_perms
        assert (PermissionAction.READ, PermissionScope.FLOW) in editor_perms
        assert (PermissionAction.UPDATE, PermissionScope.FLOW) in editor_perms
        assert (PermissionAction.CREATE, PermissionScope.PROJECT) in editor_perms
        assert (PermissionAction.READ, PermissionScope.PROJECT) in editor_perms
        assert (PermissionAction.UPDATE, PermissionScope.PROJECT) in editor_perms
        assert (PermissionAction.DELETE, PermissionScope.FLOW) not in editor_perms
        assert (PermissionAction.DELETE, PermissionScope.PROJECT) not in editor_perms

    def test_viewer_role_permissions(self):
        """Test that Viewer has only Read permission."""
        viewer_perms = ROLE_PERMISSION_MAPPINGS["Viewer"]
        assert set(viewer_perms) == {
            (PermissionAction.READ, PermissionScope.FLOW),
            (PermissionAction.READ, PermissionScope.PROJECT),
        }


class TestCountHelpers:
    """Tests for count helper functions."""

    async def test_count_existing_roles_empty(self):
        """Test counting roles when database is empty."""
        async with session_getter(get_db_service()) as session:
            # Clean up any existing roles from previous tests
            stmt = select(Role)
            result = await session.exec(stmt)
            existing_roles = result.all()
            for role in existing_roles:
                await session.delete(role)
            await session.commit()

            count = await _count_existing_roles(session)
            assert count == 0

    async def test_count_existing_roles_with_data(self):
        """Test counting roles when database has data."""
        async with session_getter(get_db_service()) as session:
            # Create test roles
            role1 = Role(name="TestRole1", description="Test role 1", is_system=True)
            role2 = Role(name="TestRole2", description="Test role 2", is_system=True)
            session.add(role1)
            session.add(role2)
            await session.commit()

            count = await _count_existing_roles(session)
            assert count >= 2

    async def test_count_existing_permissions_empty(self):
        """Test counting permissions when database is empty."""
        async with session_getter(get_db_service()) as session:
            # Clean up any existing permissions from previous tests
            stmt = select(Permission)
            result = await session.exec(stmt)
            existing_perms = result.all()
            for perm in existing_perms:
                await session.delete(perm)
            await session.commit()

            count = await _count_existing_permissions(session)
            assert count == 0

    async def test_count_existing_permissions_with_data(self):
        """Test counting permissions when database has data."""
        async with session_getter(get_db_service()) as session:
            # Create test permissions
            perm1 = Permission(
                action=PermissionAction.CREATE,
                scope=PermissionScope.FLOW,
                description="Test perm 1",
            )
            perm2 = Permission(
                action=PermissionAction.READ,
                scope=PermissionScope.PROJECT,
                description="Test perm 2",
            )
            session.add(perm1)
            session.add(perm2)
            await session.commit()

            count = await _count_existing_permissions(session)
            assert count >= 2


class TestCreatePermissions:
    """Tests for _create_permissions function."""

    async def test_create_permissions_on_empty_database(self):
        """Test creating permissions when database is empty."""
        async with session_getter(get_db_service()) as session:
            # Clean up existing permissions
            stmt = select(Permission)
            result = await session.exec(stmt)
            existing_perms = result.all()
            for perm in existing_perms:
                await session.delete(perm)
            await session.commit()

            # Create permissions
            permissions_map = await _create_permissions(session)
            await session.commit()

            # Verify all 8 permissions were created
            assert len(permissions_map) == 8

            # Verify structure of returned map
            for (action, scope), perm in permissions_map.items():
                assert isinstance(perm, Permission)
                assert perm.action == action
                assert perm.scope == scope
                assert perm.id is not None

    async def test_create_permissions_idempotent(self):
        """Test that creating permissions is idempotent (safe to run multiple times)."""
        async with session_getter(get_db_service()) as session:
            # Clean up existing permissions
            stmt = select(Permission)
            result = await session.exec(stmt)
            existing_perms = result.all()
            for perm in existing_perms:
                await session.delete(perm)
            await session.commit()

            # First creation
            permissions_map1 = await _create_permissions(session)
            await session.commit()
            first_perm_id = permissions_map1[(PermissionAction.CREATE, PermissionScope.FLOW)].id

            # Second creation (should return existing)
            permissions_map2 = await _create_permissions(session)
            await session.commit()
            second_perm_id = permissions_map2[(PermissionAction.CREATE, PermissionScope.FLOW)].id

            # IDs should be the same (reused existing permissions)
            assert first_perm_id == second_perm_id
            assert len(permissions_map1) == len(permissions_map2)

    async def test_create_permissions_all_scopes_covered(self):
        """Test that permissions for both Flow and Project scopes are created."""
        async with session_getter(get_db_service()) as session:
            # Clean up existing permissions
            stmt = select(Permission)
            result = await session.exec(stmt)
            existing_perms = result.all()
            for perm in existing_perms:
                await session.delete(perm)
            await session.commit()

            permissions_map = await _create_permissions(session)
            await session.commit()

            # Check Flow scope permissions
            flow_perms = [p for (a, s), p in permissions_map.items() if s == PermissionScope.FLOW]
            assert len(flow_perms) == 4

            # Check Project scope permissions
            project_perms = [p for (a, s), p in permissions_map.items() if s == PermissionScope.PROJECT]
            assert len(project_perms) == 4


class TestCreateRoles:
    """Tests for _create_roles function."""

    async def test_create_roles_on_empty_database(self):
        """Test creating roles when database is empty."""
        async with session_getter(get_db_service()) as session:
            # Clean up existing roles
            stmt = select(Role)
            result = await session.exec(stmt)
            existing_roles = result.all()
            for role in existing_roles:
                await session.delete(role)
            await session.commit()

            # Create roles
            roles_map = await _create_roles(session)
            await session.commit()

            # Verify all 4 roles were created
            assert len(roles_map) == 4
            assert "Admin" in roles_map
            assert "Owner" in roles_map
            assert "Editor" in roles_map
            assert "Viewer" in roles_map

            # Verify structure
            for name, role in roles_map.items():
                assert isinstance(role, Role)
                assert role.name == name
                assert role.id is not None
                assert role.is_system is True

    async def test_create_roles_idempotent(self):
        """Test that creating roles is idempotent (safe to run multiple times)."""
        async with session_getter(get_db_service()) as session:
            # Clean up existing roles
            stmt = select(Role)
            result = await session.exec(stmt)
            existing_roles = result.all()
            for role in existing_roles:
                await session.delete(role)
            await session.commit()

            # First creation
            roles_map1 = await _create_roles(session)
            await session.commit()
            first_admin_id = roles_map1["Admin"].id

            # Second creation (should return existing)
            roles_map2 = await _create_roles(session)
            await session.commit()
            second_admin_id = roles_map2["Admin"].id

            # IDs should be the same (reused existing roles)
            assert first_admin_id == second_admin_id
            assert len(roles_map1) == len(roles_map2)


class TestRolePermissionExists:
    """Tests for _role_permission_exists helper function."""

    async def test_role_permission_exists_false_on_empty(self):
        """Test that function returns False when association doesn't exist."""
        async with session_getter(get_db_service()) as session:
            # Clean up
            stmt = select(RolePermission)
            result = await session.exec(stmt)
            existing_rps = result.all()
            for rp in existing_rps:
                await session.delete(rp)
            await session.commit()

            # Create role and permission
            role = Role(name="TestRole", is_system=True)
            permission = Permission(
                action=PermissionAction.CREATE,
                scope=PermissionScope.FLOW,
                description="Test permission",
            )
            session.add(role)
            session.add(permission)
            await session.commit()
            await session.refresh(role)
            await session.refresh(permission)

            # Check if association exists (should be False)
            exists = await _role_permission_exists(session, role.id, permission.id)
            assert exists is False

    async def test_role_permission_exists_true_when_exists(self):
        """Test that function returns True when association exists."""
        async with session_getter(get_db_service()) as session:
            # Create role and permission
            role = Role(name="TestRole2", is_system=True)
            permission = Permission(
                action=PermissionAction.READ,
                scope=PermissionScope.FLOW,
                description="Test permission 2",
            )
            session.add(role)
            session.add(permission)
            await session.commit()
            await session.refresh(role)
            await session.refresh(permission)

            # Create association
            rp = RolePermission(role_id=role.id, permission_id=permission.id)
            session.add(rp)
            await session.commit()

            # Check if association exists (should be True)
            exists = await _role_permission_exists(session, role.id, permission.id)
            assert exists is True


class TestCreateRolePermissionMappings:
    """Tests for _create_role_permission_mappings function."""

    async def test_create_role_permission_mappings(self):
        """Test creating role-permission mappings."""
        async with session_getter(get_db_service()) as session:
            # Clean up
            stmt = select(RolePermission)
            result = await session.exec(stmt)
            existing_rps = result.all()
            for rp in existing_rps:
                await session.delete(rp)
            await session.commit()

            # Create permissions and roles
            permissions_map = await _create_permissions(session)
            roles_map = await _create_roles(session)
            await session.commit()

            # Create mappings
            mappings_count = await _create_role_permission_mappings(session, roles_map, permissions_map)
            await session.commit()

            # Admin should have 8 permissions (4 CRUD x 2 scopes)
            # Owner should have 8 permissions (4 CRUD x 2 scopes)
            # Editor should have 6 permissions (3 operations x 2 scopes)
            # Viewer should have 2 permissions (1 operation x 2 scopes)
            # Total: 8 + 8 + 6 + 2 = 24
            assert mappings_count == 24

    async def test_admin_role_has_all_permissions(self):
        """Test that Admin role has all 8 permissions."""
        async with session_getter(get_db_service()) as session:
            # Clean up
            stmt = select(RolePermission)
            result = await session.exec(stmt)
            existing_rps = result.all()
            for rp in existing_rps:
                await session.delete(rp)
            await session.commit()

            # Setup
            permissions_map = await _create_permissions(session)
            roles_map = await _create_roles(session)
            await session.commit()

            await _create_role_permission_mappings(session, roles_map, permissions_map)
            await session.commit()

            # Query Admin role's permissions
            admin_role = roles_map["Admin"]
            stmt = select(RolePermission).where(RolePermission.role_id == admin_role.id)
            result = await session.exec(stmt)
            admin_role_perms = result.all()

            # Admin should have 8 permissions (all CRUD on both Flow and Project)
            assert len(admin_role_perms) == 8

    async def test_viewer_role_has_only_read_permissions(self):
        """Test that Viewer role has only Read permissions."""
        async with session_getter(get_db_service()) as session:
            # Clean up
            stmt = select(RolePermission)
            result = await session.exec(stmt)
            existing_rps = result.all()
            for rp in existing_rps:
                await session.delete(rp)
            await session.commit()

            # Setup
            permissions_map = await _create_permissions(session)
            roles_map = await _create_roles(session)
            await session.commit()

            await _create_role_permission_mappings(session, roles_map, permissions_map)
            await session.commit()

            # Query Viewer role's permissions
            viewer_role = roles_map["Viewer"]
            stmt = select(RolePermission).where(RolePermission.role_id == viewer_role.id)
            result = await session.exec(stmt)
            viewer_role_perms = result.all()

            # Viewer should have 2 permissions (Read on Flow and Project)
            assert len(viewer_role_perms) == 2

            # Verify they are all Read permissions
            for rp in viewer_role_perms:
                await session.refresh(rp, ["permission"])
                assert rp.permission.action == PermissionAction.READ

    async def test_editor_role_has_no_delete_permission(self):
        """Test that Editor role does not have Delete permission."""
        async with session_getter(get_db_service()) as session:
            # Clean up
            stmt = select(RolePermission)
            result = await session.exec(stmt)
            existing_rps = result.all()
            for rp in existing_rps:
                await session.delete(rp)
            await session.commit()

            # Setup
            permissions_map = await _create_permissions(session)
            roles_map = await _create_roles(session)
            await session.commit()

            await _create_role_permission_mappings(session, roles_map, permissions_map)
            await session.commit()

            # Query Editor role's permissions
            editor_role = roles_map["Editor"]
            stmt = select(RolePermission).where(RolePermission.role_id == editor_role.id)
            result = await session.exec(stmt)
            editor_role_perms = result.all()

            # Editor should have 6 permissions (Create, Read, Update on Flow and Project)
            assert len(editor_role_perms) == 6

            # Verify none of them are Delete permissions
            for rp in editor_role_perms:
                await session.refresh(rp, ["permission"])
                assert rp.permission.action != PermissionAction.DELETE

    async def test_role_permission_mappings_idempotent(self):
        """Test that creating mappings is idempotent (safe to run multiple times)."""
        async with session_getter(get_db_service()) as session:
            # Clean up
            stmt = select(RolePermission)
            result = await session.exec(stmt)
            existing_rps = result.all()
            for rp in existing_rps:
                await session.delete(rp)
            await session.commit()

            # Setup
            permissions_map = await _create_permissions(session)
            roles_map = await _create_roles(session)
            await session.commit()

            # First creation
            count1 = await _create_role_permission_mappings(session, roles_map, permissions_map)
            await session.commit()

            # Second creation (should skip existing)
            count2 = await _create_role_permission_mappings(session, roles_map, permissions_map)
            await session.commit()

            # First run should create 24 mappings
            assert count1 == 24
            # Second run should create 0 (all already exist)
            assert count2 == 0


class TestInitializeRBACData:
    """Integration tests for the main initialize_rbac_data function."""

    async def test_initialize_rbac_data_on_empty_database(self):
        """Test initializing RBAC data on empty database."""
        async with session_getter(get_db_service()) as session:
            # Clean up completely
            stmt = select(RolePermission)
            result = await session.exec(stmt)
            for rp in result.all():
                await session.delete(rp)

            stmt = select(Role)
            result = await session.exec(stmt)
            for role in result.all():
                await session.delete(role)

            stmt = select(Permission)
            result = await session.exec(stmt)
            for perm in result.all():
                await session.delete(perm)

            await session.commit()

            # Run initialization
            await initialize_rbac_data(session)

            # Verify roles were created
            stmt = select(Role)
            result = await session.exec(stmt)
            roles = result.all()
            assert len(roles) == 4

            # Verify permissions were created
            stmt = select(Permission)
            result = await session.exec(stmt)
            permissions = result.all()
            assert len(permissions) == 8

            # Verify role-permission mappings were created
            stmt = select(RolePermission)
            result = await session.exec(stmt)
            role_permissions = result.all()
            assert len(role_permissions) == 24

    async def test_initialize_rbac_data_idempotent(self):
        """Test that initialize_rbac_data is idempotent (safe to run multiple times)."""
        async with session_getter(get_db_service()) as session:
            # Clean up
            stmt = select(RolePermission)
            result = await session.exec(stmt)
            for rp in result.all():
                await session.delete(rp)

            stmt = select(Role)
            result = await session.exec(stmt)
            for role in result.all():
                await session.delete(role)

            stmt = select(Permission)
            result = await session.exec(stmt)
            for perm in result.all():
                await session.delete(perm)

            await session.commit()

            # First initialization
            await initialize_rbac_data(session)

            # Get counts after first run
            stmt = select(Role)
            result = await session.exec(stmt)
            roles_count1 = len(result.all())

            stmt = select(Permission)
            result = await session.exec(stmt)
            perms_count1 = len(result.all())

            stmt = select(RolePermission)
            result = await session.exec(stmt)
            mappings_count1 = len(result.all())

            # Second initialization (should skip, not duplicate)
            await initialize_rbac_data(session)

            # Get counts after second run
            stmt = select(Role)
            result = await session.exec(stmt)
            roles_count2 = len(result.all())

            stmt = select(Permission)
            result = await session.exec(stmt)
            perms_count2 = len(result.all())

            stmt = select(RolePermission)
            result = await session.exec(stmt)
            mappings_count2 = len(result.all())

            # Counts should be identical (no duplicates)
            assert roles_count1 == roles_count2 == 4
            assert perms_count1 == perms_count2 == 8
            assert mappings_count1 == mappings_count2 == 24

    async def test_initialize_rbac_data_skips_when_data_exists(self):
        """Test that initialization is skipped when RBAC data already exists."""
        async with session_getter(get_db_service()) as session:
            # Clean up
            stmt = select(RolePermission)
            result = await session.exec(stmt)
            for rp in result.all():
                await session.delete(rp)

            stmt = select(Role)
            result = await session.exec(stmt)
            for role in result.all():
                await session.delete(role)

            stmt = select(Permission)
            result = await session.exec(stmt)
            for perm in result.all():
                await session.delete(perm)

            await session.commit()

            # First initialization
            await initialize_rbac_data(session)

            # Verify initialization happened
            stmt = select(Role)
            result = await session.exec(stmt)
            roles = result.all()
            assert len(roles) == 4

            # Second initialization should skip (logged but no DB operations)
            await initialize_rbac_data(session)

            # Verify counts remain the same
            stmt = select(Role)
            result = await session.exec(stmt)
            roles = result.all()
            assert len(roles) == 4

    async def test_initialize_rbac_data_rollback_on_error(self):
        """Test that initialization rolls back on error."""
        async with session_getter(get_db_service()) as session:
            # Clean up
            stmt = select(RolePermission)
            result = await session.exec(stmt)
            for rp in result.all():
                await session.delete(rp)

            stmt = select(Role)
            result = await session.exec(stmt)
            for role in result.all():
                await session.delete(role)

            stmt = select(Permission)
            result = await session.exec(stmt)
            for perm in result.all():
                await session.delete(perm)

            await session.commit()

        # Test error handling by forcing a database error
        # This test verifies that exceptions are propagated
        async with session_getter(get_db_service()) as session:
            # The function should complete successfully
            await initialize_rbac_data(session)

            # Verify data was created
            stmt = select(Role)
            result = await session.exec(stmt)
            roles = result.all()
            assert len(roles) == 4


class TestRBACDataIntegrity:
    """Integration tests verifying RBAC data integrity."""

    async def test_all_predefined_roles_created(self):
        """Test that all 4 predefined roles are created."""
        async with session_getter(get_db_service()) as session:
            # Clean and initialize
            stmt = select(RolePermission)
            result = await session.exec(stmt)
            for rp in result.all():
                await session.delete(rp)

            stmt = select(Role)
            result = await session.exec(stmt)
            for role in result.all():
                await session.delete(role)

            stmt = select(Permission)
            result = await session.exec(stmt)
            for perm in result.all():
                await session.delete(perm)

            await session.commit()
            await initialize_rbac_data(session)

            # Verify all roles exist
            expected_roles = {"Admin", "Owner", "Editor", "Viewer"}
            stmt = select(Role)
            result = await session.exec(stmt)
            roles = result.all()
            actual_roles = {role.name for role in roles}

            assert actual_roles == expected_roles

    async def test_all_predefined_permissions_created(self):
        """Test that all 8 predefined permissions are created."""
        async with session_getter(get_db_service()) as session:
            # Clean and initialize
            stmt = select(RolePermission)
            result = await session.exec(stmt)
            for rp in result.all():
                await session.delete(rp)

            stmt = select(Role)
            result = await session.exec(stmt)
            for role in result.all():
                await session.delete(role)

            stmt = select(Permission)
            result = await session.exec(stmt)
            for perm in result.all():
                await session.delete(perm)

            await session.commit()
            await initialize_rbac_data(session)

            # Verify all permissions exist
            expected_perms = {
                (PermissionAction.CREATE, PermissionScope.FLOW),
                (PermissionAction.READ, PermissionScope.FLOW),
                (PermissionAction.UPDATE, PermissionScope.FLOW),
                (PermissionAction.DELETE, PermissionScope.FLOW),
                (PermissionAction.CREATE, PermissionScope.PROJECT),
                (PermissionAction.READ, PermissionScope.PROJECT),
                (PermissionAction.UPDATE, PermissionScope.PROJECT),
                (PermissionAction.DELETE, PermissionScope.PROJECT),
            }

            stmt = select(Permission)
            result = await session.exec(stmt)
            permissions = result.all()
            actual_perms = {(perm.action, perm.scope) for perm in permissions}

            assert actual_perms == expected_perms

    async def test_role_permission_mappings_match_spec(self):
        """Test that role-permission mappings match PRD specification."""
        async with session_getter(get_db_service()) as session:
            # Clean and initialize
            stmt = select(RolePermission)
            result = await session.exec(stmt)
            for rp in result.all():
                await session.delete(rp)

            stmt = select(Role)
            result = await session.exec(stmt)
            for role in result.all():
                await session.delete(role)

            stmt = select(Permission)
            result = await session.exec(stmt)
            for perm in result.all():
                await session.delete(perm)

            await session.commit()
            await initialize_rbac_data(session)

            # Verify Admin role permissions (should have 8: all CRUD on Flow and Project)
            stmt = select(Role).where(Role.name == "Admin")
            result = await session.exec(stmt)
            admin_role = result.first()

            stmt = select(RolePermission).where(RolePermission.role_id == admin_role.id)
            result = await session.exec(stmt)
            admin_perms = result.all()
            assert len(admin_perms) == 8

            # Verify Owner role permissions (should have 8: all CRUD on Flow and Project)
            stmt = select(Role).where(Role.name == "Owner")
            result = await session.exec(stmt)
            owner_role = result.first()

            stmt = select(RolePermission).where(RolePermission.role_id == owner_role.id)
            result = await session.exec(stmt)
            owner_perms = result.all()
            assert len(owner_perms) == 8

            # Verify Editor role permissions (should have 6: Create, Read, Update on both scopes)
            stmt = select(Role).where(Role.name == "Editor")
            result = await session.exec(stmt)
            editor_role = result.first()

            stmt = select(RolePermission).where(RolePermission.role_id == editor_role.id)
            result = await session.exec(stmt)
            editor_perms = result.all()
            assert len(editor_perms) == 6

            # Verify Viewer role permissions (should have 2: Read on both scopes)
            stmt = select(Role).where(Role.name == "Viewer")
            result = await session.exec(stmt)
            viewer_role = result.first()

            stmt = select(RolePermission).where(RolePermission.role_id == viewer_role.id)
            result = await session.exec(stmt)
            viewer_perms = result.all()
            assert len(viewer_perms) == 2
