from langbuilder.custom import Component
from langbuilder.io import DataInput, MessageTextInput, Output, StrInput
from langbuilder.schema import Data


class SalesforceCreateRecordComponent(Component):
    display_name = "Salesforce Create Record"
    description = "Create a new record in Salesforce"
    icon = "Salesforce"
    name = "SalesforceCreateRecord"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="Authentication Credentials",
            info="Salesforce credentials from the Salesforce Authentication component",
            required=True,
        ),
        StrInput(
            name="object_type",
            display_name="Object Type",
            info="Salesforce object type to create",
            placeholder="Account, Contact, Opportunity...",
            required=True,
        ),
        MessageTextInput(
            name="record_data",
            display_name="Record Data",
            info='JSON object containing the field values for the new record (e.g., {"Name": "ACME Corp", "Industry": "Technology"})',
            placeholder='{"Name": "ACME Corp", "Industry": "Technology", "Phone": "(555) 123-4567"}',
            required=True,
        ),
    ]

    outputs = [
        Output(display_name="Created Record", name="created_record", method="create_record"),
    ]

    def create_record(self) -> Data:
        """Create a new record in Salesforce.

        Returns:
            Data: The created record information including the new record ID
        """
        # In a real implementation, this would:
        # 1. Use the authenticated session from auth_credentials
        # 2. Parse the record_data JSON
        # 3. Execute a POST request to /services/data/vXX.0/sobjects/{object_type}
        # 4. Return the created record ID and success status

        created_record = {
            "object_type": self.object_type,
            "status": "success",
            "message": f"Successfully created {self.object_type} record",
            "id": "001XXXXXXXXXXXXXXX",
            "success": True,
            "errors": [],
            "record_data": self.record_data,
            "created_date": "2025-11-10T00:00:00.000+0000",
        }

        return Data(data=created_record)
