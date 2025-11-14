from langbuilder.custom import Component
from langbuilder.io import DataInput, IntInput, Output, StrInput
from langbuilder.schema import Data


class SharePointListItems(Component):
    display_name = "SharePoint List Items"
    description = "Retrieve items from a SharePoint list with pagination"
    icon = "SharePoint"
    name = "SharePointListItems"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="Auth Credentials",
            info="Authentication credentials from SharePoint Authentication",
            required=True
        ),
        StrInput(
            name="list_name",
            display_name="List Name",
            info="Name of the SharePoint list",
            required=True
        ),
        StrInput(
            name="folder_path",
            display_name="Folder Path",
            info="Optional folder path to filter items",
            value="/"
        ),
        IntInput(
            name="limit",
            display_name="Result Limit",
            info="Maximum number of items to retrieve",
            value=100
        ),
    ]

    outputs = [
        Output(display_name="Items", name="items", method="list_items")
    ]

    def list_items(self) -> Data:
        items_data = {
            "list_name": self.list_name,
            "folder_path": self.folder_path,
            "limit": self.limit,
            "items": [],
            "total_count": 0,
        }
        return Data(data=items_data)
