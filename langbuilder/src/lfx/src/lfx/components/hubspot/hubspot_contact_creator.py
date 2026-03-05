"""
HubSpot Contact Creator - LangBuilder Custom Component

Creates new contacts in HubSpot CRM with company association.
Used in ICP Validator FALSE path to create new buyer contacts
discovered via Apollo search.

Author: CloudGeometry
Project: Carter's Agents - ICP Validator
"""

from langflow.custom import Component
from langflow.io import HandleInput, SecretStrInput, StrInput, Output
from langflow.schema import Data
# ValueError not used
from loguru import logger
import httpx


class HubSpotContactCreatorComponent(Component):
    """
    Create new contacts in HubSpot CRM with company association.

    This component creates a new contact from Apollo search results
    and associates it with an existing company.

    API Calls:
    - POST /crm/v3/objects/contacts (create contact with association)

    Required scope: crm.objects.contacts.write
    """

    display_name = "HubSpot Contact Creator"
    description = "Creates new contacts in HubSpot CRM from Apollo search results"
    icon = "user-plus"
    name = "HubSpotContactCreator"

    inputs = [
        HandleInput(
            name="contact_data",
            display_name="Contact Data",
            input_types=["Data"],
            required=True,
            info="Contact data from Apollo search (or any Data with contact fields)",
        ),
        HandleInput(
            name="company_input",
            display_name="Company Input",
            input_types=["Data"],
            required=False,
            info="Data containing company_id for association (optional)",
        ),
        SecretStrInput(
            name="hubspot_api_key",
            display_name="HubSpot API Key",
            required=True,
            info="HubSpot Private App API key with crm.objects.contacts.write scope",
        ),
        StrInput(
            name="static_company_id",
            display_name="Static Company ID",
            required=False,
            info="HubSpot company ID to associate (overrides input if provided)",
        ),
        StrInput(
            name="lead_source",
            display_name="Lead Source",
            value="Apollo - ICP Validator",
            required=False,
            info="Value for lead source property",
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
            method="create_contact",
        ),
    ]

    def _extract_contact_info(self) -> dict:
        """Extract contact information from input data."""
        input_data = self.contact_data
        contact_info = {}

        if hasattr(input_data, "data"):
            data = input_data.data
            if isinstance(data, dict):
                # Handle Apollo best_match format
                if "best_match" in data and data["best_match"]:
                    person = data["best_match"]
                else:
                    # Try direct person data or first in people list
                    person = data.get("person") or data
                    if "people" in data and data["people"]:
                        person = data["people"][0]

                # Extract fields with Apollo → HubSpot mapping
                contact_info = {
                    "firstname": person.get("first_name") or person.get("firstname", ""),
                    "lastname": person.get("last_name") or person.get("lastname", ""),
                    "email": person.get("email", ""),
                    "jobtitle": person.get("title") or person.get("jobtitle", ""),
                    "city": person.get("city", ""),
                    "state": person.get("state", ""),
                    "country": person.get("country", ""),
                }

                # Add LinkedIn if available
                linkedin = person.get("linkedin_url")
                if linkedin:
                    contact_info["hs_linkedin_url"] = linkedin

                # Add lead source
                if self.lead_source:
                    contact_info["leadsource"] = self.lead_source

        return contact_info

    def _extract_company_id(self) -> str | None:
        """Extract company ID for association."""
        # Static company ID takes precedence
        if self.static_company_id:
            return self.static_company_id

        # Try company_input
        if self.company_input:
            company_data = self.company_input
            if hasattr(company_data, "data"):
                data = company_data.data
                if isinstance(data, dict):
                    for key in ["company_id", "companyId", "id"]:
                        if key in data:
                            return str(data[key])
                    # Check nested company object
                    if "company" in data and isinstance(data["company"], dict):
                        company = data["company"]
                        for key in ["id", "company_id"]:
                            if key in company:
                                return str(company[key])

        return None

    async def create_contact(self) -> Data:
        """
        Create a new contact in HubSpot with company association.

        Returns:
            Data object with:
            - success: Boolean indicating if creation succeeded
            - contact_id: New contact's HubSpot ID
            - hubspot_url: Direct link to contact in HubSpot
            - properties: Properties set on the contact
            - company_id: Associated company ID (if any)
        """
        if not self.hubspot_api_key:
            raise ValueError("HubSpot API key is required")

        contact_info = self._extract_contact_info()
        company_id = self._extract_company_id()

        # Validate required fields
        if not contact_info.get("email") and not (
            contact_info.get("firstname") and contact_info.get("lastname")
        ):
            raise ValueError(
                "Contact requires either email or (firstname + lastname)"
            )

        base_url = self.base_url or "https://api.hubapi.com"
        url = f"{base_url}/crm/v3/objects/contacts"

        headers = {
            "Authorization": f"Bearer {self.hubspot_api_key}",
            "Content-Type": "application/json",
        }

        # Build payload
        payload = {
            "properties": {k: v for k, v in contact_info.items() if v}
        }

        # Add company association if provided
        # Association Type ID 279 = Contact to Company (HubSpot-defined)
        if company_id:
            payload["associations"] = [
                {
                    "to": {"id": company_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": 279,
                        }
                    ],
                }
            ]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code in [200, 201]:
                    result = response.json()
                    new_contact_id = result.get("id")

                    # Build HubSpot URL
                    hubspot_url = (
                        f"https://app.hubspot.com/contacts/contacts/{new_contact_id}"
                    )

                    contact_name = (
                        f"{contact_info.get('firstname', '')} "
                        f"{contact_info.get('lastname', '')}".strip()
                    )
                    self.status = f"Created: {contact_name}"

                    logger.info(
                        f"HubSpot contact created: {new_contact_id} "
                        f"({contact_name}, {contact_info.get('jobtitle', 'No title')})"
                    )

                    return Data(
                        data={
                            "success": True,
                            "contact_id": new_contact_id,
                            "hubspot_url": hubspot_url,
                            "properties": contact_info,
                            "company_id": company_id,
                            "name": contact_name,
                            "email": contact_info.get("email", ""),
                            "title": contact_info.get("jobtitle", ""),
                        }
                    )

                elif response.status_code == 409:
                    # Contact already exists (duplicate email)
                    try:
                        error_data = response.json()
                        existing_id = error_data.get("message", "").split("ID: ")[-1]
                        self.status = f"Duplicate - exists: {existing_id}"

                        return Data(
                            data={
                                "success": False,
                                "error": "Contact already exists",
                                "existing_contact_id": existing_id.strip(),
                                "email": contact_info.get("email"),
                            }
                        )
                    except Exception:
                        pass

                    self.status = "Duplicate contact"
                    raise ValueError("Contact already exists in HubSpot")

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
                        f"HubSpot contact creation failed ({response.status_code}): {error_msg}"
                    )

        except ValueError:
            raise
        except Exception as e:
            logger.opt(exception=True).error("HubSpot contact creation failed")
            self.status = f"Error: {str(e)}"
            raise ValueError(f"HubSpot contact creation failed: {str(e)}") from e
