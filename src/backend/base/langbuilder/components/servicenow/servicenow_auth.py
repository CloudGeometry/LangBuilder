"""ServiceNow authentication component for ActionBridge."""

import base64

from langbuilder.custom import Component
from langbuilder.io import DropdownInput, Output, SecretStrInput, StrInput
from langbuilder.schema import Data


class ServiceNowAuth(Component):
    """ServiceNow Authentication Component.

    Handles authentication with ServiceNow instances using Basic Auth or OAuth.
    Returns a Data object containing authentication credentials that can be passed to other ServiceNow components.
    """

    display_name = "ServiceNow Authentication"
    description = "Authenticate with ServiceNow instance using credentials or OAuth"
    documentation = "https://developer.servicenow.com/dev.do#!/reference/api/latest/rest/c_TableAPI"
    icon = "ServiceNow"
    name = "ServiceNowAuth"

    inputs = [
        StrInput(
            name="instance_url",
            display_name="Instance URL",
            info="Your ServiceNow instance URL (e.g., https://your-instance.service-now.com)",
            required=True,
            placeholder="https://your-instance.service-now.com",
        ),
        StrInput(
            name="username",
            display_name="Username",
            info="ServiceNow username for authentication",
            required=True,
        ),
        SecretStrInput(
            name="password",
            display_name="Password / Token",
            info="ServiceNow password or OAuth token",
            required=True,
        ),
        DropdownInput(
            name="auth_type",
            display_name="Authentication Type",
            options=["basic", "oauth"],
            value="basic",
            info="Authentication method - Basic Auth or OAuth Bearer token",
        ),
    ]

    outputs = [
        Output(
            display_name="Auth Credentials",
            name="credentials",
            method="authenticate",
        ),
    ]

    def authenticate(self) -> Data:
        """Create authentication credentials for ServiceNow API requests.

        Returns:
            Data: Object containing instance_url, headers, and auth details
        """
        try:
            # Validate inputs
            if not self.instance_url.startswith(("http://", "https://")):
                raise ValueError("Instance URL must start with http:// or https://")

            # Build headers based on auth type
            if self.auth_type == "basic":
                # Create basic auth credentials
                credentials_string = f"{self.username}:{self.password}"
                encoded_credentials = base64.b64encode(credentials_string.encode("utf-8")).decode("utf-8")

                headers = {
                    "Authorization": f"Basic {encoded_credentials}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }
            else:  # oauth
                headers = {
                    "Authorization": f"Bearer {self.password}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }

            # Create auth data object
            auth_data = {
                "instance_url": self.instance_url.rstrip("/"),  # Remove trailing slash
                "username": self.username,
                "headers": headers,
                "auth_type": self.auth_type,
                "authenticated": True,
            }

            self.status = f"Successfully authenticated with {self.instance_url}"
            self.log(f"Authentication configured for {self.username} at {self.instance_url}")

            return Data(data=auth_data)

        except Exception as e:
            error_msg = f"Authentication failed: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "authenticated": False})
