from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Form
from typing import List
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi.responses import FileResponse
from src.models.document import Document, DocumentChunk
from src.services.rag.parser import document_parser
from src.services.rag.chunker import text_chunker
from src.services.rag.retriever import get_retriever
from src.services.rag.ocr import analyze_image, enrich_pdf_with_ocr
from src.utils.logger import logger
from src.models.workspace import Workspace

router = APIRouter(prefix="/api/documents", tags=["Documents"])

# Directory for storing uploaded files persistently (images etc.)
UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
TEXT_EXTENSIONS = {"pdf", "docx", "pptx", "txt", "md"}
ALL_EXTENSIONS = IMAGE_EXTENSIONS | TEXT_EXTENSIONS

# Max accepted upload size in bytes (prevents memory/disk exhaustion DoS).
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def _safe_filename(filename: str | None) -> str:
    """Strip path separators and header-injection characters from a client filename."""
    name = Path(filename or "").name
    name = "".join(ch for ch in name if ch not in '\r\n"\\')
    return name.strip() or "unnamed"


async def can_use_workspace(workspace_id: str | None, user_id: str) -> bool:
    if not workspace_id:
        return True
    workspace = await Workspace.get(workspace_id)
    return bool(workspace and (workspace.user_id == user_id or user_id in workspace.member_ids))


