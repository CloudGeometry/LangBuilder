"""Workday get employee component for ActionBridge."""


import requests

from langbuilder.custom import Component
from langbuilder.io import DataInput, MessageTextInput, Output, StrInput
from langbuilder.schema import Data


class WorkdayGetEmployee(Component):
    """Workday Get Employee Component.

    Retrieves employee details from Workday by employee ID.
    Returns a Data object containing employee information and fields.
    """

    display_name = "Workday Get Employee"
    description = "Retrieve employee details from Workday by employee ID"
    documentation = "https://community.workday.com/sites/default/files/file-hosting/restapi/index.html"
    icon = "Workday"
    name = "WorkdayGetEmployee"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="Workday Auth",
            info="Authentication credentials from Workday Auth component",
            required=True,
        ),
        StrInput(
            name="employee_id",
            display_name="Employee ID",
            info="The employee ID or worker ID to retrieve",
            required=True,
            placeholder="12345",
        ),
        MessageTextInput(
            name="fields",
            display_name="Fields to Return",
            info="Comma-separated list of fields (use *all for all fields)",
            value="*all",
            required=False,
        ),
    ]

    outputs = [
        Output(
            display_name="Employee Data",
            name="employee",
            method="get_employee",
        ),
    ]

    def get_employee(self) -> Data:
        """Retrieve employee details from Workday.

        Returns:
            Data: Object containing employee information
        """
        try:
            # Extract auth data
            auth_data = self.auth_credentials.data if hasattr(self.auth_credentials, "data") else self.auth_credentials

            if not isinstance(auth_data, dict):
                raise ValueError("Invalid authentication data. Please connect a Workday Auth component.")

            if not auth_data.get("authenticated", False):
                error = auth_data.get("error", "Authentication not established")
                raise ValueError(f"Authentication failed: {error}")

            tenant_url = auth_data["tenant_url"]
            headers = auth_data["headers"]
            api_version = auth_data.get("api_version", "v1")

            # Build API endpoint
            endpoint = f"{tenant_url}/ccx/api/{api_version}/{tenant_url.split('/')[-1]}/workers/{self.employee_id}"

            self.log(f"Retrieving Workday employee {self.employee_id}")

            # Make API request (mock implementation - actual Workday API may differ)
            # Note: This is a simplified implementation. Real Workday API endpoints may vary.
            response = requests.get(
                endpoint,
                headers=headers,
                timeout=30,
            )

            # Check response
            response.raise_for_status()
            employee_data = response.json()

            # Extract key employee information
            # This structure is a mock - actual Workday response structure may differ
            employee_info = {
                "employee_id": self.employee_id,
                "worker_id": employee_data.get("workerId"),
                "employee_number": employee_data.get("employeeNumber"),
                "name": {
                    "first_name": employee_data.get("firstName"),
                    "last_name": employee_data.get("lastName"),
                    "preferred_name": employee_data.get("preferredName"),
                    "full_name": employee_data.get("fullName"),
                },
                "contact": {
                    "email": employee_data.get("email"),
                    "phone": employee_data.get("phone"),
                    "mobile": employee_data.get("mobile"),
                },
                "job": {
                    "title": employee_data.get("jobTitle"),
                    "department": employee_data.get("department"),
                    "location": employee_data.get("location"),
                    "manager": employee_data.get("manager"),
                },
                "employment": {
                    "status": employee_data.get("employmentStatus"),
                    "type": employee_data.get("employmentType"),
                    "hire_date": employee_data.get("hireDate"),
                    "termination_date": employee_data.get("terminationDate"),
                },
                # Full data for advanced use
                "all_fields": employee_data,
            }

            # Filter fields if specified
            if self.fields and self.fields != "*all":
                fields_list = [f.strip() for f in self.fields.split(",")]
                filtered_info = {k: v for k, v in employee_info.items() if k in fields_list or k == "all_fields"}
                employee_info = filtered_info

            self.status = f"Retrieved employee {self.employee_id}"
            self.log(f"Successfully retrieved Workday employee {self.employee_id}")

            return Data(data=employee_info)

        except requests.exceptions.HTTPError as e:
            error_msg = f"Workday API error: {e.response.status_code} - {e.response.text}"
            self.status = f"Retrieval failed: {e.response.status_code}"
            self.log(error_msg)
            return Data(data={"error": error_msg, "employee_id": self.employee_id})

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "employee_id": self.employee_id})

        except Exception as e:
            error_msg = f"Retrieval failed: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "employee_id": self.employee_id})
