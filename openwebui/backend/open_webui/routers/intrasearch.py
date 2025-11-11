"""
IntraSearch API Router - Independent from LLM providers
Handles enterprise internal search without GPT/LLM dependencies
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from open_webui.utils.auth import get_verified_user

router = APIRouter()

# Pydantic models for IntraSearch (independent from chat models)
class SearchRequest(BaseModel):
    query: str
    sources: Optional[List[str]] = None
    max_results: Optional[int] = 10
    search_depth: Optional[str] = "detailed"  # basic, detailed, comprehensive
    include_attachments: Optional[bool] = True
    language: Optional[str] = "auto"

class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    source: str
    score: float
    metadata: Dict[str, Any] = {}

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: int
    suggestions: Optional[List[str]] = None

class IntraSearchMessage(BaseModel):
    id: Optional[str] = None
    role: str  # user, assistant, system
    content: str
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class IntraSearchSession(BaseModel):
    id: str
    title: str
    messages: List[IntraSearchMessage] = []
    created_at: datetime
    updated_at: datetime

class IntraSearchSettings(BaseModel):
    search_depth: str = "detailed"
    search_sources: List[str] = ["documents", "wiki", "knowledge_base"]
    max_results: int = 10
    include_attachments: bool = True
    language: str = "auto"

# Mock data for development (replace with real implementation)
MOCK_SEARCH_RESULTS = [
    SearchResult(
        id="doc_001",
        title="Corporate Security Policy",
        content="This document describes the core principles of the company's information security, including rules for handling confidential information, password requirements, and system access procedures.",
        source="Corporate Wiki",
        score=0.95,
        metadata={
            "document_type": "policy",
            "author": "Security Team",
            "created_at": "2024-01-15",
            "tags": ["security", "policy", "compliance"]
        }
    ),
    SearchResult(
        id="kb_002",
        title="CRM System User Guide",
        content="Comprehensive guide for using the corporate CRM system, including customer creation, deal management, report configuration, and integration with other systems.",
        source="Knowledge Base",
        score=0.88,
        metadata={
            "document_type": "manual",
            "author": "IT Department",
            "created_at": "2024-02-10",
            "tags": ["crm", "manual", "sales"]
        }
    ),
    SearchResult(
        id="db_003",
        title="Department Contact Directory",
        content="Database containing contact information for all company departments, including phone numbers, email addresses, office locations, and responsible personnel.",
        source="Employee Database",
        score=0.82,
        metadata={
            "document_type": "directory",
            "author": "HR Department",
            "created_at": "2024-03-01",
            "tags": ["contacts", "directory", "hr"]
        }
    )
]

# In-memory storage for demo (replace with database)
sessions_storage: Dict[str, IntraSearchSession] = {}
user_settings: Dict[str, IntraSearchSettings] = {}

@router.post("/search", response_model=SearchResponse)
async def perform_search(
    request: SearchRequest,
    user=Depends(get_verified_user)
):
    """Perform enterprise internal search (mock implementation)"""

    # Simulate search processing time
    import time
    start_time = time.time()

    # Mock search logic - filter results based on query
    query_lower = request.query.lower()
    filtered_results = []

    for result in MOCK_SEARCH_RESULTS:
        if (query_lower in result.title.lower() or
            query_lower in result.content.lower() or
            any(query_lower in tag for tag in result.metadata.get("tags", []))):
            filtered_results.append(result)

    # Limit results
    limited_results = filtered_results[:request.max_results]

    # Generate mock suggestions
    suggestions = []
    if query_lower:
        base_suggestions = [
            "security policy",
            "crm system guide",
            "department contacts",
            "document workflow",
            "corporate standards",
            "employee handbook",
            "it support portal"
        ]
        suggestions = [s for s in base_suggestions if query_lower not in s.lower()][:3]

    search_time = int((time.time() - start_time) * 1000)

    return SearchResponse(
        query=request.query,
        results=limited_results,
        total_results=len(filtered_results),
        search_time_ms=search_time,
        suggestions=suggestions
    )

@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., description="Search query"),
    user=Depends(get_verified_user)
):
    """Get search suggestions based on query"""

    suggestions = [
        f"{q} policy",
        f"{q} guide",
        f"{q} contacts",
        f"how to {q}",
        f"{q} documents"
    ]

    return {"suggestions": suggestions[:5]}

@router.post("/sessions", response_model=IntraSearchSession)
async def create_session(
    title: Optional[str] = "IntraSearch Session",
    user=Depends(get_verified_user)
):
    """Create new IntraSearch session"""

    session_id = str(uuid.uuid4())
    now = datetime.now()

    session = IntraSearchSession(
        id=session_id,
        title=title or f"IntraSearch Session {now.strftime('%Y-%m-%d %H:%M')}",
        messages=[],
        created_at=now,
        updated_at=now
    )

    sessions_storage[f"{user.id}_{session_id}"] = session
    return session

@router.get("/sessions", response_model=List[IntraSearchSession])
async def get_sessions(user=Depends(get_verified_user)):
    """Get all IntraSearch sessions for user"""

    user_sessions = [
        session for key, session in sessions_storage.items()
        if key.startswith(f"{user.id}_")
    ]

    return sorted(user_sessions, key=lambda x: x.updated_at, reverse=True)

@router.get("/sessions/{session_id}", response_model=IntraSearchSession)
async def get_session(
    session_id: str,
    user=Depends(get_verified_user)
):
    """Get specific IntraSearch session"""

    session_key = f"{user.id}_{session_id}"
    if session_key not in sessions_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return sessions_storage[session_key]

@router.post("/sessions/{session_id}/messages", response_model=IntraSearchMessage)
async def save_message(
    session_id: str,
    message: IntraSearchMessage,
    user=Depends(get_verified_user)
):
    """Save message to IntraSearch session"""

    session_key = f"{user.id}_{session_id}"
    if session_key not in sessions_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Set message ID and timestamp if not provided
    if not message.id:
        message.id = str(uuid.uuid4())
    if not message.timestamp:
        message.timestamp = datetime.now()

    sessions_storage[session_key].messages.append(message)
    sessions_storage[session_key].updated_at = datetime.now()

    return message

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user=Depends(get_verified_user)
):
    """Delete IntraSearch session"""

    session_key = f"{user.id}_{session_id}"
    if session_key not in sessions_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    del sessions_storage[session_key]
    return {"message": "Session deleted successfully"}

@router.get("/settings", response_model=IntraSearchSettings)
async def get_settings(user=Depends(get_verified_user)):
    """Get IntraSearch settings for user"""

    return user_settings.get(user.id, IntraSearchSettings())

@router.put("/settings")
async def update_settings(
    settings: IntraSearchSettings,
    user=Depends(get_verified_user)
):
    """Update IntraSearch settings for user"""

    user_settings[user.id] = settings
    return {"message": "Settings updated successfully"}

@router.get("/sources")
async def get_search_sources(user=Depends(get_verified_user)):
    """Get available search sources"""

    sources = [
        "documents",
        "wiki",
        "knowledge_base",
        "databases",
        "repositories",
        "email_archives",
        "project_files",
        "policies"
    ]

    return {"sources": sources}