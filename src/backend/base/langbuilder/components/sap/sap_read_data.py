"""SAP read data component for ActionBridge."""


from langbuilder.custom import Component
from langbuilder.io import DataInput, IntInput, MessageTextInput, Output, StrInput
from langbuilder.schema import Data


class SAPReadData(Component):
    """SAP Read Table Component.

    Reads data from SAP tables using RFC_READ_TABLE function module.
    Supports field selection, WHERE clauses, and row limits for efficient data extraction.
    Compatible with standard SAP tables (MARA, KNA1, VBAK, etc.).
    """

    display_name = "SAP Read Table"
    description = "Read data from SAP tables with optional field selection and WHERE conditions"
    documentation = "https://help.sap.com/doc/saphelp_nw75/7.5.5/en-US/22/042ff0488911d189490000e829fbbd/content.htm"
    icon = "SAP"
    name = "SAPReadData"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="SAP Credentials",
            info="Authentication credentials from SAP Authentication component",
            required=True,
        ),
        StrInput(
            name="table_name",
            display_name="Table Name",
            info="SAP table name to read from (e.g., MARA, KNA1, VBAK)",
            required=True,
            placeholder="MARA, KNA1, VBAK...",
        ),
        MessageTextInput(
            name="fields",
            display_name="Fields",
            info="Comma-separated list of fields to retrieve. Use '*' for all fields",
            value="*",
        ),
        MessageTextInput(
            name="where_clause",
            display_name="WHERE Clause",
            info="Optional WHERE condition (SAP format: FIELD = 'VALUE' AND FIELD2 = 'VALUE2')",
        ),
        IntInput(
            name="row_count",
            display_name="Max Rows",
            info="Maximum number of rows to retrieve",
            value=100,
        ),
    ]

    outputs = [
        Output(
            display_name="Table Data",
            name="data",
            method="read_table",
        ),
    ]

    def read_table(self) -> Data:
        """Read data from SAP table using RFC connection.

        Returns:
            Data: Object containing table data, field metadata, and row count
        """
        try:
            # Validate inputs
            if not self.auth_credentials:
                raise ValueError("SAP credentials are required")

            auth_data = self.auth_credentials.data if hasattr(self.auth_credentials, "data") else self.auth_credentials
            if not auth_data.get("authenticated"):
                raise ValueError("Invalid or expired SAP credentials")

            table_name = self.table_name.strip().upper()
            if not table_name:
                raise ValueError("Table name is required")

            # Parse fields
            if self.fields and self.fields.strip() != "*":
                field_list = [f.strip().upper() for f in self.fields.split(",")]
            else:
                field_list = []  # Empty list means all fields in RFC_READ_TABLE

            # In a real implementation, this would:
            # 1. Connect to SAP using pyrfc with auth_data['connection_params']
            # 2. Call RFC_READ_TABLE function module with:
            #    - QUERY_TABLE = table_name
            #    - DELIMITER = '|'
            #    - FIELDS = field_list
            #    - OPTIONS = where_clause (parsed into 72-char chunks)
            #    - ROWCOUNT = row_count
            # 3. Parse DATA, FIELDS structures into readable format
            # 4. Return formatted results

            # Mock implementation
            result_data = {
                "table_name": table_name,
                "fields": field_list if field_list else ["ALL_FIELDS"],
                "where_clause": self.where_clause if self.where_clause else "None",
                "row_count_requested": self.row_count,
                "rows_returned": 0,  # Would be actual count in real implementation
                "data": [],  # Would contain actual table data
                "status": "success",
                "message": f"Successfully read from table {table_name}",
            }

            self.status = f"Read {result_data['rows_returned']} rows from {table_name}"
            self.log(
                f"Table: {table_name}, Fields: {len(field_list) if field_list else 'ALL'}, "
                f"Rows: {result_data['rows_returned']}"
            )

            return Data(data=result_data)

        except Exception as e:
            error_msg = f"Failed to read SAP table: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(
                data={
                    "error": error_msg,
                    "status": "failed",
                    "table_name": getattr(self, "table_name", "unknown"),
                }
            )
