"""
Zoho People API Router
Provides endpoints for accessing Zoho People data for personalized AI responses
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

from open_webui.utils.auth import get_verified_user
from open_webui.services.zoho_people import zoho_people_api
from open_webui.services.oauth_token_manager import token_manager
from open_webui.utils.oauth_services import ServiceType

router = APIRouter()


class EmployeeProfile(BaseModel):
    employee_id: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    employee_status: Optional[str] = None
    joining_date: Optional[str] = None
    mobile: Optional[str] = None
    reporting_to: Optional[str] = None
    location: Optional[str] = None
    employee_type: Optional[str] = None


class TeamMember(BaseModel):
    employee_id: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    employee_status: Optional[str] = None
    mobile: Optional[str] = None
    location: Optional[str] = None


class AttendanceSummary(BaseModel):
    total_days: int
    present_days: int
    absent_days: int
    late_days: int
    early_departure_days: int
    total_hours: float
    from_date: str
    to_date: str


class LeaveBalance(BaseModel):
    allocated: int
    used: int
    available: int
    pending: int


class LeaveRequest(BaseModel):
    leave_id: Optional[str] = None
    leave_type: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    days: Optional[int] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    applied_date: Optional[str] = None
    approved_by: Optional[str] = None


class EmployeeContext(BaseModel):
    profile: Optional[EmployeeProfile] = None
    team: Dict[str, Any] = {}
    attendance: Optional[AttendanceSummary] = None
    leave: Dict[str, Any] = {}
    timestamp: str


def check_zoho_authorization(user_id: str):
    """Check if user has authorized Zoho access"""
    token_data = token_manager.get_token(user_id, ServiceType.ZOHO)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Zoho People access not authorized. Please connect to Zoho in Settings -> External Tools."
        )
    return token_data


@router.get("/profile", response_model=EmployeeProfile)
async def get_employee_profile(user=Depends(get_verified_user)):
    """Get current employee's profile information from Zoho People"""
    check_zoho_authorization(user.id)

    profile_data = await zoho_people_api.get_employee_profile(user.id)

    if not profile_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found or access denied"
        )

    return EmployeeProfile(**profile_data)


@router.get("/team", response_model=List[TeamMember])
async def get_team_members(user=Depends(get_verified_user)):
    """Get team members (employees reporting to current user)"""
    check_zoho_authorization(user.id)

    team_data = await zoho_people_api.get_team_members(user.id)
    return [TeamMember(**member) for member in team_data]


@router.get("/attendance", response_model=AttendanceSummary)
async def get_attendance_summary(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    user=Depends(get_verified_user)
):
    """Get attendance summary for current employee"""
    check_zoho_authorization(user.id)

    attendance_data = await zoho_people_api.get_attendance_summary(user.id, from_date, to_date)

    if not attendance_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance data not found"
        )

    return AttendanceSummary(**attendance_data)


@router.get("/leave/balance")
async def get_leave_balance(user=Depends(get_verified_user)):
    """Get leave balance for current employee"""
    check_zoho_authorization(user.id)

    balance_data = await zoho_people_api.get_leave_balance(user.id)

    if not balance_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave balance data not found"
        )

    return balance_data


@router.get("/leave/requests", response_model=List[LeaveRequest])
async def get_recent_leave_requests(
    limit: int = 10,
    user=Depends(get_verified_user)
):
    """Get recent leave requests for current employee"""
    check_zoho_authorization(user.id)

    requests_data = await zoho_people_api.get_recent_leave_requests(user.id, limit)
    return [LeaveRequest(**request) for request in requests_data]


@router.get("/context", response_model=EmployeeContext)
async def get_employee_context(user=Depends(get_verified_user)):
    """Get comprehensive employee context for personalized AI responses"""
    check_zoho_authorization(user.id)

    context_data = await zoho_people_api.get_employee_context(user.id)

    if not context_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee context data not found"
        )

    return EmployeeContext(
        profile=EmployeeProfile(**context_data.get("profile", {})) if context_data.get("profile") else None,
        team=context_data.get("team", {}),
        attendance=AttendanceSummary(**context_data.get("attendance", {})) if context_data.get("attendance") else None,
        leave=context_data.get("leave", {}),
        timestamp=context_data.get("timestamp", datetime.now().isoformat())
    )


@router.get("/connection/status")
async def get_zoho_connection_status(user=Depends(get_verified_user)):
    """Get Zoho People connection status for current user"""
    try:
        print("\n" + "="*60)
        print("ZOHO CONNECTION STATUS CHECK")
        print("="*60)
        print(f"User ID: {user.id}")

        token_data = token_manager.get_token(user.id, ServiceType.ZOHO)

        if not token_data:
            print("No token data found for user")
            return {
                "connected": False,
                "message": "Not connected to Zoho People"
            }

        print(f"Token data found:")
        print(f"  - User email from token: {token_data.user_email}")
        print(f"  - User name from token: {token_data.user_name}")
        print(f"  - Token expires at: {token_data.expires_at}")
        print(f"  - Token scope: {token_data.scope}")

        # If we have a valid OAuth token, consider it connected
        # Even if the user doesn't have access to People API
        result = {
            "connected": True,
            "employee_email": token_data.user_email or "zoho_user@example.com",
            "employee_name": token_data.user_name or "Zoho User",
            "last_updated": token_data.expires_at.isoformat() if token_data.expires_at else None,
            "message": "OAuth connected successfully"
        }

        print(f"Returning result: {result}")
        print("="*60 + "\n")
        return result

    except Exception as e:
        return {
            "connected": False,
            "message": f"Connection error: {str(e)}"
        }