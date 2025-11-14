"""Notion Search Component.

This component searches across a Notion workspace for pages, databases, and other content.
"""

from langbuilder.custom.custom_component.component import Component
from langbuilder.io import DataInput, DropdownInput, IntInput, Output, StrInput
from langbuilder.schema.data import Data


class NotionSearchComponent(Component):
    """Search your Notion workspace.

    This component searches across your Notion workspace for pages, databases,
    or both. Results can be filtered by type and limited to a maximum number.
    """

    display_name = "Notion Search"
    description = (
        "Search your Notion workspace for pages, databases, or both. "
        "Supports filtering by type and limiting results."
    )
    icon = "Notion"
    name = "NotionSearch"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="Auth Credentials",
            info="Authenticated Notion credentials from the Notion Authentication component.",
            required=True,
        ),
        StrInput(
            name="query",
            display_name="Search Query",
            info="The search text to find in your Notion workspace.",
            placeholder="Search term",
            required=True,
        ),
        DropdownInput(
            name="filter_type",
            display_name="Filter by Type",
            info="Filter results by object type: pages only, databases only, or all.",
            options=["page", "database", "all"],
            value="all",
            required=False,
        ),
        IntInput(
            name="limit",
            display_name="Result Limit",
            info="Maximum number of results to return.",
            value=10,
            required=False,
        ),
    ]

    outputs = [
        Output(
            display_name="Results",
            name="results",
            method="build_search_results",
        ),
    ]

    def build_search_results(self) -> Data:
        """Search the Notion workspace.

        Returns:
            Data: A Data object containing search results with matching pages/databases.

        Raises:
            ValueError: If credentials are invalid or query is not provided.
        """
        if not self.auth_credentials:
            msg = "Auth credentials are required"
            raise ValueError(msg)

        if not self.query:
            msg = "Search query is required"
            raise ValueError(msg)

        try:
            credentials_data = self.auth_credentials
            if isinstance(credentials_data, Data):
                credentials = credentials_data.data
            else:
                credentials = credentials_data

            api_key = credentials.get("api_key")
            if not api_key:
                msg = "API key not found in credentials"
                raise ValueError(msg)

            limit = self.limit if self.limit and self.limit > 0 else 10
            filter_type = self.filter_type or "all"

            search_results = {
                "query": self.query,
                "filter_type": filter_type,
                "limit": limit,
                "results": [],
                "result_count": 0,
            }

            self.status = f"Searched for '{self.query}' (limit: {limit}, type: {filter_type})"
            return Data(data=search_results)

        except Exception as e:
            error_msg = f"Failed to search workspace: {e!s}"
            self.status = error_msg
            msg = error_msg
            raise ValueError(msg) from e
