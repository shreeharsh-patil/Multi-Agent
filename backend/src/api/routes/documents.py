from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import os
import tempfile
from src.models.document import Document
from src.services.rag.parser import document_parser
from src.services.rag.chunker import text_chunker
from src.services.rag.retriever import get_retriever
from src.utils.logger import logger

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.get("")
async def list_documents(user_id: str = "default") -> list[dict]:
    docs = await Document.find(Document.user_id == user_id).sort(-Document.created_at).to_list()
    return [
        {
            "id": str(d.id),
            "fileName": d.file_name,
            "fileType": d.file_type,
            "fileSize": d.file_size,
            "status": d.status,
            "chunks": d.chunk_count,
            "createdAt": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), user_id: str = "default") -> dict:
    if file.filename is None:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
    if ext not in ("pdf", "docx", "pptx", "txt", "md"):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    doc = Document(
        user_id=user_id,
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
            user_id=user_id,
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


@router.delete("/{document_id}")
async def delete_document(document_id: str) -> dict:
    doc = await Document.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from src.services.vector_store.factory import vector_store
    await vector_store.delete("documents", [document_id])

    await doc.delete()
    return {"success": True, "message": "Document deleted"}
