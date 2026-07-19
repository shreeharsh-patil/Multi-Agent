import asyncio
import io

from docx import Document

from src.api.routes.flashcards import generated_card_values
from src.services.notes.exporter import notes_exporter


def test_generated_cards_accept_question_answer_fields():
    result = generated_card_values({"question": "What is SM-2?", "answer": "A scheduling algorithm.", "tags": "review"})

    assert result == ("What is SM-2?", "A scheduling algorithm.", ["review"])


def test_pdf_export_handles_ai_markdown_and_unicode():
    content = '# **Key finding**\n\nText with “quotes”, an em dash — and *emphasis*.'

    output = asyncio.run(notes_exporter.export_pdf("Agent’s report", content))

    assert output.startswith(b"%PDF")
    assert len(output) > 500


def test_docx_export_creates_native_bold_and_italic_runs():
    output = asyncio.run(notes_exporter.export_docx("Agent report", "A **bold** and *italic* result."))
    document = Document(io.BytesIO(output))
    runs = [run for paragraph in document.paragraphs for run in paragraph.runs]

    assert any(run.text == "bold" and run.bold for run in runs)
    assert any(run.text == "italic" and run.italic for run in runs)
