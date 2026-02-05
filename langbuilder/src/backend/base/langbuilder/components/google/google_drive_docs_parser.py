"""
Google Drive Docs Parser (Service Account)

Connects to Google Drive using service account credentials,
finds the latest Google Doc in a shared folder, and extracts its content.

This is the MANUAL trigger version - call it explicitly to parse documents.
"""

from langbuilder.custom.custom_component.component import Component
from langbuilder.io import BoolInput, MessageTextInput, Output, SecretStrInput
from langbuilder.schema.data import Data
from langbuilder.schema.message import Message
from langbuilder.logging import logger


class GoogleDriveDocsParserSA(Component):
    """Parse Google Docs from Drive using a service account.

    Setup:
    1. Create a service account in Google Cloud Console
    2. Enable Google Drive API for your project
    3. Download the service account JSON key
    4. Share the target Drive folder with the service account email
    """

    display_name = "Google Drive Docs Parser"
    description = "Parse the latest Google Doc from a Google Drive folder using service account credentials."
    icon = "Google"
    name = "GoogleDriveDocsParserSA"

    inputs = [
        MessageTextInput(
            name="project_id",
            display_name="Project ID",
            info="Google Cloud project ID",
            required=True,
        ),
        MessageTextInput(
            name="client_email",
            display_name="Client Email",
            info="Service account email (ends with .iam.gserviceaccount.com)",
            required=True,
        ),
        SecretStrInput(
            name="private_key",
            display_name="Private Key",
            info="Private key from service account JSON - paste the entire key including BEGIN/END lines",
            required=True,
        ),
        MessageTextInput(
            name="private_key_id",
            display_name="Private Key ID",
            info="Private key ID from service account JSON",
            required=False,
            advanced=True,
        ),
        MessageTextInput(
            name="client_id",
            display_name="Client ID",
            info="Client ID (numeric) from service account JSON",
            required=False,
            advanced=True,
        ),
        MessageTextInput(
            name="folder_name",
            display_name="Folder Name",
            info="Name of the Google Drive folder (must be shared with service account email)",
            value="Meet recordings",
            required=True,
        ),
        MessageTextInput(
            name="folder_id",
            display_name="Folder ID (Optional)",
            info="Direct folder ID from URL - overrides folder name if provided",
            required=False,
            advanced=True,
        ),
        MessageTextInput(
            name="file_filter",
            display_name="File Name Filter",
            info="Optional: filter files by name (contains match)",
            required=False,
        ),
        MessageTextInput(
            name="specific_file_id",
            display_name="Specific File ID",
            info="Optional: parse a specific file by ID instead of latest",
            required=False,
            advanced=True,
        ),
        BoolInput(
            name="include_metadata",
            display_name="Include Metadata",
            info="Include file metadata (name, modified time, etc.) in output",
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Document Content", name="content", method="parse_document"),
        Output(display_name="Document Data", name="data", method="get_document_data"),
    ]

    def _get_credentials(self):
        """Build credentials from component inputs."""
        from google.oauth2.service_account import Credentials

        private_key = self.private_key
        # Handle SecretStrInput
        if hasattr(private_key, "get_secret_value"):
            private_key = private_key.get_secret_value()

        # Fix escaped newlines (common when pasting from JSON)
        if "\\n" in private_key and "\n" not in private_key:
            private_key = private_key.replace("\\n", "\n")

        # URL-encode the email for the cert URL
        client_email_encoded = self.client_email.replace("@", "%40")

        creds_dict = {
            "type": "service_account",
            "project_id": self.project_id,
            "private_key_id": self.private_key_id or "",
            "private_key": private_key,
            "client_email": self.client_email,
            "client_id": self.client_id or "",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email_encoded}",
            "universe_domain": "googleapis.com",
        }

        return Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/documents.readonly",
            ],
        )

    def _get_drive_service(self):
        """Build the Google Drive API service."""
        from googleapiclient.discovery import build

        credentials = self._get_credentials()
        return build("drive", "v3", credentials=credentials)

    def _find_folder_id(self, service, folder_name: str) -> str:
        """Find folder ID by name."""
        query = (
            f"name = '{folder_name}' and "
            "mimeType = 'application/vnd.google-apps.folder' and "
            "trashed = false"
        )

        results = (
            service.files()
            .list(
                q=query,
                pageSize=10,
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )

        folders = results.get("files", [])
        if not folders:
            raise ValueError(
                f"Folder '{folder_name}' not found. "
                f"Ensure it's shared with: {self.client_email}"
            )

        logger.debug(f"Found folder '{folder_name}' with ID: {folders[0]['id']}")
        return folders[0]["id"]

    def _get_latest_google_doc(self, service, folder_id: str, name_filter: str = "") -> dict:
        """Get the most recently modified Google Doc in the folder."""
        google_doc_mime = "application/vnd.google-apps.document"
        query = (
            f"'{folder_id}' in parents and "
            f"mimeType = '{google_doc_mime}' and "
            "trashed = false"
        )

        if name_filter:
            query += f" and name contains '{name_filter}'"

        results = (
            service.files()
            .list(
                q=query,
                pageSize=1,
                orderBy="modifiedTime desc",
                fields="files(id, name, modifiedTime, createdTime, owners, webViewLink)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )

        files = results.get("files", [])
        if not files:
            msg = "No Google Docs found in folder"
            if name_filter:
                msg += f" matching '{name_filter}'"
            raise ValueError(msg)

        return files[0]

    def _get_file_by_id(self, service, file_id: str) -> dict:
        """Get file metadata by ID."""
        return (
            service.files()
            .get(
                fileId=file_id,
                fields="id, name, modifiedTime, createdTime, owners, webViewLink, mimeType",
                supportsAllDrives=True,
            )
            .execute()
        )

    def _export_google_doc(self, service, file_id: str) -> str:
        """Export Google Doc content as plain text."""
        content = (
            service.files()
            .export(
                fileId=file_id,
                mimeType="text/plain",
            )
            .execute()
        )

        if isinstance(content, bytes):
            return content.decode("utf-8")

        return str(content)

    def _execute(self) -> dict:
        """Main execution logic."""
        service = self._get_drive_service()

        # Get file info - either specific file, or latest from folder
        if self.specific_file_id and self.specific_file_id.strip():
            file_info = self._get_file_by_id(service, self.specific_file_id.strip())
            folder_id = None
        else:
            # Determine folder ID
            if self.folder_id and self.folder_id.strip():
                folder_id = self.folder_id.strip()
            else:
                folder_id = self._find_folder_id(service, self.folder_name)

            file_filter = self.file_filter.strip() if self.file_filter else ""
            file_info = self._get_latest_google_doc(service, folder_id, file_filter)

        # Export content
        content = self._export_google_doc(service, file_info["id"])

        result = {
            "text": content,
            "file_name": file_info["name"],
            "file_id": file_info["id"],
            "modified_time": file_info.get("modifiedTime"),
            "created_time": file_info.get("createdTime"),
            "web_link": file_info.get("webViewLink"),
        }

        if folder_id:
            result["folder_id"] = folder_id
            result["folder_name"] = self.folder_name

        return result

    def parse_document(self) -> Message:
        """Return the document content as a Message."""
        result = self._execute()
        self.status = f"Parsed: {result['file_name']}"
        return Message(text=result["text"])

    def get_document_data(self) -> Data:
        """Return document content with metadata as Data."""
        result = self._execute()
        self.status = f"Parsed: {result['file_name']}"

        if self.include_metadata:
            return Data(data=result, text=result["text"])
        else:
            return Data(data={"text": result["text"]}, text=result["text"])
