"""ServiceNow search records component for ActionBridge."""


import requests

from langbuilder.custom import Component
from langbuilder.io import DataInput, IntInput, MessageTextInput, Output, StrInput
from langbuilder.schema import Data


class ServiceNowSearch(Component):
    """ServiceNow Search Component.

    Searches for records in ServiceNow tables using encoded queries.
    Returns a Data object containing search results with record details.
    """

    display_name = "ServiceNow Search"
    description = "Search for records in ServiceNow tables using queries"
    documentation = "https://developer.servicenow.com/dev.do#!/reference/api/latest/rest/c_TableAPI"
    icon = "ServiceNow"
    name = "ServiceNowSearch"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="ServiceNow Auth",
            info="Authentication credentials from ServiceNow Auth component",
            required=True,
        ),
        StrInput(
            name="table",
            display_name="Table Name",
            info="ServiceNow table to search (e.g., incident, problem, change_request)",
            required=True,
            placeholder="incident",
        ),
        MessageTextInput(
            name="query",
            display_name="Query",
            info="Encoded query string (e.g., active=true^priority=1)",
            required=False,
            placeholder="active=true^priority=1",
        ),
        IntInput(
            name="limit",
            display_name="Limit",
            info="Maximum number of records to return (1-1000)",
            value=10,
            required=False,
        ),
        MessageTextInput(
            name="fields",
            display_name="Fields to Return",
            info="Comma-separated list of fields (leave empty for all fields)",
            required=False,
            placeholder="number,short_description,state,priority",
        ),
        StrInput(
            name="order_by",
            display_name="Order By",
            info="Field to order results by (prefix with - for descending)",
            required=False,
            placeholder="-sys_updated_on",
        ),
    ]

    outputs = [
        Output(
            display_name="Search Results",
            name="results",
            method="search_records",
        ),
    ]

    def search_records(self) -> Data:
        """Search for records in ServiceNow table.

        Returns:
            Data: Object containing search results with records array
        """
        try:
            # Extract auth data
            auth_data = self.auth_credentials.data if hasattr(self.auth_credentials, "data") else self.auth_credentials

            if not isinstance(auth_data, dict):
                raise ValueError("Invalid authentication data. Please connect a ServiceNow Auth component.")

            if not auth_data.get("authenticated", False):
                error = auth_data.get("error", "Authentication not established")
                raise ValueError(f"Authentication failed: {error}")

            instance_url = auth_data["instance_url"]
            headers = auth_data["headers"]

            # Validate and build parameters
            params = {}

            # Add query if provided
            if self.query:
                params["sysparm_query"] = self.query

            # Validate and add limit
            limit = max(1, min(1000, self.limit))
            params["sysparm_limit"] = limit

            # Add fields if specified
            if self.fields:
                fields_list = [f.strip() for f in self.fields.split(",")]
                params["sysparm_fields"] = ",".join(fields_list)

            # Add order by if specified
            if self.order_by:
                # Handle descending order (prefix with -)
                if self.order_by.startswith("-"):
                    params["sysparm_query"] += f"^ORDERBY{self.order_by[1:]}DESC"
                else:
                    params["sysparm_query"] += f"^ORDERBY{self.order_by}"

            self.log(f"Searching ServiceNow table '{self.table}' with query: {self.query or 'all records'}")

            # Make API request
            response = requests.get(
                f"{instance_url}/api/now/table/{self.table}",
                headers=headers,
                params=params,
                timeout=30,
            )

            # Check response
            response.raise_for_status()
            result_data = response.json()

            # Extract records
            records = result_data.get("result", [])

            # Build search results
            search_results = {
                "table": self.table,
                "query": self.query or "all records",
                "count": len(records),
                "limit": limit,
                "records": records,
            }

            self.status = f"Found {len(records)} records in {self.table}"
            self.log(f"Successfully retrieved {len(records)} records from {self.table}")

            return Data(data=search_results)

        except requests.exceptions.HTTPError as e:
            error_msg = f"ServiceNow API error: {e.response.status_code} - {e.response.text}"
            self.status = f"Search failed: {e.response.status_code}"
            self.log(error_msg)
            return Data(data={"error": error_msg, "records": [], "count": 0})

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "records": [], "count": 0})

        except Exception as e:
            error_msg = f"Search failed: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "records": [], "count": 0})
