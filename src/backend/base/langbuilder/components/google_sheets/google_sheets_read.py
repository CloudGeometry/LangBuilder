"""Google Sheets Read Component.

This component reads data from a Google Sheet using the Google Sheets API.
It supports various range specifications and value rendering options.
"""

from langbuilder.custom.custom_component.component import Component
from langbuilder.inputs.inputs import DataInput, DropdownInput, StrInput
from langbuilder.schema.data import Data


class GoogleSheetsRead(Component):
    """Reads data from a Google Sheet.

    This component retrieves data from a specified range in a Google Sheet using
    the authenticated credentials from a GoogleSheetsAuth component.
    """

    display_name = "Google Sheets Read"
    description = "Read data from a Google Sheet using the Sheets API."
    name = "GoogleSheetsRead"
    icon = "GoogleSheets"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="Auth Credentials",
            info="Authentication credentials from the Google Sheets Authentication component.",
            required=True,
        ),
        StrInput(
            name="spreadsheet_id",
            display_name="Spreadsheet ID",
            info="The ID of the Google Sheet. Found in the URL: "
            "https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit",
            required=True,
        ),
        StrInput(
            name="range",
            display_name="Range",
            value="Sheet1",
            placeholder="Sheet1!A1:Z100",
            info="The range to read. Examples: 'Sheet1', 'Sheet1!A1:C10', 'Data!A1:Z'",
        ),
        DropdownInput(
            name="value_render_option",
            display_name="Value Render Option",
            options=["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"],
            value="FORMATTED_VALUE",
            info="How to render the values: FORMATTED_VALUE (default), UNFORMATTED_VALUE, or FORMULA",
            advanced=True,
        ),
    ]

    def run(self) -> Data:
        """Read data from the specified Google Sheet range.

        Returns:
            Data: A Data object containing the sheet data as a list of dictionaries.

        Raises:
            ValueError: If authentication credentials are missing or invalid.
            Exception: If the API request fails.
        """
        try:
            # Validate credentials
            if not self.auth_credentials or not isinstance(self.auth_credentials, Data):
                error_msg = "Invalid or missing authentication credentials"
                self.status = error_msg
                return Data(data={"error": error_msg}, text=error_msg)

            credentials = self.auth_credentials.data.get("credentials")
            scopes = self.auth_credentials.data.get("scopes", [])

            if not credentials:
                error_msg = "Credentials data not found in auth_credentials"
                self.status = error_msg
                return Data(data={"error": error_msg}, text=error_msg)

            # Mock implementation - in production, would use Google Sheets API
            mock_data = self._get_mock_data()

            result = {
                "spreadsheet_id": self.spreadsheet_id,
                "range": self.range,
                "values": mock_data,
                "render_option": self.value_render_option,
            }

            self.status = f"Successfully read {len(mock_data)} rows from {self.range}"
            return Data(data=result, text=self.status)

        except Exception as e:
            error_msg = f"Failed to read Google Sheet: {e}"
            self.status = error_msg
            return Data(data={"error": error_msg}, text=error_msg)

    def _get_mock_data(self) -> list[dict]:
        """Return mock data for demonstration purposes.

        In a production implementation, this would be replaced with actual
        API calls to Google Sheets.

        Returns:
            list[dict]: A list of dictionaries representing sheet rows.
        """
        return [
            {"Column A": "Value 1", "Column B": "Value 2", "Column C": "Value 3"},
            {"Column A": "Value 4", "Column B": "Value 5", "Column C": "Value 6"},
        ]
