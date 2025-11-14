"""ServiceNow get incident component for ActionBridge."""


import requests

from langbuilder.custom import Component
from langbuilder.io import DataInput, MessageTextInput, Output, StrInput
from langbuilder.schema import Data


class ServiceNowGetIncident(Component):
    """ServiceNow Get Incident Component.

    Retrieves details of a single ServiceNow incident by its number.
    Returns a Data object containing incident details and fields.
    """

    display_name = "ServiceNow Get Incident"
    description = "Retrieve details of a single ServiceNow incident"
    documentation = "https://developer.servicenow.com/dev.do#!/reference/api/latest/rest/c_TableAPI"
    icon = "ServiceNow"
    name = "ServiceNowGetIncident"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="ServiceNow Auth",
            info="Authentication credentials from ServiceNow Auth component",
            required=True,
        ),
        StrInput(
            name="incident_number",
            display_name="Incident Number",
            info="The incident number to retrieve (e.g., INC0010001)",
            required=True,
            placeholder="INC0010001",
        ),
        MessageTextInput(
            name="fields",
            display_name="Fields to Return",
            info="Comma-separated list of fields (leave empty for all fields)",
            value="*all",
            required=False,
        ),
    ]

    outputs = [
        Output(
            display_name="Incident Details",
            name="incident",
            method="get_incident",
        ),
    ]

    def get_incident(self) -> Data:
        """Retrieve a single ServiceNow incident by number.

        Returns:
            Data: Object containing incident details
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

            # Build query parameters
            params = {
                "sysparm_query": f"number={self.incident_number}",
            }

            # Parse fields
            if self.fields and self.fields != "*all":
                fields_list = [f.strip() for f in self.fields.split(",")]
                params["sysparm_fields"] = ",".join(fields_list)

            self.log(f"Retrieving ServiceNow incident {self.incident_number}")

            # Make API request
            response = requests.get(
                f"{instance_url}/api/now/table/incident",
                headers=headers,
                params=params,
                timeout=30,
            )

            # Check response
            response.raise_for_status()
            result_data = response.json()

            # Extract incident from results
            incidents = result_data.get("result", [])

            if not incidents:
                raise ValueError(f"Incident {self.incident_number} not found")

            incident_data = incidents[0]

            # Build simplified incident object
            incident_info = {
                "sys_id": incident_data.get("sys_id"),
                "number": incident_data.get("number"),
                "short_description": incident_data.get("short_description"),
                "description": incident_data.get("description"),
                "state": incident_data.get("state"),
                "priority": incident_data.get("priority"),
                "urgency": incident_data.get("urgency"),
                "impact": incident_data.get("impact"),
                "category": incident_data.get("category"),
                "subcategory": incident_data.get("subcategory"),
                "assigned_to": incident_data.get("assigned_to"),
                "assignment_group": incident_data.get("assignment_group"),
                "caller_id": incident_data.get("caller_id"),
                "opened_at": incident_data.get("opened_at"),
                "updated_at": incident_data.get("sys_updated_on"),
                "resolved_at": incident_data.get("resolved_at"),
                "closed_at": incident_data.get("closed_at"),
                "url": f"{instance_url}/nav_to.do?uri=incident.do?sys_id={incident_data.get('sys_id')}",
                # Full fields for advanced use
                "all_fields": incident_data,
            }

            self.status = f"Retrieved incident {self.incident_number}"
            self.log(f"Successfully retrieved ServiceNow incident {self.incident_number}")

            return Data(data=incident_info)

        except requests.exceptions.HTTPError as e:
            error_msg = f"ServiceNow API error: {e.response.status_code} - {e.response.text}"
            self.status = f"Retrieval failed: {e.response.status_code}"
            self.log(error_msg)
            return Data(data={"error": error_msg, "incident_number": self.incident_number})

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "incident_number": self.incident_number})

        except Exception as e:
            error_msg = f"Retrieval failed: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "incident_number": self.incident_number})
