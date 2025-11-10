import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

import orjson
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from fastapi_pagination import Params
from fastapi_pagination.ext.sqlmodel import apaginate
from sqlalchemy import update
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from langbuilder.api.utils import CurrentActiveUser, DbSession, cascade_delete_flow, custom_params, remove_api_keys
from langbuilder.api.v1.flows import create_flows
from langbuilder.api.v1.schemas import FlowListCreate
from langbuilder.helpers.flow import generate_unique_flow_name
from langbuilder.helpers.folders import generate_unique_folder_name
from langbuilder.initial_setup.constants import STARTER_FOLDER_NAME
from langbuilder.logging import logger
from langbuilder.services.database.models.flow.model import Flow, FlowCreate, FlowRead
from langbuilder.services.database.models.folder.constants import DEFAULT_FOLDER_NAME
from langbuilder.services.database.models.folder.model import (
    Folder,
    FolderCreate,
    FolderRead,
    FolderReadWithFlows,
    FolderUpdate,
)
from langbuilder.services.database.models.folder.pagination_model import FolderWithPaginatedFlows
from langbuilder.services.deps import get_rbac_service
from langbuilder.services.rbac.service import RBACService

router = APIRouter(prefix="/projects", tags=["Projects"])


async def _filter_projects_by_read_permission(
    projects: list[Folder],
    user_id: UUID,
    rbac_service: RBACService,
    session: AsyncSession,
) -> list[Folder]:
    """Filter projects to return only those the user has Read permission for.

    This function implements fine-grained RBAC filtering:
    1. Superusers and Global Admins bypass all checks (return all projects)
    2. For each project, check if user has Read permission at Project scope

    Args:
        projects: List of projects to filter
        user_id: The user's ID
        rbac_service: RBAC service for permission checks
        session: Database session

    Returns:
        List of projects the user has Read permission for
    """
    # Check if user is superuser or Global Admin (bypass filtering)
    from langbuilder.services.database.models.user.crud import get_user_by_id

    user = await get_user_by_id(session, user_id)
    if user and user.is_superuser:
        return projects

    if await rbac_service._has_global_admin_role(user_id, session):
        return projects

    # Filter projects by Read permission
    accessible_projects = []
    for project in projects:
        if await rbac_service.can_access(
            user_id=user_id,
            permission_name="Read",
            scope_type="Project",
            scope_id=project.id,
            db=session,
        ):
            accessible_projects.append(project)  # noqa: PERF401

    return accessible_projects


@router.post("/", response_model=FolderRead, status_code=201)
async def create_project(
    *,
    session: DbSession,
    project: FolderCreate,
    current_user: CurrentActiveUser,
    rbac_service: Annotated[RBACService, Depends(get_rbac_service)],
):
    """Create a new project with RBAC permission enforcement.

    This endpoint allows all authenticated users to create projects (Global permission per Story 1.5):
    1. User creates the project
    2. User is automatically assigned Owner role on the new Project
    3. Owner role assignment is mutable for new projects (unlike Starter Projects)

    Args:
        session: Database session
        project: Project creation data
        current_user: The current authenticated user
        rbac_service: RBAC service for permission checks

    Returns:
        FolderRead: The created project

    Raises:
        HTTPException: 400 if unique constraint violated
        HTTPException: 500 for other errors (including role assignment failures)
    """
    try:
        new_project = Folder.model_validate(project, from_attributes=True)
        new_project.user_id = current_user.id
        # First check if the project.name is unique
        # there might be flows with name like: "MyFlow", "MyFlow (1)", "MyFlow (2)"
        # so we need to check if the name is unique with `like` operator
        # if we find a flow with the same name, we add a number to the end of the name
        # based on the highest number found
        if (
            await session.exec(
                statement=select(Folder).where(Folder.name == new_project.name).where(Folder.user_id == current_user.id)
            )
        ).first():
            project_results = await session.exec(
                select(Folder).where(
                    Folder.name.like(f"{new_project.name}%"),  # type: ignore[attr-defined]
                    Folder.user_id == current_user.id,
                )
            )
            if project_results:
                project_names = [project.name for project in project_results]
                project_numbers = [int(name.split("(")[-1].split(")")[0]) for name in project_names if "(" in name]
                if project_numbers:
                    new_project.name = f"{new_project.name} ({max(project_numbers) + 1})"
                else:
                    new_project.name = f"{new_project.name} (1)"

        session.add(new_project)

        # Assign Owner role to creating user for this Project (before commit for atomicity)
        # Note: Starter Projects have immutable Owner assignments, but new projects do not
        try:
            await rbac_service.assign_role(
                user_id=current_user.id,
                role_name="Owner",
                scope_type="Project",
                scope_id=new_project.id,
                created_by=current_user.id,
                db=session,
                is_immutable=False,  # New projects have mutable Owner assignments
            )
        except Exception as role_error:
            # Log the specific error for debugging
            logger.error(f"Failed to assign Owner role for new project: {role_error}")
            # Re-raise to trigger rollback
            raise HTTPException(
                status_code=500,
                detail=f"Failed to assign owner role: {role_error!s}",
            ) from role_error

        # Commit both project and role assignment atomically
        await session.commit()
        await session.refresh(new_project)

        if project.components_list:
            update_statement_components = (
                update(Flow).where(Flow.id.in_(project.components_list)).values(folder_id=new_project.id)  # type: ignore[attr-defined]
            )
            await session.exec(update_statement_components)
            await session.commit()

        if project.flows_list:
            update_statement_flows = (
                update(Flow).where(Flow.id.in_(project.flows_list)).values(folder_id=new_project.id)  # type: ignore[attr-defined]
            )
            await session.exec(update_statement_flows)
            await session.commit()

    except HTTPException:
        # Re-raise HTTP exceptions (including role assignment failures)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return new_project


