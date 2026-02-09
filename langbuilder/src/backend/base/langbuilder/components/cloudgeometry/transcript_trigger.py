"""
Transcript Trigger - Custom LangBuilder Component

All-in-one component for the trigger flow:
1. Parses the input JSON (slack_id, last_processed) from ChatInput
2. Fetches the latest Google Doc from GDrive (reuses GoogleDriveDocsParserSA patterns)
3. Compares timestamps against last_processed
4. Returns JSON result indicating whether new transcripts exist

This keeps the trigger flow to just 3 nodes: ChatInput → TranscriptTrigger → ChatOutput
"""

import json

from langbuilder.custom import Component
from langbuilder.inputs.inputs import HandleInput
from langbuilder.io import MessageTextInput, Output, SecretStrInput
from langbuilder.logging import logger
from langbuilder.schema.message import Message


class TranscriptTrigger(Component):
    display_name = "Transcript Trigger"
    description = (
        "Checks Google Drive for new transcripts by comparing against "
        "the last processed timestamp. Returns JSON with has_new_transcripts, "
        "new_files, and latest_file."
    )
    icon = "Google"
    name = "TranscriptTrigger"

    inputs = [
        # PM config from DynamoDB — contains last_processed_transcript for comparison
        HandleInput(
            name="pm_config",
            display_name="PM Config (from DynamoDB)",
            info="Data output from DynamoDB PM Config Reader. Contains last_processed_transcript with modified_time.",
            input_types=["Data"],
            required=False,
        ),
        # GDrive credentials — injected via tweaks from the scheduler
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
    ]

    outputs = [
        Output(display_name="Result", name="result", method="check"),
    ]

    # ------------------------------------------------------------------
    # Google Drive helpers (from GoogleDriveDocsParserSA)
    # ------------------------------------------------------------------

    def _get_credentials(self):
        """Build credentials from component inputs."""
        from google.oauth2.service_account import Credentials

        private_key = self.private_key
        if hasattr(private_key, "get_secret_value"):
            private_key = private_key.get_secret_value()

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

        return build("drive", "v3", credentials=self._get_credentials())

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

    def _list_recent_docs(self, service, folder_id: str, name_filter: str = "") -> list[dict]:
        """Get the most recently modified Google Docs in the folder."""
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
                pageSize=10,
                orderBy="modifiedTime desc",
                fields="files(id, name, modifiedTime, createdTime)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        return results.get("files", [])

    # ------------------------------------------------------------------
    # Timestamp comparison (from TranscriptChangeDetector)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_time(time_str):
        if not time_str:
            return None
        from datetime import datetime, timezone

        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f+00:00",
            "%Y-%m-%dT%H:%M:%S+00:00",
            "%Y-%m-%d %H:%M:%S",
        ):
            try:
                dt = datetime.strptime(time_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
        return None

    def _is_new(self, file_info: dict, last_processed: dict) -> tuple[bool, str]:
        """Return (is_new, reason).

        Comparison is purely timestamp-based:
        - If no last_processed exists → everything is new (first run)
        - If file's modifiedTime > last_processed.modified_time → new
        - Otherwise → already processed (even if file_id differs)
        """
        last_modified = last_processed.get("modified_time", "")

        if not last_modified:
            return True, "first_run"

        cur_modified = file_info.get("modifiedTime", "")
        cur_dt = self._parse_time(cur_modified)
        last_dt = self._parse_time(last_modified)

        if cur_dt and last_dt and cur_dt > last_dt:
            return True, "new_transcript"

        return False, "already_processed"

    # ------------------------------------------------------------------
    # Main output method
    # ------------------------------------------------------------------

    def _extract_last_processed(self) -> dict:
        """Extract last_processed_transcript from the pm_config Data input."""
        pm = self.pm_config
        if pm is None:
            return {}
        # Handle Data object
        if hasattr(pm, "data") and isinstance(pm.data, dict):
            # scan_enabled returns {pm_configs: [...], count: N}
            configs = pm.data.get("pm_configs", [])
            if configs and isinstance(configs, list):
                return configs[0].get("last_processed_transcript", {})
            # get_item might return the config directly
            return pm.data.get("last_processed_transcript", {})
        if isinstance(pm, dict):
            return pm.get("last_processed_transcript", {})
        return {}

    def check(self) -> Message:
        # 1. Get last_processed from DynamoDB PM config
        last_processed = self._extract_last_processed()
        logger.info(f"last_processed_transcript: {last_processed}")

        # 2. Fetch latest docs from GDrive
        service = self._get_drive_service()
        if self.folder_id and self.folder_id.strip():
            fid = self.folder_id.strip()
        else:
            fid = self._find_folder_id(service, self.folder_name)

        file_filter = self.file_filter.strip() if self.file_filter else ""
        files = self._list_recent_docs(service, fid, file_filter)

        if not files:
            result = {
                "has_new_transcripts": False,
                "reason": "no_files_found",
                "new_files": [],
                "latest_file": {},
            }
            self.status = "No files found"
            return Message(text=json.dumps(result))

        # 3. Compare each file against last_processed
        new_files = []
        for f in files:
            is_new, reason = self._is_new(f, last_processed)
            if is_new:
                new_files.append({
                    "file_id": f["id"],
                    "name": f["name"],
                    "modified_time": f.get("modifiedTime", ""),
                    "reason": reason,
                })

        latest = files[0]
        result = {
            "has_new_transcripts": len(new_files) > 0,
            "reason": "new_transcripts" if new_files else "already_processed",
            "new_files": new_files,
            "latest_file": {
                "file_id": latest["id"],
                "name": latest["name"],
                "modified_time": latest.get("modifiedTime", ""),
            },
        }

        self.status = f"{'NEW' if new_files else 'SKIP'}: {len(new_files)} file(s)"
        return Message(text=json.dumps(result))
