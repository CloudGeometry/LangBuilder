from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from langbuilder.services.database.models.role_permission.model import (
    RolePermission,
    RolePermissionCreate,
    RolePermissionUpdate,
)


async def create_role_permission(db: AsyncSession, role_permission: RolePermissionCreate) -> RolePermission:
    """Create a new role-permission association."""
    db_role_permission = RolePermission.model_validate(role_permission)
    db.add(db_role_permission)
    try:
        await db.commit()
        await db.refresh(db_role_permission)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Role-permission association already exists") from e
    else:
        return db_role_permission


async def get_role_permission_by_id(db: AsyncSession, role_permission_id: UUID) -> RolePermission | None:
    """Get a role-permission by ID."""
    if isinstance(role_permission_id, str):
        role_permission_id = UUID(role_permission_id)
    stmt = select(RolePermission).where(RolePermission.id == role_permission_id)
    result = await db.exec(stmt)
    return result.first()


async def get_role_permission(db: AsyncSession, role_id: UUID, permission_id: UUID) -> RolePermission | None:
    """Get a role-permission by role_id and permission_id."""
    stmt = select(RolePermission).where(
        RolePermission.role_id == role_id, RolePermission.permission_id == permission_id
    )
    result = await db.exec(stmt)
    return result.first()


async def list_role_permissions(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[RolePermission]:
    """List all role-permissions with pagination."""
    stmt = select(RolePermission).offset(skip).limit(limit)
    result = await db.exec(stmt)
    return list(result.all())


async def list_permissions_by_role(db: AsyncSession, role_id: UUID) -> list[RolePermission]:
    """List all permissions for a specific role."""
    stmt = select(RolePermission).where(RolePermission.role_id == role_id)
    result = await db.exec(stmt)
    return list(result.all())


async def list_roles_by_permission(db: AsyncSession, permission_id: UUID) -> list[RolePermission]:
    """List all roles that have a specific permission."""
    stmt = select(RolePermission).where(RolePermission.permission_id == permission_id)
    result = await db.exec(stmt)
    return list(result.all())


async def update_role_permission(
    db: AsyncSession, role_permission_id: UUID, role_permission_update: RolePermissionUpdate
) -> RolePermission:
    """Update a role-permission."""
    db_role_permission = await get_role_permission_by_id(db, role_permission_id)
    if not db_role_permission:
        raise HTTPException(status_code=404, detail="Role-permission not found")

    role_permission_data = role_permission_update.model_dump(exclude_unset=True)
    for key, value in role_permission_data.items():
        setattr(db_role_permission, key, value)

    try:
        await db.commit()
        await db.refresh(db_role_permission)
        return db_role_permission
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


async def delete_role_permission(db: AsyncSession, role_permission_id: UUID) -> dict:
    """Delete a role-permission."""
    db_role_permission = await get_role_permission_by_id(db, role_permission_id)
    if not db_role_permission:
        raise HTTPException(status_code=404, detail="Role-permission not found")

    await db.delete(db_role_permission)
    await db.commit()
    return {"detail": "Role-permission deleted successfully"}


async def delete_role_permission_by_ids(db: AsyncSession, role_id: UUID, permission_id: UUID) -> dict:
    """Delete a role-permission by role_id and permission_id."""
    db_role_permission = await get_role_permission(db, role_id, permission_id)
    if not db_role_permission:
        raise HTTPException(status_code=404, detail="Role-permission not found")

    await db.delete(db_role_permission)
    await db.commit()
    return {"detail": "Role-permission deleted successfully"}
