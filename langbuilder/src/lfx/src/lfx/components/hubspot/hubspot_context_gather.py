"""
HubSpot Context Gather - LangBuilder Custom Component

Gathers contact and associated company context from HubSpot CRM.
Used as the first step in ICP Validator flow to get data for LLM reasoning.

Author: CloudGeometry
Project: Carter's Agents - ICP Validator
"""

from lfx.custom import Component
from lfx.io import HandleInput, SecretStrInput, StrInput, Output
from lfx.schema import Data
# ValueError not used - using ValueError instead
from loguru import logger
import httpx


class HubSpotContextGatherComponent(Component):
    """
    Gather contact and company context from HubSpot for ICP validation.

    This component fetches:
    1. Contact properties (name, title, email)
    2. Associated company properties (industry, size, pain point)

    The combined context is used by downstream LLM to determine
    if the contact is the correct economic buyer.

    API Calls:
    - GET /crm/v3/objects/contacts/{id}
    - GET /crm/v3/objects/companies/{id}

    Required scope: crm.objects.contacts.read, crm.objects.companies.read
    """

    display_name = "HubSpot Context Gather"
    description = "Gathers contact and company context from HubSpot for ICP validation"
    icon = "database"
    name = "HubSpotContextGather"

    inputs = [
        HandleInput(
            name="contact_input",
            display_name="Contact Input",
            input_types=["Data", "Message"],
            required=True,
            info="Input containing contact_id (from webhook or upstream component)",
        ),
        SecretStrInput(
            name="hubspot_api_key",
            display_name="HubSpot API Key",
            required=True,
            info="HubSpot Private App API key",
        ),
        StrInput(
            name="contact_properties",
            display_name="Contact Properties",
            required=False,
            value="firstname,lastname,jobtitle,email,phone",
            advanced=True,
            info="Comma-separated list of contact properties to fetch",
        ),
        StrInput(
            name="company_properties",
            display_name="Company Properties",
            required=False,
            value="name,industry,numberofemployees,domain,pain_point",
            advanced=True,
            info="Comma-separated list of company properties to fetch",
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
            name="context_data",
            display_name="Context Data",
            method="gather_context",
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
                # Check nested properties
                if "properties" in data:
                    props = data["properties"]
                    if "hs_object_id" in props:
                        return str(props["hs_object_id"])

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

    async def gather_context(self) -> Data:
        """
        Gather contact and company context from HubSpot.

        Returns:
            Data object with:
            - contact: Contact properties dict
            - company: Associated company properties dict
            - contact_id: Original contact ID
            - company_id: Associated company ID (if found)
        """
        if not self.hubspot_api_key:
            raise ValueError("HubSpot API key is required")

        contact_id = self._extract_contact_id()
        if not contact_id:
            raise ValueError("contact_id is required")

        base_url = self.base_url or "https://api.hubapi.com"

        headers = {
            "Authorization": f"Bearer {self.hubspot_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: Fetch contact with associations
                contact_props = self.contact_properties or "firstname,lastname,jobtitle,email"
                contact_url = (
                    f"{base_url}/crm/v3/objects/contacts/{contact_id}"
                    f"?properties={contact_props}"
                    f"&associations=companies"
                )

                contact_response = await client.get(contact_url, headers=headers)

                if contact_response.status_code == 404:
                    self.status = "Contact not found"
                    raise ValueError(f"Contact {contact_id} not found in HubSpot")

                if contact_response.status_code != 200:
                    self._handle_error(contact_response, "Contact fetch")

                contact_data = contact_response.json()
                contact_props_dict = contact_data.get("properties", {})

                # Step 2: Get associated company ID
                company_id = None
                associations = contact_data.get("associations", {})
                companies = associations.get("companies", {}).get("results", [])

                if companies:
                    # Get first associated company
                    company_id = companies[0].get("id")

                # Step 3: Fetch company data if associated
                company_props_dict = {}
                if company_id:
                    company_props = self.company_properties or "name,industry,numberofemployees"
                    company_url = (
                        f"{base_url}/crm/v3/objects/companies/{company_id}"
                        f"?properties={company_props}"
                    )

                    company_response = await client.get(company_url, headers=headers)

                    if company_response.status_code == 200:
                        company_data = company_response.json()
                        company_props_dict = company_data.get("properties", {})
                    else:
                        logger.warning(f"Could not fetch company {company_id}: {company_response.status_code}")

                # Build result
                result = {
                    "contact_id": contact_id,
                    "company_id": company_id,
                    "contact": {
                        "id": contact_id,
                        "firstname": contact_props_dict.get("firstname", ""),
                        "lastname": contact_props_dict.get("lastname", ""),
                        "jobtitle": contact_props_dict.get("jobtitle", ""),
                        "email": contact_props_dict.get("email", ""),
                        "phone": contact_props_dict.get("phone", ""),
                    },
                    "company": {
                        "id": company_id,
                        "name": company_props_dict.get("name", ""),
                        "industry": company_props_dict.get("industry", ""),
                        "numberofemployees": company_props_dict.get("numberofemployees", ""),
                        "domain": company_props_dict.get("domain", ""),
                        "pain_point": company_props_dict.get("pain_point", ""),
                    },
                }

                # Set status for UI
                contact_name = f"{result['contact']['firstname']} {result['contact']['lastname']}".strip()
                company_name = result["company"]["name"] or "No company"
                self.status = f"Gathered: {contact_name} @ {company_name}"

                logger.info(
                    f"HubSpot context gathered for contact {contact_id}: "
                    f"{contact_name}, {result['contact']['jobtitle']} at {company_name}"
                )

                return Data(data=result)

        except ValueError:
            raise
        except Exception as e:
            logger.opt(exception=True).error("HubSpot context gather failed")
            self.status = f"Error: {str(e)}"
            raise ValueError(f"HubSpot context gather failed: {str(e)}") from e

    def _handle_error(self, response: httpx.Response, operation: str):
        """Handle API error response."""
        if response.status_code == 401:
            self.status = "Authentication failed"
            raise ValueError("HubSpot authentication failed - check API key")
        elif response.status_code == 403:
            self.status = "Permission denied"
            raise ValueError(
                f"HubSpot permission denied for {operation} - "
                "ensure crm.objects.contacts.read and crm.objects.companies.read scopes"
            )
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get("message", response.text)
            except Exception:
                error_msg = response.text

            self.status = f"Error: {response.status_code}"
            raise ValueError(f"HubSpot {operation} failed ({response.status_code}): {error_msg}")
