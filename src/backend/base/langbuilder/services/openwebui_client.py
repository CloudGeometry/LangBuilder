"""OpenWebUI API Client

This module provides a client for interacting with OpenWebUI's REST API,
specifically for deploying Pipe functions and managing models.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OpenWebUIClient:
    """Client for interacting with OpenWebUI API."""

    def __init__(self, base_url: str, api_key: str, timeout: int = 30):
        """Initialize OpenWebUI client.

        Args:
            base_url: Base URL of OpenWebUI instance (e.g., "http://localhost:5839")
            api_key: OpenWebUI API key (starts with "sk-")
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def check_function_exists(self, function_id: str) -> bool:
        """Check if a function exists in OpenWebUI.

        Args:
            function_id: The function ID to check

        Returns:
            True if function exists, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/functions/id/{function_id}",
                    headers=self._headers,
                )
                return response.status_code == 200
        except httpx.HTTPStatusError:
            return False
        except Exception as e:
            logger.error(f"Error checking function existence: {e}")
            return False

    async def deploy_function(
        self, function_id: str, function_code: str, function_meta: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Deploy or update a function in OpenWebUI.

        Args:
            function_id: Unique identifier for the function
            function_code: Python code for the function
            function_meta: Optional metadata (name, description, etc.)

        Returns:
            Response from OpenWebUI API

        Raises:
            httpx.HTTPStatusError: If the API request fails
        """
        meta = function_meta or {}
        payload = {
            "id": function_id,
            "content": function_code,
            "meta": meta,
        }

        # Add required fields for update endpoint
        if "name" in meta:
            payload["name"] = meta["name"]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Check if function exists
            exists = await self.check_function_exists(function_id)

            if exists:
                # Update existing function
                response = await client.post(
                    f"{self.base_url}/api/v1/functions/id/{function_id}/update",
                    headers=self._headers,
                    json=payload,
                )
            else:
                # Create new function
                response = await client.post(
                    f"{self.base_url}/api/v1/functions/create",
                    headers=self._headers,
                    json=payload,
                )

            response.raise_for_status()
            return response.json()

    async def create_model(
        self,
        model_id: str,
        model_name: str,
        model_params: dict[str, Any],
        model_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a model entry in OpenWebUI.

        Args:
            model_id: Unique identifier for the model
            model_name: Display name for the model
            model_params: Parameters to pass to the model (e.g., flow_id)
            model_meta: Optional metadata (description, icon, etc.)

        Returns:
            Response from OpenWebUI API

        Raises:
            httpx.HTTPStatusError: If the API request fails
        """
        payload = {
            "id": model_id,
            "name": model_name,
            "params": model_params,
            "meta": model_meta or {},
            "base_model_id": None,
            "is_active": True,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/models/create",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def update_model(
        self,
        model_id: str,
        model_name: str | None = None,
        model_params: dict[str, Any] | None = None,
        model_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update an existing model in OpenWebUI by deleting and recreating it.

        OpenWebUI doesn't have a native update endpoint, so we delete and recreate.

        Args:
            model_id: Identifier of the model to update
            model_name: New display name (optional)
            model_params: New parameters (optional)
            model_meta: New metadata (optional)

        Returns:
            Response from OpenWebUI API

        Raises:
            httpx.HTTPStatusError: If the API request fails
        """
        # Delete the existing model
        await self.delete_model(model_id)

        # Recreate with new parameters
        payload = {"id": model_id}

        if model_name is not None:
            payload["name"] = model_name
        if model_params is not None:
            payload["params"] = model_params
        if model_meta is not None:
            payload["meta"] = model_meta

        # Need to include required fields for creation
        if "name" not in payload:
            payload["name"] = model_id
        if "params" not in payload:
            payload["params"] = {}
        if "meta" not in payload:
            payload["meta"] = {}

        payload["base_model_id"] = None
        payload["is_active"] = True

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/models/create",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def delete_model(self, model_id: str) -> bool:
        """Delete a model from OpenWebUI.

        Args:
            model_id: Identifier of the model to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}/api/v1/models/model/delete",
                    headers=self._headers,
                    params={"id": model_id},
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Error deleting model: {e}")
            return False

    async def get_model(self, model_id: str) -> dict[str, Any] | None:
        """Get model details from OpenWebUI.

        Args:
            model_id: Identifier of the model

        Returns:
            Model data if found, None otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/models/model",
                    headers=self._headers,
                    params={"id": model_id},
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.error(f"Error getting model: {e}")
            return None

    async def test_connection(self) -> bool:
        """Test if connection to OpenWebUI is working.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    headers=self._headers,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
