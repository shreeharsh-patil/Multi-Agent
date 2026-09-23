from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    if new in text:
        print(f"already applied: {label}")
        return
    if old not in text:
        raise RuntimeError(f"could not find expected block for {label} in {path}")
    file_path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"applied: {label}")


replace_once(
    "backend/src/orchestrator/router.py",
    '''            if requested_agent_id == "image":\n                # Image agent should only execute when user explicitly requests image generation\n                return "auto"\n''',
    '''            if requested_agent_id == "image":\n                # Selecting the Image agent is itself explicit generation intent.\n                # Do not silently downgrade a deliberate UI choice to auto.\n                return "image"\n''',
    "preserve explicit image-agent selection",
)

replace_once(
    "backend/src/services/llm/factory.py",
    '''        groq_model = settings.groq_model\n        # Older deployments commonly retained this model after Groq removed\n        # it. Upgrade at runtime so an unchanged Render environment cannot\n        # take down the entire provider chain.\n        if groq_model in {"mixtral-8x7b-32768", "llama3-8b-8192", "llama-3.3-70b-versatile"}:\n            logger.warning("GROQ_MODEL %s is invalid/retired; using openai/gpt-oss-20b instead", groq_model)\n            groq_model = "openai/gpt-oss-20b"\n''',
    '''        groq_model = settings.groq_model\n        # Defense in depth for stale hosted environment values. Qwen 3.6 was\n        # retired by Groq on 2026-09-14; use the supported Qwen 3.8 route that\n        # also works with the ADK reasoning_format=hidden configuration.\n        if groq_model in {\n            "qwen/qwen3.6-27b",\n            "openai/gpt-oss-20b",\n            "mixtral-8x7b-32768",\n            "llama3-8b-8192",\n            "llama-3.1-8b-instant",\n            "llama-3.3-70b-versatile",\n        }:\n            logger.warning("GROQ_MODEL %s is stale/incompatible; using qwen/qwen3.8-27b instead", groq_model)\n            groq_model = "qwen/qwen3.8-27b"\n''',
    "migrate stale Groq model in factory",
)

replace_once(
    "backend/tests/test_adk_runner.py",
    '    assert configured.groq_model == "qwen/qwen3.6-27b"\n',
    '    assert configured.groq_model == "qwen/qwen3.8-27b"\n',
    "update stale Groq model assertion",
)

replace_once(
    "backend/tests/test_adk_runner.py",
    '        model="qwen/qwen3.6-27b",\n        api_key="gsk_diagnostic",\n',
    '        model="qwen/qwen3.8-27b",\n        api_key="gsk_diagnostic",\n',
    "update Groq ADK route fixture",
)

replace_once(
    ".env.example",
    "GROQ_MODEL=openai/gpt-oss-20b\n",
    "GROQ_MODEL=qwen/qwen3.8-27b\n",
    "update example Groq model",
)

replace_once(
    ".env.example",
    "# --- Image generation (auto | openai | stability) ---\nIMAGE_PROVIDER=auto\nOPENAI_API_KEY=\n",
    "# --- Image generation (auto | cloudflare | openai | stability | pollinations) ---\nIMAGE_PROVIDER=auto\nCLOUDFLARE_ACCOUNT_ID=\nCLOUDFLARE_API_TOKEN=\nOPENAI_API_KEY=\n",
    "document all image providers",
)

print("generation repair patch complete")
