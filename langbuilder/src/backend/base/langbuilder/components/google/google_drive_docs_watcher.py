"""
Google Drive Docs Watcher (Service Account)

Monitors a Google Drive folder for new Google Docs and processes them automatically.
Uses polling to detect new documents since last check.

This component is designed for automation workflows like MeetBot transcript processing.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from langbuilder.custom.custom_component.component import Component
from langbuilder.io import (
    BoolInput,
    IntInput,
    MessageTextInput,
    Output,
    SecretStrInput,
)
from langbuilder.logging import logger
from langbuilder.schema.data import Data
from langbuilder.schema.message import Message


class GoogleDriveDocsWatcher(Component):
    """Watch a Google Drive folder for new Google Docs.

    This component monitors a shared folder and returns documents that have been
    added or modified since the last check. It maintains state to track processed
    files and avoid duplicates.

    Setup:
    1. Create a service account in Google Cloud Console
    2. Enable Google Drive API for your project
    3. Download the service account JSON key
    4. Share the target Drive folder with the service account email

    Use Cases:
    - Automatic transcript processing from Google Meet recordings
    - Document intake workflows
    - Real-time document monitoring
    """

    display_name = "Google Drive Docs Watcher"
    description = "Monitor a Google Drive folder for new documents and process them automatically."
    icon = "Google"
    name = "GoogleDriveDocsWatcher"

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
            info="Name of the Google Drive folder to monitor (must be shared with service account email)",
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
        IntInput(
            name="max_files",
            display_name="Max Files Per Check",
            info="Maximum number of new files to process in a single check",
            value=10,
            advanced=True,
        ),
        IntInput(
            name="lookback_hours",
            display_name="Lookback Hours",
            info="On first run, look back this many hours for existing documents (0 = only future docs)",
            value=24,
            advanced=True,
        ),
        MessageTextInput(
            name="state_key",
            display_name="State Key",
            info="Unique key for storing watcher state (allows multiple watchers)",
            value="default",
            advanced=True,
        ),
        BoolInput(
            name="include_metadata",
            display_name="Include Metadata",
            info="Include file metadata (name, modified time, etc.) in output",
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="mark_as_processed",
            display_name="Mark as Processed",
            info="Track processed files to avoid reprocessing (disable for testing)",
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="New Documents", name="documents", method="check_for_new_documents"),
        Output(display_name="Has New Documents", name="has_new", method="has_new_documents"),
        Output(display_name="Document Count", name="count", method="get_new_document_count"),
    ]

    def _get_credentials(self):
        """Build credentials from component inputs."""
        from google.oauth2.service_account import Credentials

        private_key = self.private_key
        if hasattr(private_key, "get_secret_value"):
            private_key = private_key.get_secret_value()

        # Fix escaped newlines
        if "\\n" in private_key and "\n" not in private_key:
            private_key = private_key.replace("\\n", "\n")

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

    def _get_state_file_path(self) -> Path:
        """Get the path for storing watcher state."""
        # Use component's data directory if available, otherwise temp
        import tempfile

        state_dir = Path(tempfile.gettempdir()) / "langbuilder_drive_watcher"
        state_dir.mkdir(exist_ok=True)

        # Create unique filename based on folder and state key
        folder_identifier = self.folder_id or self.folder_name.replace(" ", "_")
        filename = f"watcher_state_{folder_identifier}_{self.state_key}.json"
        return state_dir / filename

    def _load_state(self) -> dict:
        """Load the watcher state from disk."""
        state_file = self._get_state_file_path()
        if state_file.exists():
            try:
                with open(state_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load watcher state: {e}")
        return {"processed_ids": [], "last_check": None}

    def _save_state(self, state: dict) -> None:
        """Save the watcher state to disk."""
        state_file = self._get_state_file_path()
        try:
            with open(state_file, "w") as f:
                json.dump(state, f)
        except OSError as e:
            logger.warning(f"Failed to save watcher state: {e}")

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

        return folders[0]["id"]

    def _get_new_google_docs(
        self, service, folder_id: str, since_time: str | None, processed_ids: list[str]
    ) -> list[dict]:
        """Get Google Docs added/modified since the given time."""
        google_doc_mime = "application/vnd.google-apps.document"

        # Build query
        query_parts = [
            f"'{folder_id}' in parents",
            f"mimeType = '{google_doc_mime}'",
            "trashed = false",
        ]

        if self.file_filter:
            query_parts.append(f"name contains '{self.file_filter.strip()}'")

        if since_time:
            query_parts.append(f"modifiedTime > '{since_time}'")

        query = " and ".join(query_parts)

        results = (
            service.files()
            .list(
                q=query,
                pageSize=self.max_files,
                orderBy="modifiedTime desc",
                fields="files(id, name, modifiedTime, createdTime, owners, webViewLink)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )

        files = results.get("files", [])

        # Filter out already processed files
        new_files = [f for f in files if f["id"] not in processed_ids]

        return new_files

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

    def _get_initial_since_time(self) -> str | None:
        """Calculate the initial 'since' time for first run."""
        if self.lookback_hours <= 0:
            return datetime.now(timezone.utc).isoformat()

        from datetime import timedelta

        lookback_time = datetime.now(timezone.utc) - timedelta(hours=self.lookback_hours)
        return lookback_time.isoformat()

    def _check_for_documents(self) -> tuple[list[dict], dict]:
        """Main logic to check for new documents.

        Returns:
            Tuple of (list of new documents with content, updated state)
        """
        service = self._get_drive_service()

        # Load state
        state = self._load_state()
        processed_ids = set(state.get("processed_ids", []))
        last_check = state.get("last_check")

        # Determine folder ID
        if self.folder_id and self.folder_id.strip():
            folder_id = self.folder_id.strip()
        else:
            folder_id = self._find_folder_id(service, self.folder_name)

        # Determine since time
        since_time = last_check or self._get_initial_since_time()

        # Get new documents
        new_files = self._get_new_google_docs(service, folder_id, since_time, list(processed_ids))

        # Process each document
        documents = []
        for file_info in new_files:
            try:
                content = self._export_google_doc(service, file_info["id"])

                doc = {
                    "text": content,
                    "file_name": file_info["name"],
                    "file_id": file_info["id"],
                    "modified_time": file_info.get("modifiedTime"),
                    "created_time": file_info.get("createdTime"),
                    "web_link": file_info.get("webViewLink"),
                    "folder_id": folder_id,
                    "folder_name": self.folder_name,
                }
                documents.append(doc)

                # Mark as processed
                if self.mark_as_processed:
                    processed_ids.add(file_info["id"])

            except Exception as e:
                logger.error(f"Failed to process document {file_info['name']}: {e}")

        # Update state
        new_state = {
            "processed_ids": list(processed_ids)[-1000:],  # Keep last 1000 to prevent unbounded growth
            "last_check": datetime.now(timezone.utc).isoformat(),
        }

        if self.mark_as_processed:
            self._save_state(new_state)

        return documents, new_state

    def check_for_new_documents(self) -> list[Data]:
        """Check for and return new documents as a list of Data objects."""
        documents, _state = self._check_for_documents()

        if not documents:
            self.status = "No new documents found"
            return []

        self.status = f"Found {len(documents)} new document(s)"

        result = []
        for doc in documents:
            if self.include_metadata:
                result.append(Data(data=doc, text=doc["text"]))
            else:
                result.append(Data(data={"text": doc["text"]}, text=doc["text"]))

        return result

    def has_new_documents(self) -> Message:
        """Check if there are new documents (for conditional branching)."""
        documents, _state = self._check_for_documents()

        has_new = len(documents) > 0
        self.status = f"Has new: {has_new} ({len(documents)} docs)"

        return Message(text=str(has_new).lower())

    def get_new_document_count(self) -> Message:
        """Get the count of new documents."""
        documents, _state = self._check_for_documents()

        self.status = f"Found {len(documents)} new document(s)"
        return Message(text=str(len(documents)))
