"""
Zoho Recruit Attachment Component - LangBuilder Custom Component

Handle CV/Resume attachments for candidates in Zoho Recruit.

Author: CloudGeometry
Project: AI Recruitment Command Center
"""

from langflow.custom import Component
from langflow.io import HandleInput, StrInput, DropdownInput, FileInput, Output
from langflow.schema import Data
import httpx
import base64
import io
from typing import Dict, List, Any, Optional

# Optional PDF text extraction
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


class ZohoRecruitAttachmentComponent(Component):
    """
    Handle CV/Resume attachments for candidates in Zoho Recruit.

    Operations:
    - list: List all attachments for a record
    - download: Download an attachment by ID
    - upload: Upload a new attachment
    - get_resume_text: Extract text from PDF resume (requires pypdf)

    This component is essential for the AI Recruitment Command Center
    to access candidate CVs for analysis by the CVAnalyzerAgent.

    Rate Limits:
    - list/download: 200 requests/minute
    - upload: 50 requests/minute
    """

    display_name = "Recruit Attachments (Zoho)"
    description = "Handle CV/Resume attachments for candidates"
    documentation = "https://www.zoho.com/recruit/developer-guide/apiv2/get-attachments.html"
    icon = "Zoho"
    name = "ZohoRecruitAttachment"

    inputs = [
        HandleInput(
            name="auth",
            display_name="Auth Config",
            input_types=["Data"],
            required=True,
            info="Auth config from ZohoRecruitAuth component"
        ),
        DropdownInput(
            name="operation",
            display_name="Operation",
            options=["list", "download", "upload", "get_resume_text"],
            value="list",
            info="Operation to perform"
        ),
        StrInput(
            name="record_id",
            display_name="Record ID",
            required=True,
            info="Candidate ID (or other module record ID)"
        ),
        DropdownInput(
            name="module",
            display_name="Module",
            options=["Candidates", "Job_Openings", "Contacts", "Clients"],
            value="Candidates",
            info="Zoho Recruit module"
        ),
        StrInput(
            name="attachment_id",
            display_name="Attachment ID",
            required=False,
            info="Required for download and get_resume_text operations"
        ),
        FileInput(
            name="file",
            display_name="File to Upload",
            required=False,
            info="File to upload (required for upload operation)",
            file_types=["pdf", "doc", "docx", "txt", "rtf"]
        ),
        StrInput(
            name="filename",
            display_name="Filename",
            required=False,
            info="Custom filename for upload (optional)"
        ),
    ]

    outputs = [
        Output(name="result", display_name="Result", method="execute"),
        Output(name="attachments", display_name="Attachments List", method="get_attachments_list"),
        Output(name="file_content", display_name="File Content (base64)", method="get_file_content"),
        Output(name="text_content", display_name="Text Content", method="get_text"),
    ]

    async def _get_headers(self, auth_config: Dict) -> Dict[str, str]:
        """Get authorization headers with fresh token."""
        auth_component = auth_config.get("_auth_component")
        if auth_component:
            access_token = await auth_component.get_access_token()
        else:
            access_token = auth_config["access_token"]
        return {
            "Authorization": f"Zoho-oauthtoken {access_token}",
        }

    async def _list_attachments(self, auth_config: Dict) -> Dict[str, Any]:
        """List all attachments for a record."""
        base_url = auth_config["api_base_url"]
        headers = await self._get_headers(auth_config)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}/{self.module}/{self.record_id}/Attachments",
                headers=headers
            )

            # 204 means no attachments found
            if response.status_code == 204:
                return {
                    "success": True,
                    "attachments": [],
                    "count": 0,
                    "record_id": self.record_id,
                    "module": self.module,
                }

            response.raise_for_status()

        data = response.json()
        attachments = data.get("data", [])

        # Add useful metadata to each attachment
        for att in attachments:
            att["is_resume"] = self._is_likely_resume(att.get("File_Name", ""))

        return {
            "success": True,
            "attachments": attachments,
            "count": len(attachments),
            "record_id": self.record_id,
            "module": self.module,
        }

    def _is_likely_resume(self, filename: str) -> bool:
        """Check if filename suggests it's a resume/CV."""
        filename_lower = filename.lower()
        resume_keywords = ["resume", "cv", "curriculum", "vitae"]
        resume_extensions = [".pdf", ".doc", ".docx"]

        has_keyword = any(kw in filename_lower for kw in resume_keywords)
        has_extension = any(filename_lower.endswith(ext) for ext in resume_extensions)

        return has_keyword or has_extension

    async def _download_attachment(self, auth_config: Dict) -> Dict[str, Any]:
        """Download an attachment by ID."""
        if not self.attachment_id:
            return {"success": False, "error": "attachment_id is required for 'download' operation"}

        base_url = auth_config["api_base_url"]
        headers = await self._get_headers(auth_config)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{base_url}/{self.module}/{self.record_id}/Attachments/{self.attachment_id}",
                headers=headers
            )
            response.raise_for_status()

        # Get content type and filename from headers
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        content_disposition = response.headers.get("Content-Disposition", "")

        filename = ""
        if "filename=" in content_disposition:
            filename = content_disposition.split("filename=")[1].strip('"')

        # Encode content as base64
        content_base64 = base64.b64encode(response.content).decode("utf-8")

        return {
            "success": True,
            "attachment_id": self.attachment_id,
            "record_id": self.record_id,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(response.content),
            "content_base64": content_base64,
        }

    async def _upload_attachment(self, auth_config: Dict) -> Dict[str, Any]:
        """Upload a new attachment."""
        if not self.file:
            return {"success": False, "error": "file is required for 'upload' operation"}

        base_url = auth_config["api_base_url"]
        headers = await self._get_headers(auth_config)

        # Handle file input - could be base64 or path
        if isinstance(self.file, str):
            if self.file.startswith("data:"):
                # Data URL format
                content_part = self.file.split(",", 1)[1] if "," in self.file else self.file
                file_bytes = base64.b64decode(content_part)
            else:
                # Assume base64
                file_bytes = base64.b64decode(self.file)
        else:
            file_bytes = self.file

        filename = self.filename or "attachment"

        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"file": (filename, file_bytes)}
            response = await client.post(
                f"{base_url}/{self.module}/{self.record_id}/Attachments",
                headers=headers,
                files=files
            )
            response.raise_for_status()

        data = response.json()
        result = data.get("data", [{}])[0] if data.get("data") else {}
        details = result.get("details", {})

        return {
            "success": True,
            "attachment_id": details.get("id"),
            "record_id": self.record_id,
            "filename": filename,
            "size_bytes": len(file_bytes),
            "created": details,
        }

    async def _get_resume_text(self, auth_config: Dict) -> Dict[str, Any]:
        """Extract text from PDF resume."""
        if not HAS_PYPDF:
            return {
                "success": False,
                "error": "pypdf library not installed. Run: pip install pypdf"
            }

        if not self.attachment_id:
            return {"success": False, "error": "attachment_id is required for 'get_resume_text' operation"}

        # First download the attachment
        download_result = await self._download_attachment(auth_config)
        if not download_result.get("success"):
            return download_result

        content_base64 = download_result.get("content_base64", "")
        filename = download_result.get("filename", "")

        # Check if it's a PDF
        if not filename.lower().endswith(".pdf"):
            return {
                "success": False,
                "error": f"File '{filename}' is not a PDF. Text extraction only supports PDF files."
            }

        try:
            # Decode and extract text
            pdf_bytes = base64.b64decode(content_base64)
            pdf_file = io.BytesIO(pdf_bytes)

            reader = pypdf.PdfReader(pdf_file)
            text_parts = []

            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")

            full_text = "\n\n".join(text_parts)

            return {
                "success": True,
                "attachment_id": self.attachment_id,
                "record_id": self.record_id,
                "filename": filename,
                "page_count": len(reader.pages),
                "text": full_text,
                "text_length": len(full_text),
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to extract text from PDF: {str(e)}",
                "filename": filename,
            }

    async def execute(self) -> Data:
        """Execute the selected operation."""
        # Get auth config from input
        auth_data = self.auth
        if isinstance(auth_data, Data):
            auth_config = auth_data.data
        else:
            auth_config = auth_data

        if auth_config.get("error"):
            self.status = "Auth error"
            return Data(data=auth_config)

        try:
            operation_map = {
                "list": self._list_attachments,
                "download": self._download_attachment,
                "upload": self._upload_attachment,
                "get_resume_text": self._get_resume_text,
            }

            operation_func = operation_map.get(self.operation)
            if not operation_func:
                return Data(data={"success": False, "error": f"Unknown operation: {self.operation}"})

            result = await operation_func(auth_config)

            if self.operation == "list":
                self.status = f"{result.get('count', 0)} attachments"
            elif self.operation == "get_resume_text":
                self.status = f"Extracted {result.get('text_length', 0)} chars"
            else:
                self.status = f"{self.operation}: OK"

            return Data(data=result)

        except httpx.HTTPStatusError as e:
            self.status = f"API error: {e.response.status_code}"
            return Data(data={
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
            })

        except Exception as e:
            self.status = f"Error: {str(e)[:30]}"
            return Data(data={
                "success": False,
                "error": str(e),
            })

    async def get_attachments_list(self) -> List[Data]:
        """Return attachments as a list of Data objects for iteration."""
        result = await self.execute()
        attachments = result.data.get("attachments", [])
        return [Data(data=a) for a in attachments]

    async def get_file_content(self) -> str:
        """Return downloaded file content as base64 string."""
        original_op = self.operation
        self.operation = "download"
        result = await self.execute()
        self.operation = original_op

        return result.data.get("content_base64", "")

    async def get_text(self) -> str:
        """Return extracted text from PDF resume."""
        original_op = self.operation
        self.operation = "get_resume_text"
        result = await self.execute()
        self.operation = original_op

        return result.data.get("text", "")