@router.get("/", response_model=list[FolderRead], status_code=200)
async def read_projects(
    *,
    session: DbSession,
    current_user: CurrentActiveUser,
    rbac_service: Annotated[RBACService, Depends(get_rbac_service)],
):
    """List all projects with RBAC permission filtering.

    This endpoint filters projects based on Read permission:
    1. Superusers and Global Admins see all projects
    2. Regular users see only projects they have Read permission on
    3. Starter Projects folder is excluded from the list

    Args:
        session: Database session
        current_user: The current authenticated user
        rbac_service: RBAC service for permission checks

    Returns:
        list[FolderRead]: List of projects the user has access to

    Raises:
        HTTPException: 500 for errors
    """
    try:
        # Query ALL projects (not just owned by current user) for RBAC filtering
        projects = (await session.exec(select(Folder))).all()

        # Filter by RBAC Read permission
        accessible_projects = await _filter_projects_by_read_permission(
            list(projects),
            current_user.id,
            rbac_service,
            session,
        )

        # Exclude Starter Projects folder
        accessible_projects = [project for project in accessible_projects if project.name != STARTER_FOLDER_NAME]

        return sorted(accessible_projects, key=lambda x: x.name != DEFAULT_FOLDER_NAME)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{project_id}", response_model=FolderWithPaginatedFlows | FolderReadWithFlows, status_code=200)
async def read_project(
    *,
    session: DbSession,
    project_id: UUID,
    current_user: CurrentActiveUser,
    params: Annotated[Params | None, Depends(custom_params)],
    rbac_service: Annotated[RBACService, Depends(get_rbac_service)],
    is_component: bool = False,
    is_flow: bool = False,
    search: str = "",
):
    """Get a project by ID with RBAC permission enforcement.

    This endpoint requires Read permission on the Project:
    1. Check if user has Read permission on the Project
    2. If permission denied, return 403 (prevents ID enumeration)
    3. Superusers and Global Admins bypass permission checks

    Args:
        session: Database session
        project_id: Project ID
        current_user: The current authenticated user
        params: Pagination parameters
        rbac_service: RBAC service for permission checks
        is_component: Filter for components
        is_flow: Filter for flows
        search: Search query

    Returns:
        FolderWithPaginatedFlows | FolderReadWithFlows: The project

    Raises:
        HTTPException: 403 if user lacks Read permission
        HTTPException: 404 if project not found (after permission check passes)
        HTTPException: 500 for other errors
    """
    # Check Read permission first (before checking if project exists - security best practice)
    has_permission = await rbac_service.can_access(
        user_id=current_user.id,
        permission_name="Read",
        scope_type="Project",
        scope_id=project_id,
        db=session,
    )

    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this project",
        )

    try:
        # Don't filter by user_id here - RBAC permission check already verified access
        project = (
            await session.exec(select(Folder).options(selectinload(Folder.flows)).where(Folder.id == project_id))
        ).first()
    except Exception as e:
        if "No result found" in str(e):
            raise HTTPException(status_code=404, detail="Project not found") from e
        raise HTTPException(status_code=500, detail=str(e)) from e

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        if params and params.page and params.size:
            stmt = select(Flow).where(Flow.folder_id == project_id)

            if Flow.updated_at is not None:
                stmt = stmt.order_by(Flow.updated_at.desc())  # type: ignore[attr-defined]
            if is_component:
                stmt = stmt.where(Flow.is_component == True)  # noqa: E712
            if is_flow:
                stmt = stmt.where(Flow.is_component == False)  # noqa: E712
            if search:
                stmt = stmt.where(Flow.name.like(f"%{search}%"))  # type: ignore[attr-defined]
            import warnings

            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore", category=DeprecationWarning, module=r"fastapi_pagination\.ext\.sqlalchemy"
                )
                paginated_flows = await apaginate(session, stmt, params=params)

            return FolderWithPaginatedFlows(folder=FolderRead.model_validate(project), flows=paginated_flows)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    # Don't filter flows by user_id - if user has Read permission on Project, they can see all flows
    # RBAC permission was already checked above
    return project


