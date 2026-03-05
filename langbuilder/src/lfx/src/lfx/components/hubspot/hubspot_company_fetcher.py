"""
HubSpot Company Fetcher - LangBuilder Custom Component

Fetches company data from HubSpot CRM API v3 for enriched
personalization in content generation.

Author: CloudGeometry
Project: Carter's Agents - Content Engine
"""

from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output
from langflow.schema import Data
import httpx


class HubSpotCompanyFetcher(Component):
    """
    Fetches company data from HubSpot CRM.

    This component is used by the Content Engine agent to retrieve
    company details (name, industry, revenue, size, etc.) for enhanced
    personalization. Typically used after HubSpotContactFetcher to
    get associated company data.
    """

    display_name = "HubSpot Company Fetcher"
    description = "Fetches company data from HubSpot CRM by company ID"
    icon = "building"
    name = "HubSpotCompanyFetcher"

    # Default properties to fetch
    DEFAULT_PROPERTIES = [
        "name",
        "domain",
        "industry",
        "annualrevenue",
        "numberofemployees",
        "city",
        "state",
        "country",
        "phone",
        "website",
        "description",
        "type",
        "lifecyclestage",
        "hs_lead_status",
    ]

    # Company size classification thresholds
    SIZE_THRESHOLDS = {
        "small": 50,       # 1-50 employees
        "mid": 500,        # 51-500 employees
        "enterprise": None # 500+ employees
    }

    inputs = [
        SecretStrInput(
            name="hubspot_api_key",
            display_name="HubSpot API Key",
            required=True,
            info="HubSpot Private App API key with crm.objects.companies.read scope"
        ),
        StrInput(
            name="company_id",
            display_name="Company ID",
            required=True,
            info="HubSpot company ID to fetch"
        ),
        StrInput(
            name="properties",
            display_name="Properties",
            required=False,
            info="Comma-separated list of properties to fetch (leave empty for defaults)",
            advanced=True
        ),
    ]

    outputs = [
        Output(
            name="company",
            display_name="Company Data",
            method="fetch_company",
        ),
    ]

    def _classify_company_size(self, num_employees) -> str:
        """Classify company size based on employee count."""
        if num_employees is None:
            return "unknown"
        try:
            count = int(num_employees)
            if count <= self.SIZE_THRESHOLDS["small"]:
                return "small"
            elif count <= self.SIZE_THRESHOLDS["mid"]:
                return "mid"
            else:
                return "enterprise"
        except (ValueError, TypeError):
            return "unknown"

    def _estimate_cloud_spend(self, annual_revenue) -> int:
        """
        Estimate annual cloud spend based on revenue.
        Industry average: 3-5% of revenue for cloud infrastructure.
        """
        if annual_revenue is None:
            return 0
        try:
            revenue = float(annual_revenue)
            # Use 4% as conservative estimate
            return int(revenue * 0.04)
        except (ValueError, TypeError):
            return 0

    def _format_location(self, city: str, state: str, country: str) -> str:
        """Format location string from components."""
        parts = [p for p in [city, state, country] if p]
        return ", ".join(parts) if parts else ""

    async def fetch_company(self) -> Data:
        """
        Fetch company data from HubSpot CRM API.

        Returns:
            Data object with company properties, size classification,
            and estimated cloud spend
        """
        # Determine which properties to fetch
        if self.properties and self.properties.strip():
            properties = [p.strip() for p in self.properties.split(",")]
        else:
            properties = self.DEFAULT_PROPERTIES

        # Build URL
        base_url = f"https://api.hubapi.com/crm/v3/objects/companies/{self.company_id}"

        # Build query parameters
        params = {
            "properties": ",".join(properties),
        }

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

                    # Get employee count and revenue for derived fields
                    num_employees = props.get("numberofemployees")
                    annual_revenue = props.get("annualrevenue")

                    # Classify company size
                    company_size = self._classify_company_size(num_employees)

                    # Estimate cloud spend
                    estimated_cloud_spend = self._estimate_cloud_spend(annual_revenue)

                    # Format location
                    location = self._format_location(
                        props.get("city", ""),
                        props.get("state", ""),
                        props.get("country", "")
                    )

                    # Build company data object
                    company_data = {
                        "id": result.get("id"),
                        "name": props.get("name", ""),
                        "domain": props.get("domain", ""),
                        "industry": props.get("industry", ""),
                        "annualrevenue": annual_revenue,
                        "numberofemployees": num_employees,
                        "city": props.get("city", ""),
                        "state": props.get("state", ""),
                        "country": props.get("country", ""),
                        "location": location,
                        "phone": props.get("phone", ""),
                        "website": props.get("website", ""),
                        "description": props.get("description", ""),
                        "type": props.get("type", ""),
                        "lifecyclestage": props.get("lifecyclestage", ""),
                        "hs_lead_status": props.get("hs_lead_status", ""),
                        # Derived fields
                        "company_size": company_size,
                        "estimated_cloud_spend": estimated_cloud_spend,
                        "estimated_cloud_spend_formatted": f"${estimated_cloud_spend:,}" if estimated_cloud_spend else "N/A",
                        # Include all fetched properties
                        "all_properties": props,
                    }

                    self.status = f"✅ Fetched: {company_data['name']}"

                    return Data(data={
                        "success": True,
                        "company": company_data,
                        "company_id": self.company_id,
                        "properties_fetched": properties,
                    })

                elif response.status_code == 404:
                    self.status = "❌ Company not found"
                    return Data(data={
                        "success": False,
                        "error": f"Company {self.company_id} not found",
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
