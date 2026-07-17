from src.services.memory.service import parse_extracted_memories


def test_parse_extracted_memories_accepts_fenced_json():
    raw = """```json
    [{
      "key": "response style",
      "content": "The user prefers concise answers.",
      "type": "preference",
      "category": "communication",
      "confidence": 0.92,
      "evidence": "Keep it concise"
    }]
    ```"""

    assert parse_extracted_memories(raw) == [{
        "key": "response_style",
        "content": "The user prefers concise answers.",
        "type": "preference",
        "category": "communication",
        "confidence": 0.92,
        "evidence": "Keep it concise",
    }]


def test_parse_extracted_memories_drops_low_confidence_and_invalid_entries():
    raw = """[
      {"key": "guess", "content": "Maybe likes jazz", "confidence": 0.3},
      {"key": "", "content": "", "confidence": 1},
      "not an object"
    ]"""

    assert parse_extracted_memories(raw) == []


def test_parse_extracted_memories_normalises_unknown_values():
    raw = """[{
      "key": "Preferred IDE!",
      "content": "The user works in VS Code.",
      "type": "unknown",
      "category": "unknown",
      "confidence": "0.8"
    }]"""

    item = parse_extracted_memories(raw)[0]
    assert item["key"] == "preferred_ide"
    assert item["type"] == "semantic"
    assert item["category"] == "general"
