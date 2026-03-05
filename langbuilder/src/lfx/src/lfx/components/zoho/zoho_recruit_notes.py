"""
Zoho Recruit Notes Component - LangBuilder Custom Component

Manage notes on candidate records in Zoho Recruit.

Author: CloudGeometry
Project: AI Recruitment Command Center
"""

from langflow.custom import Component
from langflow.io import HandleInput, StrInput, DropdownInput, MultilineInput, Output
from langflow.schema import Data
import httpx
from typing import Dict, List, Any


class ZohoRecruitNotesComponent(Component):
    """
    Manage notes on candidate records in Zoho Recruit.

    Operations:
    - get_notes: Get all notes for a record
    - add_note: Add a new note to a record
    - update_note: Update an existing note
    - delete_note: Delete a note

    Notes are used to store:
    - Interview feedback
    - Recruiter observations
    - AI-generated summaries
    - Status updates

    Rate Limits:
    - get_notes: 200 requests/minute
    - add/update/delete: 100 requests/minute
    """

    display_name = "Recruit Notes (Zoho)"
    description = "Manage notes on candidate records"
    documentation = "https://www.zoho.com/recruit/developer-guide/apiv2/get-notes.html"
    icon = "Zoho"
    name = "ZohoRecruitNotes"

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
            options=["get_notes", "add_note", "update_note", "delete_note"],
            value="get_notes",
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
            name="note_id",
            display_name="Note ID",
            required=False,
            info="Required for update_note and delete_note operations"
        ),
        StrInput(
            name="note_title",
            display_name="Note Title",
            required=False,
            info="Title for the note (required for add_note)"
        ),
        MultilineInput(
            name="note_content",
            display_name="Note Content",
            required=False,
            info="Content of the note (required for add_note)"
        ),
    ]

    outputs = [
        Output(name="result", display_name="Result", method="execute"),
        Output(name="notes", display_name="Notes List", method="get_notes_list"),
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
            "Content-Type": "application/json"
        }

    async def _get_notes(self, auth_config: Dict) -> Dict[str, Any]:
        """Get all notes for a record."""
        base_url = auth_config["api_base_url"]
        headers = await self._get_headers(auth_config)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}/{self.module}/{self.record_id}/Notes",
                headers=headers
            )

            # 204 means no notes found
            if response.status_code == 204:
                return {
                    "success": True,
                    "notes": [],
                    "count": 0,
                    "record_id": self.record_id,
                    "module": self.module,
                }

            response.raise_for_status()

        data = response.json()
        notes = data.get("data", [])

        return {
            "success": True,
            "notes": notes,
            "count": len(notes),
            "record_id": self.record_id,
            "module": self.module,
        }

    async def _add_note(self, auth_config: Dict) -> Dict[str, Any]:
        """Add a new note to a record."""
        if not self.note_title:
            return {"success": False, "error": "note_title is required for 'add_note' operation"}
        if not self.note_content:
            return {"success": False, "error": "note_content is required for 'add_note' operation"}

        base_url = auth_config["api_base_url"]
        headers = await self._get_headers(auth_config)

        payload = {
            "data": [{
                "Note_Title": self.note_title,
                "Note_Content": self.note_content,
                "Parent_Id": self.record_id,
                "se_module": self.module,
            }]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/{self.module}/{self.record_id}/Notes",
                headers=headers,
                json=payload
            )
            response.raise_for_status()

        data = response.json()
        result = data.get("data", [{}])[0] if data.get("data") else {}
        details = result.get("details", {})

        return {
            "success": True,
            "note_id": details.get("id"),
            "record_id": self.record_id,
            "module": self.module,
            "created": details,
        }

    async def _update_note(self, auth_config: Dict) -> Dict[str, Any]:
        """Update an existing note."""
        if not self.note_id:
            return {"success": False, "error": "note_id is required for 'update_note' operation"}

        base_url = auth_config["api_base_url"]
        headers = await self._get_headers(auth_config)

        update_data = {"id": self.note_id}
        if self.note_title:
            update_data["Note_Title"] = self.note_title
        if self.note_content:
            update_data["Note_Content"] = self.note_content

        payload = {"data": [update_data]}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{base_url}/{self.module}/{self.record_id}/Notes/{self.note_id}",
                headers=headers,
                json=payload
            )
            response.raise_for_status()

        data = response.json()
        result = data.get("data", [{}])[0] if data.get("data") else {}

        return {
            "success": True,
            "note_id": self.note_id,
            "record_id": self.record_id,
            "updated": result,
        }

    async def _delete_note(self, auth_config: Dict) -> Dict[str, Any]:
        """Delete a note."""
        if not self.note_id:
            return {"success": False, "error": "note_id is required for 'delete_note' operation"}

        base_url = auth_config["api_base_url"]
        headers = await self._get_headers(auth_config)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{base_url}/{self.module}/{self.record_id}/Notes/{self.note_id}",
                headers=headers
            )
            response.raise_for_status()

        data = response.json()
        result = data.get("data", [{}])[0] if data.get("data") else {}

        return {
            "success": True,
            "note_id": self.note_id,
            "record_id": self.record_id,
            "deleted": result,
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
                "get_notes": self._get_notes,
                "add_note": self._add_note,
                "update_note": self._update_note,
                "delete_note": self._delete_note,
            }

            operation_func = operation_map.get(self.operation)
            if not operation_func:
                return Data(data={"success": False, "error": f"Unknown operation: {self.operation}"})

            result = await operation_func(auth_config)

            if self.operation == "get_notes":
                self.status = f"{result.get('count', 0)} notes"
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

    async def get_notes_list(self) -> List[Data]:
        """Return notes as a list of Data objects for iteration."""
        result = await self.execute()
        notes = result.data.get("notes", [])
        return [Data(data=n) for n in notes]
