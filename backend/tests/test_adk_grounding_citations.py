"""Regression tests for Google Search grounding source presentation."""

from types import SimpleNamespace

from src.adk.runner import _extract_grounding_citations


def test_extracts_google_grounding_chunks_from_python_sdk_shape():
    event = SimpleNamespace(
        grounding_metadata=SimpleNamespace(
            grounding_chunks=[
                SimpleNamespace(web=SimpleNamespace(title="Official docs", uri="https://example.com/docs")),
                SimpleNamespace(web=SimpleNamespace(title="Official docs", uri="https://example.com/docs")),
            ]
        )
    )

    assert _extract_grounding_citations(event) == [
        {
            "file_name": "Official docs",
            "text": "https://example.com/docs",
            "url": "https://example.com/docs",
        }
    ]


def test_extracts_google_grounding_chunks_from_api_payload_shape():
    event = {
        "groundingMetadata": {
            "groundingChunks": [
                {"web": {"title": "Release notes", "uri": "https://example.com/releases"}},
            ]
        }
    }

    assert _extract_grounding_citations(event)[0]["url"] == "https://example.com/releases"
