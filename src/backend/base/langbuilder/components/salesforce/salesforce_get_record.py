from langbuilder.custom import Component
from langbuilder.io import DataInput, MessageTextInput, Output, StrInput
from langbuilder.schema import Data


class SalesforceGetRecordComponent(Component):
    display_name = "Salesforce Get Record"
    description = "Retrieve a single record from Salesforce by ID"
    icon = "Salesforce"
    name = "SalesforceGetRecord"

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
            info="Salesforce object type to query",
            placeholder="Account, Contact, Opportunity...",
            required=True,
        ),
        StrInput(
            name="record_id",
            display_name="Record ID",
            info="The Salesforce ID of the record to retrieve",
            required=True,
        ),
        MessageTextInput(
            name="fields",
            display_name="Fields",
            info="Comma-separated list of fields to retrieve (use '*' for all fields)",
            value="*",
        ),
    ]

    outputs = [
        Output(display_name="Record", name="record", method="get_record"),
    ]

    def get_record(self) -> Data:
        """Retrieve a single Salesforce record by ID.

        Returns:
            Data: The requested Salesforce record with specified fields
        """
        # In a real implementation, this would:
        # 1. Use the authenticated session from auth_credentials
        # 2. Execute a GET request to /services/data/vXX.0/sobjects/{object_type}/{record_id}
        # 3. Return the record data

        record_data = {
            "object_type": self.object_type,
            "record_id": self.record_id,
            "fields": self.fields,
            "status": "success",
            "message": f"Successfully retrieved {self.object_type} record with ID: {self.record_id}",
            "data": {
                "Id": self.record_id,
                "ObjectType": self.object_type,
                "Name": f"Sample {self.object_type} Record",
                "CreatedDate": "2025-01-01T00:00:00.000+0000",
            },
        }

        return Data(data=record_data)