@router.patch("/{project_id}", response_model=FolderRead, status_code=200)
async def update_project(
    *,
    session: DbSession,
    project_id: UUID,
    project: FolderUpdate,  # Assuming FolderUpdate is a Pydantic model defining updatable fields
    current_user: CurrentActiveUser,
    rbac_service: Annotated[RBACService, Depends(get_rbac_service)],
):
    """Update a project with RBAC permission enforcement.

    This endpoint requires Update permission on the Project:
    1. Check if user has Update permission on the Project
    2. If permission denied, return 403
    3. Superusers and Global Admins bypass permission checks

    Args:
        session: Database session
        project_id: Project ID to update
        project: Project update data
        current_user: The current authenticated user
        rbac_service: RBAC service for permission checks

    Returns:
        FolderRead: The updated project

    Raises:
        HTTPException: 403 if user lacks Update permission
        HTTPException: 404 if project not found (after permission check passes)
        HTTPException: 500 for other errors
    """
    # Check Update permission first (before checking if project exists - security best practice)
    has_permission = await rbac_service.can_access(
        user_id=current_user.id,
        permission_name="Update",
        scope_type="Project",
        scope_id=project_id,
        db=session,
    )

    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to update this project",
        )

    try:
        # Don't filter by user_id here - RBAC permission check already verified access
        existing_project = (await session.exec(select(Folder).where(Folder.id == project_id))).first()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    if not existing_project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        # Apply updates from the input project to existing project
        update_data = project.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key not in {"components", "flows"} and value is not None:
                setattr(existing_project, key, value)

        session.add(existing_project)
        await session.commit()
        await session.refresh(existing_project)

        concat_project_components = project.components + project.flows

        flows_ids = (await session.exec(select(Flow.id).where(Flow.folder_id == existing_project.id))).all()

        excluded_flows = list(set(flows_ids) - set(concat_project_components))

        my_collection_project = (await session.exec(select(Folder).where(Folder.name == DEFAULT_FOLDER_NAME))).first()
        if my_collection_project:
            update_statement_my_collection = (
                update(Flow).where(Flow.id.in_(excluded_flows)).values(folder_id=my_collection_project.id)  # type: ignore[attr-defined]
            )
            await session.exec(update_statement_my_collection)
            await session.commit()

        if concat_project_components:
            update_statement_components = (
                update(Flow).where(Flow.id.in_(concat_project_components)).values(folder_id=existing_project.id)  # type: ignore[attr-defined]
            )
            await session.exec(update_statement_components)
            await session.commit()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return existing_project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    *,
    session: DbSession,
    project_id: UUID,
    current_user: CurrentActiveUser,
    rbac_service: Annotated[RBACService, Depends(get_rbac_service)],
):
    """Delete a project with RBAC permission enforcement and Starter Project protection.

    This endpoint requires Delete permission on the Project:
    1. Check if user has Delete permission on the Project
    2. If permission denied, return 403
    3. Check if this is a Starter Project - cannot be deleted (Story 1.4)
    4. Superusers and Global Admins bypass permission checks (but cannot delete Starter Projects)

    Args:
        session: Database session
        project_id: Project ID to delete
        current_user: The current authenticated user
        rbac_service: RBAC service for permission checks

    Returns:
        Response: 204 No Content on success

    Raises:
        HTTPException: 403 if user lacks Delete permission
        HTTPException: 400 if attempting to delete Starter Project
        HTTPException: 404 if project not found (after permission check passes)
        HTTPException: 500 for other errors
    """
    # Check Delete permission first (before checking if project exists - security best practice)
    has_permission = await rbac_service.can_access(
        user_id=current_user.id,
        permission_name="Delete",
        scope_type="Project",
        scope_id=project_id,
        db=session,
    )

    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete this project",
        )

    try:
        # Don't filter by user_id here - RBAC permission check already verified access
        project = (await session.exec(select(Folder).where(Folder.id == project_id))).first()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if this is a Starter Project (Story 1.4 - immutable)
    if project.is_starter_project:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete Starter Project. Starter Projects are protected and cannot be deleted.",
        )

    try:
        # Delete all flows in the project first (all flows, not just owned by current_user)
        flows = (await session.exec(select(Flow).where(Flow.folder_id == project_id))).all()
        if len(flows) > 0:
            for flow in flows:
                await cascade_delete_flow(session, flow.id)

        # Delete the project
        await session.delete(project)
        await session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/download/{project_id}", status_code=200)
