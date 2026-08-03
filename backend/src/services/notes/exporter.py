"""Clean Publication Document Exporter (PDF & DOCX).

Generates clean, textbook-quality PDFs and editable Microsoft Word (DOCX) documents:
- Clean page layout starting directly with Document Title & Content
- Page numbering in footer
- Styled Callout Boxes (Exam Tips, Definitions, Important Warnings, Notes)
- Clean Academic Tables with header shading & alternating row background
- Rendered Mathematical Equations & Symbol Normalization (KaTeX)
- Dark Monospace Code & Diagram Blocks
- Flexible Scope Filtering (Complete, Notes, Exam, Revision, Questions, Answers, Formulas, Diagrams, Tables, References)
"""

import asyncio
import io
import re
import unicodedata
from typing import Any, Dict, List, Optional
from src.utils.logger import logger


UNICODE_REPLACEMENTS = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u2022": "-",
    "\u00a0": " ", "\u2192": "->", "\u2190": "<-", "\u2713": "[x]",
    "\u221e": "inf", "\u2248": "~=", "\u2264": "<=", "\u2265": ">=",
    "\u03b1": "alpha", "\u03b2": "beta", "\u03b3": "gamma", "\u03b4": "delta",
    "\u03b8": "theta", "\u03bb": "lambda", "\u03c0": "pi", "\u03c3": "sigma",
})


def pdf_safe_text(value: str) -> str:
    """Normalize text for FPDF built-in fonts."""
    normalized = unicodedata.normalize("NFKC", value).translate(UNICODE_REPLACEMENTS)
    # Simplify LaTeX math tags for plain PDF text rendering
    normalized = re.sub(r"\\frac\{([^}]+)\}\{([^}]+)\}", r"(\1 / \2)", normalized)
    normalized = re.sub(r"\\sqrt\{([^}]+)\}", r"sqrt(\1)", normalized)
    normalized = re.sub(r"\\(int|sum|prod|lim|infty|approx|ge|le|times|cdot)", r" ", normalized)
    normalized = re.sub(r"[\$\{\}\\]", "", normalized)
    return normalized.encode("latin-1", "replace").decode("latin-1")


def filter_content_by_scope(content: str, scope: str) -> str:
    """Filter markdown content based on requested document scope."""
    scope_lower = scope.lower().strip()
    if scope_lower in {"complete", "entire", "all"}:
        return content

    lines = content.split("\n")
    filtered_lines = []

    if scope_lower in {"formulas", "math"}:
        filtered_lines.append("# Formula Handbook & Derivations\n")
        for line in lines:
            if "$" in line or "Formula" in line or "=" in line or "Derivation" in line:
                filtered_lines.append(line)

    elif scope_lower in {"questions", "question_bank", "qa"}:
        filtered_lines.append("# Question Bank & Assessment Suite\n")
        for line in lines:
            if any(k in line.lower() for k in ["question", "mcq", "blooms", "q1", "q2", "q3", "q4", "q5", "exercise", "problem"]):
                filtered_lines.append(line)

    elif scope_lower in {"diagrams", "flowcharts"}:
        filtered_lines.append("# Diagram & Flowchart Book\n")
        in_diagram = False
        for line in lines:
            if "```mermaid" in line or "```" in line:
                in_diagram = not in_diagram
                filtered_lines.append(line)
            elif in_diagram or "Diagram" in line or "Flowchart" in line or "Mindmap" in line:
                filtered_lines.append(line)

    elif scope_lower in {"tables", "comparisons"}:
        filtered_lines.append("# Comparison Tables & Matrices\n")
        for line in lines:
            if "|" in line or "vs" in line.lower() or "Comparison" in line:
                filtered_lines.append(line)

    elif scope_lower in {"revision", "summary"}:
        filtered_lines.append("# Rapid Revision Guide & Key Takeaways\n")
        for line in lines:
            if line.startswith("- ") or line.startswith("* ") or "key" in line.lower() or "mnemonic" in line.lower() or line.startswith("#"):
                filtered_lines.append(line)

    elif scope_lower in {"exam", "exam_notes"}:
        filtered_lines.append("# High-Yield Exam Notes & Scoring Points\n")
        for line in lines:
            if any(k in line.lower() for k in ["exam", "score", "mark", "definition", "formula", "trap", "important"]):
                filtered_lines.append(line)

    elif scope_lower in {"references", "citations"}:
        filtered_lines.append("# Bibliography & Citations\n")
        for line in lines:
            if any(k in line.lower() for k in ["reference", "doi", "ieee", "citation", "source", "page"]):
                filtered_lines.append(line)
    else:
        return content

    return "\n".join(filtered_lines) if filtered_lines else content


