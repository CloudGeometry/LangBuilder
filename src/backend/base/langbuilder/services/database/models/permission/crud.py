from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from langbuilder.services.database.models.permission.model import Permission, PermissionCreate, PermissionUpdate


async def create_permission(db: AsyncSession, permission: PermissionCreate) -> Permission:
    """Create a new permission."""
    db_permission = Permission.model_validate(permission)
    db.add(db_permission)
    try:
        await db.commit()
        await db.refresh(db_permission)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=400, detail=f"Permission '{permission.name}' with scope '{permission.scope}' already exists"
        ) from e
    else:
        return db_permission


async def get_permission_by_id(db: AsyncSession, permission_id: UUID) -> Permission | None:
    """Get a permission by ID."""
    if isinstance(permission_id, str):
        permission_id = UUID(permission_id)
    stmt = select(Permission).where(Permission.id == permission_id)
    result = await db.exec(stmt)
    return result.first()


async def get_permission_by_name_and_scope(db: AsyncSession, name: str, scope: str) -> Permission | None:
    """Get a permission by name and scope."""
    stmt = select(Permission).where(Permission.name == name, Permission.scope == scope)
    result = await db.exec(stmt)
    return result.first()


async def list_permissions(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Permission]:
    """List all permissions with pagination."""
    stmt = select(Permission).offset(skip).limit(limit)
    result = await db.exec(stmt)
    return list(result.all())


async def list_permissions_by_scope(db: AsyncSession, scope: str) -> list[Permission]:
    """List all permissions for a specific scope."""
    stmt = select(Permission).where(Permission.scope == scope)
    result = await db.exec(stmt)
    return list(result.all())


async def update_permission(db: AsyncSession, permission_id: UUID, permission_update: PermissionUpdate) -> Permission:
    """Update a permission."""
    db_permission = await get_permission_by_id(db, permission_id)
    if not db_permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    permission_data = permission_update.model_dump(exclude_unset=True)
    for key, value in permission_data.items():
        setattr(db_permission, key, value)

    try:
        await db.commit()
        await db.refresh(db_permission)
        return db_permission
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


async def delete_permission(db: AsyncSession, permission_id: UUID) -> dict:
    """Delete a permission."""
    db_permission = await get_permission_by_id(db, permission_id)
    if not db_permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    await db.delete(db_permission)
    await db.commit()
    return {"detail": "Permission deleted successfully"}
