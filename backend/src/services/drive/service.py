from typing import Optional, BinaryIO
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from src.config import settings
from src.utils.logger import logger
import io


class DriveService:
    SCOPES = ["https://www.googleapis.com/auth/drive.file"]

    def __init__(self):
        self.service = None
        logger.info("Drive service initialized")

    def _get_service(self, access_token: str):
        creds = Credentials(token=access_token)
        self.service = build("drive", "v3", credentials=creds)
        return self.service

    async def list_files(
        self,
        access_token: str,
        folder_id: Optional[str] = None,
        page_size: int = 20,
    ) -> list[dict]:
        service = self._get_service(access_token)
        query = f"'{folder_id}' in parents" if folder_id else None

        results = service.files().list(
            q=query,
            pageSize=page_size,
            fields="files(id, name, mimeType, size, modifiedTime, webViewLink)",
        ).execute()

        return results.get("files", [])

    async def upload_file(
        self,
        access_token: str,
        file_path: str,
        file_name: str,
        mime_type: str,
        folder_id: Optional[str] = None,
    ) -> dict:
        service = self._get_service(access_token)
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

        file_metadata = {
            "name": file_name,
            "mimeType": mime_type,
        }
        if folder_id:
            file_metadata["parents"] = [folder_id]

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, mimeType, size, webViewLink",
        ).execute()

        logger.info(f"Uploaded file to Drive: {file_name}")
        return file

    async def download_file(
        self,
        access_token: str,
        file_id: str,
    ) -> bytes:
        service = self._get_service(access_token)
        request = service.files().get_media(fileId=file_id)
        file_bytes = io.BytesIO()
        downloader = MediaIoBaseDownload(file_bytes, request)
        done = False

        while not done:
            _, done = downloader.next_chunk()

        logger.info(f"Downloaded file: {file_id}")
        return file_bytes.getvalue()


drive_service = DriveService()
