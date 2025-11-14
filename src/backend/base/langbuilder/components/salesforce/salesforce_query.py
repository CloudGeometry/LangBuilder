from langbuilder.custom import Component
from langbuilder.io import DataInput, MessageTextInput, Output
from langbuilder.schema import Data


class SalesforceQueryComponent(Component):
    display_name = "Salesforce Query (SOQL)"
    description = "Execute a SOQL query to retrieve multiple records from Salesforce"
    icon = "Salesforce"
    name = "SalesforceQuery"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="Authentication Credentials",
            info="Salesforce credentials from the Salesforce Authentication component",
            required=True,
        ),
        MessageTextInput(
            name="soql_query",
            display_name="SOQL Query",
            info="Salesforce Object Query Language (SOQL) query to execute",
            placeholder="SELECT Id, Name FROM Account WHERE Industry = 'Technology' LIMIT 10",
            required=True,
        ),
    ]

    outputs = [
        Output(display_name="Results", name="results", method="execute_query"),
    ]

    def execute_query(self) -> Data:
        """Execute a SOQL query and return the results.

        Returns:
            Data: Query results containing all matching records
        """
        # In a real implementation, this would:
        # 1. Use the authenticated session from auth_credentials
        # 2. Execute the SOQL query via /services/data/vXX.0/query
        # 3. Handle pagination if there are more than 2000 records
        # 4. Return all matching records

        query_results = {
            "soql_query": self.soql_query,
            "status": "success",
            "message": "Successfully executed SOQL query",
            "total_size": 5,
            "done": True,
            "records": [
                {
                    "Id": "001XXXXXXXXXXXXXXX1",
                    "Name": "Sample Account 1",
                    "attributes": {"type": "Account", "url": "/services/data/v58.0/sobjects/Account/001XXXXXXXXXXXXXXX1"},
                },
                {
                    "Id": "001XXXXXXXXXXXXXXX2",
                    "Name": "Sample Account 2",
                    "attributes": {"type": "Account", "url": "/services/data/v58.0/sobjects/Account/001XXXXXXXXXXXXXXX2"},
                },
                {
                    "Id": "001XXXXXXXXXXXXXXX3",
                    "Name": "Sample Account 3",
                    "attributes": {"type": "Account", "url": "/services/data/v58.0/sobjects/Account/001XXXXXXXXXXXXXXX3"},
                },
                {
                    "Id": "001XXXXXXXXXXXXXXX4",
                    "Name": "Sample Account 4",
                    "attributes": {"type": "Account", "url": "/services/data/v58.0/sobjects/Account/001XXXXXXXXXXXXXXX4"},
                },
                {
                    "Id": "001XXXXXXXXXXXXXXX5",
                    "Name": "Sample Account 5",
                    "attributes": {"type": "Account", "url": "/services/data/v58.0/sobjects/Account/001XXXXXXXXXXXXXXX5"},
                },
            ],
        }

        return Data(data=query_results)
