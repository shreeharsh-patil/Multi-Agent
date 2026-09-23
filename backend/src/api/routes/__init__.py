"""API route package bootstrap."""

# Install the production chat quality boundary before ``routes.chat`` imports
# functions from ``src.adk.runner``.  Keeping this bootstrap at the route layer
# leaves the lower-level ADK runner independently testable while ensuring every
# HTTP chat request uses the hardened user-facing execution path.
from src.api.routes._chat_quality import install_chat_quality_runtime

install_chat_quality_runtime()

__all__ = []
