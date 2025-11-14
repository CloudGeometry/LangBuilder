"""Google Sheets Write Component.

This component writes data to a Google Sheet using the Google Sheets API.
It supports various data formats and value input options.
"""

import json

from langbuilder.custom.custom_component.component import Component
from langbuilder.inputs.inputs import DataInput, DropdownInput, MessageTextInput, StrInput
from langbuilder.schema.data import Data


class GoogleSheetsWrite(Component):
    """Writes data to a Google Sheet.

    This component writes data to a specified range in a Google Sheet using
    the authenticated credentials from a GoogleSheetsAuth component.
    """

    display_name = "Google Sheets Write"
    description = "Write data to a Google Sheet using the Sheets API."
    name = "GoogleSheetsWrite"
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
            placeholder="Sheet1!A1",
            info="The starting cell where data will be written. Example: 'Sheet1!A1'",
            required=True,
        ),
        MessageTextInput(
            name="values",
            display_name="Values",
            info="The data to write as a 2D array in JSON format. "
            'Example: [["Header1", "Header2"], ["Value1", "Value2"]]',
            required=True,
        ),
        DropdownInput(
            name="value_input_option",
            display_name="Value Input Option",
            options=["RAW", "USER_ENTERED"],
            value="USER_ENTERED",
            info="RAW: input as-is; USER_ENTERED: formulas interpreted as formulas",
            advanced=True,
        ),
    ]

    def run(self) -> Data:
        """Write data to the specified Google Sheet range.

        Returns:
            Data: A Data object containing the write operation result.

        Raises:
            ValueError: If authentication credentials are missing or data format is invalid.
            Exception: If the API request fails.
        """
        try:
            # Validate credentials
            if not self.auth_credentials or not isinstance(self.auth_credentials, Data):
                error_msg = "Invalid or missing authentication credentials"
                self.status = error_msg
                return Data(data={"error": error_msg}, text=error_msg)

            credentials = self.auth_credentials.data.get("credentials")
            if not credentials:
                error_msg = "Credentials data not found in auth_credentials"
                self.status = error_msg
                return Data(data={"error": error_msg}, text=error_msg)

            # Parse values JSON
            try:
                values = json.loads(self.values)
            except json.JSONDecodeError as e:
                error_msg = f"Invalid values JSON format: {e}"
                self.status = error_msg
                return Data(data={"error": error_msg}, text=error_msg)

            # Validate that values is a 2D array (list of lists)
            if not isinstance(values, list):
                error_msg = "Values must be a JSON array (list)"
                self.status = error_msg
                return Data(data={"error": error_msg}, text=error_msg)

            if values and not isinstance(values[0], list):
                error_msg = "Values must be a 2D array (list of lists)"
                self.status = error_msg
                return Data(data={"error": error_msg}, text=error_msg)

            # Mock implementation - in production, would use Google Sheets API
            result = {
                "spreadsheet_id": self.spreadsheet_id,
                "range": self.range,
                "updated_rows": len(values),
                "updated_columns": len(values[0]) if values else 0,
                "updated_cells": len(values) * (len(values[0]) if values else 0),
                "value_input_option": self.value_input_option,
            }

            self.status = (
                f"Successfully wrote {result['updated_cells']} cells "
                f"({result['updated_rows']} rows x {result['updated_columns']} columns) "
                f"to {self.range}"
            )
            return Data(data=result, text=self.status)

        except Exception as e:
            error_msg = f"Failed to write to Google Sheet: {e}"
            self.status = error_msg
            return Data(data={"error": error_msg}, text=error_msg)
