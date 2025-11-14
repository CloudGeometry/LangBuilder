"""ServiceNow create incident component for ActionBridge."""

import json

import requests

from langbuilder.custom import Component
from langbuilder.io import DataInput, DropdownInput, MessageTextInput, Output, StrInput
from langbuilder.schema import Data


class ServiceNowCreateIncident(Component):
    """ServiceNow Create Incident Component.

    Creates a new incident in ServiceNow with specified fields.
    Returns a Data object containing the created incident details.
    """

    display_name = "ServiceNow Create Incident"
    description = "Create a new incident in ServiceNow"
    documentation = "https://developer.servicenow.com/dev.do#!/reference/api/latest/rest/c_TableAPI"
    icon = "ServiceNow"
    name = "ServiceNowCreateIncident"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="ServiceNow Auth",
            info="Authentication credentials from ServiceNow Auth component",
            required=True,
        ),
        StrInput(
            name="short_description",
            display_name="Short Description",
            info="Brief summary of the incident",
            required=True,
            placeholder="Brief description of the issue",
        ),
        MessageTextInput(
            name="description",
            display_name="Description",
            info="Detailed description of the incident",
            required=False,
            placeholder="Detailed description of the incident...",
        ),
        DropdownInput(
            name="priority",
            display_name="Priority",
            options=["1 - Critical", "2 - High", "3 - Moderate", "4 - Low", "5 - Planning"],
            value="3 - Moderate",
            info="Incident priority level",
        ),
        StrInput(
            name="category",
            display_name="Category",
            info="Incident category (e.g., Software, Hardware, Network)",
            required=False,
            placeholder="Software",
        ),
        StrInput(
            name="caller_id",
            display_name="Caller ID",
            info="Sys ID of the caller (user who reported the incident)",
            required=False,
        ),
        StrInput(
            name="assignment_group",
            display_name="Assignment Group",
            info="Sys ID of the assignment group",
            required=False,
        ),
        StrInput(
            name="assigned_to",
            display_name="Assigned To",
            info="Sys ID of the user to assign the incident to",
            required=False,
        ),
    ]

    outputs = [
        Output(
            display_name="Created Incident",
            name="created_incident",
            method="create_incident",
        ),
    ]

    def create_incident(self) -> Data:
        """Create a new ServiceNow incident.

        Returns:
            Data: Object containing created incident details
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

            # Build incident fields
            fields = {
                "short_description": self.short_description,
            }

            # Add description if provided
            if self.description:
                fields["description"] = self.description

            # Extract priority number (e.g., "1 - Critical" -> "1")
            priority_num = self.priority.split(" ")[0]
            fields["priority"] = priority_num

            # Add optional fields if provided
            if self.category:
                fields["category"] = self.category

            if self.caller_id:
                fields["caller_id"] = self.caller_id

            if self.assignment_group:
                fields["assignment_group"] = self.assignment_group

            if self.assigned_to:
                fields["assigned_to"] = self.assigned_to

            self.log(f"Creating ServiceNow incident: {self.short_description}")

            # Make API request
            response = requests.post(
                f"{instance_url}/api/now/table/incident",
                headers=headers,
                data=json.dumps(fields),
                timeout=30,
            )

            # Check response
            response.raise_for_status()
            result_data = response.json()

            # Extract incident data
            incident_data = result_data.get("result", {})

            # Build response object
            incident_info = {
                "sys_id": incident_data.get("sys_id"),
                "number": incident_data.get("number"),
                "short_description": incident_data.get("short_description"),
                "description": incident_data.get("description"),
                "priority": incident_data.get("priority"),
                "state": incident_data.get("state"),
                "category": incident_data.get("category"),
                "opened_at": incident_data.get("opened_at"),
                "url": f"{instance_url}/nav_to.do?uri=incident.do?sys_id={incident_data.get('sys_id')}",
                "created": True,
                "all_fields": incident_data,
            }

            incident_number = incident_data.get("number", "Unknown")
            self.status = f"Created incident {incident_number}"
            self.log(f"Successfully created ServiceNow incident {incident_number}")

            return Data(data=incident_info)

        except requests.exceptions.HTTPError as e:
            error_msg = f"ServiceNow API error: {e.response.status_code} - {e.response.text}"
            self.status = f"Creation failed: {e.response.status_code}"
            self.log(error_msg)
            return Data(data={"error": error_msg, "created": False})

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "created": False})

        except Exception as e:
            error_msg = f"Incident creation failed: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "created": False})
