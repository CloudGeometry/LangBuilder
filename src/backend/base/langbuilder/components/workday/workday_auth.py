"""Workday authentication component for ActionBridge."""

import base64

from langbuilder.custom import Component
from langbuilder.io import Output, SecretStrInput, StrInput
from langbuilder.schema import Data


class WorkdayAuth(Component):
    """Workday Authentication Component.

    Handles authentication with Workday using API credentials.
    Returns a Data object containing authentication credentials that can be passed to other Workday components.
    """

    display_name = "Workday Authentication"
    description = "Authenticate with Workday using tenant URL, username, and password"
    documentation = "https://community.workday.com/sites/default/files/file-hosting/restapi/index.html"
    icon = "Workday"
    name = "WorkdayAuth"

    inputs = [
        StrInput(
            name="tenant_url",
            display_name="Tenant URL",
            info="Your Workday tenant URL (e.g., https://wd2-impl.workday.com/your-tenant)",
            required=True,
            placeholder="https://wd2-impl.workday.com/your-tenant",
        ),
        StrInput(
            name="username",
            display_name="Username",
            info="Your Workday API username or integration system user",
            required=True,
        ),
        SecretStrInput(
            name="password",
            display_name="Password",
            info="Your Workday API password or integration system password",
            required=True,
        ),
        StrInput(
            name="api_version",
            display_name="API Version",
            info="Workday REST API version",
            value="v1",
            required=False,
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
        """Create authentication credentials for Workday API requests.

        Returns:
            Data: Object containing tenant_url, headers, and auth details
        """
        try:
            # Validate inputs
            if not self.tenant_url.startswith(("http://", "https://")):
                raise ValueError("Tenant URL must start with http:// or https://")

            # Create basic auth credentials
            credentials_string = f"{self.username}:{self.password}"
            encoded_credentials = base64.b64encode(credentials_string.encode("utf-8")).decode("utf-8")

            # Build headers for Workday API
            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            # Determine API version to use
            api_version = self.api_version if self.api_version else "v1"

            # Create auth data object
            auth_data = {
                "tenant_url": self.tenant_url.rstrip("/"),  # Remove trailing slash
                "username": self.username,
                "api_version": api_version,
                "headers": headers,
                "authenticated": True,
            }

            self.status = f"Successfully authenticated with {self.tenant_url}"
            self.log(f"Authentication configured for {self.username} at {self.tenant_url}")

            return Data(data=auth_data)

        except Exception as e:
            error_msg = f"Authentication failed: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "authenticated": False})
