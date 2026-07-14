import asyncio
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from src.config import settings
from src.utils.logger import logger
import io


class DriveService:
    SCOPES = ["https://www.googleapis.com/auth/drive.file"]

    def __init__(self):
        logger.info("Drive service initialized")

    TOKEN_URI = "https://oauth2.googleapis.com/token"

    async def _get_service(self, access_token: str, refresh_token: str = ""):
        """Build a Google Drive service authenticated with the given access token.

        When *refresh_token* is provided the credentials can auto-refresh after
        expiry, which avoids 401 → crash cycles.
        """
        kwargs: dict = {"token": access_token}
        if refresh_token and settings.google_client_id and settings.google_client_secret:
            kwargs.update(
                refresh_token=refresh_token,
                token_uri=self.TOKEN_URI,
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
            )
        creds = Credentials(**kwargs)
        service = await asyncio.to_thread(build, "drive", "v3", credentials=creds)
        return service

    async def list_files(
        self,
        access_token: str,
        refresh_token: str = "",
        folder_id: Optional[str] = None,
        page_size: int = 20,
    ) -> list[dict]:
        service = await self._get_service(access_token, refresh_token)
        query = None
        if folder_id:
            query = f"'{folder_id}' in parents"

        request = service.files().list(
            q=query,
            pageSize=page_size,
            fields="files(id, name, mimeType, size, modifiedTime, webViewLink, iconLink)",
        )
        results = await asyncio.to_thread(request.execute)

        return results.get("files", [])

    async def upload_file(
        self,
        access_token: str,
        file_path: str,
        file_name: str,
        mime_type: str,
        refresh_token: str = "",
        folder_id: Optional[str] = None,
    ) -> dict:
        service = await self._get_service(access_token, refresh_token)
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

        file_metadata = {
            "name": file_name,
            "mimeType": mime_type,
        }
        if folder_id:
            file_metadata["parents"] = [folder_id]

        request = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, mimeType, size, webViewLink",
        )
        file = await asyncio.to_thread(request.execute)

        logger.info(f"Uploaded file to Drive: {file_name}")
        return file

    async def download_file(
        self,
        access_token: str,
        file_id: str,
        refresh_token: str = "",
    ) -> bytes:
        service = await self._get_service(access_token, refresh_token)
        request = service.files().get_media(fileId=file_id)
        file_bytes = io.BytesIO()
        downloader = MediaIoBaseDownload(file_bytes, request)

        def _download():
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return file_bytes

        result = await asyncio.to_thread(_download)
        logger.info(f"Downloaded file: {file_id}")
        return result.getvalue()

    async def delete_file(
        self,
        access_token: str,
        file_id: str,
        refresh_token: str = "",
    ) -> dict:
        """Delete a file from Google Drive."""
        service = await self._get_service(access_token, refresh_token)
        request = service.files().delete(fileId=file_id)
        await asyncio.to_thread(request.execute)
        logger.info(f"Deleted file: {file_id}")
        return {"success": True, "file_id": file_id}

    async def get_file_info(
        self,
        access_token: str,
        file_id: str,
        refresh_token: str = "",
    ) -> dict:
        """Get metadata for a single file."""
        service = await self._get_service(access_token, refresh_token)
        request = service.files().get(
            fileId=file_id,
            fields="id, name, mimeType, size, modifiedTime, webViewLink",
        )
        result = await asyncio.to_thread(request.execute)
        return result

    async def create_folder(
        self,
        access_token: str,
        folder_name: str,
        parent_id: Optional[str] = None,
        refresh_token: str = "",
    ) -> dict:
        """Create a folder in Google Drive."""
        service = await self._get_service(access_token, refresh_token)
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            file_metadata["parents"] = [parent_id]

        request = service.files().create(
            body=file_metadata,
            fields="id, name, mimeType, webViewLink",
        )
        folder = await asyncio.to_thread(request.execute)
        logger.info(f"Created Drive folder: {folder_name}")
        return folder

    async def get_storage_usage(self, access_token: str, refresh_token: str = "") -> dict:
        """Get the user's Drive storage usage (approximation from about)."""
        service = await self._get_service(access_token, refresh_token)
        request = service.about().get(fields="storageQuota")
        result = await asyncio.to_thread(request.execute)
        return result.get("storageQuota", {})


drive_service = DriveService()
