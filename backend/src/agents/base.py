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

    # --- Rich orchestration metadata (used by the Boss Agent / agentic engine) ---
    # All fields have safe defaults so existing agents remain unaffected.
    department: str = "General"
    responsibilities: list[str] = field(default_factory=list)
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    required_tools: list[str] = field(default_factory=list)
    optional_tools: list[str] = field(default_factory=list)
    # Higher priority is considered first when the Boss picks a specialist.
    priority: int = 50
    dependencies: list[str] = field(default_factory=list)
    can_run_in_parallel: bool = True
    max_retries: int = 2
    # Lightweight ("cheap") / "balanced" / "strong" — Boss routes by complexity.
    model_tier: str = "balanced"
    cost_weight: float = 1.0
    avg_latency_ms: int = 1000

    def to_brief(self) -> dict:
        """Compact serialization used for observability and the UI."""
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.id,
            "department": self.department,
            "description": self.description,
            "icon": self.icon,
            "capabilities": self.capabilities,
            "required_tools": self.required_tools,
            "priority": self.priority,
            "can_run_in_parallel": self.can_run_in_parallel,
            "max_retries": self.max_retries,
            "model_tier": self.model_tier,
            "enabled": self.enabled,
        }


class AgentTaskSpec:
    """Standardized task object delivered to every worker agent.

    This is the contract the Boss uses to communicate with specialists.
    `context` is scoped: it contains only the user context, prior results
    of dependent subtasks, and authorized tool outputs relevant to this step.
    """

    def __init__(
        self,
        task_id: str,
        objective: str,
        instructions: str,
        context: dict,
        dependencies: Optional[list] = None,
        previous_results: Optional[list] = None,
        available_tools: Optional[list] = None,
        constraints: Optional[list] = None,
    ):
        self.task_id = task_id
        self.objective = objective
        self.instructions = instructions
        self.context = context or {}
        self.dependencies = dependencies or []
        self.previous_results = previous_results or []
        self.available_tools = available_tools or []
        self.constraints = constraints or []

    def render(self) -> str:
        """Format the task spec as the prompt delivered to an agent."""
        parts = [f"Objective: {self.objective}", f"Instructions: {self.instructions}"]
        if self.previous_results:
            block = "\n\n".join(f"[{r.get('agent', r.get('source', 'prior'))}]:\n{r.get('result', '')}" for r in self.previous_results)
            parts.append(f"Previous results available:\n{block}")
        if self.context:
            ctx = self.context.get("summary") or self.context.get("memory") or ""
            if ctx:
                parts.append(f"Shared task context:\n{ctx}")
        if self.available_tools:
            parts.append(f"Authorized tools: {', '.join(self.available_tools)}")
        if self.constraints:
            parts.append("Constraints: " + "; ".join(self.constraints))
        return "\n\n".join(part for part in parts if part)


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
