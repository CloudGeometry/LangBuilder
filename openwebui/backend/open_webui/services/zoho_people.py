"""
Zoho People API Integration Module
Provides methods to interact with Zoho People API for employee data and personalized responses
"""

import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from open_webui.services.oauth_token_manager import token_manager
from open_webui.utils.oauth_services import ServiceType

log = logging.getLogger(__name__)


class ZohoPeopleAPI:
    """Zoho People API client for employee data retrieval"""

    def __init__(self):
        self.base_url = "https://people.zoho.eu/people/api"
        self.service_id = ServiceType.ZOHO

    async def _get_headers(self, user_id: str) -> Optional[Dict[str, str]]:
        """Get authorization headers with valid access token"""
        access_token = await token_manager.get_valid_token(user_id, self.service_id)
        if not access_token:
            return None

        return {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Content-Type": "application/json"
        }

    async def _make_request(self, user_id: str, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated request to Zoho People API"""
        headers = await self._get_headers(user_id)
        if not headers:
            log.error(f"No valid token for user {user_id}")
            return None

        url = f"{self.base_url}/{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params or {})

                if response.status_code == 200:
                    data = response.json()
                    log.info(f"Zoho People API response for {endpoint}: {data}")
                    return data
                elif response.status_code == 401:
                    log.error(f"Unauthorized access to Zoho People API for user {user_id}")
                    return None
                else:
                    log.error(f"Zoho People API error: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            log.error(f"Error making request to Zoho People API: {e}")
            return None

    async def get_employee_profile(self, user_id: str) -> Optional[Dict]:
        """Get current employee's profile information"""
        try:
            # Get current user's employee info
            response = await self._make_request(user_id, "forms/employee/getRecords")

            if response and response.get("success"):
                employee_data = response.get("data", {})

                # Extract relevant profile information
                profile = {
                    "employee_id": employee_data.get("Employee_Id"),
                    "email": employee_data.get("Email_Id"),
                    "first_name": employee_data.get("First_Name"),
                    "last_name": employee_data.get("Last_Name"),
                    "full_name": f"{employee_data.get('First_Name', '')} {employee_data.get('Last_Name', '')}".strip(),
                    "department": employee_data.get("Department"),
                    "designation": employee_data.get("Designation"),
                    "employee_status": employee_data.get("Employee_Status"),
                    "joining_date": employee_data.get("Date_of_joining"),
                    "mobile": employee_data.get("Mobile"),
                    "reporting_to": employee_data.get("Reporting_To"),
                    "location": employee_data.get("Location"),
                    "employee_type": employee_data.get("Employee_Type")
                }

                return profile

            return None

        except Exception as e:
            log.error(f"Error getting employee profile: {e}")
            return None

    async def get_team_members(self, user_id: str) -> List[Dict]:
        """Get team members (employees reporting to current user)"""
        try:
            # First get current user's profile to find their employee ID
            profile = await self.get_employee_profile(user_id)
            if not profile:
                return []

            # Get all employees and filter those reporting to current user
            response = await self._make_request(user_id, "forms/employee/getRecords")

            if response and response.get("success"):
                all_employees = response.get("data", [])
                team_members = []

                current_employee_id = profile.get("employee_id")

                for employee in all_employees:
                    if employee.get("Reporting_To") == current_employee_id:
                        team_member = {
                            "employee_id": employee.get("Employee_Id"),
                            "email": employee.get("Email_Id"),
                            "full_name": f"{employee.get('First_Name', '')} {employee.get('Last_Name', '')}".strip(),
                            "department": employee.get("Department"),
                            "designation": employee.get("Designation"),
                            "employee_status": employee.get("Employee_Status"),
                            "mobile": employee.get("Mobile"),
                            "location": employee.get("Location")
                        }
                        team_members.append(team_member)

                return team_members

            return []

        except Exception as e:
            log.error(f"Error getting team members: {e}")
            return []

    async def get_attendance_summary(self, user_id: str, from_date: str = None, to_date: str = None) -> Optional[Dict]:
        """Get attendance summary for current employee"""
        try:
            # Default to current month if no dates provided
            if not from_date or not to_date:
                now = datetime.now(timezone.utc)
                from_date = now.replace(day=1).strftime("%Y-%m-%d")
                to_date = now.strftime("%Y-%m-%d")

            params = {
                "fromDate": from_date,
                "toDate": to_date
            }

            response = await self._make_request(user_id, "attendance/getattendanceentries", params)

            if response and response.get("success"):
                attendance_data = response.get("data", [])

                # Process attendance data
                summary = {
                    "total_days": len(attendance_data),
                    "present_days": 0,
                    "absent_days": 0,
                    "late_days": 0,
                    "early_departure_days": 0,
                    "total_hours": 0.0,
                    "from_date": from_date,
                    "to_date": to_date
                }

                for entry in attendance_data:
                    if entry.get("Status") == "Present":
                        summary["present_days"] += 1
                    elif entry.get("Status") == "Absent":
                        summary["absent_days"] += 1

                    if entry.get("Late_Hours"):
                        summary["late_days"] += 1

                    if entry.get("Early_Hours"):
                        summary["early_departure_days"] += 1

                    # Add worked hours if available
                    worked_hours = entry.get("Total_Hours", 0)
                    if worked_hours:
                        summary["total_hours"] += float(worked_hours)

                return summary

            return None

        except Exception as e:
            log.error(f"Error getting attendance summary: {e}")
            return None

    async def get_leave_balance(self, user_id: str) -> Optional[Dict]:
        """Get leave balance for current employee"""
        try:
            response = await self._make_request(user_id, "leave/getleavebalance")

            if response and response.get("success"):
                leave_data = response.get("data", [])

                balance = {}
                for leave_type in leave_data:
                    leave_name = leave_type.get("LeaveType_Name", "Unknown")
                    balance[leave_name] = {
                        "allocated": leave_type.get("Allocated_Days", 0),
                        "used": leave_type.get("Used_Days", 0),
                        "available": leave_type.get("Available_Days", 0),
                        "pending": leave_type.get("Pending_Days", 0)
                    }

                return balance

            return None

        except Exception as e:
            log.error(f"Error getting leave balance: {e}")
            return None

    async def get_recent_leave_requests(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get recent leave requests for current employee"""
        try:
            response = await self._make_request(user_id, "leave/getleaverequests")

            if response and response.get("success"):
                leave_requests = response.get("data", [])

                # Sort by date and limit results
                recent_requests = []
                for request in leave_requests[:limit]:
                    leave_info = {
                        "leave_id": request.get("Leave_Id"),
                        "leave_type": request.get("LeaveType_Name"),
                        "from_date": request.get("From_Date"),
                        "to_date": request.get("To_Date"),
                        "days": request.get("Days_Count"),
                        "status": request.get("Leave_Status"),
                        "reason": request.get("Reason"),
                        "applied_date": request.get("Applied_Date"),
                        "approved_by": request.get("Approved_By")
                    }
                    recent_requests.append(leave_info)

                return recent_requests

            return []

        except Exception as e:
            log.error(f"Error getting recent leave requests: {e}")
            return []

    async def get_employee_context(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive employee context for personalized responses"""
        try:
            # Gather all relevant employee data
            profile = await self.get_employee_profile(user_id)
            team_members = await self.get_team_members(user_id)
            attendance = await self.get_attendance_summary(user_id)
            leave_balance = await self.get_leave_balance(user_id)
            recent_leaves = await self.get_recent_leave_requests(user_id, 5)

            context = {
                "profile": profile,
                "team": {
                    "members": team_members,
                    "count": len(team_members)
                },
                "attendance": attendance,
                "leave": {
                    "balance": leave_balance,
                    "recent_requests": recent_leaves
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            return context

        except Exception as e:
            log.error(f"Error getting employee context: {e}")
            return {}


# Global instance
zoho_people_api = ZohoPeopleAPI()