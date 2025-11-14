"""
Google Drive API Router
Exposes Google Drive functionality through REST API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user
from open_webui.integrations.google_drive import google_drive, GoogleDriveFile


router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    file_types: Optional[List[str]] = None
    limit: int = 50
    include_content: bool = False


class FileContent(BaseModel):
    file_id: str
    name: str
    content: str
    mime_type: str


@router.post("/search")
async def search_drive_files(
    request: SearchRequest,
    user=Depends(get_verified_user)
):
    """Search for files in user's Google Drive"""
    try:
        files = await google_drive.search_files(
            user_id=user.id,
            query=request.query,
            file_types=request.file_types,
            limit=request.limit,
            include_content=request.include_content
        )

        return {
            "files": [file.to_dict() for file in files],
            "count": len(files)
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/files/{file_id}")
async def get_file_metadata(
    file_id: str,
    user=Depends(get_verified_user)
):
    """Get metadata for a specific file"""
    try:
        file_metadata = await google_drive.get_file_metadata(user.id, file_id)
        return file_metadata.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file metadata: {str(e)}")


@router.get("/files/{file_id}/content")
async def get_file_content(
    file_id: str,
    user=Depends(get_verified_user),
    max_size: int = Query(default=10*1024*1024, description="Maximum file size in bytes")
):
    """Get text content of a file"""
    try:
        # Get file metadata first
        file_metadata = await google_drive.get_file_metadata(user.id, file_id)

        # Get content
        content = await google_drive.get_file_content(user.id, file_id, max_size)

        return FileContent(
            file_id=file_id,
            name=file_metadata.name,
            content=content,
            mime_type=file_metadata.mime_type
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file content: {str(e)}")


@router.get("/recent")
async def get_recent_files(
    user=Depends(get_verified_user),
    limit: int = Query(default=20, le=100)
):
    """Get recently modified files"""
    try:
        files = await google_drive.get_recent_files(user.id, limit)
        return {
            "files": [file.to_dict() for file in files],
            "count": len(files)
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent files: {str(e)}")


@router.get("/shared")
async def get_shared_files(
    user=Depends(get_verified_user),
    limit: int = Query(default=50, le=100)
):
    """Get files shared with the user"""
    try:
        files = await google_drive.get_shared_files(user.id, limit)
        return {
            "files": [file.to_dict() for file in files],
            "count": len(files)
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get shared files: {str(e)}")


@router.get("/folders")
async def list_folders(
    user=Depends(get_verified_user),
    parent_id: Optional[str] = Query(default=None, description="Parent folder ID")
):
    """List folders in Drive"""
    try:
        folders = await google_drive.list_folders(user.id, parent_id)
        return {
            "folders": [folder.to_dict() for folder in folders],
            "count": len(folders)
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list folders: {str(e)}")


@router.get("/content-type/{content_type}")
async def search_by_content_type(
    content_type: str,
    user=Depends(get_verified_user),
    limit: int = Query(default=50, le=100)
):
    """Search files by content type (documents, spreadsheets, presentations, etc.)"""
    try:
        files = await google_drive.search_by_content_type(user.id, content_type, limit)
        return {
            "files": [file.to_dict() for file in files],
            "count": len(files),
            "content_type": content_type
        }
    except ValueError as e:
        if "Unsupported content type" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/user-info")
async def get_drive_user_info(user=Depends(get_verified_user)):
    """Get information about the user's Google Drive"""
    try:
        user_info = await google_drive.get_user_info(user.id)
        return user_info
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user info: {str(e)}")