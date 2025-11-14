from langbuilder.custom import Component
from langbuilder.io import BoolInput, DataInput, Output, StrInput
from langbuilder.schema import Data


class SharePointGetFile(Component):
    display_name = "SharePoint Get File"
    description = "Retrieve a file from SharePoint document library"
    icon = "SharePoint"
    name = "SharePointGetFile"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="Auth Credentials",
            info="Authentication credentials from SharePoint Authentication",
            required=True
        ),
        StrInput(
            name="file_path",
            display_name="File Path",
            placeholder="/Shared Documents/file.docx",
            required=True
        ),
        BoolInput(
            name="download_content",
            display_name="Download Content",
            info="Whether to download the complete file content",
            value=False
        ),
    ]

    outputs = [
        Output(display_name="File", name="file", method="get_file")
    ]

    def get_file(self) -> Data:
        file_data = {
            "file_path": self.file_path,
            "name": self.file_path.split("/")[-1] if self.file_path else "",
            "size": 0,
            "modified_date": None,
            "created_by": None,
            "download_content": self.download_content,
        }
        return Data(data=file_data)
