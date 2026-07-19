import asyncio
from pathlib import Path
from src.config import settings
from src.services.rag.parser import ParseResult
from src.services.llm import llm_service
from src.utils.logger import logger


def needs_ocr(page_text: str) -> bool:
    return len("".join(page_text.split())) < settings.ocr_min_page_chars


async def enrich_pdf_with_ocr(file_path: str, parsed: ParseResult) -> tuple[ParseResult, int]:
    """OCR low-text PDF pages with Gemini vision and preserve page boundaries."""
    if not settings.enable_multimodal_ocr or not parsed.pages:
        return parsed, 0

    page_indexes = [index for index, text in enumerate(parsed.pages) if needs_ocr(text)]
    if not page_indexes:
        return parsed, 0

    try:
        import fitz
        pdf = await asyncio.to_thread(fitz.open, file_path)
    except ImportError:
        logger.warning("PyMuPDF is not installed; skipping scanned PDF OCR")
        return parsed, 0
    except Exception as exc:
        logger.warning(f"Could not open PDF for multimodal OCR: {exc}")
        return parsed, 0

    ocr_count = 0
    try:
        for page_index in page_indexes:
            page = pdf.load_page(page_index)
            pixmap = await asyncio.to_thread(page.get_pixmap, matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            image_bytes = await asyncio.to_thread(pixmap.tobytes, "png")
            prompt = (
                "Transcribe and describe this document page for semantic search. "
                "Extract all readable text exactly, including handwritten text, equations, labels, "
                "table values, diagram relationships, and meaningful visual context. "
                "Return clean plain text with short headings where useful. Do not mention the OCR process."
            )
            try:
                text = await llm_service.generate_multimodal(prompt, image_bytes, "image/png", max_output_tokens=4096)
                if text.strip():
                    parsed.pages[page_index] = text.strip()
                    ocr_count += 1
            except NotImplementedError:
                logger.info("Skipping PDF OCR because the configured LLM provider is not multimodal")
                break
            except Exception as exc:
                logger.warning(f"OCR failed for PDF page {page_index + 1}: {exc}")
    finally:
        pdf.close()

    parsed.text = "\n\n".join(parsed.pages)
    return parsed, ocr_count


async def analyze_image(image_bytes: bytes, mime_type: str, file_name: str) -> str:
    """Extract readable text and useful visual context from an image."""
    prompt = (
        f"Analyze the uploaded image named {file_name!r}. Extract all readable text exactly, "
        "including handwriting, labels, tables, equations, and UI text. Then describe the "
        "important objects, layout, relationships, and any visible issue relevant to a user asking "
        "questions about the image. Return concise plain text with 'Extracted text' and "
        "'Visual analysis' sections. Do not mention the OCR process."
    )
    return await llm_service.generate_multimodal(
        prompt,
        image_bytes,
        mime_type,
        max_output_tokens=4096,
    )
