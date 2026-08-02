"""Sandboxed Code Agent.

Writes code for a user's request, executes it in a remote sandbox (Piston API),
reads the output, and iteratively fixes errors until it runs or the iteration
budget is exhausted. Streams progress as Server-Sent Events.
"""
import json
import re
from typing import AsyncGenerator, Optional

from src.services.llm import llm_service
from src.utils.logger import logger
from src.config import settings

MAX_ITERATIONS = 3
PISTON_URL = "https://emkc.org/api/v2/piston"

LANGUAGE_ALIASES = {
    "python": "python", "py": "python",
    "javascript": "javascript", "js": "javascript", "node": "javascript", "nodejs": "javascript",
    "typescript": "typescript", "ts": "typescript",
    "java": "java",
    "c++": "c++", "cpp": "c++", "cplusplus": "c++", "cplusplusplus": "c++", "cc": "c++",
    "c": "c",
    "rust": "rust", "rs": "rust",
    "go": "go", "golang": "go",
    "ruby": "ruby", "rb": "ruby",
    "php": "php",
    "bash": "bash", "sh": "bash", "shell": "bash",
}

DEFAULT_VERSIONS = {
    "python": "3.10.0",
    "javascript": "18.15.0",
    "typescript": "5.0.3",
    "java": "15.0.2",
    "c++": "10.2.0",
    "c": "10.2.0",
    "rust": "1.68.2",
    "go": "1.16.2",
    "ruby": "3.0.1",
    "php": "8.2.3",
    "bash": "5.2.0",
}

SUPPORTED_LANGUAGES = list(DEFAULT_VERSIONS.keys())

_runtimes_cache: Optional[dict[str, str]] = None


def normalize_language(raw: str) -> str:
    key = (raw or "").strip().lower()
    return LANGUAGE_ALIASES.get(key, "python")


def _safe_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


async def _fetch_runtimes(client) -> dict[str, str]:
    global _runtimes_cache
    if _runtimes_cache is not None:
        return _runtimes_cache
    try:
        resp = await client.get(f"{PISTON_URL}/runtimes")
        if resp.status_code == 200:
            found: dict[str, str] = {}
            for rt in resp.json():
                name = str(rt.get("language", "")).lower()
                aliases = [str(a).lower() for a in rt.get("aliases", [])]
                for alias in aliases + [name]:
                    if alias not in found and rt.get("version"):
                        found[alias] = str(rt["version"])
            _runtimes_cache = found or {}
            return _runtimes_cache
    except Exception as e:
        logger.warning(f"Could not fetch Piston runtimes: {e}")
    _runtimes_cache = {}
    return _runtimes_cache


async def _runtime_for(client, language: str) -> tuple[str, str]:
    runtimes = await _fetch_runtimes(client)
    version = runtimes.get(language) or DEFAULT_VERSIONS.get(language, "3.10.0")
    return language, version


async def _execute_local_subprocess(language: str, code: str, stdin: str = "") -> Optional[dict]:
    """Execute code locally in a sandboxed, time-bounded subprocess."""
    import sys, asyncio
    try:
        if language == "python":
            cmd = [sys.executable, "-c", code]
        elif language == "javascript":
            cmd = ["node", "-e", code]
        elif language == "bash":
            cmd = ["bash", "-c", code]
        else:
            return None

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(input=stdin.encode("utf-8") if stdin else None),
                timeout=10.0,
            )
            return {
                "language": language,
                "version": "local",
                "exit_code": proc.returncode,
                "stdout": stdout_b.decode("utf-8", errors="replace"),
                "stderr": stderr_b.decode("utf-8", errors="replace"),
                "signal": None,
            }
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return {
                "language": language,
                "version": "local",
                "exit_code": 124,
                "stdout": "",
                "stderr": "Execution timed out (10s limit exceeded)",
                "signal": "SIGKILL",
            }
    except Exception as err:
        logger.warning(f"Local subprocess execution failed for {language}: {err}")
        return None


