"""
HubSpot Property Update - LangBuilder Custom Component

Updates contact properties in HubSpot CRM.
Used in ICP Validator TRUE path to set "verified_buyer" property.

Author: CloudGeometry
Project: Carter's Agents - ICP Validator
"""

from lfx.custom import Component
from lfx.io import HandleInput, SecretStrInput, StrInput, Output
from lfx.schema import Data
# ValueError not used
from loguru import logger
import httpx
import json


class HubSpotPropertyUpdateComponent(Component):
    """
    Update contact properties in HubSpot CRM.

    This component updates one or more properties on an existing contact.
    Used in ICP Validator to set the "verified_buyer" flag.

    API: PATCH /crm/v3/objects/contacts/{id}
    Required scope: crm.objects.contacts.write
    """

    display_name = "HubSpot Property Update"
    description = "Updates contact properties in HubSpot CRM"
    icon = "edit"
    name = "HubSpotPropertyUpdate"

    inputs = [
        HandleInput(
            name="contact_input",
            display_name="Contact Input",
            input_types=["Data", "Message"],
            required=True,
            info="Input containing contact_id to update",
        ),
        HandleInput(
            name="properties_input",
            display_name="Properties Input",
            input_types=["Data"],
            required=False,
            info="Data object containing properties to update (alternative to static properties)",
        ),
        SecretStrInput(
            name="hubspot_api_key",
            display_name="HubSpot API Key",
            required=True,
            info="HubSpot Private App API key with crm.objects.contacts.write scope",
        ),
        StrInput(
            name="static_properties",
            display_name="Static Properties",
            required=False,
            value='{"verified_buyer": "true"}',
            info="JSON object of properties to set (used if Properties Input not connected)",
        ),
        StrInput(
            name="base_url",
            display_name="Base URL",
            required=False,
            value="https://api.hubapi.com",
            advanced=True,
            info="HubSpot API base URL",
        ),
    ]

    outputs = [
        Output(
            name="result",
            display_name="Result",
            method="update_properties",
        ),
    ]

    def _extract_contact_id(self) -> str:
        """Extract contact_id from the input data."""
        input_data = self.contact_input

        # Handle Data object
        if hasattr(input_data, "data"):
            data = input_data.data
            if isinstance(data, dict):
                # Try different possible keys
                for key in ["contact_id", "contactId", "id", "hs_object_id"]:
                    if key in data:
                        return str(data[key])
                # Check nested contact object
                if "contact" in data and isinstance(data["contact"], dict):
                    contact = data["contact"]
                    for key in ["id", "contact_id", "hs_object_id"]:
                        if key in contact:
                            return str(contact[key])

        # Handle string (direct contact_id)
        if isinstance(input_data, str):
            return input_data

        # Handle Message object
        if hasattr(input_data, "text"):
            return str(input_data.text).strip()

        raise ValueError(
            "Could not extract contact_id from input. "
            "Expected Data with 'contact_id' or 'id' field."
        )

    def _get_properties(self) -> dict:
        """Get properties to update from input or static config."""
        # First, try properties_input if connected
        if self.properties_input:
            props_data = self.properties_input
            if hasattr(props_data, "data"):
                data = props_data.data
                if isinstance(data, dict):
                    # Look for a 'properties' key or use the whole dict
                    return data.get("properties", data)

        # Fall back to static_properties
        if self.static_properties:
            try:
                return json.loads(self.static_properties)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in static_properties: {e}")

        raise ValueError("No properties to update - provide properties_input or static_properties")

    async def update_properties(self) -> Data:
        """
        Update contact properties in HubSpot.

        Returns:
            Data object with:
            - success: Boolean indicating if update succeeded
            - contact_id: Updated contact ID
            - properties_updated: List of property names updated
            - hubspot_url: Link to contact in HubSpot
        """
        if not self.hubspot_api_key:
            raise ValueError("HubSpot API key is required")

        contact_id = self._extract_contact_id()
        properties = self._get_properties()

        if not properties:
            raise ValueError("No properties provided to update")

        base_url = self.base_url or "https://api.hubapi.com"
        url = f"{base_url}/crm/v3/objects/contacts/{contact_id}"

        headers = {
            "Authorization": f"Bearer {self.hubspot_api_key}",
            "Content-Type": "application/json",
        }

        payload = {"properties": properties}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=payload)

                if response.status_code == 200:
                    result = response.json()

                    # Build HubSpot URL
                    hubspot_url = f"https://app.hubspot.com/contacts/contacts/{contact_id}"

                    props_list = list(properties.keys())
                    self.status = f"Updated: {', '.join(props_list)}"

                    logger.info(f"HubSpot contact {contact_id} updated with properties: {props_list}")

                    return Data(
                        data={
                            "success": True,
                            "contact_id": contact_id,
                            "properties_updated": props_list,
                            "hubspot_url": hubspot_url,
                        }
                    )

                elif response.status_code == 404:
                    self.status = "Contact not found"
                    raise ValueError(f"Contact {contact_id} not found in HubSpot")

                elif response.status_code == 401:
                    self.status = "Authentication failed"
                    raise ValueError("HubSpot authentication failed - check API key")

                elif response.status_code == 403:
                    self.status = "Permission denied"
                    raise ValueError(
                        "HubSpot permission denied - ensure crm.objects.contacts.write scope"
                    )

                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", response.text)
                    except Exception:
                        error_msg = response.text

                    self.status = f"Error: {response.status_code}"
                    raise ValueError(
                        f"HubSpot property update failed ({response.status_code}): {error_msg}"
                    )

        except ValueError:
            raise
        except Exception as e:
            logger.opt(exception=True).error("HubSpot property update failed")
            self.status = f"Error: {str(e)}"
            raise ValueError(f"HubSpot property update failed: {str(e)}") from e
