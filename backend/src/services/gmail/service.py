import asyncio
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from src.config import settings
from src.utils.logger import logger

class GmailService:
    TOKEN_URI = "https://oauth2.googleapis.com/token"

    async def _get_service(self, access_token: str, refresh_token: str = ""):
        if not access_token:
            raise ValueError("Gmail is not connected. Reconnect Google with Gmail access enabled.")
        kwargs: dict = {"token": access_token}
        if refresh_token and settings.google_client_id and settings.google_client_secret:
            kwargs.update(
                refresh_token=refresh_token,
                token_uri=self.TOKEN_URI,
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
            )
        credentials = Credentials(**kwargs)
        return await asyncio.to_thread(build, "gmail", "v1", credentials=credentials, cache_discovery=False)

    async def list_emails(self, access_token: str, refresh_token: str = "", query: str = "", max_results: int = 5) -> list[dict]:
        service = await self._get_service(access_token, refresh_token)
        result = await asyncio.to_thread(lambda: service.users().messages().list(userId='me', q=query, maxResults=max_results).execute())
        messages = result.get('messages', [])
        
        emails = []
        for msg in messages:
            msg_id = msg['id']
            full_msg = await asyncio.to_thread(lambda: service.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders=['Subject', 'From', 'Date']).execute())
            headers = full_msg.get('payload', {}).get('headers', [])
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
            
            emails.append({
                "id": msg_id,
                "subject": subject,
                "from": sender,
                "date": date,
                "snippet": full_msg.get('snippet', '')
            })
        return emails

gmail_service = GmailService()
