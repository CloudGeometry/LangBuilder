"""Notion Authentication Component.

This component handles authentication with the Notion API and stores credentials
for use in other Notion components.
"""

from langbuilder.custom.custom_component.component import Component
from langbuilder.io import Output, SecretStrInput, StrInput
from langbuilder.schema.data import Data


class NotionAuthComponent(Component):
    """Authenticate with Notion API and retrieve credentials.

    This component securely stores your Notion API credentials (API key and workspace
    information) for use in other Notion-based components. The API key can be obtained
    from https://www.notion.so/my-integrations after creating a new integration.
    """

    display_name = "Notion Authentication"
    description = (
        "Authenticate with Notion API using an API key. "
        "Get your API key from https://www.notion.so/my-integrations"
    )
    icon = "Notion"
    name = "NotionAuth"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="Notion API Key",
            info="Your Notion API key from https://www.notion.so/my-integrations. "
            "Create a new integration and copy the Internal Integration Token.",
            required=True,
        ),
        StrInput(
            name="workspace_name",
            display_name="Workspace Name",
            info="A friendly name for your Notion workspace (for reference).",
            placeholder="My Workspace",
            required=False,
        ),
    ]

    outputs = [
        Output(
            display_name="Credentials",
            name="credentials",
            method="build_credentials",
        ),
    ]

    def build_credentials(self) -> Data:
        """Build and return Notion API credentials.

        Returns:
            Data: A Data object containing the API key and workspace information.

        Raises:
            ValueError: If the API key is not provided.
        """
        if not self.api_key:
            msg = "Notion API key is required"
            raise ValueError(msg)

        credentials = {
            "api_key": self.api_key,
            "workspace_name": self.workspace_name or "Notion Workspace",
            "authenticated": True,
        }

        self.status = f"Authenticated with workspace: {self.workspace_name or 'Notion'}"
        return Data(data=credentials)
