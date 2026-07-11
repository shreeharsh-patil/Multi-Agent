from typing import Optional
from src.services.rag.parser import ParseResult
from src.utils.logger import logger


class TextChunk:
    def __init__(self, content: str, chunk_index: int, page_number: Optional[int] = None, section: Optional[str] = None):
        self.content = content
        self.chunk_index = chunk_index
        self.page_number = page_number
        self.section = section


class TextChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, parse_result: ParseResult) -> list[TextChunk]:
        chunks = []
        chunk_index = 0

        for page_num, page_text in enumerate(parse_result.pages, start=1):
            page_chunks = self._split_text(page_text, page_num)
            for chunk in page_chunks:
                chunk.chunk_index = chunk_index
                chunk_index += 1
                chunks.append(chunk)

        logger.info(f"Chunked into {len(chunks)} chunks")
        return chunks

    def _split_text(self, text: str, page_number: int) -> list[TextChunk]:
        if len(text) <= self.chunk_size:
            return [TextChunk(content=text, chunk_index=0, page_number=page_number)]

        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))

            if end < len(text):
                last_period = text.rfind(".", start, end)
                last_newline = text.rfind("\n", start, end)
                split_at = max(last_period + 1 if last_period > start else -1,
                               last_newline + 1 if last_newline > start else -1)
                if split_at > start:
                    end = split_at

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(TextChunk(content=chunk_text, chunk_index=index, page_number=page_number))

            start = end - self.chunk_overlap if end < len(text) else len(text)
            index += 1

        return chunks


text_chunker = TextChunker()
