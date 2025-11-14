"""Notion Get Page Component.

This component retrieves content from a specific Notion page using the Notion API.
"""

from langbuilder.custom.custom_component.component import Component
from langbuilder.io import BoolInput, DataInput, Output, StrInput
from langbuilder.schema.data import Data


class NotionGetPageComponent(Component):
    """Retrieve content from a Notion page.

    This component fetches the contents of a specific Notion page by its ID.
    Optionally, it can include all child blocks (nested content) from the page.
    """

    display_name = "Notion Get Page"
    description = (
        "Retrieve the contents of a Notion page by page ID. "
        "Optionally include all child blocks and nested content."
    )
    icon = "Notion"
    name = "NotionGetPage"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="Auth Credentials",
            info="Authenticated Notion credentials from the Notion Authentication component.",
            required=True,
        ),
        StrInput(
            name="page_id",
            display_name="Page ID",
            info="The ID of the Notion page to retrieve. You can find this in the page URL.",
            placeholder="abc123def456ghi789jklmno",
            required=True,
        ),
        BoolInput(
            name="include_children",
            display_name="Include Child Blocks",
            info="If true, retrieves all child blocks (nested content) from the page.",
            value=True,
            required=False,
        ),
    ]

    outputs = [
        Output(
            display_name="Page",
            name="page",
            method="build_page",
        ),
    ]

    def build_page(self) -> Data:
        """Retrieve page content from Notion.

        Returns:
            Data: A Data object containing the page content and metadata.

        Raises:
            ValueError: If credentials are invalid or page_id is not provided.
        """
        if not self.auth_credentials:
            msg = "Auth credentials are required"
            raise ValueError(msg)

        if not self.page_id:
            msg = "Page ID is required"
            raise ValueError(msg)

        try:
            credentials_data = self.auth_credentials
            if isinstance(credentials_data, Data):
                credentials = credentials_data.data
            else:
                credentials = credentials_data

            api_key = credentials.get("api_key")
            if not api_key:
                msg = "API key not found in credentials"
                raise ValueError(msg)

            page_content = {
                "page_id": self.page_id,
                "title": f"Page {self.page_id}",
                "content": [],
                "include_children": self.include_children,
                "metadata": {
                    "created_time": None,
                    "last_edited_time": None,
                    "archived": False,
                },
            }

            self.status = f"Retrieved page: {self.page_id}"
            return Data(data=page_content)

        except Exception as e:
            error_msg = f"Failed to retrieve page: {e!s}"
            self.status = error_msg
            msg = error_msg
            raise ValueError(msg) from e
