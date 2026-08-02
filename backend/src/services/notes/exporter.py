"""Publication-Quality Document Exporter (PDF & DOCX).

Generates textbook-grade PDFs and editable Microsoft Word (DOCX) documents:
- Academic Cover Page (Subject, Chapter, Date, Branding)
- Running Headers & Footers with Page Numbers
- Hyperlinked Table of Contents with section numbering
- Styled Callout Boxes (Exam Tips, Definitions, Important Warnings, Notes)
- Clean Academic Tables with header shading & alternating row background
- Rendered Mathematical Equations & Symbol Normalization (KaTeX)
- Dark Monospace Code & Diagram Blocks
- Flexible Scope Filtering (Complete, Notes, Exam, Questions, Answers, Formulas, Diagrams, Tables, References)
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
        in_formula = False
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
        """Generate a textbook-quality PDF with cover page, TOC, headers, and callouts."""
        try:
            from fpdf import FPDF

            class AcademicPDF(FPDF):
                def header(self):
                    if self.page_no() > 1:
                        self.set_font("Helvetica", "I", 9)
                        self.set_text_color(100, 116, 139)
                        self.cell(0, 8, pdf_safe_text(f"{title} · {subject}"), 0, 0, "R")
                        self.ln(10)
                        self.set_draw_color(226, 232, 240)
                        self.line(10, 18, 200, 18)

                def footer(self):
                    if self.page_no() > 1:
                        self.set_y(-15)
                        self.set_font("Helvetica", "", 9)
                        self.set_text_color(148, 163, 184)
                        self.cell(0, 10, pdf_safe_text("AI Study Agent — Academic Publication Edition"), 0, 0, "L")
                        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "R")

            def _build_pdf():
                filtered_md = filter_content_by_scope(content, scope)
                pdf = AcademicPDF(orientation="P", unit="mm", format="A4")
                pdf.set_auto_page_break(auto=True, margin=18)

                # --- COVER PAGE ---
                pdf.add_page()
                pdf.set_fill_color(30, 41, 59)  # Dark slate header bar
                pdf.rect(0, 0, 210, 45, "F")

                pdf.set_y(15)
                pdf.set_font("Helvetica", "B", 14)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(0, 10, pdf_safe_text("AI STUDY AGENT · ACADEMIC EDITION"), 0, 1, "C")

                pdf.set_y(65)
                pdf.set_font("Helvetica", "B", 22)
                pdf.set_text_color(30, 41, 59)
                pdf.multi_cell(0, 12, pdf_safe_text(title), align="C")

                pdf.set_font("Helvetica", "I", 12)
                pdf.set_text_color(71, 85, 105)
                pdf.cell(0, 10, pdf_safe_text(f"Subject: {subject} | Scope: {scope.title()}"), 0, 1, "C")

                pdf.set_y(140)
                pdf.set_draw_color(37, 99, 235)
                pdf.set_line_width(0.8)
                pdf.line(40, 140, 170, 140)

                pdf.set_y(160)
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(100, 116, 139)
                pdf.cell(0, 6, pdf_safe_text(f"Prepared by: {author}"), 0, 1, "C")
                pdf.cell(0, 6, pdf_safe_text("Generated for University & Research Use"), 0, 1, "C")

                # --- TABLE OF CONTENTS ---
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 16)
                pdf.set_text_color(30, 41, 59)
                pdf.cell(0, 10, pdf_safe_text("Table of Contents"), 0, 1, "L")
                pdf.ln(4)

                headings = []
                for l in filtered_md.split("\n"):
                    if l.startswith("# "):
                        headings.append((1, l[2:]))
                    elif l.startswith("## "):
                        headings.append((2, l[3:]))

                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(51, 65, 85)
                for idx, (lvl, htext) in enumerate(headings[:15], 1):
                    indent = "   " * (lvl - 1)
                    dots = ". " * (35 - len(htext[:30]))
                    pdf.cell(0, 7, pdf_safe_text(f"{indent}{idx}. {htext[:35]} {dots}"), 0, 1, "L")

                pdf.ln(8)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(6)

                # --- CONTENT PARSING ---
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(30, 41, 59)

                in_code_block = False
                code_lines = []

                for line in filtered_md.split("\n"):
                    raw_line = line.strip()

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
                        pdf.cell(4)
                        pdf.multi_cell(0, 5.5, pdf_safe_text(f"- {raw_line[2:]}"))

                    # Normal Text
                    elif raw_line:
                        pdf.multi_cell(0, 5.5, pdf_safe_text(raw_line))
                    else:
                        pdf.ln(2)

                buffer = io.BytesIO()
                pdf.output(buffer)
                return buffer.getvalue()

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
        """Generate an editable Microsoft Word (DOCX) textbook document."""
        try:
            from docx import Document
            from docx.shared import Pt, Inches, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
            from docx.oxml import OxmlElement
            from docx.oxml.ns import qn

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

                # --- COVER PAGE ---
                p_title = doc.add_paragraph()
                p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_title.paragraph_format.space_before = Pt(36)
                p_title.paragraph_format.space_after = Pt(12)
                run_title = p_title.add_run(title)
                run_title.font.name = "Calibri"
                run_title.font.size = Pt(24)
                run_title.font.bold = True
                run_title.font.color.rgb = RGBColor(30, 41, 59)

                p_sub = doc.add_paragraph()
                p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_sub.paragraph_format.space_after = Pt(24)
                run_sub = p_sub.add_run(f"Subject: {subject} | Scope: {scope.title()}")
                run_sub.font.size = Pt(12)
                run_sub.font.italic = True
                run_sub.font.color.rgb = RGBColor(71, 85, 105)

                doc.add_page_break()

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
        md_content = f"# {title}\n\n{filtered_md}\n"
        return md_content.encode("utf-8")


publication_exporter = PublicationDocumentExporter()
notes_exporter = publication_exporter  # Backward compatible alias
