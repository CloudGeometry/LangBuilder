"""Jira authentication component for ActionBridge."""

import base64

from langbuilder.custom import Component
from langbuilder.io import DropdownInput, Output, SecretStrInput, StrInput
from langbuilder.schema import Data


class JiraAuth(Component):
    """Jira Authentication Component.

    Handles authentication with Jira Cloud or Jira Server/Data Center using various methods.
    Returns a Data object containing authentication credentials that can be passed to other Jira components.
    """

    display_name = "Jira Authentication"
    description = "Authenticate with Jira Cloud or Jira Server using API tokens or credentials"
    documentation = "https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/#authentication"
    icon = "Jira"
    name = "JiraAuth"

    inputs = [
        StrInput(
            name="jira_url",
            display_name="Jira URL",
            info="Your Jira instance URL (e.g., https://your-domain.atlassian.net)",
            required=True,
            placeholder="https://your-domain.atlassian.net",
        ),
        StrInput(
            name="email",
            display_name="Email",
            info="Your Atlassian account email (for Cloud) or username (for Server)",
            required=True,
        ),
        SecretStrInput(
            name="api_token",
            display_name="API Token / Password",
            info="API Token for Cloud or password for Server/Data Center",
            required=True,
        ),
        DropdownInput(
            name="auth_type",
            display_name="Authentication Type",
            options=["basic", "bearer"],
            value="basic",
            info="Authentication method - Basic for most cases, Bearer for specific APIs",
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
        """Create authentication credentials for Jira API requests.

        Returns:
            Data: Object containing jira_url, headers, and auth details
        """
        try:
            import os

            # Auto-load credentials from environment variables if not provided
            email = self.email
            api_token = self.api_token
            jira_url = self.jira_url

            # If fields are empty, try to load from environment
            if not email:
                email = os.getenv("JIRA_EMAIL", "")
                if email:
                    self.log("Using JIRA_EMAIL from environment variables")

            if not api_token:
                api_token = os.getenv("JIRA_API_KEY", "")
                if api_token:
                    self.log("Using JIRA_API_KEY from environment variables")

            if not jira_url:
                jira_url = os.getenv("JIRA_URL", "")
                if jira_url:
                    self.log("Using JIRA_URL from environment variables")

            # Validate we have credentials (either from input or env)
            if not email or not api_token or not jira_url:
                raise ValueError(
                    "Missing Jira credentials. Please provide email, API token, and Jira URL, "
                    "or set JIRA_EMAIL, JIRA_API_KEY, and JIRA_URL environment variables."
                )

            # Validate URL format
            if not jira_url.startswith(("http://", "https://")):
                raise ValueError("Jira URL must start with http:// or https://")

            # Create basic auth credentials
            credentials_string = f"{email}:{api_token}"
            encoded_credentials = base64.b64encode(credentials_string.encode("utf-8")).decode("utf-8")

            # Build headers based on auth type
            if self.auth_type == "basic":
                headers = {
                    "Authorization": f"Basic {encoded_credentials}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }
            else:  # bearer
                headers = {
                    "Authorization": f"Bearer {self.api_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }

            # Create auth data object
            auth_data = {
                "jira_url": jira_url.rstrip("/"),  # Remove trailing slash
                "email": email,
                "headers": headers,
                "auth_type": self.auth_type,
                "authenticated": True,
            }

            self.status = f"Successfully authenticated with {jira_url}"
            self.log(f"Authentication configured for {email} at {jira_url}")

            return Data(data=auth_data)

        except Exception as e:
            error_msg = f"Authentication failed: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "authenticated": False})
