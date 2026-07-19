from unittest.mock import AsyncMock, patch

import pytest

from src.agents.drive.agent import DriveAgent


@pytest.mark.asyncio
async def test_drive_agent_requires_google_token():
    result = await DriveAgent().execute("list my files", {})

    assert result.success is False
    assert result.error == "missing_google_drive_token"
    assert "Connect Google Drive" in result.output


@pytest.mark.asyncio
async def test_drive_agent_lists_files_with_request_token():
    files = [
        {
            "id": "file-1",
            "name": "Project plan.pdf",
            "mimeType": "application/pdf",
            "modifiedTime": "2026-07-19T12:00:00Z",
            "webViewLink": "https://drive.google.com/file/d/file-1/view",
        }
    ]

    with (
        patch("src.services.llm.llm_service.generate", new=AsyncMock(return_value='{"action":"list","query":""}')),
        patch("src.services.drive.drive_service.list_files", new=AsyncMock(return_value=files)) as list_files,
    ):
        result = await DriveAgent().execute(
            "what is in my Drive?",
            {"google_access_token": "request-token"},
        )

    assert result.success is True
    assert "Project plan.pdf" in result.output
    list_files.assert_awaited_once_with(
        access_token="request-token",
        refresh_token="",
        page_size=100,
        name_query=None,
    )


@pytest.mark.asyncio
async def test_drive_agent_searches_by_name():
    with (
        patch(
            "src.services.llm.llm_service.generate",
            new=AsyncMock(return_value='{"action":"search","query":"invoice"}'),
        ),
        patch("src.services.drive.drive_service.list_files", new=AsyncMock(return_value=[])) as list_files,
    ):
        result = await DriveAgent().execute(
            "find invoice files",
            {"google_access_token": "request-token"},
        )

    assert result.success is True
    assert 'No Drive files matched "invoice"' in result.output
    assert list_files.await_args.kwargs["name_query"] == "invoice"
