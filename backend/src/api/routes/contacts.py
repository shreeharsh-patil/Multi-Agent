from fastapi import APIRouter, Depends, Query, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, List
from src.services.contacts.service import contacts_service
from src.adk.tools import find_user_access_token
from src.utils.logger import logger

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


class CreateContactRequest(BaseModel):
    name: str = Field(..., description="Full name of contact")
    email: Optional[str] = ""
    phone: Optional[str] = ""
    company: Optional[str] = ""


async def _resolve_token(
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    access_token: Optional[str] = Header(None, alias="X-Google-Access-Token"),
    refresh_token: Optional[str] = Header(None, alias="X-Google-Refresh-Token"),
) -> tuple[str, str]:
    token = access_token or ""
    r_token = refresh_token or ""
    if not token and user_id:
        token = await find_user_access_token(user_id)
    return token, r_token


@router.get("")
async def list_contacts(
    query: Optional[str] = Query(""),
    limit: int = Query(50, ge=1, le=200),
    user_id: str = Query("default"),
    token_data: tuple[str, str] = Depends(_resolve_token),
):
    token, refresh_token = token_data
    if not token and user_id:
        token = await find_user_access_token(user_id)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Google Contacts is not connected. Reconnect Google in Settings > Integrations."
        )

    try:
        contacts = await contacts_service.list_contacts(
            access_token=token,
            refresh_token=refresh_token,
            query=query or "",
            limit=limit,
        )
        return {"contacts": contacts, "count": len(contacts)}
    except Exception as exc:
        logger.error(f"Error listing contacts: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("")
async def create_contact(
    body: CreateContactRequest,
    user_id: str = Query("default"),
    token_data: tuple[str, str] = Depends(_resolve_token),
):
    token, refresh_token = token_data
    if not token and user_id:
        token = await find_user_access_token(user_id)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Google Contacts is not connected. Reconnect Google in Settings > Integrations."
        )

    try:
        contact = await contacts_service.create_contact(
            access_token=token,
            name=body.name,
            email=body.email or "",
            phone=body.phone or "",
            company=body.company or "",
            refresh_token=refresh_token,
        )
        return {"contact": contact, "success": True}
    except Exception as exc:
        logger.error(f"Error creating contact: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{resource_name:path}")
async def delete_contact(
    resource_name: str,
    user_id: str = Query("default"),
    token_data: tuple[str, str] = Depends(_resolve_token),
):
    token, refresh_token = token_data
    if not token and user_id:
        token = await find_user_access_token(user_id)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Google Contacts is not connected. Reconnect Google in Settings > Integrations."
        )

    try:
        # Handle resourceName prefix if missing
        res_name = resource_name if resource_name.startswith("people/") else f"people/{resource_name}"
        await contacts_service.delete_contact(
            access_token=token,
            resource_name=res_name,
            refresh_token=refresh_token,
        )
        return {"success": True, "message": f"Contact {res_name} deleted"}
    except Exception as exc:
        logger.error(f"Error deleting contact: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