async def _execute_wandbox(language: str, code: str, stdin: str = "") -> Optional[dict]:
    """Execute code via Wandbox free API (supports C++, Rust, Go, Python, JS, Java, etc.)."""
    import httpx

    wandbox_compiler_map = {
        "python": "cpython-3.10.11",
        "javascript": "nodejs-18.16.0",
        "c++": "gcc-head",
        "c": "gcc-head-c",
        "rust": "rust-1.70.0",
        "go": "go-1.20.4",
        "ruby": "ruby-3.2.2",
        "java": "openjdk-head",
    }
    compiler = wandbox_compiler_map.get(language)
    if not compiler:
        return None

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://wandbox.org/api/compile.json",
                json={
                    "compiler": compiler,
                    "code": code,
                    "stdin": stdin,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                status = int(data.get("status", 0))
                stdout = data.get("program_output", "") or data.get("compiler_output", "")
                stderr = data.get("program_error", "") or data.get("compiler_error", "")
                return {
                    "language": language,
                    "version": "wandbox",
                    "exit_code": status,
                    "stdout": stdout,
                    "stderr": stderr,
                    "signal": None,
                }
    except Exception as err:
        logger.warning(f"Wandbox execution failed: {err}")
        return None


async def _execute_judge0(language: str, code: str, stdin: str = "") -> Optional[dict]:
    """Execute code via Judge0 CE free public API (https://ce.judge0.com)."""
    import httpx

    judge0_lang_map = {
        "python": 71,       # Python (3.8.1)
        "javascript": 63,   # JavaScript (Node.js 12.14.0)
        "typescript": 74,   # TypeScript (3.7.4)
        "c++": 54,          # C++ (GCC 9.2.0)
        "c": 50,            # C (GCC 9.2.0)
        "java": 62,         # Java (OpenJDK 13.0.1)
        "rust": 73,         # Rust (1.40.0)
        "go": 60,           # Go (1.13.5)
        "ruby": 72,         # Ruby (2.7.0)
        "php": 68,          # PHP (7.4.1)
        "bash": 46,         # Bash (5.0.0)
    }
    lang_id = judge0_lang_map.get(language)
    if not lang_id:
        return None

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://ce.judge0.com/submissions?wait=true",
                json={
                    "language_id": lang_id,
                    "source_code": code,
                    "stdin": stdin,
                },
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                stdout = data.get("stdout") or ""
                stderr = data.get("stderr") or data.get("compile_output") or ""
                status_id = data.get("status", {}).get("id", 3)
                exit_code = 0 if status_id == 3 else 1
                return {
                    "language": language,
                    "version": "judge0",
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                    "signal": None,
                }
    except Exception as err:
        logger.warning(f"Judge0 CE execution failed: {err}")
        return None


async def execute_code(language: str, code: str, stdin: str = "") -> dict:
    """Execute code using a 3-tier cascade: Local Subprocess -> Wandbox -> Judge0 -> Piston."""
    import httpx

    language = normalize_language(language)

    # Priority 1: Try local subprocess execution (instant) only when explicitly
    # allowed. It runs untrusted code on the backend host, so it is disabled by
    # default for security; remote sandboxes are used instead.
    if settings.allow_local_code_execution:
        local_res = await _execute_local_subprocess(language, code, stdin)
        if local_res is not None:
            return local_res

    # Priority 2: Try Wandbox free public API
    wandbox_res = await _execute_wandbox(language, code, stdin)
    if wandbox_res is not None:
        return wandbox_res

    # Priority 3: Try Judge0 CE free public API
    judge0_res = await _execute_judge0(language, code, stdin)
    if judge0_res is not None:
        return judge0_res

    # Priority 4: Legacy Piston API fallback
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            canonical, version = await _runtime_for(client, language)
            ext = {
                "python": "py", "javascript": "js", "typescript": "ts", "java": "java",
                "c++": "cpp", "c": "c", "rust": "rs", "go": "go", "ruby": "rb",
                "php": "php", "bash": "sh",
            }.get(canonical, "txt")
            resp = await client.post(
                f"{PISTON_URL}/execute",
                json={
                    "language": canonical,
                    "version": version,
                    "files": [{"name": f"main.{ext}", "content": code}],
                    "stdin": stdin,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                run = data.get("run", {})
                stdout = run.get("stdout", "") or ""
                stderr = run.get("stderr", "") or ""
                raw_code = run.get("code")
                signal = run.get("signal")
                exit_code = 0 if raw_code is None and not stderr.strip() else (raw_code or 1)
                return {
                    "language": canonical, "version": version,
                    "exit_code": exit_code, "stdout": stdout,
                    "stderr": stderr, "signal": signal,
                }
    except Exception as e:
        logger.error(f"Piston fallback execution failed: {e}")

    return {
        "language": language, "version": "",
        "exit_code": -1, "stdout": "",
        "stderr": f"Code execution failed on remote sandbox.",
        "signal": None,
    }


async def _generate_code(prompt: str, language_hint: Optional[str]) -> Optional[dict]:
    allowed = ", ".join(SUPPORTED_LANGUAGES)
    hint = ""
    if language_hint:
        normalized = normalize_language(language_hint)
        hint = f"The user requested {normalized} specifically, so you MUST use language \"{normalized}\"."
    system = (
        f"You are a senior software engineer working inside a sandboxed code agent. "
        f"Given the user's request, produce a complete, self-contained, runnable program. "
        f"Return ONLY a JSON object with three keys: "
        f'"language" (exactly one of: {allowed}), '
        f'"code" (the full program source — no external file or network access; read input from stdin if needed), and '
        f'"description" (one short sentence about what it does). No markdown fences, no extra text. {hint}'
    )
    try:
        raw = await llm_service.generate(
            prompt=prompt,
            system_instruction=system,
            temperature=0.3,
            max_output_tokens=3000,
        )
    except Exception as e:
        logger.error(f"Code generation failed: {e}")
        return None
    data = _safe_json(raw)
    code = str(data.get("code", "")).strip()
    if not code:
        return None
    return {
        "language": normalize_language(str(data.get("language", "python"))),
        "code": code,
        "description": str(data.get("description", "")).strip(),
    }


async def _fix_code(prompt: str, code: str, language: str, stdout: str, stderr: str) -> Optional[str]:
    system = (
        "You are debugging a program that failed to run in a sandbox. Using the error below, "
        "produce the corrected program. Return ONLY a JSON object with keys "
        '"language", "code", and "description". Preserve the same language. '
        "If the error cannot be fixed without more information, still return your best-effort corrected code. "
        "No markdown fences, no extra text."
    )
    inner = (
        f"Original request: {prompt}\n\n"
        f"Language: {language}\n\n"
        f"Current code:\n{code}\n\n"
        f"STDOUT:\n{stdout[:2000]}\n\n"
        f"STDERR:\n{stderr[:3000]}\n\n"
        "Fixed code:"
    )
    try:
        raw = await llm_service.generate(
            prompt=inner,
            system_instruction=system,
            temperature=0.2,
            max_output_tokens=3000,
        )
    except Exception as e:
        logger.error(f"Code fix generation failed: {e}")
        return None
    data = _safe_json(raw)
    new_code = str(data.get("code", "")).strip()
    return new_code or None


async def _explain(prompt: str, language: str, code: str, stdout: str, stderr: str, exit_code: int, iterations: int) -> str:
    system = (
        "You are a code agent summarizer. Write a concise, friendly Markdown explanation of the final "
        "solution: what it does, how it works, the execution result (success or what failed), and any caveats. "
        "Do not dump the whole code; explain the approach instead."
    )
    inner = (
        f"User request: {prompt}\n\n"
        f"Language: {language}\n\n"
        f"Final code:\n{code}\n\n"
        f"STDOUT:\n{stdout[:2000]}\n\n"
        f"STDERR:\n{stderr[:2000]}\n\n"
        f"Exit code: {exit_code} after {iterations} iteration(s).\n\n"
        "Write the summary now."
    )
    try:
        return await llm_service.generate(
            prompt=inner,
            system_instruction=system,
            max_output_tokens=900,
        )
    except Exception as e:
        logger.error(f"Code explanation failed: {e}")
        return f"Finished after {iterations} iteration(s). Exit code {exit_code}."


async def stream_code_run(prompt: str, language_hint: Optional[str] = None, user_id: str = "default") -> AsyncGenerator[str, None]:
    """Run the code agent pipeline and yield SSE strings (event: code_* + data JSON)."""

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    goal = prompt.strip()
    yield sse("code_start", {"title": goal[:120], "max_iterations": MAX_ITERATIONS})

    plan = ""
    try:
        plan = await llm_service.generate(
            prompt=goal,
            system_instruction=(
                "You are a code agent planner. In 2-4 short bullet points, describe the approach you will "
                "take to implement the user's request, the algorithm/data structure, and edge cases to handle. "
                "Keep it under 120 words."
            ),
            max_output_tokens=300,
        )
    except Exception as e:
        logger.warning(f"Code plan failed: {e}")
    if plan:
        yield sse("code_plan", {"plan": plan})

    initial = await _generate_code(goal, language_hint)
    if not initial:
        yield sse("code_complete", {"error": "The code agent could not generate a solution. Please rephrase your request."})
        return

    code = initial["code"]
    language = initial["language"]
    description = initial.get("description", "")

    iterations = 0
    exit_code = None
    stdout = ""
    stderr = ""

    for iteration in range(1, MAX_ITERATIONS + 1):
        iterations = iteration
        yield sse("code_write", {"iteration": iteration, "language": language, "code": code, "description": description})
        result = await execute_code(language, code)
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        exit_code = result.get("exit_code")
        yield sse("code_run", {
            "iteration": iteration, "language": result.get("language", language),
            "version": result.get("version", ""), "exit_code": exit_code,
            "stdout": stdout, "stderr": stderr,
        })
        if exit_code == 0:
            break
        if iteration >= MAX_ITERATIONS:
            break
        fixed = await _fix_code(goal, code, language, stdout, stderr)
        if not fixed:
            break
        code = fixed
        reason = (stderr.strip() or stdout.strip() or f"Exit code {exit_code}")[:400]
        yield sse("code_retry", {
            "iteration": iteration, "next_iteration": iteration + 1,
            "max_iterations": MAX_ITERATIONS, "reason": reason,
        })

    explanation = await _explain(goal, language, code, stdout, stderr, exit_code or 0, iterations)
    yield sse("code_complete", {
        "language": language,
        "code": code,
        "iterations": iterations,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "explanation": explanation,
    })
