from datetime import datetime
from typing import Optional, Literal
from beanie import Document as BeanieDocument
from pydantic import Field


class Document(BeanieDocument):
    user_id: str
    file_name: str
    file_type: Literal["pdf", "docx", "pptx", "txt", "md"]
    file_size: int
    file_path: str
    status: Literal["uploading", "processing", "ready", "error"] = "uploading"
    chunk_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "documents"
        use_state_management = True


class DocumentChunk(BeanieDocument):
    document_id: str
    user_id: str
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    section: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    embedding: Optional[list[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "document_chunks"
        use_state_management = True
