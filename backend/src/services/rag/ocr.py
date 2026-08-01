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
                "Transcribe and analyze this document page for scientific search and Q&A. "
                "Extract all readable text exactly, including handwritten text, forms, labels, equations, and tables. "
                "MANDATORY FORMATTING RULES:\n"
                "1. Format all mathematical equations, formulas, fractions, matrices, and variables in standard LaTeX ($...$ for inline, $$...$$ for display math).\n"
                "2. Format all tables as clean, valid Markdown tables (| Header 1 | Header 2 |).\n"
                "3. Use Markdown headings (##, ###), bullet lists, and bold text for visual structure.\n"
                "Do not mention the OCR process."
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
        f"Analyze the uploaded image or document named {file_name!r}. Extract all readable text exactly, "
        "including handwriting, labels, receipts, invoices, forms, tables, and equations. "
        "MANDATORY FORMATTING RULES:\n"
        "1. Format all mathematical formulas and variables in standard LaTeX ($...$ for inline math, $$...$$ for display math).\n"
        "2. Format all tables as clean, valid Markdown tables (| Col 1 | Col 2 |).\n"
        "3. Return clean Markdown with '### Extracted Content' and '### Visual & Layout Analysis' sections. "
        "Do not mention the OCR process."
    )
    try:
        res = await llm_service.generate_multimodal(
            prompt,
            image_bytes,
            mime_type,
            max_output_tokens=4096,
        )
        if res and res.strip():
            return res.strip()
    except Exception as exc:
        logger.warning(f"generate_multimodal vision analysis failed for {file_name}: {exc}")

    # Fallback: try PIL & PyTesseract OCR if available
    try:
        import io
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
        mode = img.mode

        ocr_text = ""
        try:
            import pytesseract
            ocr_text = pytesseract.image_to_string(img).strip()
        except Exception:
            pass

        if ocr_text:
            return f"Extracted Text from Image ({file_name}):\n{ocr_text}"
        return f"Image attachment '{file_name}' ({width}x{height} pixels, format {mode})."
    except Exception as err:
        logger.warning(f"PIL fallback failed for {file_name}: {err}")
        return f"Image attachment '{file_name}'."
