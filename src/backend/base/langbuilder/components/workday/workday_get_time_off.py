"""Workday get time off component for ActionBridge."""


import requests

from langbuilder.custom import Component
from langbuilder.io import DataInput, DropdownInput, Output, StrInput
from langbuilder.schema import Data


class WorkdayGetTimeOff(Component):
    """Workday Get Time Off Component.

    Retrieves time off balance information for an employee from Workday.
    Returns a Data object containing time off balances and details.
    """

    display_name = "Workday Get Time Off"
    description = "Retrieve time off balance information for an employee from Workday"
    documentation = "https://community.workday.com/sites/default/files/file-hosting/restapi/index.html"
    icon = "Workday"
    name = "WorkdayGetTimeOff"

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
            info="The employee ID or worker ID to retrieve time off balance for",
            required=True,
            placeholder="12345",
        ),
        DropdownInput(
            name="time_off_type",
            display_name="Time Off Type",
            options=["PTO", "Sick Leave", "Vacation", "Personal", "All"],
            value="All",
            info="Type of time off balance to retrieve",
        ),
    ]

    outputs = [
        Output(
            display_name="Time Off Data",
            name="time_off_data",
            method="get_time_off",
        ),
    ]

    def get_time_off(self) -> Data:
        """Retrieve time off balance information from Workday.

        Returns:
            Data: Object containing time off balances and details
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
            # Note: This is a simplified endpoint structure. Actual Workday API may differ.
            endpoint = f"{tenant_url}/ccx/api/{api_version}/{tenant_url.split('/')[-1]}/workers/{self.employee_id}/timeOff"

            # Add query parameters for time off type if not "All"
            params = {}
            if self.time_off_type != "All":
                params["type"] = self.time_off_type

            self.log(f"Retrieving Workday time off balance for employee {self.employee_id}")

            # Make API request (mock implementation - actual Workday API may differ)
            response = requests.get(
                endpoint,
                headers=headers,
                params=params,
                timeout=30,
            )

            # Check response
            response.raise_for_status()
            time_off_response = response.json()

            # Extract and structure time off information
            # This structure is a mock - actual Workday response structure may differ
            time_off_info = {
                "employee_id": self.employee_id,
                "time_off_type": self.time_off_type,
                "balances": [],
                "summary": {},
            }

            # Process time off balances
            balances = time_off_response.get("balances", [])

            for balance in balances:
                balance_entry = {
                    "type": balance.get("timeOffType"),
                    "balance": balance.get("balance"),
                    "unit": balance.get("unit", "hours"),
                    "accrued": balance.get("accrued"),
                    "used": balance.get("used"),
                    "planned": balance.get("planned"),
                    "available": balance.get("available"),
                    "as_of_date": balance.get("asOfDate"),
                }
                time_off_info["balances"].append(balance_entry)

            # Create summary
            if balances:
                total_available = sum(b.get("available", 0) for b in balances if isinstance(b.get("available"), (int, float)))
                total_used = sum(b.get("used", 0) for b in balances if isinstance(b.get("used"), (int, float)))

                time_off_info["summary"] = {
                    "total_balances": len(balances),
                    "total_available": total_available,
                    "total_used": total_used,
                    "primary_unit": balances[0].get("unit", "hours") if balances else "hours",
                }

            # Include full response for advanced use
            time_off_info["all_fields"] = time_off_response

            self.status = f"Retrieved time off balance for employee {self.employee_id}"
            self.log(f"Successfully retrieved Workday time off balance for employee {self.employee_id}")

            return Data(data=time_off_info)

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
