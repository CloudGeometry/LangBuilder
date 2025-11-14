"""OpenWebUI Publish API.

This module provides endpoints for publishing LangBuilder flows to OpenWebUI.
Users can one-click publish flows which automatically deploys the Pipe function
and creates model entries in OpenWebUI.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import select

from datetime import datetime, timezone

from langbuilder.api.utils import CurrentActiveUser, DbSession
from langbuilder.logging import logger
from langbuilder.services.database.models.flow.model import Flow
from langbuilder.services.database.models.publish_record import (
    PublishRecord,
    PublishRecordCreate,
    PublishRecordRead,
    PublishStatusEnum,
)
from langbuilder.services.openwebui_client import OpenWebUIClient

# Build router
router = APIRouter(prefix="/publish", tags=["Publish"])


# Pydantic schemas
class PublishToOpenWebUIRequest(BaseModel):
    """Request schema for publishing a flow to OpenWebUI."""

    flow_id: UUID = Field(..., description="UUID of the flow to publish")
    openwebui_url: str = Field(..., description="Base URL of OpenWebUI instance (e.g., http://localhost:5839)")
    openwebui_api_key: str = Field(..., description="OpenWebUI API key (starts with 'sk-')")
    model_name: str | None = Field(None, description="Custom model name to display in OpenWebUI (defaults to flow name)")
    model_config = {"json_schema_extra": {"example": {
        "flow_id": "3a5bbb51-d819-4a17-8af5-3e562e1fce54",
        "openwebui_url": "http://localhost:5839",
        "openwebui_api_key": "sk-...",
        "model_name": "My Custom Model Name",
    }}}


class PublishToOpenWebUIResponse(BaseModel):
    """Response schema for publish operation."""

    success: bool = Field(..., description="Whether publish was successful")
    model_id: str = Field(..., description="ID of the created/updated model in OpenWebUI")
    model_name: str = Field(..., description="Display name of the model")
    openwebui_url: str = Field(..., description="URL to access OpenWebUI")
    pipe_function_deployed: bool = Field(..., description="Whether Pipe function was deployed")
    message: str = Field(..., description="Human-readable status message")


# Pipe function template that will be deployed to OpenWebUI
LANGBUILDER_PIPE_FUNCTION_CODE = '''"""
title: LangBuilder Flow Pipe
description: Execute LangBuilder flows from OpenWebUI
author: LangBuilder Team
version: 1.0.8
requirements: httpx
"""

from typing import Union, Generator, Iterator, Any
from pydantic import BaseModel, Field
import httpx


class Pipe:
    class Valves(BaseModel):
        LANGBUILDER_URL: str = Field(
            default="http://host.docker.internal:8765",
            description="LangBuilder backend URL"
        )
        LANGBUILDER_API_KEY: str = Field(
            default="",
            description="API key for authentication (optional)"
        )
        REQUEST_TIMEOUT: int = Field(
            default=120,
            description="Request timeout in seconds"
        )

    def __init__(self):
        self.type = "manifold"
        self.name = ""  # Empty name to avoid prefix in model names
        self.valves = self.Valves()
        # Initialize with published flows
        self.pipelines = self.get_langbuilder_flows()

    def get_langbuilder_flows(self):
        """Fetch published flows from LangBuilder backend."""
        try:
            langbuilder_url = self.valves.LANGBUILDER_URL.strip() if self.valves.LANGBUILDER_URL else ""

            if not langbuilder_url or not langbuilder_url.startswith(("http://", "https://")):
                return [{"id": "error", "name": "Configure LANGBUILDER_URL in Function Settings"}]

            # Fetch published flows from LangBuilder
            url = f"{langbuilder_url.rstrip('/')}/api/v1/publish/flows"
            headers = {}
            if self.valves.LANGBUILDER_API_KEY:
                headers["x-api-key"] = self.valves.LANGBUILDER_API_KEY

            with httpx.Client(timeout=10) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                flows = response.json()

                # Convert flows to OpenWebUI model format
                return [
                    {
                        "id": str(flow["id"]),
                        "name": flow["name"],
                        "description": flow.get("description", "")
                    }
                    for flow in flows
                ]
        except Exception as e:
            return [{"id": "error", "name": f"Error loading flows: {str(e)}"}]

    def pipes(self):
        """Return list of available LangBuilder flows as selectable models."""
        return self.get_langbuilder_flows()

    async def pipe(self, body: dict, __user__: dict = None, __model__: dict = None):
        # Extract model ID from body
        model_id = body.get("model", "")

        # Extract flow ID (after last dot if prefixed)
        if "." in model_id:
            flow_id = model_id[model_id.rfind(".") + 1:]
        else:
            flow_id = model_id

        if not flow_id:
            return "Error: Flow ID not found in request"

        # Get LangBuilder URL from valves
        langbuilder_url = self.valves.LANGBUILDER_URL.strip() if self.valves.LANGBUILDER_URL else ""

        if not langbuilder_url:
            return "Error: LANGBUILDER_URL is not configured. Please set it in Function Settings."

        if not langbuilder_url.startswith(("http://", "https://")):
            return f"Error: LANGBUILDER_URL must start with http:// or https://. Current value: '{langbuilder_url}'"

        # Prepare LangBuilder request
        url = f"{langbuilder_url.rstrip('/')}/api/v1/run/{flow_id}"

        headers = {"Content-Type": "application/json"}
        if self.valves.LANGBUILDER_API_KEY:
            headers["x-api-key"] = self.valves.LANGBUILDER_API_KEY

        # Get last user message
        messages = body.get("messages", [])
        user_messages = [m for m in messages if m.get("role") == "user"]
        last_message = user_messages[-1]["content"] if user_messages else ""

        payload = {
            "input_value": last_message,
            "stream": body.get("stream", False),
            "tweaks": {}
        }

        try:
            async with httpx.AsyncClient(timeout=self.valves.REQUEST_TIMEOUT) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                result = response.json()

                # Extract output from LangBuilder's nested response structure
                if isinstance(result, dict):
                    try:
                        outputs = result.get("outputs", [])
                        if outputs and len(outputs) > 0:
                            nested_outputs = outputs[0].get("outputs", [])
                            if nested_outputs and len(nested_outputs) > 0:
                                results = nested_outputs[0].get("results", {})
                                message = results.get("message", {})
                                output = message.get("text", str(result))
                            else:
                                output = str(result)
                        else:
                            output = str(result)
                    except (KeyError, IndexError, TypeError):
                        output = str(result)
                else:
                    output = str(result)

                return output

        except httpx.TimeoutException:
            return f"Error: Request timed out after {self.valves.REQUEST_TIMEOUT}s"
        except httpx.HTTPStatusError as e:
            return f"Error: LangBuilder returned {e.response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"
'''


PIPE_FUNCTION_ID = "langbuilder_flow_execution_pipe"
PIPE_FUNCTION_META = {
    "name": "LangBuilder Flow Execution Pipe",
    "description": "Executes LangBuilder flows as selectable models in OpenWebUI",
    "author": "LangBuilder Team",
    "version": "1.0.8",
}


@router.get("/flows")
async def get_published_flows(
    session: DbSession,
) -> list[dict]:
    """Get all active published flows.

    This endpoint is called by the OpenWebUI Pipe function to dynamically
    fetch the list of available LangBuilder flows.

    Args:
        session: Database session

    Returns:
        List of published flow metadata (id, name, description)
    """
    try:
        # Get all active publish records with ACTIVE status
        result = await session.exec(
            select(PublishRecord)
            .where(PublishRecord.platform == "openwebui")
            .where(PublishRecord.status == PublishStatusEnum.ACTIVE)
        )
        records = result.all()

        # Get unique flow IDs
        flow_ids = list(set(record.flow_id for record in records))

        if not flow_ids:
            return []

        # Fetch flow details
        flows_result = await session.exec(select(Flow).where(Flow.id.in_(flow_ids)))
        flows = flows_result.all()

        # Return flow metadata
        return [
            {
                "id": str(flow.id),
                "name": flow.name,
                "description": flow.description or f"LangBuilder flow: {flow.name}",
            }
            for flow in flows
        ]

    except Exception as e:
        logger.exception(f"Failed to get published flows: {e}")
        return []


@router.post("/openwebui", response_model=PublishToOpenWebUIResponse)
async def publish_to_openwebui(
    request: PublishToOpenWebUIRequest,
    current_user: CurrentActiveUser,
    session: DbSession,
) -> PublishToOpenWebUIResponse:
    """Publish a LangBuilder flow to OpenWebUI.

    This endpoint automates the entire publish process:
    1. Fetches the flow from the database
    2. Checks if the Pipe function exists in OpenWebUI
    3. Deploys/updates the Pipe function
    4. Creates a publish record in the database
    5. The Pipe function dynamically loads flows via /api/v1/publish/flows

    Args:
        request: Publish request with flow_id, OpenWebUI URL, and API key
        current_user: Current authenticated user
        session: Database session

    Returns:
        PublishToOpenWebUIResponse with success status and model details

    Raises:
        HTTPException: If flow not found, OpenWebUI connection fails, or publish fails
    """
    try:
        # 1. Fetch the flow from database
        result = await session.exec(
            select(Flow).where(Flow.id == request.flow_id).where(Flow.user_id == current_user.id)
        )
        flow = result.first()

        if not flow:
            msg = f"Flow {request.flow_id} not found or access denied"
            raise HTTPException(status_code=404, detail=msg)

        logger.info(f"Publishing flow '{flow.name}' ({flow.id}) to OpenWebUI at {request.openwebui_url}")

        # 2. Initialize OpenWebUI client
        client = OpenWebUIClient(
            base_url=request.openwebui_url,
            api_key=request.openwebui_api_key,
            timeout=30,
        )

        # 3. Test connection to OpenWebUI
        if not await client.test_connection():
            msg = (
                f"Failed to connect to OpenWebUI at {request.openwebui_url}. "
                "Please check the URL and ensure OpenWebUI is running."
            )
            raise HTTPException(status_code=503, detail=msg)

        # 4. Deploy/update Pipe function (always update to ensure latest version)
        pipe_exists = await client.check_function_exists(PIPE_FUNCTION_ID)

        logger.info(f"Deploying/updating Pipe function '{PIPE_FUNCTION_ID}' to OpenWebUI")
        await client.deploy_function(
            function_id=PIPE_FUNCTION_ID,
            function_code=LANGBUILDER_PIPE_FUNCTION_CODE,
            function_meta=PIPE_FUNCTION_META,
        )
        pipe_deployed = not pipe_exists  # True if this was first deployment
        logger.info("Pipe function deployed/updated successfully")

        # 5. Model will appear automatically via pipes() method
        model_id = str(flow.id)  # Just the flow UUID
        model_name = request.model_name or flow.name

        # 6. Create or update publish record in database
        # Check if a record already exists
        result = await session.exec(
            select(PublishRecord).where(
                PublishRecord.flow_id == flow.id,
                PublishRecord.platform == "openwebui",
                PublishRecord.platform_url == request.openwebui_url,
            )
        )
        publish_record = result.first()

        if publish_record:
            # Update existing record
            publish_record.status = PublishStatusEnum.ACTIVE
            publish_record.last_sync_at = datetime.now(timezone.utc)
            publish_record.error_message = None
            publish_record.metadata_ = {
                "model_name": model_name,
                "pipe_function_version": PIPE_FUNCTION_META["version"],
            }
            message = f"Flow '{model_name}' updated successfully in OpenWebUI"
        else:
            # Create new record
            publish_record = PublishRecord(
                flow_id=flow.id,
                platform="openwebui",
                platform_url=request.openwebui_url,
                external_id=model_id,
                published_by=current_user.id,
                status=PublishStatusEnum.ACTIVE,
                metadata_={
                    "model_name": model_name,
                    "pipe_function_version": PIPE_FUNCTION_META["version"],
                },
            )
            session.add(publish_record)
            message = f"Flow '{model_name}' published successfully to OpenWebUI"

        await session.commit()
        logger.info(f"Saved publish record for flow {flow.id} - {message}")

        return PublishToOpenWebUIResponse(
            success=True,
            model_id=model_id,
            model_name=model_name,
            openwebui_url=request.openwebui_url,
            pipe_function_deployed=pipe_deployed,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to publish flow to OpenWebUI: {e}")
        msg = f"Failed to publish flow: {e!s}"
        raise HTTPException(status_code=500, detail=msg) from e


class UnpublishRequest(BaseModel):
    """Request schema for unpublishing a flow."""

    flow_id: UUID = Field(..., description="UUID of the flow to unpublish")
    openwebui_url: str = Field(..., description="OpenWebUI instance URL")
    openwebui_api_key: str = Field(..., description="OpenWebUI API key")


class UnpublishResponse(BaseModel):
    """Response schema for unpublish operation."""

    success: bool
    message: str
    flow_id: str
    platform_url: str


@router.delete("/openwebui", response_model=UnpublishResponse)
async def unpublish_from_openwebui(
    request: UnpublishRequest,
    current_user: CurrentActiveUser,
    session: DbSession,
) -> UnpublishResponse:
    """Unpublish a flow from OpenWebUI.

    This removes the model from OpenWebUI and marks the publish record as unpublished.

    Args:
        request: Unpublish request with flow_id and OpenWebUI details
        current_user: Current authenticated user
        session: Database session

    Returns:
        UnpublishResponse with success status

    Raises:
        HTTPException: If flow not found or unpublish fails
    """
    try:
        # 1. Find the publish record
        result = await session.exec(
            select(PublishRecord).where(
                PublishRecord.flow_id == request.flow_id,
                PublishRecord.platform == "openwebui",
                PublishRecord.platform_url == request.openwebui_url,
                PublishRecord.status == PublishStatusEnum.ACTIVE,
            )
        )
        publish_record = result.first()

        if not publish_record:
            msg = f"No active publication found for flow {request.flow_id} at {request.openwebui_url}"
            raise HTTPException(status_code=404, detail=msg)

        logger.info(f"Unpublishing flow {request.flow_id} from OpenWebUI at {request.openwebui_url}")

        # 2. Initialize OpenWebUI client
        client = OpenWebUIClient(
            base_url=request.openwebui_url,
            api_key=request.openwebui_api_key,
            timeout=30,
        )

        # 3. Delete the model from OpenWebUI
        model_id = publish_record.external_id
        delete_success = await client.delete_model(model_id)

        if not delete_success:
            logger.warning(f"Failed to delete model {model_id} from OpenWebUI, but continuing...")

        # 4. Update publish record status
        publish_record.status = PublishStatusEnum.UNPUBLISHED
        publish_record.last_sync_at = datetime.now(timezone.utc)
        await session.commit()

        logger.info(f"Successfully unpublished flow {request.flow_id}")

        return UnpublishResponse(
            success=True,
            message=f"Flow unpublished successfully from OpenWebUI",
            flow_id=str(request.flow_id),
            platform_url=request.openwebui_url,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to unpublish flow: {e}")
        msg = f"Failed to unpublish flow: {e!s}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.get("/status/{flow_id}", response_model=list[PublishRecordRead])
async def get_publish_status(
    flow_id: UUID,
    current_user: CurrentActiveUser,
    session: DbSession,
) -> list[PublishRecordRead]:
    """Get publish status for a flow.

    Returns all active publications for the specified flow.

    Args:
        flow_id: UUID of the flow
        current_user: Current authenticated user
        session: Database session

    Returns:
        List of publish records for the flow

    Raises:
        HTTPException: If flow not found
    """
    try:
        # Verify flow exists and user has access
        flow_result = await session.exec(
            select(Flow).where(Flow.id == flow_id).where(Flow.user_id == current_user.id)
        )
        flow = flow_result.first()

        if not flow:
            msg = f"Flow {flow_id} not found or access denied"
            raise HTTPException(status_code=404, detail=msg)

        # Get all active publish records for this flow
        result = await session.exec(
            select(PublishRecord).where(
                PublishRecord.flow_id == flow_id,
                PublishRecord.status == PublishStatusEnum.ACTIVE,
            )
        )
        records = result.all()

        # Convert to response models
        return [
            PublishRecordRead(
                id=record.id,
                flow_id=record.flow_id,
                platform=record.platform,
                platform_url=record.platform_url,
                external_id=record.external_id,
                published_at=record.published_at,
                published_by=record.published_by,
                status=record.status,
                metadata_=record.metadata_,
                last_sync_at=record.last_sync_at,
                error_message=record.error_message,
            )
            for record in records
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get publish status: {e}")
        msg = f"Failed to get publish status: {e!s}"
        raise HTTPException(status_code=500, detail=msg) from e
