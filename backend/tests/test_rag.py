import pytest
import tempfile
import os
from src.services.rag.parser import document_parser
from src.services.rag.chunker import text_chunker, TextChunker


class TestDocumentParser:
    def test_parse_txt(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello world.\nThis is a test document.")
            tmp_path = f.name

        try:
            result = document_parser.parse(tmp_path, "txt")
            assert "Hello world" in result.text
            assert "test document" in result.text
        finally:
            os.unlink(tmp_path)

    def test_parse_md(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Heading\n\nSome markdown content.")
            tmp_path = f.name

        try:
            result = document_parser.parse(tmp_path, "md")
            assert "# Heading" in result.text
        finally:
            os.unlink(tmp_path)

    def test_unsupported_format(self):
        with pytest.raises(ValueError):
            document_parser.parse("test.html", "html")


class TestTextChunker:
    def test_small_text_stays_as_one_chunk(self):
        class MockParseResult:
            def __init__(self):
                self.text = "Short text"
                self.pages = ["Short text"]

        chunks = text_chunker.chunk(MockParseResult())
        assert len(chunks) == 1
        assert chunks[0].content == "Short text"

    def test_large_text_is_split(self):
        long_text = "Word " * 5000

        class MockParseResult:
            def __init__(self):
                self.text = long_text
                self.pages = [long_text]

        chunks = text_chunker.chunk(MockParseResult())
        assert len(chunks) > 1


class TestChunkerConfig:
    def test_custom_chunk_size(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)

        class MockParseResult:
            def __init__(self):
                self.text = "A " * 200
                self.pages = ["A " * 200]

        chunks = chunker.chunk(MockParseResult())
        assert all(len(c.content) <= 100 for c in chunks)
