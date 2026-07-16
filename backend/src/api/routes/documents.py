from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Form
from typing import List
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi.responses import FileResponse
from src.models.document import Document
from src.services.rag.parser import document_parser
from src.services.rag.chunker import text_chunker
from src.services.rag.retriever import get_retriever
from src.services.rag.ocr import enrich_pdf_with_ocr
from src.utils.logger import logger
from src.models.workspace import Workspace

router = APIRouter(prefix="/api/documents", tags=["Documents"])

# Directory for storing uploaded files persistently (images etc.)
UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
TEXT_EXTENSIONS = {"pdf", "docx", "pptx", "txt", "md"}
ALL_EXTENSIONS = IMAGE_EXTENSIONS | TEXT_EXTENSIONS


async def can_use_workspace(workspace_id: str | None, user_id: str) -> bool:
    if not workspace_id:
        return True
    workspace = await Workspace.get(workspace_id)
    return bool(workspace and (workspace.user_id == user_id or user_id in workspace.member_ids))


@router.get("/storage")
async def document_storage(http_request: Request, user_id: str = "default") -> dict:
    """Return total storage used by documents for a user.

    Calculates aggregated file sizes from MongoDB rather than relying
    on client-side computation or hardcoded limits.
    """
    auth_user = getattr(http_request.state, "user", None)
    resolved_user_id = (auth_user.get("sub") if auth_user else None) or user_id

    from src.models.document import Document

    total_used = 0
    try:
        pipeline = [
            {"$match": {"user_id": resolved_user_id}},
            {"$group": {"_id": None, "total": {"$sum": "$file_size"}}},
        ]
        result = await Document.aggregate(pipeline).to_list()
        if result:
            total_used = result[0].get("total", 0)
    except Exception as e:
        logger.warning(f"Storage aggregation failed, falling back to sum: {e}")
        docs = await Document.find(Document.user_id == resolved_user_id).to_list()
        total_used = sum(d.file_size for d in docs)

    return {
        "used": total_used,
    }


@router.get("")
async def list_documents(http_request: Request, user_id: str = "default", workspace_id: str | None = None) -> list[dict]:
    auth_user = getattr(http_request.state, "user", None)
    resolved_user_id = (auth_user.get("sub") if auth_user else None) or user_id
    if workspace_id and workspace_id != "__unfiled__" and not await can_use_workspace(workspace_id, resolved_user_id):
        raise HTTPException(status_code=404, detail="Workspace not found")

    from src.services.rag.opendocuments_client import should_use_opendocuments, opendocuments_client
    # Workspace-scoped documents must stay in the local index so member
    # permissions and workspace filtering remain enforceable.
    if not workspace_id and await should_use_opendocuments(resolved_user_id):
        return await opendocuments_client.list_documents()

    # Build a query scoped to the user. When a workspace is specified, also
    # filter by workspace — but never remove the user ownership filter.
    query = Document.find(Document.user_id == resolved_user_id)
    if workspace_id == "__unfiled__":
        query = query.find(Document.workspace_id == None)
    elif workspace_id:
        query = query.find(Document.workspace_id == workspace_id)
    docs = await query.sort(-Document.created_at).to_list()
    return [
        {
            "id": str(d.id),
            "fileName": d.file_name,
            "fileType": d.file_type,
            "fileSize": d.file_size,
            "status": d.status,
            "chunks": d.chunk_count,
            "createdAt": d.created_at.isoformat(),
            "imageUrl": f"/api/documents/{d.id}/download" if d.file_type in IMAGE_EXTENSIONS else None,
            "workspaceId": d.workspace_id,
            "ocrPages": d.ocr_pages,
            "driveWebViewLink": d.drive_web_view_link,
        }
        for d in docs
    ]


