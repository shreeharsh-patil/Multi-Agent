import httpx
from src.config import settings
from src.utils.logger import logger


# Shared httpx client with connection pooling for all OpenDocuments API calls.
_opendocuments_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _opendocuments_client
    if _opendocuments_client is None:
        _opendocuments_client = httpx.AsyncClient(
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            timeout=httpx.Timeout(30.0, connect=5.0),
        )
    return _opendocuments_client


class OpenDocumentsClient:
    def __init__(self):
        self.api_url = settings.opendocuments_api_url

    async def is_available(self) -> bool:
        try:
            client = _get_client()
            res = await client.get(f"{self.api_url}/api/v1/health", timeout=2.0)
            return res.status_code == 200
        except Exception:
            return False

    async def list_documents(self) -> list[dict]:
        try:
            client = _get_client()
            res = await client.get(f"{self.api_url}/api/v1/documents", timeout=5.0)
            if res.status_code == 200:
                data = res.json()
                docs = data.get("documents", [])
                return [
                    {
                        "id": d["id"],
                        "fileName": d.get("title") or d.get("fileName") or "Untitled",
                        "fileType": d.get("file_type") or d.get("fileType") or "unknown",
                        "fileSize": d.get("file_size_bytes") or d.get("fileSize") or 0,
                        "status": d.get("status") or "ready",
                        "chunks": d.get("chunk_count") or d.get("chunks") or 0,
                        "createdAt": d.get("created_at") or d.get("createdAt") or "",
                        "imageUrl": None,
                    }
                    for d in docs
                ]
        except Exception as e:
            logger.error(f"Failed to list documents from OpenDocuments: {e}")
        return []

    async def upload_document(self, file_name: str, content: bytes) -> dict:
        try:
            client = _get_client()
            files = {"file": (file_name, content)}
            res = await client.post(f"{self.api_url}/api/v1/documents/upload", files=files, timeout=30.0)
            if res.status_code in (200, 201):
                d = res.json()
                return {
                    "id": d["id"],
                    "fileName": d.get("title") or d.get("fileName") or file_name,
                    "fileType": d.get("file_type") or d.get("fileType") or "unknown",
                    "fileSize": d.get("file_size_bytes") or d.get("fileSize") or len(content),
                    "status": d.get("status") or "ready",
                    "chunks": d.get("chunk_count") or d.get("chunks") or 0,
                    "imageUrl": None,
                }
            else:
                raise Exception(f"HTTP {res.status_code}: {res.text}")
        except Exception as e:
            logger.error(f"Failed to upload document to OpenDocuments: {e}")
            raise e

    async def delete_document(self, doc_id: str) -> bool:
        try:
            client = _get_client()
            res = await client.delete(f"{self.api_url}/api/v1/documents/{doc_id}", timeout=5.0)
            return res.status_code == 200
        except Exception as e:
            logger.error(f"Failed to delete document from OpenDocuments: {e}")
        return False

    async def query_rag(self, query: str, top_k: int = 5) -> dict:
        try:
            client = _get_client()
            payload = {
                "query": query,
                "profile": "balanced"
            }
            res = await client.post(f"{self.api_url}/api/v1/chat", json=payload, timeout=20.0)
            if res.status_code == 200:
                data = res.json()
                answer = data.get("answer", "")
                sources = data.get("sources", [])

                results = []
                citations = []
                for idx, src in enumerate(sources[:top_k]):
                    doc_id = src.get("documentId")
                    score = src.get("score") or 0.0
                    text_content = src.get("content") or ""
                    file_name = src.get("fileName") or src.get("title") or f"Source {idx+1}"

                    results.append({
                        "id": doc_id or f"opendoc_{idx}",
                        "content": text_content,
                        "metadata": {
                            "file_name": file_name,
                            "page_number": src.get("pageNumber"),
                            "section": src.get("section")
                        },
                        "score": score
                    })
                    citations.append({
                        "file_name": file_name,
                        "page_number": src.get("pageNumber")
                    })

                return {
                    "results": results,
                    "citations": citations,
                    "answer": answer
                }
        except Exception as e:
            logger.error(f"Failed to query OpenDocuments RAG: {e}")
        return {
            "results": [],
            "citations": [],
            "answer": "Failed to connect to OpenDocuments RAG engine."
        }


opendocuments_client = OpenDocumentsClient()


async def should_use_opendocuments(user_id: str = "default") -> bool:
    from src.config import settings
    if settings.use_opendocuments_rag:
        return True

    try:
        from src.models.user import User
        # Try finding by MongoDB ObjectId first (most common), then by email
        user = await User.get(user_id)
        if not user:
            user = await User.find_one(User.email == user_id)

        if user and hasattr(user, 'preferences'):
            return getattr(user.preferences, "use_opendocuments_rag", False)
    except Exception:
        pass

    return False
