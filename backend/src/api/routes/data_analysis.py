"""Data Analysis Agent API routes — CSV/Excel upload, analysis, chart generation."""

import io
import json
import csv
import os
import uuid
import tempfile
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel

from src.utils.logger import logger

router = APIRouter(prefix="/api/data-analysis", tags=["Data Analysis"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MAX_ROWS_FOR_CONTEXT = 200  # rows sent verbatim to the LLM
MAX_FILE_MB = 20


def _parse_csv(content: bytes) -> tuple[list[str], list[list[str]]]:
    text = content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _parse_excel(content: bytes) -> tuple[list[str], list[list]]:
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(status_code=500, detail="openpyxl is required for Excel support. Run: pip install openpyxl")

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        return [], []
    headers = [str(c) if c is not None else "" for c in rows[0]]
    data = [[str(c) if c is not None else "" for c in row] for row in rows[1:]]
    return headers, data


def _build_data_context(headers: list, rows: list, max_rows: int = MAX_ROWS_FOR_CONTEXT) -> str:
    """Serialize a subset of rows as a Markdown table for the LLM context."""
    sample = rows[:max_rows]
    lines = ["| " + " | ".join(str(h) for h in headers) + " |",
             "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in sample:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    note = f"\n\n*Showing {len(sample)} of {len(rows)} rows.*" if len(rows) > max_rows else ""
    return "Uploaded tabular data:\n\n" + "\n".join(lines) + note


def _compute_stats(headers: list, rows: list) -> dict:
    """Compute basic statistics (count, min, max, mean, nulls) for each column."""
    stats = {}
    for i, col in enumerate(headers):
        values = []
        nulls = 0
        for row in rows:
            val = row[i] if i < len(row) else ""
            if val == "" or val is None:
                nulls += 1
            else:
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    pass
        col_stat = {"count": len(rows), "nulls": nulls}
        if values:
            col_stat["numeric"] = True
            col_stat["min"] = min(values)
            col_stat["max"] = max(values)
            col_stat["mean"] = round(sum(values) / len(values), 4)
            col_stat["sum"] = round(sum(values), 4)
        else:
            col_stat["numeric"] = False
        stats[col] = col_stat
    return stats


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class AnalyseRequest(BaseModel):
    session_id: str
    question: str
    user_id: Optional[str] = "default"


# In-memory session store (maps session_id -> {headers, rows, filename})
_sessions: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Form("default"),
):
    """Upload a CSV or Excel file and return a session_id + preview stats."""
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in {"csv", "xlsx", "xls"}:
        raise HTTPException(status_code=400, detail="Only CSV and Excel (.xlsx/.xls) files are supported.")

    content = await file.read()
    if len(content) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_FILE_MB} MB limit.")

    try:
        if ext == "csv":
            headers, rows = _parse_csv(content)
        else:
            headers, rows = _parse_excel(content)
    except Exception as exc:
        logger.error("Data file parse error: %s", exc)
        raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}")

    if not headers:
        raise HTTPException(status_code=422, detail="File appears to be empty or unreadable.")

    session_id = uuid.uuid4().hex
    _sessions[session_id] = {
        "filename": file.filename,
        "headers": headers,
        "rows": rows,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    stats = _compute_stats(headers, rows)

    # Build a concise preview (first 5 rows)
    preview_rows = rows[:5]

    return {
        "success": True,
        "session_id": session_id,
        "filename": file.filename,
        "row_count": len(rows),
        "column_count": len(headers),
        "headers": headers,
        "preview": preview_rows,
        "stats": stats,
    }


@router.post("/analyse")
async def analyse(
    request: Request,
    body: AnalyseRequest,
):
    """Send a question about the uploaded dataset to the LLM."""
    session = _sessions.get(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Please re-upload the file.")

    from src.services.llm import llm_service

    headers = session["headers"]
    rows = session["rows"]
    data_context = _build_data_context(headers, rows)

    system = (
        "You are a Data Analysis Agent. Analyse tabular data and answer user questions clearly. "
        "Provide statistical summaries, identify trends, correlations, outliers, and insights. "
        "When asked for charts, respond with JSON inside a ```chart``` code block using this schema: "
        '{"type": "bar|line|pie|scatter", "title": "...", "labels": [...], "datasets": [{"label": "...", "data": [...]}]}. '
        "When showing tables, use GitHub-flavoured markdown table syntax. "
        "Always be concise and precise with numbers."
    )
    prompt = f"{data_context}\n\nUser request: {body.question}"

    try:
        response = await llm_service.generate(prompt=prompt, system_instruction=system)
    except Exception as exc:
        logger.error("LLM error in data analysis: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return {"success": True, "answer": response, "session_id": body.session_id}


@router.get("/session/{session_id}")
async def get_session(session_id: str, request: Request):
    """Get metadata for an active analysis session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {
        "success": True,
        "session_id": session_id,
        "filename": session["filename"],
        "headers": session["headers"],
        "row_count": len(session["rows"]),
        "column_count": len(session["headers"]),
        "created_at": session["created_at"],
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, request: Request):
    """Remove a session from memory."""
    _sessions.pop(session_id, None)
    return {"success": True}
