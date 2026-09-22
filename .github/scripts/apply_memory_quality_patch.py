from pathlib import Path

path = Path("backend/src/services/memory/service.py")
text = path.read_text(encoding="utf-8")

if "import asyncio\n" not in text.split("from datetime", 1)[0]:
    marker = "import json\n"
    if marker not in text:
        raise RuntimeError("memory service import block changed unexpectedly")
    text = text.replace(marker, "import asyncio\nimport json\n", 1)
    path.write_text(text, encoding="utf-8")
    print("applied: restore asyncio-backed memory context")
else:
    print("already applied: memory asyncio import")
