"""Unit tests for UserRoleAssignment model."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from langbuilder.services.database.models.rbac import (
    Role,
    UserRoleAssignment,
    UserRoleAssignmentCreate,
    UserRoleAssignmentRead,
    UserRoleAssignmentUpdate,
)
from langbuilder.services.database.models.user.model import User
from langbuilder.services.database.utils import session_getter
from langbuilder.services.deps import get_db_service
from sqlalchemy.exc import IntegrityError
from sqlmodel import select


class TestUserRoleAssignmentModel:
    """Tests for the UserRoleAssignment model."""

    async def test_user_role_assignment_creation_global_scope(self):
        """Test creating a user role assignment with global scope."""
        async with session_getter(get_db_service()) as session:
            # Create a user
            user = User(username="testuser1", password="testpass")
            session.add(user)

            # Create a role
            role = Role(name="GlobalAdmin", description="Global administrator")
            session.add(role)
            await session.commit()
            await session.refresh(user)
            await session.refresh(role)

        async with session_getter(get_db_service()) as session:
            # Create global scope assignment
            assignment = UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                scope_type="global",
                scope_id=None,
                is_immutable=False,
            )
            session.add(assignment)
            await session.commit()
            await session.refresh(assignment)

            assert assignment.id is not None
            assert assignment.user_id == user.id
            assert assignment.role_id == role.id
            assert assignment.scope_type == "global"
            assert assignment.scope_id is None
            assert assignment.is_immutable is False
            assert assignment.created_at is not None
            assert isinstance(assignment.created_at, datetime)

    async def test_user_role_assignment_creation_project_scope(self):
        """Test creating a user role assignment with project scope."""
        async with session_getter(get_db_service()) as session:
            # Create a user
            user = User(username="testuser2", password="testpass")
            session.add(user)

            # Create a role
            role = Role(name="ProjectOwner", description="Project owner")
            session.add(role)
            await session.commit()
            await session.refresh(user)
            await session.refresh(role)

        # Create a project ID
        project_id = uuid4()

        async with session_getter(get_db_service()) as session:
            # Create project scope assignment
            assignment = UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                scope_type="project",
                scope_id=project_id,
                is_immutable=False,
            )
            session.add(assignment)
            await session.commit()
            await session.refresh(assignment)

            assert assignment.id is not None
            assert assignment.user_id == user.id
            assert assignment.role_id == role.id
            assert assignment.scope_type == "project"
            assert assignment.scope_id == project_id
            assert assignment.is_immutable is False

    async def test_user_role_assignment_creation_flow_scope(self):
        """Test creating a user role assignment with flow scope."""
        async with session_getter(get_db_service()) as session:
            # Create a user
            user = User(username="testuser3", password="testpass")
            session.add(user)

            # Create a role
            role = Role(name="FlowEditor", description="Flow editor")
            session.add(role)
            await session.commit()
            await session.refresh(user)
            await session.refresh(role)

        # Create a flow ID
        flow_id = uuid4()

        async with session_getter(get_db_service()) as session:
            # Create flow scope assignment
            assignment = UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                scope_type="flow",
                scope_id=flow_id,
                is_immutable=False,
            )
            session.add(assignment)
            await session.commit()
            await session.refresh(assignment)

            assert assignment.id is not None
            assert assignment.user_id == user.id
            assert assignment.role_id == role.id
            assert assignment.scope_type == "flow"
            assert assignment.scope_id == flow_id
            assert assignment.is_immutable is False

    async def test_user_role_assignment_with_immutable_flag(self):
        """Test creating an immutable user role assignment (Starter Project Owner)."""
        async with session_getter(get_db_service()) as session:
            # Create a user
            user = User(username="testuser4", password="testpass")
            session.add(user)

            # Create a role
            role = Role(name="StarterOwner", description="Starter project owner")
            session.add(role)
            await session.commit()
            await session.refresh(user)
            await session.refresh(role)

        # Create a project ID
        project_id = uuid4()

        async with session_getter(get_db_service()) as session:
            # Create immutable assignment
            assignment = UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                scope_type="project",
                scope_id=project_id,
                is_immutable=True,
            )
            session.add(assignment)
            await session.commit()
            await session.refresh(assignment)

            assert assignment.id is not None
            assert assignment.is_immutable is True

    async def test_user_role_assignment_with_created_by(self):
        """Test creating a user role assignment with created_by tracking."""
        async with session_getter(get_db_service()) as session:
            # Create users
            user = User(username="testuser5", password="testpass")
            admin_user = User(username="adminuser", password="testpass")
            session.add(user)
            session.add(admin_user)

            # Create a role
            role = Role(name="AssignedRole", description="Assigned role")
            session.add(role)
            await session.commit()
            await session.refresh(user)
            await session.refresh(admin_user)
            await session.refresh(role)

        async with session_getter(get_db_service()) as session:
            # Create assignment with created_by
            assignment = UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                scope_type="global",
                scope_id=None,
                is_immutable=False,
                created_by=admin_user.id,
            )
            session.add(assignment)
            await session.commit()
            await session.refresh(assignment)

            assert assignment.id is not None
            assert assignment.created_by == admin_user.id

    async def test_user_role_assignment_unique_constraint(self):
        """Test that duplicate user-role-scope assignments are prevented."""
        async with session_getter(get_db_service()) as session:
            # Create a user
            user = User(username="testuser6", password="testpass")
            session.add(user)

            # Create a role
            role = Role(name="UniqueRole", description="Unique role test")
            session.add(role)
            await session.commit()
            await session.refresh(user)
            await session.refresh(role)

        # Create a project ID
        project_id = uuid4()

        async with session_getter(get_db_service()) as session:
            # Create first assignment
            assignment1 = UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                scope_type="project",
                scope_id=project_id,
                is_immutable=False,
            )
            session.add(assignment1)
            await session.commit()

        # Try to create duplicate assignment
        with pytest.raises(IntegrityError):
            async with session_getter(get_db_service()) as session:
                assignment2 = UserRoleAssignment(
                    user_id=user.id,
                    role_id=role.id,
                    scope_type="project",
                    scope_id=project_id,
                    is_immutable=False,
                )
                session.add(assignment2)
                await session.commit()

    async def test_user_role_assignment_different_scopes_allowed(self):
        """Test that same user-role pair is allowed for different scopes."""
        async with session_getter(get_db_service()) as session:
            # Create a user
            user = User(username="testuser7", password="testpass")
            session.add(user)

            # Create a role
            role = Role(name="MultiScopeRole", description="Multi-scope role test")
            session.add(role)
            await session.commit()
            await session.refresh(user)
            await session.refresh(role)

        # Create project IDs
        project_id1 = uuid4()
        project_id2 = uuid4()

        async with session_getter(get_db_service()) as session:
            # Create assignment for project 1
            assignment1 = UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                scope_type="project",
                scope_id=project_id1,
            )
            # Create assignment for project 2
            assignment2 = UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                scope_type="project",
                scope_id=project_id2,
            )
            # Create global assignment
            assignment3 = UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                scope_type="global",
                scope_id=None,
            )
            session.add(assignment1)
            session.add(assignment2)
            session.add(assignment3)
            await session.commit()

            # All three should succeed (different scopes)
            assert assignment1.id is not None
            assert assignment2.id is not None
            assert assignment3.id is not None

    async def test_user_role_assignment_query_by_user(self):
        """Test querying assignments by user."""
        async with session_getter(get_db_service()) as session:
            # Create a user
            user = User(username="testuser8", password="testpass")
            session.add(user)

            # Create roles
            role1 = Role(name="QueryRole1", description="Query role 1")
            role2 = Role(name="QueryRole2", description="Query role 2")
            session.add(role1)
            session.add(role2)
            await session.commit()
            await session.refresh(user)
            await session.refresh(role1)
            await session.refresh(role2)

        async with session_getter(get_db_service()) as session:
            # Create multiple assignments for the user
            assignment1 = UserRoleAssignment(
                user_id=user.id,
                role_id=role1.id,
                scope_type="global",
                scope_id=None,
            )
            assignment2 = UserRoleAssignment(
                user_id=user.id,
                role_id=role2.id,
                scope_type="project",
                scope_id=uuid4(),
            )
            session.add(assignment1)
            session.add(assignment2)
            await session.commit()

        # Query by user_id
        async with session_getter(get_db_service()) as session:
            stmt = select(UserRoleAssignment).where(UserRoleAssignment.user_id == user.id)
            result = await session.exec(stmt)
            assignments = result.all()

            assert len(assignments) >= 2
            assert all(a.user_id == user.id for a in assignments)

    async def test_user_role_assignment_query_by_scope(self):
        """Test querying assignments by scope (permission check pattern)."""
        async with session_getter(get_db_service()) as session:
            # Create a user
            user = User(username="testuser9", password="testpass")
            session.add(user)

            # Create a role
            role = Role(name="ScopeQueryRole", description="Scope query role")
            session.add(role)
            await session.commit()
            await session.refresh(user)
            await session.refresh(role)

        # Create a project ID
        project_id = uuid4()

        async with session_getter(get_db_service()) as session:
            # Create project scope assignment
            assignment = UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                scope_type="project",
                scope_id=project_id,
            )
            session.add(assignment)
            await session.commit()

        # Query by user_id, scope_type, and scope_id (permission check pattern)
        async with session_getter(get_db_service()) as session:
            stmt = select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == user.id,
                UserRoleAssignment.scope_type == "project",
                UserRoleAssignment.scope_id == project_id,
            )
            result = await session.exec(stmt)
            found_assignments = result.all()

            assert len(found_assignments) >= 1
            assert found_assignments[0].user_id == user.id
            assert found_assignments[0].scope_type == "project"
            assert found_assignments[0].scope_id == project_id

    async def test_user_role_assignment_relationship_to_user(self):
        """Test relationship traversal from UserRoleAssignment to User."""
        async with session_getter(get_db_service()) as session:
            # Create a user
            user = User(username="testuser10", password="testpass")
            session.add(user)

            # Create a role
            role = Role(name="RelationRole", description="Relation test role")
            session.add(role)
            await session.commit()
            await session.refresh(user)
            await session.refresh(role)

        async with session_getter(get_db_service()) as session:
            # Create assignment
            assignment = UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                scope_type="global",
                scope_id=None,
            )
            session.add(assignment)
            await session.commit()
            assignment_id = assignment.id

        # Query and verify relationship
        async with session_getter(get_db_service()) as session:
            stmt = select(UserRoleAssignment).where(UserRoleAssignment.id == assignment_id)
            result = await session.exec(stmt)
            found_assignment = result.first()

            # Load the relationship
            await session.refresh(found_assignment, ["user"])

            assert found_assignment is not None
            assert found_assignment.user is not None
            assert found_assignment.user.username == "testuser10"

    async def test_user_role_assignment_relationship_to_role(self):
        """Test relationship traversal from UserRoleAssignment to Role."""
        async with session_getter(get_db_service()) as session:
            # Create a user
            user = User(username="testuser11", password="testpass")
            session.add(user)

            # Create a role
            role = Role(name="RoleRelationTest", description="Role relation test")
            session.add(role)
            await session.commit()
            await session.refresh(user)
            await session.refresh(role)

        async with session_getter(get_db_service()) as session:
            # Create assignment
            assignment = UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                scope_type="global",
                scope_id=None,
            )
            session.add(assignment)
            await session.commit()
            assignment_id = assignment.id

        # Query and verify relationship
        async with session_getter(get_db_service()) as session:
            stmt = select(UserRoleAssignment).where(UserRoleAssignment.id == assignment_id)
            result = await session.exec(stmt)
            found_assignment = result.first()

            # Load the relationship
            await session.refresh(found_assignment, ["role"])

            assert found_assignment is not None
            assert found_assignment.role is not None
            assert found_assignment.role.name == "RoleRelationTest"
            assert found_assignment.role.description == "Role relation test"

    async def test_user_to_role_assignments_relationship(self):
        """Test relationship traversal from User to UserRoleAssignment list."""
        async with session_getter(get_db_service()) as session:
            # Create a user
            user = User(username="testuser12", password="testpass")
            session.add(user)

            # Create roles
            role1 = Role(name="UserRelRole1", description="User relation role 1")
            role2 = Role(name="UserRelRole2", description="User relation role 2")
            session.add(role1)
            session.add(role2)
            await session.commit()
            await session.refresh(user)
            await session.refresh(role1)
            await session.refresh(role2)
            user_id = user.id

        async with session_getter(get_db_service()) as session:
            # Create multiple assignments
            assignment1 = UserRoleAssignment(
                user_id=user_id,
                role_id=role1.id,
                scope_type="global",
                scope_id=None,
            )
            assignment2 = UserRoleAssignment(
                user_id=user_id,
                role_id=role2.id,
                scope_type="project",
                scope_id=uuid4(),
            )
            session.add(assignment1)
            session.add(assignment2)
            await session.commit()

        # Query user and verify relationships
        async with session_getter(get_db_service()) as session:
            stmt = select(User).where(User.id == user_id)
            result = await session.exec(stmt)
            found_user = result.first()

            # Load the relationships
            await session.refresh(found_user, ["role_assignments"])

            assert found_user is not None
            assert len(found_user.role_assignments) >= 2
            assert all(isinstance(a, UserRoleAssignment) for a in found_user.role_assignments)

    async def test_role_to_user_assignments_relationship(self):
        """Test relationship traversal from Role to UserRoleAssignment list."""
        async with session_getter(get_db_service()) as session:
            # Create a role
            role = Role(name="RoleToUserRel", description="Role to user relation test")
            session.add(role)

            # Create users
            user1 = User(username="testuser13", password="testpass")
            user2 = User(username="testuser14", password="testpass")
            session.add(user1)
            session.add(user2)
            await session.commit()
            await session.refresh(role)
            await session.refresh(user1)
            await session.refresh(user2)
            role_id = role.id

        async with session_getter(get_db_service()) as session:
            # Create multiple assignments
            assignment1 = UserRoleAssignment(
                user_id=user1.id,
                role_id=role_id,
                scope_type="global",
                scope_id=None,
            )
            assignment2 = UserRoleAssignment(
                user_id=user2.id,
                role_id=role_id,
                scope_type="global",
                scope_id=None,
            )
            session.add(assignment1)
            session.add(assignment2)
            await session.commit()

        # Query role and verify relationships
        async with session_getter(get_db_service()) as session:
            stmt = select(Role).where(Role.id == role_id)
            result = await session.exec(stmt)
            found_role = result.first()

            # Load the relationships
            await session.refresh(found_role, ["user_assignments"])

            assert found_role is not None
            assert len(found_role.user_assignments) >= 2
            assert all(isinstance(a, UserRoleAssignment) for a in found_role.user_assignments)

    async def test_user_role_assignment_delete(self):
        """Test deleting a user role assignment."""
        async with session_getter(get_db_service()) as session:
            # Create a user
            user = User(username="testuser15", password="testpass")
            session.add(user)

            # Create a role
            role = Role(name="DeleteTestRole", description="Delete test role")
            session.add(role)
            await session.commit()
            await session.refresh(user)
            await session.refresh(role)

        async with session_getter(get_db_service()) as session:
            # Create assignment
            assignment = UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                scope_type="global",
                scope_id=None,
            )
            session.add(assignment)
            await session.commit()
            await session.refresh(assignment)
            assignment_id = assignment.id

        async with session_getter(get_db_service()) as session:
            # Delete the assignment
            stmt = select(UserRoleAssignment).where(UserRoleAssignment.id == assignment_id)
            result = await session.exec(stmt)
            assignment = result.first()

            await session.delete(assignment)
            await session.commit()

        # Verify deletion
        async with session_getter(get_db_service()) as session:
            stmt = select(UserRoleAssignment).where(UserRoleAssignment.id == assignment_id)
            result = await session.exec(stmt)
            deleted_assignment = result.first()

            assert deleted_assignment is None

    async def test_user_role_assignment_created_at_timestamp(self):
        """Test that created_at timestamp is automatically set."""
        async with session_getter(get_db_service()) as session:
            # Create a user
            user = User(username="testuser16", password="testpass")
            session.add(user)

            # Create a role
            role = Role(name="TimestampRole", description="Timestamp test role")
            session.add(role)
            await session.commit()
            await session.refresh(user)
            await session.refresh(role)

        before_creation = datetime.now(timezone.utc)

        async with session_getter(get_db_service()) as session:
            # Create assignment
            assignment = UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                scope_type="global",
                scope_id=None,
            )
            session.add(assignment)
            await session.commit()
            await session.refresh(assignment)

        after_creation = datetime.now(timezone.utc)

        assert assignment.created_at is not None
        assert before_creation <= assignment.created_at <= after_creation

    async def test_user_role_assignment_multiple_roles_per_user(self):
        """Test that a user can have multiple role assignments."""
        async with session_getter(get_db_service()) as session:
            # Create a user
            user = User(username="testuser17", password="testpass")
            session.add(user)

            # Create roles
            role1 = Role(name="MultiRole1", description="Multi role 1")
            role2 = Role(name="MultiRole2", description="Multi role 2")
            role3 = Role(name="MultiRole3", description="Multi role 3")
            session.add(role1)
            session.add(role2)
            session.add(role3)
            await session.commit()
            await session.refresh(user)
            await session.refresh(role1)
            await session.refresh(role2)
            await session.refresh(role3)

        async with session_getter(get_db_service()) as session:
            # Create multiple assignments for the same user
            assignment1 = UserRoleAssignment(
                user_id=user.id,
                role_id=role1.id,
                scope_type="global",
                scope_id=None,
            )
            assignment2 = UserRoleAssignment(
                user_id=user.id,
                role_id=role2.id,
                scope_type="project",
                scope_id=uuid4(),
            )
            assignment3 = UserRoleAssignment(
                user_id=user.id,
                role_id=role3.id,
                scope_type="flow",
                scope_id=uuid4(),
            )
            session.add(assignment1)
            session.add(assignment2)
            session.add(assignment3)
            await session.commit()

            # All three should succeed
            assert assignment1.id is not None
            assert assignment2.id is not None
            assert assignment3.id is not None


class TestUserRoleAssignmentSchemas:
    """Tests for UserRoleAssignment Pydantic schemas."""

    def test_user_role_assignment_create_schema(self):
        """Test UserRoleAssignmentCreate schema validation."""
        user_id = uuid4()
        role_id = uuid4()
        scope_id = uuid4()

        assignment_create = UserRoleAssignmentCreate(
            user_id=user_id,
            role_id=role_id,
            scope_type="project",
            scope_id=scope_id,
            is_immutable=False,
        )

        assert assignment_create.user_id == user_id
        assert assignment_create.role_id == role_id
        assert assignment_create.scope_type == "project"
        assert assignment_create.scope_id == scope_id
        assert assignment_create.is_immutable is False

    def test_user_role_assignment_create_schema_global_scope(self):
        """Test UserRoleAssignmentCreate schema with global scope."""
        user_id = uuid4()
        role_id = uuid4()

        assignment_create = UserRoleAssignmentCreate(
            user_id=user_id,
            role_id=role_id,
            scope_type="global",
            scope_id=None,
        )

        assert assignment_create.user_id == user_id
        assert assignment_create.role_id == role_id
        assert assignment_create.scope_type == "global"
        assert assignment_create.scope_id is None
        assert assignment_create.is_immutable is False

    def test_user_role_assignment_create_schema_immutable(self):
        """Test UserRoleAssignmentCreate schema with immutable flag."""
        user_id = uuid4()
        role_id = uuid4()
        scope_id = uuid4()

        assignment_create = UserRoleAssignmentCreate(
            user_id=user_id,
            role_id=role_id,
            scope_type="project",
            scope_id=scope_id,
            is_immutable=True,
        )

        assert assignment_create.is_immutable is True

    def test_user_role_assignment_create_schema_with_created_by(self):
        """Test UserRoleAssignmentCreate schema with created_by."""
        user_id = uuid4()
        role_id = uuid4()
        admin_id = uuid4()

        assignment_create = UserRoleAssignmentCreate(
            user_id=user_id,
            role_id=role_id,
            scope_type="global",
            scope_id=None,
            created_by=admin_id,
        )

        assert assignment_create.created_by == admin_id

    def test_user_role_assignment_read_schema(self):
        """Test UserRoleAssignmentRead schema."""
        id = uuid4()
        user_id = uuid4()
        role_id = uuid4()
        scope_id = uuid4()
        created_at = datetime.now(timezone.utc)
        created_by = uuid4()

        assignment_read = UserRoleAssignmentRead(
            id=id,
            user_id=user_id,
            role_id=role_id,
            scope_type="project",
            scope_id=scope_id,
            is_immutable=False,
            created_at=created_at,
            created_by=created_by,
        )

        assert assignment_read.id == id
        assert assignment_read.user_id == user_id
        assert assignment_read.role_id == role_id
        assert assignment_read.scope_type == "project"
        assert assignment_read.scope_id == scope_id
        assert assignment_read.is_immutable is False
        assert assignment_read.created_at == created_at
        assert assignment_read.created_by == created_by

    def test_user_role_assignment_update_schema(self):
        """Test UserRoleAssignmentUpdate schema."""
        role_id = uuid4()

        assignment_update = UserRoleAssignmentUpdate(
            role_id=role_id,
            is_immutable=True,
        )

        assert assignment_update.role_id == role_id
        assert assignment_update.is_immutable is True
        assert assignment_update.user_id is None
        assert assignment_update.scope_type is None

    def test_user_role_assignment_update_schema_partial(self):
        """Test UserRoleAssignmentUpdate schema with partial updates."""
        assignment_update = UserRoleAssignmentUpdate(is_immutable=True)

        assert assignment_update.user_id is None
        assert assignment_update.role_id is None
        assert assignment_update.scope_type is None
        assert assignment_update.scope_id is None
        assert assignment_update.is_immutable is True
