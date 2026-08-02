import asyncio
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from src.config import settings
from src.utils.logger import logger


class ContactsService:
    TOKEN_URI = "https://oauth2.googleapis.com/token"

    async def _get_service(self, access_token: str, refresh_token: str = ""):
        kwargs = {"token": access_token}
        if refresh_token and settings.google_client_id and settings.google_client_secret:
            kwargs.update(
                refresh_token=refresh_token,
                token_uri=self.TOKEN_URI,
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
            )
        creds = Credentials(**kwargs)
        service = await asyncio.to_thread(build, "people", "v1", credentials=creds)
        return service

    async def list_contacts(
        self,
        access_token: str,
        refresh_token: str = "",
        query: str = "",
        limit: int = 50,
    ) -> list[dict]:
        """Fetch or search Google Contacts for the authenticated user."""
        service = await self._get_service(access_token, refresh_token)
        contacts = []
        clean_query = query.strip()

        if clean_query:
            try:
                request = service.people().searchContacts(
                    query=clean_query,
                    readMask="names,emailAddresses,phoneNumbers,organizations",
                    pageSize=min(limit, 30),
                )
                res = await asyncio.to_thread(request.execute)
                results = res.get("results", [])
                for item in results:
                    person = item.get("person", {})
                    contacts.append(self._parse_person(person))
            except Exception as exc:
                logger.warning(f"Google People searchContacts error: {exc}")

        if not contacts:
            try:
                request = service.people().connections().list(
                    resourceName="people/me",
                    personFields="names,emailAddresses,phoneNumbers,organizations",
                    pageSize=min(limit, 100),
                )
                res = await asyncio.to_thread(request.execute)
                connections = res.get("connections", [])
                for person in connections:
                    parsed = self._parse_person(person)
                    if clean_query:
                        q_lower = clean_query.lower()
                        name_match = q_lower in parsed.get("name", "").lower()
                        email_match = q_lower in parsed.get("email", "").lower()
                        phone_match = q_lower in parsed.get("phone", "").lower()
                        if name_match or email_match or phone_match:
                            contacts.append(parsed)
                    else:
                        contacts.append(parsed)
            except Exception as exc:
                logger.error(f"Google People connections list error: {exc}")

        return contacts

    def _parse_person(self, person: dict) -> dict:
        names = person.get("names", [])
        display_name = names[0].get("displayName") if names else "Unnamed"
        emails = person.get("emailAddresses", [])
        email_val = emails[0].get("value") if emails else ""
        phones = person.get("phoneNumbers", [])
        phone_val = phones[0].get("value") if phones else ""
        orgs = person.get("organizations", [])
        company = orgs[0].get("name") if orgs else ""
        resource_name = person.get("resourceName", "")
        return {
            "resourceName": resource_name,
            "name": display_name,
            "email": email_val,
            "phone": phone_val,
            "company": company,
        }

    async def create_contact(
        self,
        access_token: str,
        name: str,
        email: str = "",
        phone: str = "",
        company: str = "",
        refresh_token: str = "",
    ) -> dict:
        """Create a new contact in Google Contacts."""
        service = await self._get_service(access_token, refresh_token)
        body: dict = {
            "names": [{"givenName": name}],
        }
        if email:
            body["emailAddresses"] = [{"value": email}]
        if phone:
            body["phoneNumbers"] = [{"value": phone}]
        if company:
            body["organizations"] = [{"name": company}]

        request = service.people().createContact(body=body)
        person = await asyncio.to_thread(request.execute)
        return self._parse_person(person)

    async def delete_contact(
        self,
        access_token: str,
        resource_name: str,
        refresh_token: str = "",
    ) -> bool:
        """Delete a contact by resourceName (e.g. people/c12345)."""
        service = await self._get_service(access_token, refresh_token)
        request = service.people().deleteContact(resourceName=resource_name)
        await asyncio.to_thread(request.execute)
        return True


contacts_service = ContactsService()
