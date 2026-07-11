from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentResult:
    success: bool
    output: str
    citations: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentManifest:
    id: str
    name: str
    description: str
    icon: str
    version: str = "0.1.0"
    capabilities: list[str] = field(default_factory=list)
    enabled: bool = True


class BaseAgent(ABC):
    def __init__(self):
        self.manifest = self._create_manifest()

    @abstractmethod
    def _create_manifest(self) -> AgentManifest:
        pass

    @abstractmethod
    async def execute(self, user_input: str, context: dict) -> AgentResult:
        pass

    async def validate_input(self, user_input: str) -> bool:
        return bool(user_input and len(user_input.strip()) > 0)
