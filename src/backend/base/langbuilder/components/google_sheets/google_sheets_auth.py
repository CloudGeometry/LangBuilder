"""Google Sheets Authentication Component.

This component handles authentication with Google Sheets API using a service account
JSON credentials file. It validates the credentials and returns them for use by other
Google Sheets components.
"""

from langbuilder.custom.custom_component.component import Component
from langbuilder.inputs.inputs import MessageTextInput
from langbuilder.schema.data import Data


class GoogleSheetsAuth(Component):
    """Authenticates with Google Sheets API using service account credentials.

    This component accepts a service account JSON file and optional OAuth scopes,
    validates the credentials, and returns them in a format suitable for use by
    other Google Sheets components.
    """

    display_name = "Google Sheets Authentication"
    description = "Authenticate with Google Sheets API using service account credentials."
    name = "GoogleSheetsAuth"
    icon = "GoogleSheets"

    inputs = [
        MessageTextInput(
            name="credentials_json",
            display_name="Service Account JSON",
            info="The contents of your Google Cloud service account JSON file. "
            "You can download this from Google Cloud Console > Service Accounts.",
        ),
        MessageTextInput(
            name="scopes",
            display_name="OAuth Scopes",
            value="https://www.googleapis.com/auth/spreadsheets",
            info="Comma-separated list of OAuth scopes. "
            "Default scope allows full access to Google Sheets.",
            advanced=True,
        ),
    ]

    def run(self) -> Data:
        """Validate and return the Google Sheets authentication credentials.

        Returns:
            Data: A Data object containing the validated credentials.

        Raises:
            ValueError: If the credentials JSON is invalid or missing required fields.
        """
        try:
            import json

            # Parse the credentials JSON
            creds_dict = json.loads(self.credentials_json)

            # Validate required fields in service account
            required_fields = ["type", "project_id", "private_key_id", "private_key", "client_email"]
            missing_fields = [field for field in required_fields if field not in creds_dict]

            if missing_fields:
                msg = f"Invalid service account JSON. Missing fields: {', '.join(missing_fields)}"
                raise ValueError(msg)

            # Parse scopes
            scopes = [scope.strip() for scope in self.scopes.split(",") if scope.strip()]
            if not scopes:
                scopes = ["https://www.googleapis.com/auth/spreadsheets"]

            # Store credentials in Data object
            auth_data = {
                "credentials": creds_dict,
                "scopes": scopes,
                "project_id": creds_dict.get("project_id"),
            }

            self.status = f"Authenticated as {creds_dict.get('client_email', 'unknown')}"
            return Data(data=auth_data, text=self.status)

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse credentials JSON: {e}"
            self.status = error_msg
            return Data(data={"error": error_msg}, text=error_msg)
        except Exception as e:
            error_msg = f"Authentication failed: {e}"
            self.status = error_msg
            return Data(data={"error": error_msg}, text=error_msg)
