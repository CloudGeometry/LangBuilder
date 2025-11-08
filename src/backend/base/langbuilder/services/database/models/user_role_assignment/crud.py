from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from langbuilder.services.database.models.user_role_assignment.model import (
    UserRoleAssignment,
    UserRoleAssignmentCreate,
    UserRoleAssignmentUpdate,
)


async def create_user_role_assignment(
    db: AsyncSession, user_role_assignment: UserRoleAssignmentCreate
) -> UserRoleAssignment:
    """Create a new user role assignment."""
    db_user_role_assignment = UserRoleAssignment.model_validate(user_role_assignment)
    db.add(db_user_role_assignment)
    try:
        await db.commit()
        await db.refresh(db_user_role_assignment)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail="User role assignment already exists") from e
    else:
        return db_user_role_assignment


async def get_user_role_assignment_by_id(db: AsyncSession, assignment_id: UUID) -> UserRoleAssignment | None:
    """Get a user role assignment by ID."""
    if isinstance(assignment_id, str):
        assignment_id = UUID(assignment_id)
    stmt = select(UserRoleAssignment).where(UserRoleAssignment.id == assignment_id)
    result = await db.exec(stmt)
    return result.first()


async def get_user_role_assignment(
    db: AsyncSession, user_id: UUID, role_id: UUID, scope_type: str, scope_id: UUID | None = None
) -> UserRoleAssignment | None:
    """Get a user role assignment by user_id, role_id, scope_type, and scope_id."""
    stmt = select(UserRoleAssignment).where(
        UserRoleAssignment.user_id == user_id,
        UserRoleAssignment.role_id == role_id,
        UserRoleAssignment.scope_type == scope_type,
        UserRoleAssignment.scope_id == scope_id,
    )
    result = await db.exec(stmt)
    return result.first()


async def list_user_role_assignments(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[UserRoleAssignment]:
    """List all user role assignments with pagination."""
    stmt = select(UserRoleAssignment).offset(skip).limit(limit)
    result = await db.exec(stmt)
    return list(result.all())


async def list_assignments_by_user(db: AsyncSession, user_id: UUID) -> list[UserRoleAssignment]:
    """List all role assignments for a specific user."""
    stmt = select(UserRoleAssignment).where(UserRoleAssignment.user_id == user_id)
    result = await db.exec(stmt)
    return list(result.all())


async def list_assignments_by_role(db: AsyncSession, role_id: UUID) -> list[UserRoleAssignment]:
    """List all user assignments for a specific role."""
    stmt = select(UserRoleAssignment).where(UserRoleAssignment.role_id == role_id)
    result = await db.exec(stmt)
    return list(result.all())


async def list_assignments_by_scope(
    db: AsyncSession, scope_type: str, scope_id: UUID | None = None
) -> list[UserRoleAssignment]:
    """List all user role assignments for a specific scope."""
    stmt = select(UserRoleAssignment).where(
        UserRoleAssignment.scope_type == scope_type, UserRoleAssignment.scope_id == scope_id
    )
    result = await db.exec(stmt)
    return list(result.all())


async def update_user_role_assignment(
    db: AsyncSession, assignment_id: UUID, assignment_update: UserRoleAssignmentUpdate
) -> UserRoleAssignment:
    """Update a user role assignment."""
    db_assignment = await get_user_role_assignment_by_id(db, assignment_id)
    if not db_assignment:
        raise HTTPException(status_code=404, detail="User role assignment not found")

    if db_assignment.is_immutable:
        raise HTTPException(status_code=400, detail="Cannot modify immutable user role assignment")

    assignment_data = assignment_update.model_dump(exclude_unset=True)
    for key, value in assignment_data.items():
        setattr(db_assignment, key, value)

    try:
        await db.commit()
        await db.refresh(db_assignment)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    else:
        return db_assignment


async def delete_user_role_assignment(db: AsyncSession, assignment_id: UUID) -> dict:
    """Delete a user role assignment."""
    db_assignment = await get_user_role_assignment_by_id(db, assignment_id)
    if not db_assignment:
        raise HTTPException(status_code=404, detail="User role assignment not found")

    if db_assignment.is_immutable:
        raise HTTPException(status_code=400, detail="Cannot delete immutable user role assignment")

    await db.delete(db_assignment)
    await db.commit()
    return {"detail": "User role assignment deleted successfully"}
