"""
Zoho Recruit Job Opening Component - LangBuilder Custom Component

Access job openings and descriptions from Zoho Recruit.

Author: CloudGeometry
Project: AI Recruitment Command Center
"""

from langflow.custom import Component
from langflow.io import HandleInput, StrInput, DropdownInput, IntInput, Output
from langflow.schema import Data
import httpx
from typing import Dict, List, Any


class ZohoRecruitJobOpeningComponent(Component):
    """
    Access job openings and descriptions from Zoho Recruit.

    Operations:
    - list: List all job openings with pagination
    - get: Get a single job opening by ID
    - get_description: Get the full job description text
    - get_requirements: Extract requirements from job description

    Rate Limits: 200 requests/minute
    """

    display_name = "Recruit Job Openings (Zoho)"
    description = "Access job openings and descriptions from Zoho Recruit"
    documentation = "https://www.zoho.com/recruit/developer-guide/apiv2/get-records.html"
    icon = "Zoho"
    name = "ZohoRecruitJobOpening"

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
            options=["list", "get", "get_description", "get_requirements"],
            value="list",
            info="Operation to perform"
        ),
        StrInput(
            name="job_opening_id",
            display_name="Job Opening ID",
            required=False,
            info="Required for get, get_description, get_requirements operations"
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
        Output(name="job_openings", display_name="Job Openings List", method="get_job_openings_list"),
        Output(name="description_text", display_name="Description Text", method="get_description_text"),
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

    async def _list_job_openings(self, auth_config: Dict) -> Dict[str, Any]:
        """List job openings with pagination."""
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
                f"{base_url}/Job_Openings",
                headers=headers,
                params=params
            )
            response.raise_for_status()

        data = response.json()
        job_openings = data.get("data", [])

        return {
            "success": True,
            "job_openings": job_openings,
            "count": len(job_openings),
            "page": self.page,
            "per_page": self.per_page,
            "info": data.get("info", {}),
        }

    async def _get_job_opening(self, auth_config: Dict) -> Dict[str, Any]:
        """Get a single job opening by ID."""
        if not self.job_opening_id:
            return {"success": False, "error": "job_opening_id is required for 'get' operation"}

        base_url = auth_config["api_base_url"]
        headers = await self._get_headers(auth_config)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}/Job_Openings/{self.job_opening_id}",
                headers=headers
            )
            response.raise_for_status()

        data = response.json()
        job_opening = data.get("data", [{}])[0] if data.get("data") else {}

        return {
            "success": True,
            "job_opening": job_opening,
        }

    async def _get_description(self, auth_config: Dict) -> Dict[str, Any]:
        """Get the full job description for a job opening."""
        if not self.job_opening_id:
            return {"success": False, "error": "job_opening_id is required for 'get_description' operation"}

        # First get the job opening
        result = await self._get_job_opening(auth_config)
        if not result.get("success"):
            return result

        job_opening = result.get("job_opening", {})

        # Extract description fields
        description = job_opening.get("Job_Description", "")
        job_title = job_opening.get("Posting_Title", job_opening.get("Job_Opening_Name", ""))

        return {
            "success": True,
            "job_opening_id": self.job_opening_id,
            "job_title": job_title,
            "description": description,
            "full_record": job_opening,
        }

    async def _get_requirements(self, auth_config: Dict) -> Dict[str, Any]:
        """Extract requirements from job description."""
        if not self.job_opening_id:
            return {"success": False, "error": "job_opening_id is required for 'get_requirements' operation"}

        # First get the description
        result = await self._get_description(auth_config)
        if not result.get("success"):
            return result

        job_opening = result.get("full_record", {})

        # Extract all requirement-related fields
        requirements = {
            "job_title": result.get("job_title", ""),
            "description": result.get("description", ""),
            "required_skills": job_opening.get("Required_Skills", ""),
            "experience": job_opening.get("Experience", ""),
            "industry": job_opening.get("Industry", ""),
            "job_type": job_opening.get("Job_Type", ""),
            "salary": job_opening.get("Salary", ""),
            "location": job_opening.get("City", ""),
            "state": job_opening.get("State", ""),
            "country": job_opening.get("Country", ""),
            "department": job_opening.get("Department", {}).get("name", "") if isinstance(job_opening.get("Department"), dict) else job_opening.get("Department", ""),
            "number_of_positions": job_opening.get("Number_of_Positions", 1),
            "date_opened": job_opening.get("Date_Opened", ""),
            "target_date": job_opening.get("Target_Date", ""),
        }

        return {
            "success": True,
            "job_opening_id": self.job_opening_id,
            "requirements": requirements,
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
                "list": self._list_job_openings,
                "get": self._get_job_opening,
                "get_description": self._get_description,
                "get_requirements": self._get_requirements,
            }

            operation_func = operation_map.get(self.operation)
            if not operation_func:
                return Data(data={"success": False, "error": f"Unknown operation: {self.operation}"})

            result = await operation_func(auth_config)
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

    async def get_job_openings_list(self) -> List[Data]:
        """Return job openings as a list of Data objects for iteration."""
        result = await self.execute()
        job_openings = result.data.get("job_openings", [])
        return [Data(data=j) for j in job_openings]

    async def get_description_text(self) -> str:
        """Return just the description text as a string."""
        # Temporarily set operation to get_description
        original_op = self.operation
        self.operation = "get_description"
        result = await self.execute()
        self.operation = original_op

        return result.data.get("description", "")
