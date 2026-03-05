"""
HubSpot Contact Search - LangBuilder Custom Component

Search HubSpot CRM for contacts by name using the Search API.
Returns matching contacts with id, name, email, company, and job title.

Author: CloudGeometry
"""

from langflow.custom import Component
from langflow.io import SecretStrInput, MessageTextInput, IntInput, Output, DataInput
from langflow.schema import Data
from langchain_core.tools import ToolException
from loguru import logger
import httpx


class HubSpotContactSearchComponent(Component):
    """
    Search HubSpot CRM for contacts by name.

    Uses HubSpot's default search which searches across all text fields,
    making it forgiving for partial names and variations.

    Returns a list of matching contacts with:
    - id: HubSpot contact ID
    - name: Full name (firstname + lastname)
    - email: Contact email
    - company: Associated company name
    - job_title: Contact's job title

    For LangBuilder automated flows, the component also returns
    `selected_contact_id` with the first/best match.

    API: POST /crm/v3/objects/contacts/search
    Required scope: crm.objects.contacts.read
    """

    display_name = "HubSpot Contact Search"
    description = "Search HubSpot CRM for contacts by name"
    icon = "search"
    name = "HubSpotContactSearch"

    inputs = [
        SecretStrInput(
            name="hubspot_api_key",
            display_name="HubSpot API Key",
            required=True,
            info="HubSpot Private App API Key",
        ),
        DataInput(
            name="parsed_data",
            display_name="Parsed Data",
            required=False,
            info="Data from ContactInfoExtractor containing contact_name and topic",
        ),
        MessageTextInput(
            name="search_query",
            display_name="Search Query",
            required=False,
            info="Name to search for (overrides parsed_data.contact_name if provided)",
            tool_mode=True,  # Agent can set this when used as tool
        ),
        IntInput(
            name="limit",
            display_name="Limit",
            required=False,
            value=5,
            info="Maximum number of results to return (default: 5)",
        ),
        MessageTextInput(
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
            name="search_results",
            display_name="Search Results",
            method="search",
        ),
    ]

    async def search(self) -> Data:
        """
        Search for contacts by name in HubSpot.

        Returns:
            Data object with:
            - success: Boolean indicating if search succeeded
            - contacts: List of matching contacts
            - count: Number of matches found
            - selected_contact_id: First match ID (for automated flows)
        """
        if not self.hubspot_api_key:
            raise ToolException("HubSpot API key is required")

        # Get query from search_query or from parsed_data.contact_name/text
        query = ""
        debug_info = []

        if self.search_query:
            query = str(self.search_query).strip()
            debug_info.append(f"search_query='{query}'")
        elif self.parsed_data:
            # Extract search query from parsed_data
            # Handle list inputs (from DataConditionalRouter which returns lists)
            pd = self.parsed_data
            debug_info.append(f"parsed_data type={type(pd).__name__}")
            if isinstance(pd, list) and len(pd) > 0:
                debug_info.append(f"list len={len(pd)}")
                pd = pd[0]  # Take first item from list
            data = pd.data if hasattr(pd, 'data') else pd
            debug_info.append(f"data type={type(data).__name__}")
            if isinstance(data, dict):
                debug_info.append(f"dict keys={list(data.keys())[:5]}")
                # Try search_query first (from Router), then contact_name, then text
                query = data.get("search_query", "") or data.get("contact_name", "") or data.get("text", "") or ""
                debug_info.append(f"query='{query}'")
            else:
                debug_info.append(f"data not dict: {str(data)[:50]}")
        else:
            debug_info.append("NO parsed_data and NO search_query")

        if not query:
            debug_str = "; ".join(debug_info)
            raise ToolException(f"Search query is required. DEBUG: {debug_str}")

        base_url = self.base_url or "https://api.hubapi.com"
        limit = self.limit or 5

        url = f"{base_url}/crm/v3/objects/contacts/search"

        headers = {
            "Authorization": f"Bearer {self.hubspot_api_key}",
            "Content-Type": "application/json",
        }

        # Use HubSpot's default search - searches across all text fields
        payload = {
            "query": query,
            "properties": ["firstname", "lastname", "email", "company", "jobtitle"],
            "limit": limit,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    contacts = []

                    for contact in data.get("results", []):
                        props = contact.get("properties", {})
                        first = props.get("firstname", "") or ""
                        last = props.get("lastname", "") or ""
                        full_name = f"{first} {last}".strip()

                        contacts.append(
                            {
                                "id": contact.get("id"),
                                "name": full_name or "Unknown",
                                "email": props.get("email", "") or "",
                                "company": props.get("company", "") or "",
                                "job_title": props.get("jobtitle", "") or "",
                            }
                        )

                    # Determine selected contact (first match for automated flows)
                    selected_id = contacts[0]["id"] if contacts else None

                    self.status = f"Found {len(contacts)} contact(s)"
                    logger.info(f"HubSpot search for '{query}' found {len(contacts)} contacts")

                    return Data(
                        data={
                            "success": True,
                            "contacts": contacts,
                            "count": len(contacts),
                            "query": query,
                            "selected_contact_id": selected_id,
                        }
                    )

                elif response.status_code == 401:
                    self.status = "Authentication failed"
                    raise ToolException(
                        "HubSpot authentication failed - check API key"
                    )
                elif response.status_code == 403:
                    self.status = "Permission denied"
                    raise ToolException(
                        "HubSpot permission denied - ensure crm.objects.contacts.read scope"
                    )
                else:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", response.text)
                    except Exception:
                        pass

                    self.status = f"Error: {response.status_code}"
                    raise ToolException(
                        f"HubSpot search failed ({response.status_code}): {error_msg}"
                    )

        except ToolException:
            raise
        except Exception as e:
            logger.opt(exception=True).error("HubSpot contact search failed")
            self.status = f"Error: {str(e)}"
            raise ToolException(f"HubSpot contact search failed: {str(e)}") from e
