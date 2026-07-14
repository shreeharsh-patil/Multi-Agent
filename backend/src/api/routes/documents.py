from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from typing import List
import os
import uuid
import tempfile
from pathlib import Path
from fastapi.responses import FileResponse
from src.models.document import Document
from src.services.rag.parser import document_parser
from src.services.rag.chunker import text_chunker
from src.services.rag.retriever import get_retriever
from src.utils.logger import logger

router = APIRouter(prefix="/api/documents", tags=["Documents"])

# Directory for storing uploaded files persistently (images etc.)
UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
TEXT_EXTENSIONS = {"pdf", "docx", "pptx", "txt", "md"}
ALL_EXTENSIONS = IMAGE_EXTENSIONS | TEXT_EXTENSIONS


@router.get("")
async def list_documents(http_request: Request, user_id: str = "default") -> list[dict]:
    auth_user = getattr(http_request.state, "user", None)
    resolved_user_id = (auth_user.get("sub") if auth_user else None) or user_id

    from src.services.rag.opendocuments_client import should_use_opendocuments, opendocuments_client
    if await should_use_opendocuments(resolved_user_id):
        return await opendocuments_client.list_documents()

    docs = await Document.find(Document.user_id == resolved_user_id).sort(-Document.created_at).to_list()
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
        }
        for d in docs
    ]


@router.post("/upload")
async def upload_document(http_request: Request, file: UploadFile = File(...), user_id: str = "default") -> dict:
    if file.filename is None:
        raise HTTPException(status_code=400, detail="No file provided")

    auth_user = getattr(http_request.state, "user", None)
    resolved_user_id = (auth_user.get("sub") if auth_user else None) or user_id

    ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
    if ext not in ALL_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    is_image = ext in IMAGE_EXTENSIONS
    content = await file.read()

    from src.services.rag.opendocuments_client import should_use_opendocuments, opendocuments_client
    if not is_image and await should_use_opendocuments(resolved_user_id):
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
        )
        await doc.insert()

        logger.info(f"Stored image: {file.filename}")

        return {
            "id": str(doc.id),
            "fileName": doc.file_name,
            "fileType": doc.file_type,
            "fileSize": doc.file_size,
            "status": doc.status,
            "chunks": doc.chunk_count,
            "imageUrl": f"/api/documents/{doc.id}/download",
        }
    else:
        # Documents: parse, chunk, store in vector DB
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        doc = Document(
            user_id=resolved_user_id,
            file_name=file.filename,
            file_type=ext,
            file_size=len(content),
            file_path=tmp_path,
            status="processing",
        )
        await doc.insert()

        try:
            parse_result = document_parser.parse(tmp_path, ext)
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
            )

            doc.chunk_count = len(chunks)
            doc.status = "ready"
            await doc.save()

            logger.info(f"Processed document: {file.filename} ({len(chunks)} chunks)")

            return {
                "id": str(doc.id),
                "fileName": doc.file_name,
                "fileType": doc.file_type,
                "fileSize": doc.file_size,
                "status": doc.status,
                "chunks": doc.chunk_count,
                "imageUrl": None,
            }
        except Exception as e:
            doc.status = "error"
            doc.error_message = str(e)
            await doc.save()
            logger.error(f"Document processing failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


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
    }


@router.get("/{document_id}/download")
async def download_document(document_id: str):
    """Download/serve an uploaded file (used for inline image display)."""
    doc = await Document.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

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

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=doc.file_name,
    )


@router.delete("/{document_id}")
async def delete_document(document_id: str) -> dict:
    from src.services.rag.opendocuments_client import should_use_opendocuments, opendocuments_client
    
    # Check if document exists locally
    doc = await Document.get(document_id)
    
    if await should_use_opendocuments() or not doc:
        if doc:
            if os.path.exists(doc.file_path):
                os.unlink(doc.file_path)
            await doc.delete()
            return {"success": True, "message": "Document deleted"}
        else:
            success = await opendocuments_client.delete_document(document_id)
            if not success:
                raise HTTPException(status_code=404, detail="Document not found")
            return {"success": True, "message": "Document deleted"}

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete the physical file if it exists
    if os.path.exists(doc.file_path):
        os.unlink(doc.file_path)

    # Delete from vector store (only for text documents)
    if doc.file_type not in IMAGE_EXTENSIONS:
        from src.services.vector_store.factory import get_vector_store
        vs = get_vector_store()
        await vs.delete("documents", [document_id])

    await doc.delete()
    return {"success": True, "message": "Document deleted"}
