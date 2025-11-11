"""
Google Drive API Integration Module
Handles search, file access, and content extraction from Google Drive
"""

from typing import List, Dict, Optional, Any, AsyncIterator
import httpx
from datetime import datetime
import json
import mimetypes
import io
from urllib.parse import quote

from open_webui.services.oauth_token_manager import token_manager
from open_webui.utils.oauth_services import ServiceType, get_service_config


class GoogleDriveFile:
    """Represents a Google Drive file with metadata"""

    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id", "")
        self.name = data.get("name", "")
        self.mime_type = data.get("mimeType", "")
        self.size = data.get("size")
        self.created_time = data.get("createdTime")
        self.modified_time = data.get("modifiedTime")
        self.web_view_link = data.get("webViewLink", "")
        self.parents = data.get("parents", [])
        self.owners = data.get("owners", [])
        self.permissions = data.get("permissions", [])
        self.description = data.get("description", "")
        self.full_text = data.get("fullText", "")  # For indexed content

    def is_readable(self) -> bool:
        """Check if file can be read (text/document formats)"""
        readable_types = [
            "application/vnd.google-apps.document",  # Google Docs
            "application/vnd.google-apps.spreadsheet",  # Google Sheets
            "application/vnd.google-apps.presentation",  # Google Slides
            "text/plain",
            "text/markdown",
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # PPTX
            "text/csv",
            "application/json",
            "text/html"
        ]
        return self.mime_type in readable_types

    def get_export_mime_type(self) -> Optional[str]:
        """Get appropriate export MIME type for Google Workspace files"""
        google_mime_exports = {
            "application/vnd.google-apps.document": "text/plain",
            "application/vnd.google-apps.spreadsheet": "text/csv",
            "application/vnd.google-apps.presentation": "text/plain",
            "application/vnd.google-apps.drawing": "image/png"
        }
        return google_mime_exports.get(self.mime_type)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "mime_type": self.mime_type,
            "size": self.size,
            "created_time": self.created_time,
            "modified_time": self.modified_time,
            "web_view_link": self.web_view_link,
            "parents": self.parents,
            "owners": self.owners,
            "description": self.description,
            "is_readable": self.is_readable(),
            "full_text": self.full_text
        }