async def can_access_document(doc, resolved_user_id: str) -> bool:
    """Ownership + workspace-membership check for document reads.

    - Owners can always access their own documents.
    - Workspace members can access documents shared into a workspace they belong to.
    - The public ``"default"`` bucket remains readable by any user/anonymous caller
      (used by shared images) but a non-owner user cannot read another person's
      non-workspace (private) document.
    """
    if doc.user_id == resolved_user_id:
        return True
    if doc.workspace_id and await can_use_workspace(doc.workspace_id, resolved_user_id):
        return True
    if doc.user_id == "default":
        return True
    return False


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

    # Build a query scoped to the user or default bucket.
    user_ids = [resolved_user_id]
    if "default" not in user_ids:
        user_ids.append("default")

    query = Document.find({"user_id": {"$in": user_ids}})
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

    safe_name = _safe_filename(file.filename)
    ext = os.path.splitext(safe_name)[1].lower().lstrip(".")
    if ext not in ALL_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    is_image = ext in IMAGE_EXTENSIONS
    # Read with a hard cap to avoid memory/disk exhaustion (50 MB).
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")

    # Optional Google Drive sync
    drive_access_token = http_request.headers.get("X-Drive-Access-Token", "")
    drive_refresh_token = http_request.headers.get("X-Drive-Refresh-Token", "")

    from src.services.rag.opendocuments_client import should_use_opendocuments, opendocuments_client
    if not workspace_id and not is_image and await should_use_opendocuments(resolved_user_id):
        return await opendocuments_client.upload_document(safe_name, content)

    if is_image:
        # Store images permanently in uploads directory
        dest_name = f"{uuid.uuid4().hex}_{safe_name}"
        dest_path = UPLOAD_DIR / dest_name
        with open(dest_path, "wb") as f:
            f.write(content)

        doc = Document(
            user_id=resolved_user_id,
            file_name=safe_name,
            file_type=ext,
            file_size=len(content),
            file_path=str(dest_path),
            status="ready",
            chunk_count=0,
            workspace_id=workspace_id,
        )
        await doc.insert()

        vision_analyzed = False
        if ext in {"png", "jpg", "jpeg", "gif", "webp"}:
            mime_map = {
                "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "gif": "image/gif", "webp": "image/webp",
            }
            try:
                analysis = await analyze_image(content, mime_map[ext], safe_name)
                if analysis.strip():
                    await DocumentChunk(
                        document_id=str(doc.id),
                        user_id=resolved_user_id,
                        content=analysis.strip(),
                        chunk_index=0,
                        section="Image analysis",
                        metadata={"file_name": safe_name, "kind": "vision_ocr"},
                    ).insert()
                    doc.chunk_count = 1
                    await doc.save()
                    vision_analyzed = True
            except Exception as e:
                logger.warning(f"Vision analysis failed for {safe_name}: {e}")

        if drive_access_token:
            try:
                from src.services.drive.service import DriveService
                drive = DriveService()
                mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp", "svg": "image/svg+xml"}
                drive_result = await drive.upload_file(
                    access_token=drive_access_token,
                    file_path=str(dest_path),
                    file_name=safe_name,
                    mime_type=mime_map.get(ext, "application/octet-stream"),
                    refresh_token=drive_refresh_token,
                )
                doc.drive_file_id = drive_result.get("id")
                doc.drive_web_view_link = drive_result.get("webViewLink")
                await doc.save()
                logger.info(f"Image synced to Drive: {safe_name} (id={doc.drive_file_id})")
            except Exception as e:
                logger.warning(f"Failed to sync image to Drive: {e}")

        logger.info(f"Stored image: {safe_name}")

        return {
            "id": str(doc.id),
            "fileName": doc.file_name,
            "fileType": doc.file_type,
            "fileSize": doc.file_size,
            "status": doc.status,
            "chunks": doc.chunk_count,
            "imageUrl": f"/api/documents/{doc.id}/download",
            "visionAnalyzed": vision_analyzed,
            "driveFileId": doc.drive_file_id,
            "driveWebViewLink": doc.drive_web_view_link,
        }
    else:
        # Documents: parse, chunk, store in vector DB
        # Store file persistently so it can be served for preview later
        dest_name = f"{uuid.uuid4().hex}_{safe_name}"
        dest_path = UPLOAD_DIR / dest_name
        with open(dest_path, "wb") as f:
            f.write(content)
        file_path = str(dest_path)

        doc = Document(
            user_id=resolved_user_id,
            file_name=safe_name,
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

            # Preserve exact attachment text for chat. Similarity search can
            # miss vague prompts such as "what is in this PDF?".
            for chunk in chunks:
                await DocumentChunk(
                    document_id=str(doc.id),
                    user_id=resolved_user_id,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    metadata={"file_name": safe_name, "kind": "document_text"},
                ).insert()

            retriever = get_retriever()
            await retriever.store_document_chunks(
                chunks=chunk_data,
                user_id=resolved_user_id,
                document_id=str(doc.id),
                file_name=safe_name,
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
                        file_name=safe_name,
                        mime_type=media_type_map.get(ext, "application/octet-stream"),
                        refresh_token=drive_refresh_token,
                    )
                    doc.drive_file_id = drive_result.get("id")
                    doc.drive_web_view_link = drive_result.get("webViewLink")
                    await doc.save()
                    logger.info(f"Document synced to Drive: {safe_name} (id={doc.drive_file_id})")
                except Exception as e:
                    logger.warning(f"Failed to sync document to Drive: {e}")

            logger.info(f"Processed document: {safe_name} ({len(chunks)} chunks)")

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
async def get_document(document_id: str, http_request: Request) -> dict:
    """Get document metadata."""
    doc = await Document.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    auth_user = getattr(http_request.state, "user", None)
    resolved_user_id = (auth_user.get("sub") if auth_user else None) or "default"
    if not await can_access_document(doc, resolved_user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access this document")

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
async def download_document(document_id: str, http_request: Request, download: bool = False):
    """Serve an uploaded file for inline preview or direct attachment download.

    If download=True, forces direct file attachment download without redirecting.
    If download=False and a Google Drive webViewLink is available, redirects to Drive.
    """
    doc = await Document.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    auth_user = getattr(http_request.state, "user", None)
    resolved_user_id = (auth_user.get("sub") if auth_user else None) or "default"
    if not await can_access_document(doc, resolved_user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access this document")

    # Image formats must be served directly as binary image bytes for <img> tags
    is_image = doc.file_type.lower() in {"png", "jpg", "jpeg", "gif", "webp", "svg"}

    # Only redirect non-image documents to Drive preview if this is an inline view request and not a download
    if doc.drive_web_view_link and not download and not is_image:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=doc.drive_web_view_link)

    file_path = doc.file_path or str(UPLOAD_DIR / doc.file_name)
    if not os.path.exists(file_path):
        if doc.drive_file_id:
            try:
                from src.services.drive.service import drive_service
                drive_token = http_request.headers.get("X-Drive-Access-Token") or http_request.headers.get("X-Google-Access-Token", "")
                drive_refresh = http_request.headers.get("X-Drive-Refresh-Token") or http_request.headers.get("X-Google-Refresh-Token", "")
                if drive_token:
                    file_bytes = await drive_service.download_file(drive_token, doc.drive_file_id, drive_refresh)
                    cached_path = Path(UPLOAD_DIR) / doc.file_name
                    cached_path.write_bytes(file_bytes)
                    doc.file_path = str(cached_path)
                    await doc.save()
                    file_path = str(cached_path)
                    logger.info(f"Recovered missing file from Google Drive: {doc.file_name}")
            except Exception as err:
                logger.warning(f"Failed to recover file {doc.file_name} from Drive: {err}")

        if not os.path.exists(file_path):
            if doc.drive_web_view_link and not is_image:
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url=doc.drive_web_view_link)
            raise HTTPException(status_code=404, detail="File not found on disk or Google Drive")

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
    disposition = "attachment" if download else ("inline" if doc.file_type in inline_types else "attachment")

    # Active-content types (SVG can carry scripts; text files can embed HTML).
    # Serve with a strict sandbox CSP so a hostile document cannot run scripts
    # in the origin if it is rendered inline.
    headers = {}
    if doc.file_type in {"svg", "txt", "md"}:
        headers["Content-Security-Policy"] = "sandbox; default-src 'none'; img-src * data:; style-src 'unsafe-inline'"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=doc.file_name,
        content_disposition_type=disposition,
        headers=headers,
    )


