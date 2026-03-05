"""
HubSpot Contact Updater - LangBuilder Custom Component

Updates contact properties in HubSpot CRM API v3.
Used to set custom properties like 'last_generated_report' URL
to trigger email workflows.

Author: CloudGeometry
Project: Carter's Agents - Content Engine
"""

from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output
from langflow.schema import Data
import httpx
import json


class HubSpotContactUpdater(Component):
    """
    Updates contact properties in HubSpot CRM.

    This component is used by the Content Engine agent to update
    contact records after generating assets - typically setting
    a custom property like 'last_generated_report' that triggers
    a HubSpot workflow to send an email.
    """

    display_name = "HubSpot Contact Updater"
    description = "Updates contact properties in HubSpot CRM"
    icon = "edit"
    name = "HubSpotContactUpdater"

    inputs = [
        SecretStrInput(
            name="hubspot_api_key",
            display_name="HubSpot API Key",
            required=True,
            info="HubSpot Private App API key with crm.objects.contacts.write scope"
        ),
        StrInput(
            name="contact_id",
            display_name="Contact ID",
            required=True,
            info="HubSpot contact ID to update"
        ),
        StrInput(
            name="properties_json",
            display_name="Properties (JSON)",
            required=True,
            info='JSON object of properties to update. Example: {"last_generated_report": "https://..."}'
        ),
    ]

    outputs = [
        Output(
            name="result",
            display_name="Update Result",
            method="update_contact",
        ),
    ]

    async def update_contact(self) -> Data:
        """
        Update contact properties in HubSpot CRM API.

        Returns:
            Data object with success status and updated properties
        """
        # Parse properties JSON
        try:
            properties = json.loads(self.properties_json)
            if not isinstance(properties, dict):
                raise ValueError("Properties must be a JSON object")
        except json.JSONDecodeError as e:
            self.status = "❌ Invalid JSON"
            return Data(data={
                "success": False,
                "error": f"Invalid JSON: {str(e)}"
            })
        except ValueError as e:
            self.status = "❌ Invalid properties"
            return Data(data={
                "success": False,
                "error": str(e)
            })

        if not properties:
            self.status = "❌ No properties provided"
            return Data(data={
                "success": False,
                "error": "No properties to update"
            })

        # Build URL
        url = f"https://api.hubapi.com/crm/v3/objects/contacts/{self.contact_id}"

        # Build request payload
        payload = {
            "properties": properties
        }

        headers = {
            "Authorization": f"Bearer {self.hubspot_api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.patch(url, headers=headers, json=payload)

                if response.status_code == 200:
                    result = response.json()

                    # Extract updated properties from response
                    updated_props = result.get("properties", {})

                    self.status = f"✅ Updated {len(properties)} properties"

                    return Data(data={
                        "success": True,
                        "contact_id": self.contact_id,
                        "properties_updated": list(properties.keys()),
                        "updated_values": {k: updated_props.get(k) for k in properties.keys()},
                    })

                elif response.status_code == 404:
                    self.status = "❌ Contact not found"
                    return Data(data={
                        "success": False,
                        "error": f"Contact {self.contact_id} not found",
                        "status_code": 404
                    })

                elif response.status_code == 400:
                    # Often means invalid property name
                    error_text = response.text
                    self.status = "❌ Invalid property"
                    return Data(data={
                        "success": False,
                        "error": f"Bad request (check property names): {error_text}",
                        "status_code": 400
                    })

                else:
                    error_text = response.text
                    self.status = f"❌ Error: {response.status_code}"
                    return Data(data={
                        "success": False,
                        "error": error_text,
                        "status_code": response.status_code
                    })

        except httpx.TimeoutException:
            self.status = "❌ Request timeout"
            return Data(data={
                "success": False,
                "error": "Request timed out after 15 seconds"
            })

        except Exception as e:
            self.status = f"❌ Error: {str(e)[:50]}"
            return Data(data={
                "success": False,
                "error": str(e)
            })