class GoogleDriveIntegration:
    """Google Drive API integration class"""

    def __init__(self):
        self.base_url = "https://www.googleapis.com/drive/v3"
        self.config = get_service_config(ServiceType.GOOGLE_DRIVE)

    async def _get_headers(self, user_id: str) -> Dict[str, str]:
        """Get authorization headers with valid token"""
        access_token = await token_manager.get_valid_token(user_id, ServiceType.GOOGLE_DRIVE)
        if not access_token:
            raise ValueError("User not authorized for Google Drive")

        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    async def _make_request(self, user_id: str, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to Google Drive API"""
        headers = await self._get_headers(user_id)
        headers.update(kwargs.pop("headers", {}))

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(method, url, headers=headers, **kwargs)

            if response.status_code == 401:
                # Try to refresh token and retry once
                await token_manager.refresh_token_if_needed(user_id, ServiceType.GOOGLE_DRIVE)
                headers = await self._get_headers(user_id)
                headers.update(kwargs.get("headers", {}))
                response = await client.request(method, url, headers=headers, **kwargs)

            if response.status_code != 200:
                raise httpx.HTTPError(
                    f"Google Drive API request failed: {response.status_code} - {response.text}"
                )

            return response.json()

    async def search_files(
        self,
        user_id: str,
        query: str,
        file_types: Optional[List[str]] = None,
        limit: int = 50,
        include_content: bool = False
    ) -> List[GoogleDriveFile]:
        """Search for files in Google Drive"""

        # Build search query
        search_parts = [f"fullText contains '{query}'"]

        if file_types:
            mime_type_conditions = []
            for file_type in file_types:
                if file_type.lower() == "documents":
                    mime_type_conditions.extend([
                        "mimeType='application/vnd.google-apps.document'",
                        "mimeType='application/pdf'",
                        "mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'"
                    ])
                elif file_type.lower() == "spreadsheets":
                    mime_type_conditions.extend([
                        "mimeType='application/vnd.google-apps.spreadsheet'",
                        "mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'",
                        "mimeType='text/csv'"
                    ])
                elif file_type.lower() == "presentations":
                    mime_type_conditions.extend([
                        "mimeType='application/vnd.google-apps.presentation'",
                        "mimeType='application/vnd.openxmlformats-officedocument.presentationml.presentation'"
                    ])

            if mime_type_conditions:
                search_parts.append(f"({' or '.join(mime_type_conditions)})")

        # Add trashed = false to exclude deleted files
        search_parts.append("trashed = false")

        search_query = " and ".join(search_parts)

        # Set up request parameters
        params = {
            "q": search_query,
            "pageSize": min(limit, 100),  # Google Drive max is 1000
            "fields": "files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink,parents,owners,permissions,description)",
            "orderBy": "modifiedTime desc"
        }

        url = f"{self.base_url}/files"
        response_data = await self._make_request(user_id, "GET", url, params=params)

        files = []
        for file_data in response_data.get("files", []):
            drive_file = GoogleDriveFile(file_data)

            # Optionally include file content for text files
            if include_content and drive_file.is_readable():
                try:
                    content = await self.get_file_content(user_id, drive_file.id)
                    file_data["fullText"] = content
                    drive_file = GoogleDriveFile(file_data)
                except Exception as e:
                    print(f"Failed to get content for file {drive_file.id}: {e}")

            files.append(drive_file)

        return files

    async def get_file_metadata(self, user_id: str, file_id: str) -> GoogleDriveFile:
        """Get detailed metadata for a specific file"""
        url = f"{self.base_url}/files/{file_id}"
        params = {
            "fields": "id,name,mimeType,size,createdTime,modifiedTime,webViewLink,parents,owners,permissions,description"
        }

        response_data = await self._make_request(user_id, "GET", url, params=params)
        return GoogleDriveFile(response_data)

    async def get_file_content(self, user_id: str, file_id: str, max_size: int = 10 * 1024 * 1024) -> str:
        """Get text content of a file"""
        file_metadata = await self.get_file_metadata(user_id, file_id)

        if not file_metadata.is_readable():
            raise ValueError(f"File type {file_metadata.mime_type} is not readable")

        # Check file size
        if file_metadata.size and int(file_metadata.size) > max_size:
            raise ValueError(f"File too large: {file_metadata.size} bytes (max {max_size})")

        headers = await self._get_headers(user_id)

        async with httpx.AsyncClient(timeout=60.0) as client:
            # For Google Workspace files, use export endpoint
            export_mime_type = file_metadata.get_export_mime_type()
            if export_mime_type:
                url = f"{self.base_url}/files/{file_id}/export"
                params = {"mimeType": export_mime_type}
            else:
                # For regular files, use download endpoint
                url = f"{self.base_url}/files/{file_id}"
                params = {"alt": "media"}

            response = await client.get(url, headers=headers, params=params)

            if response.status_code != 200:
                raise httpx.HTTPError(
                    f"Failed to download file content: {response.status_code} - {response.text}"
                )

            # Return text content
            content = response.text if response.text else response.content.decode('utf-8', errors='ignore')
            return content

    async def list_folders(self, user_id: str, parent_id: Optional[str] = None) -> List[GoogleDriveFile]:
        """List folders in Drive"""
        query_parts = ["mimeType='application/vnd.google-apps.folder'", "trashed = false"]

        if parent_id:
            query_parts.append(f"'{parent_id}' in parents")

        params = {
            "q": " and ".join(query_parts),
            "fields": "files(id,name,createdTime,modifiedTime,parents)",
            "orderBy": "name"
        }

        url = f"{self.base_url}/files"
        response_data = await self._make_request(user_id, "GET", url, params=params)

        return [GoogleDriveFile(file_data) for file_data in response_data.get("files", [])]

    async def get_recent_files(self, user_id: str, limit: int = 20) -> List[GoogleDriveFile]:
        """Get recently modified files"""
        params = {
            "q": "trashed = false",
            "pageSize": min(limit, 100),
            "fields": "files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink,owners)",
            "orderBy": "modifiedTime desc"
        }

        url = f"{self.base_url}/files"
        response_data = await self._make_request(user_id, "GET", url, params=params)

        return [GoogleDriveFile(file_data) for file_data in response_data.get("files", [])]

    async def get_shared_files(self, user_id: str, limit: int = 50) -> List[GoogleDriveFile]:
        """Get files shared with the user"""
        params = {
            "q": "sharedWithMe = true and trashed = false",
            "pageSize": min(limit, 100),
            "fields": "files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink,owners,sharingUser)",
            "orderBy": "modifiedTime desc"
        }

        url = f"{self.base_url}/files"
        response_data = await self._make_request(user_id, "GET", url, params=params)

        return [GoogleDriveFile(file_data) for file_data in response_data.get("files", [])]

    async def search_by_content_type(
        self,
        user_id: str,
        content_type: str,
        limit: int = 50
    ) -> List[GoogleDriveFile]:
        """Search files by content type (documents, spreadsheets, presentations, etc.)"""

        mime_type_queries = {
            "documents": [
                "mimeType='application/vnd.google-apps.document'",
                "mimeType='application/pdf'",
                "mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'",
                "mimeType='text/plain'"
            ],
            "spreadsheets": [
                "mimeType='application/vnd.google-apps.spreadsheet'",
                "mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'",
                "mimeType='text/csv'"
            ],
            "presentations": [
                "mimeType='application/vnd.google-apps.presentation'",
                "mimeType='application/vnd.openxmlformats-officedocument.presentationml.presentation'"
            ],
            "images": [
                "mimeType contains 'image/'"
            ],
            "pdfs": [
                "mimeType='application/pdf'"
            ]
        }

        mime_conditions = mime_type_queries.get(content_type.lower(), [])
        if not mime_conditions:
            raise ValueError(f"Unsupported content type: {content_type}")

        query = f"({' or '.join(mime_conditions)}) and trashed = false"

        params = {
            "q": query,
            "pageSize": min(limit, 100),
            "fields": "files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink,owners)",
            "orderBy": "modifiedTime desc"
        }

        url = f"{self.base_url}/files"
        response_data = await self._make_request(user_id, "GET", url, params=params)

        return [GoogleDriveFile(file_data) for file_data in response_data.get("files", [])]

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get information about the user's Google Drive"""
        headers = await self._get_headers(user_id)

        async with httpx.AsyncClient() as client:
            # Get drive info
            about_response = await client.get(
                f"{self.base_url}/about",
                headers=headers,
                params={"fields": "user,storageQuota"}
            )

            if about_response.status_code != 200:
                raise httpx.HTTPError(f"Failed to get user info: {about_response.text}")

            return about_response.json()


# Global instance
google_drive = GoogleDriveIntegration()