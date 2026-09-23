"""API route package bootstrap."""

import os
import sys

# Install the production chat quality boundary before ``routes.chat`` imports
# functions from ``src.adk.runner``. Keeping this bootstrap at the route layer
# leaves the lower-level ADK runner independently testable while ensuring every
# real HTTP chat request uses the hardened user-facing execution path.
#
# Pytest imports route modules during collection in the same interpreter as
# low-level runner tests. Skip the global patch there unless an isolated test
# explicitly opts in; production processes do not import pytest.
if "pytest" not in sys.modules or os.getenv("AGENTIC_FORCE_CHAT_QUALITY") == "1":
    from src.api.routes._chat_quality import install_chat_quality_runtime

    install_chat_quality_runtime()

__all__ = []