@router.post("/upload")
async def upload_document(http_request: Request, file: UploadFile = File(...), user_id: str = "default", workspace_id: str | None = Form(None)) -> dict:
    if file.filename is None:
        raise HTTPException(status_code=400, detail="No file provided")

    auth_user = getattr(http_request.state, "user", None)
    resolved_user_id = (auth_user.get("sub") if auth_user else None) or user_id
    if workspace_id and not await can_use_workspace(workspace_id, resolved_user_id):
        raise HTTPException(status_code=404, detail="Workspace not found")

    ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
    if ext not in ALL_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    is_image = ext in IMAGE_EXTENSIONS
    content = await file.read()

    # Optional Google Drive sync
    drive_access_token = http_request.headers.get("X-Drive-Access-Token", "")
    drive_refresh_token = http_request.headers.get("X-Drive-Refresh-Token", "")

    from src.services.rag.opendocuments_client import should_use_opendocuments, opendocuments_client
    if not workspace_id and not is_image and await should_use_opendocuments(resolved_user_id):
        return await opendocuments_client.upload_document(file.filename, content)

    if is_image:
        # Store images permanently in uploads directory
        safe_name = f"{uuid.uuid4().hex}_{file.filename}"
        dest_path = UPLOAD_DIR / safe_name
        with open(dest_path, "wb") as f:
            f.write(content)

        doc = Document(
            user_id=resolved_user_id,
            file_name=file.filename,
            file_type=ext,
            file_size=len(content),
            file_path=str(dest_path),
            status="ready",
            chunk_count=0,
            workspace_id=workspace_id,
        )
        await doc.insert()

        if drive_access_token:
            try:
                from src.services.drive.service import DriveService
                drive = DriveService()
                mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp", "svg": "image/svg+xml"}
                drive_result = await drive.upload_file(
                    access_token=drive_access_token,
                    file_path=str(dest_path),
                    file_name=file.filename,
                    mime_type=mime_map.get(ext, "application/octet-stream"),
                    refresh_token=drive_refresh_token,
                )
                doc.drive_file_id = drive_result.get("id")
                doc.drive_web_view_link = drive_result.get("webViewLink")
                await doc.save()
                logger.info(f"Image synced to Drive: {file.filename} (id={doc.drive_file_id})")
            except Exception as e:
                logger.warning(f"Failed to sync image to Drive: {e}")

        logger.info(f"Stored image: {file.filename}")

        return {
            "id": str(doc.id),
            "fileName": doc.file_name,
            "fileType": doc.file_type,
            "fileSize": doc.file_size,
            "status": doc.status,
            "chunks": doc.chunk_count,
            "imageUrl": f"/api/documents/{doc.id}/download",
            "driveFileId": doc.drive_file_id,
            "driveWebViewLink": doc.drive_web_view_link,
        }
    else:
        # Documents: parse, chunk, store in vector DB
        # Store file persistently so it can be served for preview later
        safe_name = f"{uuid.uuid4().hex}_{file.filename}"
        dest_path = UPLOAD_DIR / safe_name
        with open(dest_path, "wb") as f:
            f.write(content)
        file_path = str(dest_path)

        doc = Document(
            user_id=resolved_user_id,
            file_name=file.filename,
            file_type=ext,
            file_size=len(content),
            file_path=file_path,
            status="processing",
            workspace_id=workspace_id,
        )
        await doc.insert()

        try:
            parse_result = document_parser.parse(file_path, ext)
            ocr_pages = 0
            if ext == "pdf":
                parse_result, ocr_pages = await enrich_pdf_with_ocr(file_path, parse_result)
            chunks = text_chunker.chunk(parse_result)

            chunk_data = [
                {
                    "content": c.content,
                    "chunk_index": c.chunk_index,
                    "page_number": c.page_number,
                    "section": c.section,
                }
                for c in chunks
            ]

            retriever = get_retriever()
            await retriever.store_document_chunks(
                chunks=chunk_data,
                user_id=resolved_user_id,
                document_id=str(doc.id),
                file_name=file.filename,
                workspace_id=workspace_id,
            )

            doc.chunk_count = len(chunks)
            doc.ocr_pages = ocr_pages
            doc.status = "ready"
            await doc.save()

            if drive_access_token:
                try:
                    from src.services.drive.service import DriveService
                    drive = DriveService()
                    media_type_map = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation", "txt": "text/plain", "md": "text/markdown"}
                    drive_result = await drive.upload_file(
                        access_token=drive_access_token,
                        file_path=file_path,
                        file_name=file.filename,
                        mime_type=media_type_map.get(ext, "application/octet-stream"),
                        refresh_token=drive_refresh_token,
                    )
                    doc.drive_file_id = drive_result.get("id")
                    doc.drive_web_view_link = drive_result.get("webViewLink")
                    await doc.save()
                    logger.info(f"Document synced to Drive: {file.filename} (id={doc.drive_file_id})")
                except Exception as e:
                    logger.warning(f"Failed to sync document to Drive: {e}")

            logger.info(f"Processed document: {file.filename} ({len(chunks)} chunks)")

            return {
                "id": str(doc.id),
                "fileName": doc.file_name,
                "fileType": doc.file_type,
                "fileSize": doc.file_size,
                "status": doc.status,
                "chunks": doc.chunk_count,
                "imageUrl": None,
                "ocrPages": ocr_pages,
                "driveFileId": doc.drive_file_id,
                "driveWebViewLink": doc.drive_web_view_link,
            }
        except Exception as e:
            doc.status = "error"
            doc.error_message = str(e)
            await doc.save()
            logger.error(f"Document processing failed: {e}")
            # Clean up the saved file on error
            if os.path.exists(file_path):
                os.unlink(file_path)
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}")
async def get_document(document_id: str) -> dict:
    """Get document metadata."""
    doc = await Document.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    is_image = doc.file_type in IMAGE_EXTENSIONS
    return {
        "id": str(doc.id),
        "fileName": doc.file_name,
        "fileType": doc.file_type,
        "fileSize": doc.file_size,
        "status": doc.status,
        "chunks": doc.chunk_count,
        "imageUrl": f"/api/documents/{doc.id}/download" if is_image else None,
        "createdAt": doc.created_at.isoformat(),
        "workspaceId": doc.workspace_id,
        "ocrPages": doc.ocr_pages,
        "driveFileId": doc.drive_file_id,
        "driveWebViewLink": doc.drive_web_view_link,
    }


