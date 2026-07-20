from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.api.routes.chat import _build_attachment_context, _load_attachment_text


class _ChunkQuery:
    def __init__(self, chunks):
        self.chunks = chunks

    def sort(self, *_args):
        return self

    async def to_list(self):
        return self.chunks


@pytest.mark.asyncio
async def test_load_attachment_text_preserves_chunk_order():
    doc = SimpleNamespace(id="doc-1", user_id="user-1", file_type="pdf", file_path="missing.pdf")
    chunks = [
        SimpleNamespace(content="First page", chunk_index=0),
        SimpleNamespace(content="Second page", chunk_index=1),
    ]

    with patch("src.api.routes.chat.DocumentChunk.find", return_value=_ChunkQuery(chunks)):
        content = await _load_attachment_text(doc)

    assert content == "First page\n\nSecond page"


@pytest.mark.asyncio
async def test_attachment_context_contains_actual_document_text():
    doc = SimpleNamespace(
        id="doc-1",
        user_id="user-1",
        file_name="report.pdf",
        file_type="pdf",
        file_path="report.pdf",
    )

    with (
        patch("src.api.routes.chat.Document.get", new=AsyncMock(return_value=doc)),
        patch("src.api.routes.chat._load_attachment_text", new=AsyncMock(return_value="Revenue grew by 18 percent.")),
    ):
        context = await _build_attachment_context(
            [{"documentId": "doc-1", "name": "report.pdf"}],
            "user-1",
            "What is in this PDF?",
        )

    assert "report.pdf (pdf)" in context
    assert "Revenue grew by 18 percent." in context
    assert context.endswith("User's request:\n")


@pytest.mark.asyncio
async def test_attachment_context_does_not_expose_another_users_document():
    doc = SimpleNamespace(
        id="doc-1",
        user_id="another-user",
        file_name="private.pdf",
        file_type="pdf",
        file_path="private.pdf",
    )

    with (
        patch("src.api.routes.chat.Document.get", new=AsyncMock(return_value=doc)),
        patch("src.api.routes.chat._load_attachment_text", new=AsyncMock(return_value="private contents")) as load_text,
    ):
        context = await _build_attachment_context(
            [{"documentId": "doc-1", "name": "private.pdf"}],
            "user-1",
        )

    assert "not available to the current user" in context
    assert "private contents" not in context
    load_text.assert_not_awaited()
