"""
HubSpot File Uploader - LangBuilder Custom Component

Uploads PDF files to HubSpot's Files API and returns a public URL
for email delivery and sharing.

Author: CloudGeometry
Project: Carter's Agents - Content Engine
"""

from langflow.custom import Component
from langflow.inputs.inputs import HandleInput
from langflow.io import StrInput, SecretStrInput, DropdownInput, Output
from langflow.schema import Data
import httpx
import base64
import time
import json


class HubSpotFileUploader(Component):
    """
    Uploads PDF files to HubSpot Files API.

    This component is used by the Content Engine agent to upload
    generated PDF reports to HubSpot, making them accessible via
    public URLs for email delivery.
    """

    display_name = "HubSpot File Uploader"
    description = "Uploads PDF files to HubSpot Files API"
    icon = "upload"
    name = "HubSpotFileUploader"

    # File access levels
    ACCESS_LEVELS = {
        "PUBLIC_INDEXABLE": "Public and searchable",
        "PUBLIC_NOT_INDEXABLE": "Public but not searchable",
        "PRIVATE": "Requires authentication",
    }

    inputs = [
        SecretStrInput(
            name="hubspot_api_key",
            display_name="HubSpot API Key",
            required=True,
            info="HubSpot Private App API key with files scope"
        ),
        HandleInput(
            name="pdf_base64",
            display_name="PDF Base64",
            required=True,
            input_types=["Message", "Data"],
            info="Base64-encoded PDF content from WeasyPrint PDF component"
        ),
        HandleInput(
            name="filename",
            display_name="Filename",
            required=True,
            input_types=["Message", "Data"],
            info="Output filename (should end in .pdf)"
        ),
        StrInput(
            name="folder_path",
            display_name="Folder Path",
            required=False,
            value="generated-reports",
            info="HubSpot folder path (without leading slash)"
        ),
        DropdownInput(
            name="access_level",
            display_name="Access Level",
            required=False,
            value="PUBLIC_INDEXABLE",
            options=["PUBLIC_INDEXABLE", "PUBLIC_NOT_INDEXABLE", "PRIVATE"],
            info="File visibility setting",
            advanced=True
        ),
    ]

    outputs = [
        Output(
            name="result",
            display_name="Upload Result",
            method="upload_file",
        ),
    ]

    def _extract_value(self, value, key: str = None) -> str:
        """Extract text from a Message object, Data object, or return string as-is.

        Args:
            value: Can be Message, Data, dict, or string
            key: Optional key to extract from Data/dict objects
        """
        if value is None:
            return ""
        # Handle Message objects
        if hasattr(value, 'text'):
            return str(value.text).strip()
        # Handle Data objects (have .data attribute with dict)
        if hasattr(value, 'data') and isinstance(value.data, dict):
            if key and key in value.data:
                return str(value.data[key]).strip()
            # Return first value if no key specified
            for v in value.data.values():
                if isinstance(v, str):
                    return v.strip()
            return str(value.data).strip()
        # Handle dict
        if isinstance(value, dict):
            if key and key in value:
                return str(value[key]).strip()
            return str(value).strip()
        return str(value).strip()

    async def upload_file(self) -> Data:
        """
        Upload PDF file to HubSpot Files API.

        Returns:
            Data object with file URL or error details
        """
        start_time = time.time()

        try:
            # Extract values from Message/Data objects
            pdf_base64_str = self._extract_value(self.pdf_base64, "pdf_base64")
            filename_str = self._extract_value(self.filename, "filename")

            # Validate and decode PDF
            if not pdf_base64_str:
                raise ValueError("PDF content is empty")

            try:
                pdf_bytes = base64.b64decode(pdf_base64_str)
            except Exception as e:
                raise ValueError(f"Invalid base64 encoding: {str(e)}")

            if len(pdf_bytes) == 0:
                raise ValueError("Decoded PDF is empty")

            # Ensure filename ends with .pdf
            filename = filename_str
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'

            # Ensure folder path has leading slash
            folder_path = self.folder_path or "generated-reports"
            if not folder_path.startswith('/'):
                folder_path = '/' + folder_path

            # Get access level
            access_level = self.access_level or "PUBLIC_INDEXABLE"

            # Build multipart form data
            files = {
                "file": (filename, pdf_bytes, "application/pdf")
            }

            data = {
                "folderPath": folder_path,
                "options": json.dumps({"access": access_level})
            }

            url = "https://api.hubapi.com/files/v3/files"

            headers = {
                "Authorization": f"Bearer {self.hubspot_api_key}"
                # Note: Don't set Content-Type header - httpx sets it for multipart
            }

            # Upload file
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data
                )

                upload_time_ms = int((time.time() - start_time) * 1000)

                if response.status_code in [200, 201]:
                    result = response.json()

                    file_url = result.get("url")
                    file_id = result.get("id")

                    self.status = f"✅ Uploaded: {filename}"

                    return Data(data={
                        "success": True,
                        "file_url": file_url,
                        "file_id": file_id,
                        "filename": filename,
                        "folder_path": folder_path,
                        "access_level": access_level,
                        "size_bytes": len(pdf_bytes),
                        "size_kb": round(len(pdf_bytes) / 1024, 1),
                        "upload_time_ms": upload_time_ms
                    })
                else:
                    # Parse error response
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", response.text)
                    except:
                        error_msg = response.text

                    self.status = f"❌ Error: {response.status_code}"

                    return Data(data={
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code,
                        "upload_time_ms": upload_time_ms
                    })

        except httpx.TimeoutException:
            upload_time_ms = int((time.time() - start_time) * 1000)
            self.status = "❌ Request timeout"
            return Data(data={
                "success": False,
                "error": "Upload timed out after 30 seconds",
                "upload_time_ms": upload_time_ms
            })

        except ValueError as e:
            upload_time_ms = int((time.time() - start_time) * 1000)
            self.status = f"❌ Validation error"
            return Data(data={
                "success": False,
                "error": str(e),
                "upload_time_ms": upload_time_ms
            })

        except Exception as e:
            upload_time_ms = int((time.time() - start_time) * 1000)
            self.status = f"❌ Error: {str(e)[:50]}"
            self.log(f"Upload failed: {str(e)}")
            return Data(data={
                "success": False,
                "error": str(e),
                "upload_time_ms": upload_time_ms
            })
