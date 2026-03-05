"""
Apollo People Search - LangBuilder Custom Component

Search for people at a company by domain and job titles using Apollo.io API.
Used in ICP Validator FALSE path to find alternative buyers.

Author: CloudGeometry
Project: Carter's Agents - ICP Validator
"""

from langflow.custom import Component
from langflow.io import HandleInput, SecretStrInput, StrInput, IntInput, Output
from langflow.schema import Data
# ValueError not used
from loguru import logger
import httpx


class ApolloPeopleSearchComponent(Component):
    """
    Search for people at a company by domain and job titles.

    This component searches Apollo's database for people matching:
    - Company domain (required)
    - Job titles (optional, but recommended for ICP validation)

    Used in ICP Validator to find alternative economic buyers when
    the original contact is not the right person.

    API: POST /v1/mixed_people/search
    """

    display_name = "Apollo People Search"
    description = "Search for people at a company by domain and job titles"
    icon = "search"
    name = "ApolloPeopleSearch"

    inputs = [
        HandleInput(
            name="search_input",
            display_name="Search Input",
            input_types=["Data"],
            required=True,
            info="Data containing domain and/or suggested_role from LLM output",
        ),
        SecretStrInput(
            name="apollo_api_key",
            display_name="Apollo API Key",
            required=True,
            info="Apollo.io API key from Settings > Integrations > API Keys",
        ),
        StrInput(
            name="static_domain",
            display_name="Static Domain",
            required=False,
            info="Company domain to search (overrides input if provided)",
        ),
        StrInput(
            name="static_titles",
            display_name="Static Titles",
            required=False,
            info="Comma-separated job titles to search (overrides input if provided)",
        ),
        IntInput(
            name="per_page",
            display_name="Results Per Page",
            value=5,
            required=False,
            info="Number of results to return (default: 5, max: 25)",
        ),
    ]

    outputs = [
        Output(
            name="search_results",
            display_name="Search Results",
            method="search_people",
        ),
    ]

    def _extract_search_params(self) -> tuple[str, list[str]]:
        """Extract domain and titles from input data."""
        domain = self.static_domain
        titles = []

        if self.static_titles:
            titles = [t.strip() for t in self.static_titles.split(",") if t.strip()]

        # Extract from input data if not provided statically
        input_data = self.search_input

        if hasattr(input_data, "data"):
            data = input_data.data
            if isinstance(data, dict):
                # Get domain
                if not domain:
                    domain = data.get("domain") or ""
                    # Try nested company object
                    if not domain and "company" in data:
                        domain = data["company"].get("domain", "")

                # Get titles from suggested_role
                if not titles:
                    suggested_role = data.get("suggested_role")
                    if suggested_role:
                        # Handle both string and list
                        if isinstance(suggested_role, str):
                            titles = [suggested_role]
                        elif isinstance(suggested_role, list):
                            titles = suggested_role

                # Expand common title variations
                if titles:
                    expanded_titles = []
                    for title in titles:
                        expanded_titles.append(title)
                        # Add common variations
                        if title.upper() == "CFO":
                            expanded_titles.extend(["Chief Financial Officer", "VP Finance"])
                        elif title.upper() == "CTO":
                            expanded_titles.extend(["Chief Technology Officer", "VP Engineering"])
                        elif title.upper() == "CEO":
                            expanded_titles.extend(["Chief Executive Officer", "President"])
                        elif title.upper() == "CMO":
                            expanded_titles.extend(["Chief Marketing Officer", "VP Marketing"])
                        elif title.upper() == "COO":
                            expanded_titles.extend(["Chief Operating Officer", "VP Operations"])
                    titles = list(set(expanded_titles))  # Remove duplicates

        return domain, titles

    async def search_people(self) -> Data:
        """
        Search Apollo for people matching domain and titles.

        Returns:
            Data object with:
            - success: Boolean indicating if search succeeded
            - people: List of matching people with contact info
            - count: Number of results found
            - domain: Domain searched
            - titles: Titles searched
        """
        if not self.apollo_api_key:
            raise ValueError("Apollo API key is required")

        domain, titles = self._extract_search_params()

        if not domain:
            raise ValueError(
                "Domain is required for people search. "
                "Provide via static_domain or in input data."
            )

        url = "https://api.apollo.io/v1/mixed_people/search"

        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": self.apollo_api_key,
        }

        # Build search payload
        payload = {
            "organization_domains": [domain],
            "page": 1,
            "per_page": min(self.per_page or 5, 25),
        }

        # Add titles filter if provided
        if titles:
            payload["person_titles"] = titles

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    result = response.json()
                    people_raw = result.get("people", [])

                    # Parse and clean people data
                    people = []
                    for person in people_raw:
                        people.append({
                            "id": person.get("id"),
                            "name": person.get("name"),
                            "first_name": person.get("first_name"),
                            "last_name": person.get("last_name"),
                            "title": person.get("title"),
                            "email": person.get("email"),
                            "email_status": person.get("email_status"),
                            "linkedin_url": person.get("linkedin_url"),
                            "city": person.get("city"),
                            "state": person.get("state"),
                            "country": person.get("country"),
                            "organization_name": person.get("organization", {}).get("name"),
                        })

                    # Determine best match (first result)
                    best_match = people[0] if people else None

                    self.status = f"Found {len(people)} people at {domain}"
                    logger.info(
                        f"Apollo search for {titles} at {domain} found {len(people)} people"
                    )

                    return Data(
                        data={
                            "success": True,
                            "people": people,
                            "count": len(people),
                            "domain": domain,
                            "titles_searched": titles,
                            "best_match": best_match,
                        }
                    )

                elif response.status_code == 401:
                    self.status = "Authentication failed"
                    raise ValueError("Apollo authentication failed - check API key")

                elif response.status_code == 403:
                    self.status = "Access forbidden"
                    raise ValueError("Apollo access forbidden - check API key permissions")

                elif response.status_code == 429:
                    self.status = "Rate limited"
                    raise ValueError("Apollo rate limit exceeded - try again later")

                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", response.text)
                    except Exception:
                        error_msg = response.text

                    self.status = f"Error: {response.status_code}"
                    raise ValueError(
                        f"Apollo people search failed ({response.status_code}): {error_msg}"
                    )

        except ValueError:
            raise
        except Exception as e:
            logger.opt(exception=True).error("Apollo people search failed")
            self.status = f"Error: {str(e)}"
            raise ValueError(f"Apollo people search failed: {str(e)}") from e