async def download_file(
    *,
    session: DbSession,
    project_id: UUID,
    current_user: CurrentActiveUser,
):
    """Download all flows from project as a zip file."""
    try:
        query = select(Folder).where(Folder.id == project_id, Folder.user_id == current_user.id)
        result = await session.exec(query)
        project = result.first()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        flows_query = select(Flow).where(Flow.folder_id == project_id)
        flows_result = await session.exec(flows_query)
        flows = [FlowRead.model_validate(flow, from_attributes=True) for flow in flows_result.all()]

        if not flows:
            raise HTTPException(status_code=404, detail="No flows found in project")

        flows_without_api_keys = [remove_api_keys(flow.model_dump()) for flow in flows]
        zip_stream = io.BytesIO()

        with zipfile.ZipFile(zip_stream, "w") as zip_file:
            for flow in flows_without_api_keys:
                flow_json = json.dumps(jsonable_encoder(flow))
                zip_file.writestr(f"{flow['name']}.json", flow_json.encode("utf-8"))

        zip_stream.seek(0)

        current_time = datetime.now(tz=timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
        filename = f"{current_time}_{project.name}_flows.zip"

        # URL encode filename handle non-ASCII (ex. Cyrillic)
        encoded_filename = quote(filename)

        return StreamingResponse(
            zip_stream,
            media_type="application/x-zip-compressed",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
        )

    except Exception as e:
        if "No result found" in str(e):
            raise HTTPException(status_code=404, detail="Project not found") from e
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/upload/", response_model=list[FlowRead], status_code=201)
async def upload_file(
    *,
    session: DbSession,
    file: Annotated[UploadFile, File(...)],
    current_user: CurrentActiveUser,
):
    """Upload flows from a file."""
    contents = await file.read()
    data = orjson.loads(contents)

    if not data:
        raise HTTPException(status_code=400, detail="No flows found in the file")

    project_name = await generate_unique_folder_name(data["folder_name"], current_user.id, session)

    data["folder_name"] = project_name

    project = FolderCreate(name=data["folder_name"], description=data["folder_description"])

    new_project = Folder.model_validate(project, from_attributes=True)
    new_project.id = None
    new_project.user_id = current_user.id
    session.add(new_project)
    await session.commit()
    await session.refresh(new_project)

    del data["folder_name"]
    del data["folder_description"]

    if "flows" in data:
        flow_list = FlowListCreate(flows=[FlowCreate(**flow) for flow in data["flows"]])
    else:
        raise HTTPException(status_code=400, detail="No flows found in the data")
    # Now we set the user_id for all flows
    for flow in flow_list.flows:
        flow_name = await generate_unique_flow_name(flow.name, current_user.id, session)
        flow.name = flow_name
        flow.user_id = current_user.id
        flow.folder_id = new_project.id

    return await create_flows(session=session, flow_list=flow_list, current_user=current_user)