@router.get("/{document_id}/download")
async def download_document(document_id: str):
    """Serve an uploaded file for inline preview.

    If a Google Drive ``webViewLink`` is available the request is redirected
    to Drive so the user gets Drive's built-in viewer (handles PDFs, images,
    DOCX, etc. perfectly).  Falls back to the local file when no Drive link
    exists (e.g. upload without a Google session).
    """
    doc = await Document.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Prefer Drive's viewer when available — it survives server restarts
    # and provides a better preview experience (especially for PDFs).
    if doc.drive_web_view_link:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=doc.drive_web_view_link)

    file_path = doc.file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    media_type_map = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
        "svg": "image/svg+xml",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "txt": "text/plain",
        "md": "text/markdown",
    }
    media_type = media_type_map.get(doc.file_type, "application/octet-stream")

    inline_types = {"pdf", "png", "jpg", "jpeg", "gif", "webp", "svg", "txt", "md"}
    disposition = "inline" if doc.file_type in inline_types else "attachment"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=doc.file_name,
        content_disposition_type=disposition,
    )


@router.post("/{document_id}/drive-upload")
async def upload_document_to_drive(document_id: str, http_request: Request) -> dict:
    """Upload an existing document to Google Drive."""
    doc = await Document.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    drive_access_token = http_request.headers.get("X-Drive-Access-Token", "")
    if not drive_access_token:
        raise HTTPException(status_code=400, detail="X-Drive-Access-Token header is required")

    if doc.drive_file_id:
        return {"driveFileId": doc.drive_file_id, "driveWebViewLink": doc.drive_web_view_link}

    file_path = doc.file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    drive_refresh_token = http_request.headers.get("X-Drive-Refresh-Token", "")
    media_type_map = {
        "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "gif": "image/gif", "webp": "image/webp", "svg": "image/svg+xml",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "txt": "text/plain", "md": "text/markdown",
    }

    try:
        from src.services.drive.service import DriveService
        drive = DriveService()
        result = await drive.upload_file(
            access_token=drive_access_token,
            file_path=file_path,
            file_name=doc.file_name,
            mime_type=media_type_map.get(doc.file_type, "application/octet-stream"),
            refresh_token=drive_refresh_token,
        )
        doc.drive_file_id = result.get("id")
        doc.drive_web_view_link = result.get("webViewLink")
        await doc.save()
        return {"driveFileId": doc.drive_file_id, "driveWebViewLink": doc.drive_web_view_link}
    except Exception as e:
        logger.error(f"Failed to upload document to Drive: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(document_id: str, http_request: Request) -> dict:
    from src.services.rag.opendocuments_client import should_use_opendocuments, opendocuments_client

    auth_user = getattr(http_request.state, "user", None)
    resolved_user_id = auth_user.get("sub") if auth_user else None

    doc = await Document.get(document_id)

    # Verify ownership if document exists locally
    if doc:
        if resolved_user_id and doc.user_id != resolved_user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this document")
    elif await should_use_opendocuments(resolved_user_id or "default"):
        success = await opendocuments_client.delete_document(document_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"success": True, "message": "Document deleted"}
    else:
        raise HTTPException(status_code=404, detail="Document not found")

    if os.path.exists(doc.file_path):
        os.unlink(doc.file_path)

    if doc.file_type not in IMAGE_EXTENSIONS:
        from src.services.vector_store.factory import get_vector_store
        vs = get_vector_store()
        await vs.delete("documents", [document_id])

    await doc.delete()
    return {"success": True, "message": "Document deleted"}


@router.patch("/{document_id}/workspace")
async def move_document(document_id: str, http_request: Request, workspace_id: str | None = None) -> dict:
    auth_user = getattr(http_request.state, "user", None)
    resolved_user_id = (auth_user.get("sub") if auth_user else None) or "default"
    doc = await Document.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.user_id != resolved_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this document")
    if workspace_id:
        from src.models.workspace import Workspace
        workspace = await Workspace.get(workspace_id)
        if not workspace or (workspace.user_id != resolved_user_id and resolved_user_id not in workspace.member_ids):
            raise HTTPException(status_code=404, detail="Workspace not found")
    doc.workspace_id = workspace_id
    doc.updated_at = datetime.now(timezone.utc)
    await doc.save()
    return {"id": str(doc.id), "workspaceId": doc.workspace_id}
