from langbuilder.custom import Component
from langbuilder.io import DropdownInput, Output, SecretStrInput, StrInput
from langbuilder.schema import Data


class SalesforceAuthComponent(Component):
    display_name = "Salesforce Authentication"
    description = "Authenticate with Salesforce using password or OAuth credentials"
    icon = "Salesforce"
    name = "SalesforceAuth"

    inputs = [
        StrInput(
            name="instance_url",
            display_name="Instance URL",
            info="Your Salesforce instance URL (e.g., https://mycompany.salesforce.com)",
            required=True,
        ),
        StrInput(
            name="username",
            display_name="Username",
            info="Salesforce username (email address)",
            required=True,
        ),
        SecretStrInput(
            name="password",
            display_name="Password",
            info="Salesforce password",
            required=True,
        ),
        SecretStrInput(
            name="security_token",
            display_name="Security Token",
            info="Salesforce security token (required for password authentication)",
            required=False,
        ),
        DropdownInput(
            name="auth_type",
            display_name="Authentication Type",
            info="Select the authentication method to use",
            options=["password", "oauth"],
            value="password",
            required=True,
        ),
    ]

    outputs = [
        Output(display_name="Credentials", name="credentials", method="authenticate"),
    ]

    def authenticate(self) -> Data:
        """Authenticate with Salesforce and return credentials object.

        Returns:
            Data: Authenticated credentials for use in other Salesforce components
        """
        # In a real implementation, this would:
        # 1. Connect to Salesforce using simple-salesforce or salesforce-api
        # 2. Validate credentials
        # 3. Return an authenticated session object

        credentials = {
            "instance_url": self.instance_url,
            "username": self.username,
            "password": self.password,
            "security_token": self.security_token,
            "auth_type": self.auth_type,
            "status": "authenticated",
            "message": f"Successfully authenticated to Salesforce instance: {self.instance_url}",
        }

        return Data(data=credentials)
