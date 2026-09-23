from pathlib import Path

p = Path("backend/tests/test_google_search_division.py")
text = p.read_text(encoding="utf-8")
old = '''    # Verify existing research agent retains web_search_tool and scrape_page_tool\n    research_agent = next(s for s in research_mgr.sub_agents if s.name == "research")\n    assert len(research_agent.tools) >= 2\n'''
new = '''    # Canonical research now uses native Google Search grounding. The runner\n    # transparently replaces it with the FunctionTool web-search fallback only\n    # when a Gemini grounding route is unavailable.\n    research_agent = next(s for s in research_mgr.sub_agents if s.name == "research")\n    assert any(\n        tool is google_search or "GoogleSearchTool" in type(tool).__name__\n        for tool in research_agent.tools\n    )\n'''
if new in text:
    print("already applied: native research expectation")
elif old in text:
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("applied: native research expectation")
else:
    raise RuntimeError("expected legacy research assertion not found")
