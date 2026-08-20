"""Security regression tests for the fixes applied in the hardening pass."""

import os
import pytest

# Import while conftest's strong test secret is active. Individual tests then
# safely mutate environment variables to exercise fresh Settings instances.
from src.config import Settings


# ---------------------------------------------------------------------------
# Config fail-closed behaviour
# ---------------------------------------------------------------------------

class TestSecretKeyFailClosed:
    def test_refuses_insecure_secret_in_production(self, monkeypatch):
        """A weak/known SECRET_KEY must prevent startup outside debug mode."""
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("SECRET_KEY", "change-this-in-production")
        from src.config import Settings
        with pytest.raises(ValueError, match="REFUSING TO START"):
            Settings()

    def test_requires_minimum_length_secret(self, monkeypatch):
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("SECRET_KEY", "short")
        from src.config import Settings
        with pytest.raises(ValueError, match="SECRET_KEY"):
            Settings()

    def test_debug_allows_fallback(self, monkeypatch):
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("SECRET_KEY", "change-this-in-production")
        from src.config import Settings
        assert Settings().debug is True

    def test_default_debug_is_false(self, monkeypatch):
        monkeypatch.delenv("DEBUG", raising=False)
        monkeypatch.setenv("SECRET_KEY", "x-strong-test-secret-key-0123456789")
        from src.config import Settings
        assert Settings(_env_file=None).debug is False


# ---------------------------------------------------------------------------
# Upload filename sanitization (path traversal / header injection)
# ---------------------------------------------------------------------------

class TestSafeFilename:
    @pytest.fixture(autouse=True)
    def _fixture(self):
        yield

    def test_strips_path_traversal(self):
        from src.api.routes.documents import _safe_filename
        assert _safe_filename("../../etc/passwd") == "passwd"
        assert _safe_filename("..\\..\\evil.png") == "evil.png"
        assert _safe_filename("C:\\Windows\\system32\\file.txt") == "file.txt"

    def test_strips_crlf_and_quotes(self):
        from src.api.routes.documents import _safe_filename
        assert '"' not in _safe_filename('a"b.txt')
        assert "\r" not in _safe_filename("a\r\nb.txt")
        assert "\n" not in _safe_filename("a\nb.txt")

    def test_none_falls_back(self):
        from src.api.routes.documents import _safe_filename
        assert _safe_filename(None) == "unnamed"


# ---------------------------------------------------------------------------
# SSRF URL guard
# ---------------------------------------------------------------------------

class TestSSRFGuard:
    def test_rejects_private_and_loopback(self):
        from src.adk.tools import _validate_outbound_url
        for url in [
            "http://localhost:27017",
            "http://127.0.0.1/admin",
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.5/internal",
            "http://192.168.1.1/panel",
        ]:
            assert _validate_outbound_url(url) is False, url

    def test_rejects_non_http_schemes(self):
        from src.adk.tools import _validate_outbound_url
        assert _validate_outbound_url("file:///etc/passwd") is False
        assert _validate_outbound_url("ftp://example.com") is False

    def test_allows_public_urls(self):
        from src.adk.tools import _validate_outbound_url
        assert _validate_outbound_url("https://example.com/page") is True
        assert _validate_outbound_url("https://sub.domain.example.com/") is True


# ---------------------------------------------------------------------------
# Document access authorization (IDOR)
# ---------------------------------------------------------------------------

class TestCanAccessDocument:
    async def test_owner_always_allowed(self):
        from src.api.routes.documents import can_access_document
        assert await can_access_document(_doc(user_id="u1"), "u1") is True

    async def test_non_owner_private_doc_denied(self):
        from src.api.routes.documents import can_access_document
        assert await can_access_document(_doc(user_id="u1"), "u2") is False

    async def test_anonymous_cannot_read_private_doc(self):
        from src.api.routes.documents import can_access_document
        # anonymous resolves to "default"
        assert await can_access_document(_doc(user_id="u1"), "default") is False

    async def test_public_default_bucket_readable(self):
        from src.api.routes.documents import can_access_document
        assert await can_access_document(_doc(user_id="default"), "u2") is True
        assert await can_access_document(_doc(user_id="default"), "default") is True


