from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from src.services.drive.service import drive_service
from src.utils.logger import logger

router = APIRouter(prefix="/api/drive", tags=["Drive"])


class DriveActionRequest(BaseModel):
    access_token: str
    folder_id: Optional[str] = None
    page_size: int = 20


@router.get("/files")
async def list_drive_files(
    access_token: str = Query(...),
    folder_id: Optional[str] = Query(None),
    page_size: int = Query(20),
) -> list[dict]:
    try:
        files = await drive_service.list_files(
            access_token=access_token,
            folder_id=folder_id,
            page_size=page_size,
        )
        return [
            {
                "id": f.get("id"),
                "name": f.get("name"),
                "mimeType": f.get("mimeType"),
                "size": f.get("size"),
                "modifiedTime": f.get("modifiedTime"),
                "webViewLink": f.get("webViewLink"),
                "iconLink": f.get("iconLink"),
                "isFolder": f.get("mimeType") == "application/vnd.google-apps.folder",
            }
            for f in files
        ]
    except Exception as e:
        logger.error(f"Drive list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage")
async def get_storage_usage(
    access_token: str = Query(...),
) -> dict:
    try:
        usage = await drive_service.get_storage_usage(access_token)
        return usage
    except Exception as e:
        logger.error(f"Drive storage error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{file_id}")
async def get_file_info(
    file_id: str,
    access_token: str = Query(...),
) -> dict:
    try:
        info = await drive_service.get_file_info(access_token, file_id)
        return info
    except Exception as e:
        logger.error(f"Drive file info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
