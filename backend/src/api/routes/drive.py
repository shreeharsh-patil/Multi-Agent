import asyncio
import os
import tempfile
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from src.services.drive.service import drive_service
from src.utils.logger import logger

router = APIRouter(prefix="/api/drive", tags=["Drive"])


class DriveListResponse(BaseModel):
    files: list[dict]
    total: int


class DriveDownloadResponse(BaseModel):
    file_id: str
    file_name: str
    mime_type: str
    file_size: int
    download_url: str


@router.get("/files")
async def list_drive_files(
    access_token: str = Query(..., description="Google Drive access token"),
    folder_id: Optional[str] = Query(None, description="Folder ID to list"),
    page_size: int = Query(20, description="Number of files per page"),
) -> DriveListResponse:
    """List files from Google Drive using the user's access token."""
    try:
        files = await drive_service.list_files(
            access_token=access_token,
            folder_id=folder_id,
            page_size=page_size,
        )

        formatted = []
        for f in files:
            formatted.append({
                "id": f.get("id"),
                "name": f.get("name"),
                "mimeType": f.get("mimeType"),
                "size": int(f.get("size", 0)),
                "modifiedTime": f.get("modifiedTime"),
                "webViewLink": f.get("webViewLink"),
                "iconLink": f.get("iconLink"),
                "isFolder": f.get("mimeType") == "application/vnd.google-apps.folder",
            })

        return DriveListResponse(files=formatted, total=len(formatted))
    except Exception as e:
        logger.error(f"Drive list failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list Drive files: {str(e)}")


@router.post("/upload")
async def upload_to_drive(
    file: UploadFile = File(...),
    access_token: str = Query(..., description="Google Drive access token"),
    folder_id: Optional[str] = Query(None, description="Target folder ID"),
) -> dict:
    """Upload a file to Google Drive."""
    if file.filename is None:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = os.path.splitext(file.filename)[1].lower()
    mime_map = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".csv": "text/csv",
        ".zip": "application/zip",
    }
    mime_type = mime_map.get(ext, "application/octet-stream")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = await drive_service.upload_file(
            access_token=access_token,
            file_path=tmp_path,
            file_name=file.filename,
            mime_type=mime_type,
            folder_id=folder_id,
        )
        return {
            "id": result.get("id"),
            "name": result.get("name"),
            "mimeType": result.get("mimeType"),
            "size": result.get("size"),
            "webViewLink": result.get("webViewLink"),
        }
    except Exception as e:
        logger.error(f"Drive upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload to Drive: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/download/{file_id}")
async def download_from_drive(
    file_id: str,
    access_token: str = Query(..., description="Google Drive access token"),
) -> dict:
    """Get download URL and metadata for a Drive file."""
    try:
        info = await drive_service.get_file_info(
            access_token=access_token,
            file_id=file_id,
        )

        return DriveDownloadResponse(
            file_id=info.get("id"),
            file_name=info.get("name"),
            mime_type=info.get("mimeType"),
            file_size=int(info.get("size", 0)),
            download_url=info.get("webViewLink"),
        ).model_dump()
    except Exception as e:
        logger.error(f"Drive download info failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{file_id}/content")
async def download_drive_file_content(
    file_id: str,
    access_token: str = Query(..., description="Google Drive access token"),
):
    """Download the actual file content from Google Drive."""
    from fastapi.responses import StreamingResponse
    import io

    try:
        info = await drive_service.get_file_info(
            access_token=access_token,
            file_id=file_id,
        )
        file_bytes = await drive_service.download_file(
            access_token=access_token,
            file_id=file_id,
        )

        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type=info.get("mimeType", "application/octet-stream"),
            headers={
                "Content-Disposition": f'attachment; filename="{info.get("name", "download")}"',
                "Content-Length": str(len(file_bytes)),
            },
        )
    except Exception as e:
        logger.error(f"Drive download content failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}")
async def delete_drive_file(
    file_id: str,
    access_token: str = Query(..., description="Google Drive access token"),
) -> dict:
    """Delete a file from Google Drive."""
    try:
        result = await drive_service.delete_file(
            access_token=access_token,
            file_id=file_id,
        )
        return result
    except Exception as e:
        logger.error(f"Drive delete failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete Drive file: {str(e)}")


@router.post("/folders")
async def create_drive_folder(
    name: str = Query(..., description="Folder name"),
    access_token: str = Query(..., description="Google Drive access token"),
    parent_id: Optional[str] = Query(None, description="Parent folder ID"),
) -> dict:
    """Create a folder in Google Drive."""
    try:
        result = await drive_service.create_folder(
            access_token=access_token,
            folder_name=name,
            parent_id=parent_id,
        )
        return result
    except Exception as e:
        logger.error(f"Drive folder creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage")
async def get_drive_storage(
    access_token: str = Query(..., description="Google Drive access token"),
) -> dict:
    """Get Drive storage usage information."""
    try:
        quota = await drive_service.get_storage_usage(access_token)
        return {
            "limit": int(quota.get("limit", 0)),
            "usage": int(quota.get("usage", 0)),
            "usageInDrive": int(quota.get("usageInDrive", 0)),
            "usageInDriveTrash": int(quota.get("usageInDriveTrash", 0)),
        }
    except Exception as e:
        logger.error(f"Drive storage check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
