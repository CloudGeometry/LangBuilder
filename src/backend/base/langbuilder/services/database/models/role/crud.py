from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from langbuilder.services.database.models.role.model import Role, RoleCreate, RoleUpdate


async def create_role(db: AsyncSession, role: RoleCreate) -> Role:
    """Create a new role."""
    db_role = Role.model_validate(role)
    db.add(db_role)
    try:
        await db.commit()
        await db.refresh(db_role)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Role with name '{role.name}' already exists") from e
    else:
        return db_role


async def get_role_by_id(db: AsyncSession, role_id: UUID) -> Role | None:
    """Get a role by ID."""
    if isinstance(role_id, str):
        role_id = UUID(role_id)
    stmt = select(Role).where(Role.id == role_id)
    result = await db.exec(stmt)
    return result.first()


async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    """Get a role by name."""
    stmt = select(Role).where(Role.name == name)
    result = await db.exec(stmt)
    return result.first()


async def list_roles(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Role]:
    """List all roles with pagination."""
    stmt = select(Role).offset(skip).limit(limit)
    result = await db.exec(stmt)
    return list(result.all())


async def update_role(db: AsyncSession, role_id: UUID, role_update: RoleUpdate) -> Role:
    """Update a role."""
    db_role = await get_role_by_id(db, role_id)
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")

    if db_role.is_system_role and role_update.is_system_role is False:
        raise HTTPException(status_code=400, detail="Cannot modify system role flag")

    role_data = role_update.model_dump(exclude_unset=True)
    for key, value in role_data.items():
        setattr(db_role, key, value)

    try:
        await db.commit()
        await db.refresh(db_role)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    else:
        return db_role


async def delete_role(db: AsyncSession, role_id: UUID) -> dict:
    """Delete a role."""
    db_role = await get_role_by_id(db, role_id)
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")

    if db_role.is_system_role:
        raise HTTPException(status_code=400, detail="Cannot delete system role")

    await db.delete(db_role)
    await db.commit()
    return {"detail": "Role deleted successfully"}