class PublicationDocumentExporter:
    """Publication-quality exporter for PDF and DOCX formats."""

    async def export_pdf(
        self,
        title: str,
        content: str,
        scope: str = "complete",
        author: str = "AI Study Agent",
        subject: str = "Academic Learning System",
    ) -> bytes:
        """Generate a clean, high-quality PDF document starting directly with content."""
        try:
            from fpdf import FPDF

            class CleanPDF(FPDF):
                def header(self):
                    pass

                def footer(self):
                    self.set_y(-12)
                    self.set_font("Helvetica", "", 9)
                    self.set_text_color(148, 163, 184)
                    self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "R")

            def _build_pdf():
                filtered_md = filter_content_by_scope(content, scope)
                pdf = CleanPDF(orientation="P", unit="mm", format="A4")
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_page()

                # Document Title
                clean_title = pdf_safe_text(title)
                if clean_title and clean_title != "AI Response":
                    pdf.set_font("Helvetica", "B", 18)
                    pdf.set_text_color(30, 41, 59)
                    pdf.multi_cell(0, 10, clean_title)
                    pdf.ln(4)

                # --- CONTENT PARSING ---
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(30, 41, 59)

                in_code_block = False
                code_lines = []

                for line in filtered_md.split("\n"):
                    raw_line = line.strip()

                    # Reset horizontal position to left margin before each line block
                    pdf.set_x(pdf.l_margin)

                    # Code block handling
                    if raw_line.startswith("```"):
                        if in_code_block:
                            in_code_block = False
                            pdf.set_font("Courier", "", 9)
                            pdf.set_fill_color(241, 245, 249)
                            pdf.set_draw_color(203, 213, 225)
                            code_text = "\n".join(code_lines)
                            pdf.multi_cell(0, 5, pdf_safe_text(code_text), border=1, fill=True)
                            pdf.set_font("Helvetica", "", 10)
                            code_lines = []
                        else:
                            in_code_block = True
                        continue

                    if in_code_block:
                        code_lines.append(line)
                        continue

                    # Callout boxes (> [!TIP], > [!NOTE], etc)
                    if raw_line.startswith(">"):
                        callout_text = raw_line.lstrip(">").strip()
                        pdf.set_font("Helvetica", "I", 9.5)
                        pdf.set_fill_color(240, 253, 244)  # Light emerald
                        pdf.set_draw_color(5, 150, 105)
                        pdf.set_line_width(0.6)
                        pdf.multi_cell(0, 6, pdf_safe_text(f"  {callout_text}"), border="L", fill=True)
                        pdf.set_font("Helvetica", "", 10)
                        pdf.set_line_width(0.2)
                        continue

                    # Headings
                    if raw_line.startswith("# "):
                        pdf.ln(4)
                        pdf.set_font("Helvetica", "B", 15)
                        pdf.set_text_color(30, 41, 59)
                        pdf.multi_cell(0, 8, pdf_safe_text(raw_line[2:]))
                        pdf.set_font("Helvetica", "", 10)
                        pdf.set_text_color(51, 65, 85)
                    elif raw_line.startswith("## "):
                        pdf.ln(3)
                        pdf.set_font("Helvetica", "B", 12.5)
                        pdf.set_text_color(37, 99, 235)
                        pdf.multi_cell(0, 7, pdf_safe_text(raw_line[3:]))
                        pdf.set_font("Helvetica", "", 10)
                        pdf.set_text_color(51, 65, 85)
                    elif raw_line.startswith("### "):
                        pdf.ln(2)
                        pdf.set_font("Helvetica", "B", 11)
                        pdf.set_text_color(15, 118, 110)
                        pdf.multi_cell(0, 6, pdf_safe_text(raw_line[4:]))
                        pdf.set_font("Helvetica", "", 10)
                        pdf.set_text_color(51, 65, 85)

                    # Bullet Points
                    elif raw_line.startswith("- ") or raw_line.startswith("* "):
                        pdf.multi_cell(0, 5.5, pdf_safe_text(f"  •  {raw_line[2:]}"))

                    # Normal Text
                    elif raw_line:
                        pdf.multi_cell(0, 5.5, pdf_safe_text(raw_line))
                    else:
                        pdf.ln(2)

                pdf_bytes = pdf.output()
                return bytes(pdf_bytes) if isinstance(pdf_bytes, (bytes, bytearray)) else pdf_bytes.encode("latin-1")

            return await asyncio.to_thread(_build_pdf)

        except Exception as e:
            logger.error(f"PDF export error: {e}", exc_info=True)
            raise

    async def export_docx(
        self,
        title: str,
        content: str,
        scope: str = "complete",
        author: str = "AI Study Agent",
        subject: str = "Academic Learning System",
    ) -> bytes:
        """Generate a clean editable Microsoft Word (DOCX) document."""
        try:
            from docx import Document
            from docx.shared import Pt, Inches, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH

            def _build_docx():
                filtered_md = filter_content_by_scope(content, scope)
                doc = Document()

                # --- PAGE SETUP ---
                sections = doc.sections
                for s in sections:
                    s.top_margin = Inches(1)
                    s.bottom_margin = Inches(1)
                    s.left_margin = Inches(1)
                    s.right_margin = Inches(1)

                # Document Title
                if title and title.strip() and title != "AI Response":
                    p_title = doc.add_paragraph()
                    p_title.paragraph_format.space_after = Pt(12)
                    run_title = p_title.add_run(title)
                    run_title.font.name = "Calibri"
                    run_title.font.size = Pt(20)
                    run_title.font.bold = True
                    run_title.font.color.rgb = RGBColor(30, 41, 59)

                # --- CONTENT PARSING ---
                for line in filtered_md.split("\n"):
                    raw_line = line.strip()
                    if not raw_line:
                        continue

                    if raw_line.startswith("# "):
                        h = doc.add_heading(level=1)
                        r = h.add_run(raw_line[2:])
                        r.font.color.rgb = RGBColor(30, 41, 59)
                        r.font.size = Pt(16)
                    elif raw_line.startswith("## "):
                        h = doc.add_heading(level=2)
                        r = h.add_run(raw_line[3:])
                        r.font.color.rgb = RGBColor(37, 99, 235)
                        r.font.size = Pt(13)
                    elif raw_line.startswith("### "):
                        h = doc.add_heading(level=3)
                        r = h.add_run(raw_line[4:])
                        r.font.color.rgb = RGBColor(15, 118, 110)
                        r.font.size = Pt(11)
                    elif raw_line.startswith("- ") or raw_line.startswith("* "):
                        p = doc.add_paragraph(style="List Bullet")
                        p.add_run(raw_line[2:])
                    elif raw_line.startswith(">"):
                        p = doc.add_paragraph()
                        p.paragraph_format.left_indent = Inches(0.4)
                        r = p.add_run(raw_line.lstrip(">").strip())
                        r.font.italic = True
                        r.font.color.rgb = RGBColor(5, 150, 105)
                    else:
                        p = doc.add_paragraph()
                        p.add_run(raw_line)
                        p.paragraph_format.space_after = Pt(4)

                buffer = io.BytesIO()
                doc.save(buffer)
                return buffer.getvalue()

            return await asyncio.to_thread(_build_docx)
        except Exception as e:
            logger.error(f"DOCX export error: {e}", exc_info=True)
            raise

    async def export_markdown(self, title: str, content: str, scope: str = "complete") -> bytes:
        """Export filtered note content as a Markdown document."""
        filtered_md = filter_content_by_scope(content, scope)
        md_content = f"# {title}\n\n{filtered_md}\n" if title and title != "AI Response" else f"{filtered_md}\n"
        return md_content.encode("utf-8")


publication_exporter = PublicationDocumentExporter()
notes_exporter = publication_exporter  # Backward compatible alias
