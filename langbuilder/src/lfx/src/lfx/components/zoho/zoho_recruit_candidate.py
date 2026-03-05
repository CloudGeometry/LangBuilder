"""
Zoho Recruit Candidate Component - LangBuilder Custom Component

CRUD operations for candidates in Zoho Recruit ATS.

Author: CloudGeometry
Project: AI Recruitment Command Center
"""

from langflow.custom import Component
from langflow.io import HandleInput, StrInput, DropdownInput, IntInput, DictInput, Output
from langflow.schema import Data
import httpx
from typing import Dict, List, Any, Optional


class ZohoRecruitCandidateComponent(Component):
    """
    Manage candidates in Zoho Recruit ATS.

    Operations:
    - list: List candidates with pagination
    - get: Get a single candidate by ID
    - search: Search candidates by criteria
    - update: Update candidate fields
    - get_by_job: Get candidates associated with a job opening

    Rate Limits:
    - list/get: 200 requests/minute
    - search/update: 100 requests/minute
    """

    display_name = "Recruit Candidates (Zoho)"
    description = "Manage candidates in Zoho Recruit ATS"
    documentation = "https://www.zoho.com/recruit/developer-guide/apiv2/get-records.html"
    icon = "Zoho"
    name = "ZohoRecruitCandidate"

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
            options=["list", "get", "search", "update", "get_by_job"],
            value="list",
            info="Operation to perform"
        ),
        StrInput(
            name="candidate_id",
            display_name="Candidate ID",
            required=False,
            info="Required for 'get' and 'update' operations"
        ),
        StrInput(
            name="job_opening_id",
            display_name="Job Opening ID",
            required=False,
            info="Required for 'get_by_job' operation"
        ),
        StrInput(
            name="search_criteria",
            display_name="Search Criteria",
            required=False,
            info="Search criteria in Zoho format, e.g., (Email:equals:john@example.com)"
        ),
        DictInput(
            name="update_data",
            display_name="Update Data",
            required=False,
            info="Dictionary of fields to update"
        ),
        StrInput(
            name="fields",
            display_name="Fields",
            required=False,
            value="",
            info="Comma-separated list of fields to return (empty = all fields)"
        ),
        IntInput(
            name="page",
            display_name="Page",
            value=1,
            info="Page number for pagination"
        ),
        IntInput(
            name="per_page",
            display_name="Per Page",
            value=200,
            info="Records per page (max 200)"
        ),
    ]

    outputs = [
        Output(name="result", display_name="Result", method="execute"),
        Output(name="candidates", display_name="Candidates List", method="get_candidates_list"),
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

    async def _list_candidates(self, auth_config: Dict) -> Dict[str, Any]:
        """List candidates with pagination."""
        base_url = auth_config["api_base_url"]
        headers = await self._get_headers(auth_config)

        params = {
            "page": self.page,
            "per_page": min(self.per_page, 200),
        }
        if self.fields:
            params["fields"] = self.fields

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}/Candidates",
                headers=headers,
                params=params
            )
            response.raise_for_status()

        data = response.json()
        candidates = data.get("data", [])

        return {
            "success": True,
            "candidates": candidates,
            "count": len(candidates),
            "page": self.page,
            "per_page": self.per_page,
            "info": data.get("info", {}),
        }

    async def _get_candidate(self, auth_config: Dict) -> Dict[str, Any]:
        """Get a single candidate by ID."""
        if not self.candidate_id:
            return {"success": False, "error": "candidate_id is required for 'get' operation"}

        base_url = auth_config["api_base_url"]
        headers = await self._get_headers(auth_config)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}/Candidates/{self.candidate_id}",
                headers=headers
            )
            response.raise_for_status()

        data = response.json()
        candidate = data.get("data", [{}])[0] if data.get("data") else {}

        return {
            "success": True,
            "candidate": candidate,
        }

    async def _search_candidates(self, auth_config: Dict) -> Dict[str, Any]:
        """Search candidates by criteria."""
        if not self.search_criteria:
            return {"success": False, "error": "search_criteria is required for 'search' operation"}

        base_url = auth_config["api_base_url"]
        headers = await self._get_headers(auth_config)

        params = {
            "criteria": self.search_criteria,
            "page": self.page,
            "per_page": min(self.per_page, 200),
        }
        if self.fields:
            params["fields"] = self.fields

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}/Candidates/search",
                headers=headers,
                params=params
            )
            response.raise_for_status()

        data = response.json()
        candidates = data.get("data", [])

        return {
            "success": True,
            "candidates": candidates,
            "count": len(candidates),
            "search_criteria": self.search_criteria,
            "info": data.get("info", {}),
        }

    async def _update_candidate(self, auth_config: Dict) -> Dict[str, Any]:
        """Update a candidate's fields."""
        if not self.candidate_id:
            return {"success": False, "error": "candidate_id is required for 'update' operation"}
        if not self.update_data:
            return {"success": False, "error": "update_data is required for 'update' operation"}

        base_url = auth_config["api_base_url"]
        headers = await self._get_headers(auth_config)

        payload = {
            "data": [self.update_data]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{base_url}/Candidates/{self.candidate_id}",
                headers=headers,
                json=payload
            )
            response.raise_for_status()

        data = response.json()
        result = data.get("data", [{}])[0] if data.get("data") else {}

        return {
            "success": True,
            "updated": result,
            "candidate_id": self.candidate_id,
        }

    async def _get_by_job(self, auth_config: Dict) -> Dict[str, Any]:
        """Get candidates associated with a job opening."""
        if not self.job_opening_id:
            return {"success": False, "error": "job_opening_id is required for 'get_by_job' operation"}

        base_url = auth_config["api_base_url"]
        headers = await self._get_headers(auth_config)

        params = {
            "page": self.page,
            "per_page": min(self.per_page, 200),
        }
        if self.fields:
            params["fields"] = self.fields

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}/Job_Openings/{self.job_opening_id}/Candidates",
                headers=headers,
                params=params
            )
            response.raise_for_status()

        data = response.json()
        candidates = data.get("data", [])

        return {
            "success": True,
            "candidates": candidates,
            "count": len(candidates),
            "job_opening_id": self.job_opening_id,
            "info": data.get("info", {}),
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
                "list": self._list_candidates,
                "get": self._get_candidate,
                "search": self._search_candidates,
                "update": self._update_candidate,
                "get_by_job": self._get_by_job,
            }

            operation_func = operation_map.get(self.operation)
            if not operation_func:
                return Data(data={"success": False, "error": f"Unknown operation: {self.operation}"})

            result = await operation_func(auth_config)
            self.status = f"{self.operation}: {result.get('count', 1)} record(s)"
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

    async def get_candidates_list(self) -> List[Data]:
        """Return candidates as a list of Data objects for iteration."""
        result = await self.execute()
        candidates = result.data.get("candidates", [])
        return [Data(data=c) for c in candidates]
