import asyncio
import io
import re
import unicodedata
from src.utils.logger import logger


UNICODE_REPLACEMENTS = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u2022": "-",
    "\u00a0": " ", "\u2192": "->", "\u2190": "<-", "\u2713": "[x]",
})


def pdf_safe_text(value: str) -> str:
    """Normalize common AI punctuation for FPDF's built-in Latin font."""
    normalized = unicodedata.normalize("NFKC", value).translate(UNICODE_REPLACEMENTS)
    return normalized.encode("latin-1", "replace").decode("latin-1")


INLINE_MARKDOWN = re.compile(r"(\*\*.+?\*\*|__.+?__|(?<!\*)\*[^*\n]+?\*(?!\*)|(?<!_)_[^_\n]+?_(?!_))")


def add_docx_markdown(paragraph, text: str) -> None:
    """Add basic bold and italic Markdown as native DOCX runs."""
    cursor = 0
    for match in INLINE_MARKDOWN.finditer(text):
        paragraph.add_run(text[cursor:match.start()])
        token = match.group(0)
        run = paragraph.add_run(token[2:-2] if token.startswith(("**", "__")) else token[1:-1])
        run.bold = token.startswith(("**", "__"))
        run.italic = not run.bold
        cursor = match.end()
    paragraph.add_run(text[cursor:])


def strip_inline_markdown(text: str) -> str:
    return INLINE_MARKDOWN.sub(
        lambda match: match.group(0)[2:-2] if match.group(0).startswith(("**", "__")) else match.group(0)[1:-1],
        text,
    )


class NotesExporter:
    """Export notes in various formats: PDF, DOCX, Markdown."""

    async def export_pdf(self, title: str, content: str) -> bytes:
        """Export note content as a PDF file."""
        try:
            from fpdf import FPDF

            def _generate():
                pdf = FPDF()
                pdf.add_page()
                pdf.set_auto_page_break(auto=True, margin=15)

                # Title
                pdf.set_font("Helvetica", "B", 16)
                pdf.multi_cell(0, 10, pdf_safe_text(title))
                pdf.ln(5)

                # Content
                pdf.set_font("Helvetica", "", 11)
                for line in content.split("\n"):
                    if line.startswith("# "):
                        pdf.set_font("Helvetica", "B", 14)
                        pdf.multi_cell(0, 8, pdf_safe_text(line[2:]), markdown=True)
                        pdf.set_font("Helvetica", "", 11)
                    elif line.startswith("## "):
                        pdf.set_font("Helvetica", "B", 12)
                        pdf.multi_cell(0, 7, pdf_safe_text(line[3:]), markdown=True)
                        pdf.set_font("Helvetica", "", 11)
                    elif line.startswith("### "):
                        pdf.set_font("Helvetica", "B", 11)
                        pdf.multi_cell(0, 6, pdf_safe_text(line[4:]), markdown=True)
                        pdf.set_font("Helvetica", "", 11)
                    elif line.startswith("- ") or line.startswith("* "):
                        pdf.cell(5)
                        pdf.multi_cell(0, 6, pdf_safe_text(f"- {line[2:]}"), markdown=True)
                    elif line.strip():
                        pdf.multi_cell(0, 6, pdf_safe_text(line), markdown=True)
                    else:
                        pdf.ln(3)

                buffer = io.BytesIO()
                pdf.output(buffer)
                return buffer.getvalue()

            return await asyncio.to_thread(_generate)
        except ImportError:
            raise ImportError(
                "fpdf2 is required for PDF export. Install it with: pip install fpdf2"
            )
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            raise

    async def export_docx(self, title: str, content: str) -> bytes:
        """Export note content as a DOCX file."""
        try:
            from docx import Document
            from docx.shared import Pt
            from docx.enum.text import WD_ALIGN_PARAGRAPH

            def _generate():
                doc = Document()

                # Title
                title_para = doc.add_heading(title, level=1)
                title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

                # Content - parse markdown-like formatting
                for line in content.split("\n"):
                    if line.startswith("# "):
                        doc.add_heading(strip_inline_markdown(line[2:]), level=1)
                    elif line.startswith("## "):
                        doc.add_heading(strip_inline_markdown(line[3:]), level=2)
                    elif line.startswith("### "):
                        doc.add_heading(strip_inline_markdown(line[4:]), level=3)
                    elif line.startswith("- ") or line.startswith("* "):
                        add_docx_markdown(doc.add_paragraph(style="List Bullet"), line[2:])
                    elif line.strip():
                        p = doc.add_paragraph()
                        add_docx_markdown(p, line)
                        p.paragraph_format.space_after = Pt(4)

                buffer = io.BytesIO()
                doc.save(buffer)
                return buffer.getvalue()

            return await asyncio.to_thread(_generate)
        except ImportError:
            raise ImportError(
                "python-docx is required for DOCX export. "
                "Install it with: pip install python-docx"
            )
        except Exception as e:
            logger.error(f"DOCX export failed: {e}")
            raise

    async def export_markdown(self, title: str, content: str) -> bytes:
        """Export note content as a Markdown file."""
        md_content = f"# {title}\n\n{content}\n"
        return md_content.encode("utf-8")


notes_exporter = NotesExporter()
