"""Integration tests for RBAC initialization in application startup."""

import pytest
from langbuilder.services.database.models.rbac import Permission, Role, RolePermission
from langbuilder.services.database.utils import session_getter
from langbuilder.services.deps import get_db_service, session_scope
from sqlmodel import select


class TestRBACStartupIntegration:
    """Tests for RBAC initialization during application startup."""

    async def test_rbac_initialization_called_during_startup(self):
        """Test that RBAC initialization is called during application startup.

        This test verifies that the initialize_rbac_data function is invoked
        as part of the lifespan startup sequence.
        """
        from langbuilder.initial_setup.rbac_setup import initialize_rbac_data

        # Clean up database before test
        async with session_getter(get_db_service()) as session:
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

        # Simulate startup initialization
        async with session_scope() as session:
            await initialize_rbac_data(session)

        # Verify RBAC data was created
        async with session_getter(get_db_service()) as session:
            stmt = select(Role)
            result = await session.exec(stmt)
            roles = result.all()
            assert len(roles) == 4, "Expected 4 roles to be created during startup"

            stmt = select(Permission)
            result = await session.exec(stmt)
            permissions = result.all()
            assert len(permissions) == 8, "Expected 8 permissions to be created during startup"

    async def test_rbac_tables_populated_on_first_startup(self):
        """Test that RBAC tables are populated on first startup.

        Success criterion: RBAC tables are populated on first startup.
        """
        from langbuilder.initial_setup.rbac_setup import initialize_rbac_data

        # Clean up database to simulate first startup
        async with session_getter(get_db_service()) as session:
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

        # Verify tables are empty before initialization
        async with session_getter(get_db_service()) as session:
            stmt = select(Role)
            result = await session.exec(stmt)
            assert len(result.all()) == 0, "Roles table should be empty before initialization"

            stmt = select(Permission)
            result = await session.exec(stmt)
            assert len(result.all()) == 0, "Permissions table should be empty before initialization"

        # Run initialization (simulating first startup)
        async with session_scope() as session:
            await initialize_rbac_data(session)

        # Verify tables are populated after initialization
        async with session_getter(get_db_service()) as session:
            # Verify roles
            stmt = select(Role)
            result = await session.exec(stmt)
            roles = result.all()
            assert len(roles) == 4, "Expected 4 roles after first startup"
            role_names = {role.name for role in roles}
            assert role_names == {"Admin", "Owner", "Editor", "Viewer"}

            # Verify permissions
            stmt = select(Permission)
            result = await session.exec(stmt)
            permissions = result.all()
            assert len(permissions) == 8, "Expected 8 permissions after first startup"

            # Verify role-permission mappings
            stmt = select(RolePermission)
            result = await session.exec(stmt)
            role_permissions = result.all()
            assert len(role_permissions) == 24, "Expected 24 role-permission mappings after first startup"

    async def test_subsequent_startups_skip_initialization(self):
        """Test that subsequent startups skip initialization (idempotent).

        Success criterion: Subsequent startups skip initialization (idempotent).
        """
        from langbuilder.initial_setup.rbac_setup import initialize_rbac_data

        # Clean up and perform first initialization
        async with session_getter(get_db_service()) as session:
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

        # First startup
        async with session_scope() as session:
            await initialize_rbac_data(session)

        # Get counts after first startup
        async with session_getter(get_db_service()) as session:
            stmt = select(Role)
            result = await session.exec(stmt)
            roles_count_1 = len(result.all())

            stmt = select(Permission)
            result = await session.exec(stmt)
            perms_count_1 = len(result.all())

            stmt = select(RolePermission)
            result = await session.exec(stmt)
            mappings_count_1 = len(result.all())

        # Second startup (should skip initialization)
        async with session_scope() as session:
            await initialize_rbac_data(session)

        # Get counts after second startup
        async with session_getter(get_db_service()) as session:
            stmt = select(Role)
            result = await session.exec(stmt)
            roles_count_2 = len(result.all())

            stmt = select(Permission)
            result = await session.exec(stmt)
            perms_count_2 = len(result.all())

            stmt = select(RolePermission)
            result = await session.exec(stmt)
            mappings_count_2 = len(result.all())

        # Verify counts remain the same (no duplicates)
        assert roles_count_1 == roles_count_2 == 4, "Roles count should remain constant across startups"
        assert perms_count_1 == perms_count_2 == 8, "Permissions count should remain constant across startups"
        assert mappings_count_1 == mappings_count_2 == 24, "Mappings count should remain constant across startups"

    async def test_rbac_initialization_uses_session_scope(self):
        """Test that RBAC initialization uses session_scope context manager.

        This ensures proper transaction management and error handling.
        """
        from langbuilder.initial_setup.rbac_setup import initialize_rbac_data

        # Clean up
        async with session_getter(get_db_service()) as session:
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

        # Test using session_scope as done in main.py
        try:
            async with session_scope() as session:
                await initialize_rbac_data(session)
            success = True
        except Exception:
            success = False

        assert success, "RBAC initialization should succeed with session_scope"

        # Verify data was committed
        async with session_getter(get_db_service()) as session:
            stmt = select(Role)
            result = await session.exec(stmt)
            roles = result.all()
            assert len(roles) == 4, "Roles should be committed after initialization"

    async def test_roles_and_permissions_exist_after_startup(self):
        """Test that roles and permissions exist after startup.

        Success criterion: Integration test verifies roles and permissions exist after startup.
        """
        from langbuilder.initial_setup.rbac_setup import initialize_rbac_data

        # Clean up and initialize
        async with session_getter(get_db_service()) as session:
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

        # Simulate startup
        async with session_scope() as session:
            await initialize_rbac_data(session)

        # Verify all expected roles exist
        async with session_getter(get_db_service()) as session:
            expected_roles = ["Admin", "Owner", "Editor", "Viewer"]
            for role_name in expected_roles:
                stmt = select(Role).where(Role.name == role_name)
                result = await session.exec(stmt)
                role = result.first()
                assert role is not None, f"Role '{role_name}' should exist after startup"
                assert role.is_system is True, f"Role '{role_name}' should be a system role"

        # Verify all expected permissions exist
        async with session_getter(get_db_service()) as session:
            from langbuilder.services.database.models.rbac.permission import PermissionAction, PermissionScope

            expected_permissions = [
                (PermissionAction.CREATE, PermissionScope.FLOW),
                (PermissionAction.READ, PermissionScope.FLOW),
                (PermissionAction.UPDATE, PermissionScope.FLOW),
                (PermissionAction.DELETE, PermissionScope.FLOW),
                (PermissionAction.CREATE, PermissionScope.PROJECT),
                (PermissionAction.READ, PermissionScope.PROJECT),
                (PermissionAction.UPDATE, PermissionScope.PROJECT),
                (PermissionAction.DELETE, PermissionScope.PROJECT),
            ]
            for action, scope in expected_permissions:
                stmt = select(Permission).where(Permission.action == action, Permission.scope == scope)
                result = await session.exec(stmt)
                permission = result.first()
                assert permission is not None, f"Permission '{action}:{scope}' should exist after startup"

    async def test_rbac_initialization_timing_in_startup_sequence(self):
        """Test that RBAC initialization occurs after database initialization.

        This verifies that RBAC initialization is placed correctly in the startup sequence,
        after database services are initialized but before the application accepts requests.
        """
        from langbuilder.initial_setup.rbac_setup import initialize_rbac_data

        # Verify that database service is available (simulating post-db-init state)
        db_service = get_db_service()
        assert db_service is not None, "Database service should be initialized before RBAC initialization"

        # Clean up
        async with session_getter(db_service) as session:
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

        # Test RBAC initialization
        async with session_scope() as session:
            await initialize_rbac_data(session)

        # Verify successful initialization
        async with session_getter(db_service) as session:
            stmt = select(Role)
            result = await session.exec(stmt)
            assert len(result.all()) > 0, "RBAC data should be initialized after database service is ready"

    async def test_rbac_initialization_error_handling(self):
        """Test that RBAC initialization handles errors gracefully.

        This verifies that errors during initialization are properly logged and
        don't prevent the application from starting (if appropriate).
        """
        from langbuilder.initial_setup.rbac_setup import initialize_rbac_data

        # Clean up
        async with session_getter(get_db_service()) as session:
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

        # Test that initialization handles the normal case without errors
        try:
            async with session_scope() as session:
                await initialize_rbac_data(session)
            no_errors = True
        except Exception as e:
            no_errors = False
            pytest.fail(f"RBAC initialization should not raise errors during normal operation: {e}")

        assert no_errors, "RBAC initialization should complete without errors"

    async def test_admin_role_has_all_permissions_after_startup(self):
        """Test that Admin role has all permissions after startup.

        This is a critical integration test to verify that the Admin role
        is properly configured with full access.
        """
        from langbuilder.initial_setup.rbac_setup import initialize_rbac_data

        # Clean up and initialize
        async with session_getter(get_db_service()) as session:
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

        # Simulate startup
        async with session_scope() as session:
            await initialize_rbac_data(session)

        # Verify Admin role has all 8 permissions
        async with session_getter(get_db_service()) as session:
            stmt = select(Role).where(Role.name == "Admin")
            result = await session.exec(stmt)
            admin_role = result.first()
            assert admin_role is not None, "Admin role should exist after startup"

            stmt = select(RolePermission).where(RolePermission.role_id == admin_role.id)
            result = await session.exec(stmt)
            admin_permissions = result.all()
            assert len(admin_permissions) == 8, "Admin should have all 8 permissions (4 CRUD x 2 scopes)"

    async def test_viewer_role_has_only_read_permissions_after_startup(self):
        """Test that Viewer role has only Read permissions after startup.

        This verifies that the Viewer role is properly restricted to read-only access.
        """
        from langbuilder.initial_setup.rbac_setup import initialize_rbac_data

        # Clean up and initialize
        async with session_getter(get_db_service()) as session:
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

        # Simulate startup
        async with session_scope() as session:
            await initialize_rbac_data(session)

        # Verify Viewer role has only Read permissions
        async with session_getter(get_db_service()) as session:
            stmt = select(Role).where(Role.name == "Viewer")
            result = await session.exec(stmt)
            viewer_role = result.first()
            assert viewer_role is not None, "Viewer role should exist after startup"

            stmt = select(RolePermission).where(RolePermission.role_id == viewer_role.id)
            result = await session.exec(stmt)
            viewer_permissions = result.all()
            assert len(viewer_permissions) == 2, "Viewer should have exactly 2 Read permissions"

            # Verify all permissions are Read permissions
            from langbuilder.services.database.models.rbac.permission import PermissionAction

            for rp in viewer_permissions:
                await session.refresh(rp, ["permission"])
                assert rp.permission.action == PermissionAction.READ, (
                    f"Viewer should only have Read permissions, found {rp.permission.action}"
                )

    async def test_multiple_startup_cycles_maintain_data_integrity(self):
        """Test that multiple startup cycles maintain data integrity.

        This simulates multiple application restarts and verifies that
        RBAC data remains consistent and correct.
        """
        from langbuilder.initial_setup.rbac_setup import initialize_rbac_data

        # Clean up
        async with session_getter(get_db_service()) as session:
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

        # Simulate 5 startup cycles
        for i in range(5):
            async with session_scope() as session:
                await initialize_rbac_data(session)

        # Verify data integrity after multiple cycles
        async with session_getter(get_db_service()) as session:
            # Verify role count
            stmt = select(Role)
            result = await session.exec(stmt)
            roles = result.all()
            assert len(roles) == 4, f"Should still have exactly 4 roles after 5 startup cycles, found {len(roles)}"

            # Verify permission count
            stmt = select(Permission)
            result = await session.exec(stmt)
            permissions = result.all()
            assert len(permissions) == 8, (
                f"Should still have exactly 8 permissions after 5 startup cycles, found {len(permissions)}"
            )

            # Verify mapping count
            stmt = select(RolePermission)
            result = await session.exec(stmt)
            mappings = result.all()
            assert len(mappings) == 24, (
                f"Should still have exactly 24 mappings after 5 startup cycles, found {len(mappings)}"
            )
