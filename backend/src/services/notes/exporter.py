import asyncio
import io
from src.utils.logger import logger


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
                pdf.multi_cell(0, 10, title)
                pdf.ln(5)

                # Content
                pdf.set_font("Helvetica", "", 11)
                for line in content.split("\n"):
                    if line.startswith("# "):
                        pdf.set_font("Helvetica", "B", 14)
                        pdf.multi_cell(0, 8, line[2:])
                        pdf.set_font("Helvetica", "", 11)
                    elif line.startswith("## "):
                        pdf.set_font("Helvetica", "B", 12)
                        pdf.multi_cell(0, 7, line[3:])
                        pdf.set_font("Helvetica", "", 11)
                    elif line.startswith("### "):
                        pdf.set_font("Helvetica", "B", 11)
                        pdf.multi_cell(0, 6, line[4:])
                        pdf.set_font("Helvetica", "", 11)
                    elif line.startswith("- ") or line.startswith("* "):
                        pdf.cell(5)
                        pdf.multi_cell(0, 6, line)
                    elif line.strip():
                        pdf.multi_cell(0, 6, line)
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
                        doc.add_heading(line[2:], level=1)
                    elif line.startswith("## "):
                        doc.add_heading(line[3:], level=2)
                    elif line.startswith("### "):
                        doc.add_heading(line[4:], level=3)
                    elif line.startswith("- ") or line.startswith("* "):
                        doc.add_paragraph(line[2:], style="List Bullet")
                    elif line.strip():
                        p = doc.add_paragraph(line)
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