@router.post("/{document_id}/drive-upload")
async def upload_document_to_drive(document_id: str, http_request: Request) -> dict:
    """Upload an existing document to Google Drive."""
    doc = await Document.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    auth_user = getattr(http_request.state, "user", None)
    resolved_user_id = (auth_user.get("sub") if auth_user else None) or "default"
    if doc.user_id != resolved_user_id:
        if not doc.workspace_id or not await can_use_workspace(doc.workspace_id, resolved_user_id):
            raise HTTPException(status_code=403, detail="Not authorized to access this document")

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
    resolved_user_id = (auth_user.get("sub") if auth_user else None) or "default"

    doc = await Document.get(document_id)

    # Verify ownership or default access if document exists locally
    if doc:
        is_owner = (
            doc.user_id == resolved_user_id
            or doc.user_id == "default"
            or resolved_user_id == "default"
        )
        if not is_owner and doc.workspace_id:
            from src.models.workspace import Workspace
            ws = await Workspace.get(doc.workspace_id)
            if ws and (ws.user_id == resolved_user_id or resolved_user_id in ws.member_ids):
                is_owner = True

        if not is_owner:
            raise HTTPException(status_code=403, detail="Not authorized to delete this document")
    elif await should_use_opendocuments(resolved_user_id):
        success = await opendocuments_client.delete_document(document_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"success": True, "message": "Document deleted"}
    else:
        raise HTTPException(status_code=404, detail="Document not found")

    if os.path.exists(doc.file_path):
        try:
            os.unlink(doc.file_path)
        except Exception as err:
            logger.warning(f"Could not remove document file on disk: {err}")

    # Remove chunk embeddings and vector store items
    try:
        await DocumentChunk.find({"document_id": document_id}).delete()
    except Exception as err:
        logger.warning(f"Could not delete DocumentChunks for {document_id}: {err}")

    if doc.file_type not in IMAGE_EXTENSIONS:
        try:
            from src.services.vector_store.factory import get_vector_store
            vs = get_vector_store()
            await vs.delete("documents", [document_id])
        except Exception as err:
            logger.warning(f"Vector store deletion warning for {document_id}: {err}")

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
