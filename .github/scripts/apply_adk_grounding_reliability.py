from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if new in text:
        print(f"already applied: {label}")
        return
    if old not in text:
        raise RuntimeError(f"missing expected block for {label}: {path}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"applied: {label}")


# 1. Make the canonical ADK research agent use native Google Search grounding.
# runner.py already replaces native google_search with the FunctionTool web-search
# implementation when no usable Gemini grounding route exists.
replace_once(
    "backend/src/adk/agents.py",
    '''def create_research_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:\n    name = registry_id_to_adk_name("research")\n    return LlmAgent(\n        name=name,\n        model=MODEL,\n        instruction=(\n            "You are the Research Agent. Conduct thorough research on topics. "\n            "Structure reports with: abstract, methodology, findings, analysis, conclusions. "\n            "Compare multiple perspectives and cite sources when possible. "\n            "Use the web_search tool to find current information, and "\n            "use the scrape_page tool to fetch the full text content of any website URL."\n        ),\n        tools=[web_search_tool, scrape_page_tool],\n        description="Conducts internet research, compares sources, and generates reports.",\n    )\n''',
    '''def create_research_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:\n    name = registry_id_to_adk_name("research")\n    return LlmAgent(\n        name=name,\n        model=MODEL,\n        instruction=(\n            "You are the Research Agent. Use the attached Google Search grounding tool before "\n            "answering any current, external, named-entity, organisation, person, address, campus, "\n            "location, product, release, or unfamiliar-acronym question. Search the user's exact "\n            "entity string together with every location qualifier; never silently substitute a "\n            "similarly named entity. Prefer official organisation domains, government sources, "\n            "primary documentation, and recent authoritative sources. Cross-check identity when "\n            "sources disagree. Base factual claims only on returned search evidence and preserve "\n            "grounding citations. If the search cannot verify the requested entity or fact, say "\n            "that verification failed instead of guessing. For broad research, compare multiple "\n            "sources and synthesize the answer directly for the user."\n        ),\n        tools=[google_search],\n        description="Google-grounded internet research for current facts and exact named entities.",\n    )\n''',
    "native Google Search research agent",
)

# 2. Expand visual intent detection so common image-generation nouns cannot fall
# through to a text agent and return paragraphs.
replace_once(
    "backend/src/orchestrator/router.py",
    '''            (r"(?i)\\b(generate|create|draw|make|design|render|paint|show|produce|visualize|visualise|illustrate)\\b.*\\b(images?|pictures?|photos?|photographs?|illustrations?|drawings?|artworks?|posters?|logos?|icons?|graphics?|banners?|vectors?|avatars?)\\b", "image"),\n''',
    '''            (r"(?i)\\b(generate|create|draw|make|design|render|paint|show|produce|visualize|visualise|illustrate)\\b.*\\b(images?|pictures?|photos?|photographs?|illustrations?|drawings?|artworks?|posters?|logos?|icons?|graphics?|banners?|vectors?|avatars?|wallpapers?|thumbnails?|covers?|mockups?|concept\\s+art)\\b", "image"),\n''',
    "expanded visual generation nouns",
)

# External named-entity questions must be researched even when they are phrased
# as "what is" / "tell me about" rather than an explicit location question.
replace_once(
    "backend/src/orchestrator/router.py",
    '''        # 4. For general explanations, questions, or concepts, default to knowledge agent\n        explanation_keywords = ["explain", "what is", "define", "how does", "why", "tell me about", "concept", "meaning", "overview", "difference between"]\n''',
    '''        # 4. Unknown acronyms/proper external entities need web verification, not model memory.\n        external_entity_question = bool(\n            re.search(r"(?i)\\b(?:what\\s+is|who\\s+is|tell\\s+me\\s+about|information\\s+about|details\\s+about|where\\s+is|where's)\\b", user_input)\n            and (\n                re.search(r"\\b[A-Z][A-Z0-9&.-]{2,}\\b", user_input)\n                or re.search(r"(?i)\\b(?:college|university|institute|company|organisation|organization|campus|hospital|school)\\b", user_input)\n            )\n        )\n        if external_entity_question:\n            return "research"\n\n        # 5. For general explanations, questions, or concepts, default to knowledge agent\n        explanation_keywords = ["explain", "what is", "define", "how does", "why", "tell me about", "concept", "meaning", "overview", "difference between"]\n''',
    "route named external entities to research",
)

# 3. Keep automatic orchestration consistent with AgentRouter.
replace_once(
    "backend/src/orchestrator/dynamic.py",
    '''def plan_dynamic(prompt: str, has_attachments: bool = False, has_workspace: bool = False) -> dict[str, Any]:\n''',
    '''def _looks_like_external_entity_question(prompt: str) -> bool:\n    return bool(\n        re.search(r"(?i)\\b(?:what\\s+is|who\\s+is|tell\\s+me\\s+about|information\\s+about|details\\s+about|where\\s+is|where's)\\b", prompt)\n        and (\n            re.search(r"\\b[A-Z][A-Z0-9&.-]{2,}\\b", prompt)\n            or re.search(r"(?i)\\b(?:college|university|institute|company|organisation|organization|campus|hospital|school)\\b", prompt)\n        )\n    )\n\n\ndef plan_dynamic(prompt: str, has_attachments: bool = False, has_workspace: bool = False) -> dict[str, Any]:\n''',
    "add external entity classifier",
)

replace_once(
    "backend/src/orchestrator/dynamic.py",
    '''    ) or is_shopping\n''',
    '''    ) or is_shopping or _looks_like_external_entity_question(prompt)\n''',
    "research external named entities",
)

# 4. Make the response quality boundary fail closed for named entities even if a
# future router regression accidentally sends one down a non-research path.
replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''_RECENCY_RE = re.compile(\n    r"(?ix)\\b(?:newest|most\\s+recent|recent(?:ly)?|currently|as\\s+of\\s+(?:today|now|20\\d{2}))\\b"\n)\n_URL_RE = re.compile(r"https?://", re.I)\n''',
    '''_RECENCY_RE = re.compile(\n    r"(?ix)\\b(?:newest|most\\s+recent|recent(?:ly)?|currently|as\\s+of\\s+(?:today|now|20\\d{2}))\\b"\n)\n_EXTERNAL_ENTITY_QUESTION_RE = re.compile(\n    r"(?ix)\\b(?:what\\s+is|who\\s+is|tell\\s+me\\s+about|information\\s+about|details\\s+about|where\\s+is|where's)\\b"\n)\n_EXTERNAL_ENTITY_SIGNAL_RE = re.compile(\n    r"(?i)(?:\\b[A-Z][A-Z0-9&.-]{2,}\\b|\\b(?:college|university|institute|company|organisation|organization|campus|hospital|school)\\b)"\n)\n_URL_RE = re.compile(r"https?://", re.I)\n''',
    "add external entity verification regexes",
)

replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''        or _EXTERNAL_FACT_RE.search(request_text)\n        or _RECENCY_RE.search(request_text)\n''',
    '''        or _EXTERNAL_FACT_RE.search(request_text)\n        or _RECENCY_RE.search(request_text)\n        or (\n            _EXTERNAL_ENTITY_QUESTION_RE.search(request_text)\n            and _EXTERNAL_ENTITY_SIGNAL_RE.search(request_text)\n        )\n''',
    "require evidence for external named entities",
)

# 5. Strengthen the global quality contract so BossAgent must use tool evidence
# for these requests and cannot substitute another similarly named entity.
replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''- If evidence is incomplete, state the specific uncertainty briefly and give\n  the most useful answer supported by the available context.\n''',
    '''- For an unfamiliar acronym or named entity, never infer its expansion, identity,\n  city, campus, address, or affiliation from model memory. Search the exact user phrase\n  first, verify that at least one returned source refers to the same entity, and only\n  then answer. A source about a different entity with a similar acronym is not evidence.\n- If evidence is incomplete, state the specific uncertainty briefly and give\n  the most useful answer supported by the available context.\n''',
    "strengthen exact-entity quality contract",
)

print("ADK grounding reliability patch complete")