def test_private_document_routes_are_not_middleware_public():
    """A browser request must authenticate before any document route runs."""
    from src.api.middleware import _is_public
    assert _is_public("GET", "/api/documents/abc123/file") is False
    assert _is_public("GET", "/api/documents/abc123/download") is False


def test_chat_request_rejects_oversized_agent_fanout():
    from pydantic import ValidationError
    from src.api.routes.chat import ChatRequest

    with pytest.raises(ValidationError):
        ChatRequest(message="hello", team_agents=["agent"] * 9)


def test_google_login_requires_a_token_in_production(monkeypatch):
    """Caller-supplied email alone can never mint a production JWT."""
    from src.api.routes import auth

    monkeypatch.setattr(auth.settings, "debug", False)
    with pytest.raises(Exception) as exc_info:
        import asyncio
        asyncio.run(auth._verify_google_identity(""))
    assert getattr(exc_info.value, "status_code", None) == 401


def _doc(**kwargs):
    """Minimal stand-in for a Document query model used by can_access_document."""
    class _D:
        pass
    d = _D()
    d.user_id = kwargs.get("user_id", "default")
    d.workspace_id = kwargs.get("workspace_id", None)
    return d


# ---------------------------------------------------------------------------
# Calculator: no eval / attribute access
# ---------------------------------------------------------------------------

class TestCalculatorSafe:
    async def test_arithmetic(self):
        from src.adk.tools import calculator
        assert (await calculator("2 + 3 * 4")).startswith("Result: 14")

    async def test_math_functions(self):
        from src.adk.tools import calculator
        out = await calculator("sqrt(16) + 1")
        assert out.startswith("Result: 5.0")

    async def test_rejects_imports_and_attribute_access(self):
        from src.adk.tools import calculator
        for expr in ["__import__('os')", "().__class__", "os.system('id')", "lambda: 1"]:
            assert "Calculation error" in await calculator(expr), expr


# ---------------------------------------------------------------------------
# Code execution default off (arbitrary code must not run on host by default)
# ---------------------------------------------------------------------------

class TestLocalCodeExecutionDisabled:
    def test_local_execution_off_by_default(self, monkeypatch):
        """Generated/untrusted code must not run on the host unless explicitly enabled."""
        monkeypatch.delenv("ALLOW_LOCAL_CODE_EXECUTION", raising=False)
        from src.config import Settings
        assert Settings().allow_local_code_execution is False

    async def test_execute_code_gates_local_runner(self, monkeypatch):
        import src.services.code_agent as ca

        calls = {"local": 0}

        async def fake_local(lang, code, stdin=""):
            calls["local"] += 1
            return None  # never used locally in the disabled case

        async def fake_wandbox(lang, code, stdin=""):
            return {"language": lang, "exit_code": 0, "stdout": "REMOTE"}

        monkeypatch.setattr(ca, "_execute_local_subprocess", fake_local)
        monkeypatch.setattr(ca, "_execute_wandbox", fake_wandbox)
        monkeypatch.setattr(ca, "_execute_judge0", fake_wandbox)

        # Disabled (default): local runner must NOT be invoked; remote is used.
        monkeypatch.setattr(ca, "settings", type("S", (), {"allow_local_code_execution": False})())
        res = await ca.execute_code("python", "print(1)")
        assert calls["local"] == 0
        assert res["stdout"] == "REMOTE"

        # Enabled: local runner is tried first and returns before remote.
        calls["local"] = 0

        async def fake_local_hit(lang, code, stdin=""):
            calls["local"] += 1
            return {"language": lang, "version": "local", "exit_code": 0, "stdout": "localhit"}

        monkeypatch.setattr(ca, "_execute_local_subprocess", fake_local_hit)
        monkeypatch.setattr(ca, "settings", type("S", (), {"allow_local_code_execution": True})())
        res2 = await ca.execute_code("python", "print(2)")
        assert calls["local"] == 1
        assert res2["stdout"] == "localhit"
