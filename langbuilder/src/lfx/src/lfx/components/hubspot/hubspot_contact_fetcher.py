"""
HubSpot Contact Fetcher - LangBuilder Custom Component

Fetches contact data from HubSpot CRM API v3, including
associated company information for personalization.

Author: CloudGeometry
Project: Carter's Agents - Content Engine
"""

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, BoolInput, Output
from lfx.schema import Data
import httpx


class HubSpotContactFetcher(Component):
    """
    Fetches contact data from HubSpot CRM.

    This component is used by the Content Engine agent to retrieve
    contact details (name, email, role, industry, etc.) for personalized
    content generation. Optionally fetches associated company data.
    """

    display_name = "HubSpot Contact Fetcher"
    description = "Fetches contact data from HubSpot CRM by contact ID"
    icon = "user"
    name = "HubSpotContactFetcher"

    # Default properties to fetch
    DEFAULT_PROPERTIES = [
        "firstname",
        "lastname",
        "email",
        "jobtitle",
        "company",
        "industry",
        "phone",
        "city",
        "state",
        "country",
        "annualrevenue",
        "lifecyclestage",
        "hs_lead_status",
    ]

    inputs = [
        SecretStrInput(
            name="hubspot_api_key",
            display_name="HubSpot API Key",
            required=True,
            info="HubSpot Private App API key with crm.objects.contacts.read scope"
        ),
        StrInput(
            name="contact_id",
            display_name="Contact ID",
            required=True,
            info="HubSpot contact ID to fetch"
        ),
        StrInput(
            name="properties",
            display_name="Properties",
            required=False,
            info="Comma-separated list of properties to fetch (leave empty for defaults)",
            advanced=True
        ),
        BoolInput(
            name="include_company_association",
            display_name="Include Company Association",
            required=False,
            value=True,
            info="Whether to include associated company IDs in the response"
        ),
    ]

    outputs = [
        Output(
            name="contact",
            display_name="Contact Data",
            method="fetch_contact",
        ),
    ]

    async def fetch_contact(self) -> Data:
        """
        Fetch contact data from HubSpot CRM API.

        Returns:
            Data object with contact properties and metadata
        """
        # Determine which properties to fetch
        if self.properties and self.properties.strip():
            properties = [p.strip() for p in self.properties.split(",")]
        else:
            properties = self.DEFAULT_PROPERTIES

        # Build URL
        base_url = f"https://api.hubapi.com/crm/v3/objects/contacts/{self.contact_id}"

        # Build query parameters
        params = {
            "properties": ",".join(properties),
        }

        # Add company associations if requested
        if self.include_company_association:
            params["associations"] = "companies"

        headers = {
            "Authorization": f"Bearer {self.hubspot_api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(base_url, headers=headers, params=params)

                if response.status_code == 200:
                    result = response.json()

                    # Extract properties
                    props = result.get("properties", {})

                    # Build contact data object
                    contact_data = {
                        "id": result.get("id"),
                        "firstname": props.get("firstname", ""),
                        "lastname": props.get("lastname", ""),
                        "full_name": f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                        "email": props.get("email", ""),
                        "jobtitle": props.get("jobtitle", ""),
                        "company": props.get("company", ""),
                        "industry": props.get("industry", ""),
                        "phone": props.get("phone", ""),
                        "city": props.get("city", ""),
                        "state": props.get("state", ""),
                        "country": props.get("country", ""),
                        "annualrevenue": props.get("annualrevenue"),
                        "lifecyclestage": props.get("lifecyclestage", ""),
                        "hs_lead_status": props.get("hs_lead_status", ""),
                        # Include all fetched properties
                        "all_properties": props,
                    }

                    # Extract company associations if present
                    company_ids = []
                    associations = result.get("associations", {})
                    if "companies" in associations:
                        company_results = associations["companies"].get("results", [])
                        company_ids = [c.get("id") for c in company_results if c.get("id")]

                    contact_data["associated_company_ids"] = company_ids
                    contact_data["primary_company_id"] = company_ids[0] if company_ids else None

                    self.status = f"✅ Fetched: {contact_data['full_name'] or contact_data['email']}"

                    return Data(data={
                        "success": True,
                        "contact": contact_data,
                        "contact_id": self.contact_id,
                        "properties_fetched": properties,
                    })

                elif response.status_code == 404:
                    self.status = "❌ Contact not found"
                    return Data(data={
                        "success": False,
                        "error": f"Contact {self.contact_id} not found",
                        "status_code": 404
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
