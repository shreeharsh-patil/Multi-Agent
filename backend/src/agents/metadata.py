from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any
from pydantic import BaseModel, Field


class AgentDepartment(str, Enum):
    COMMAND_PLANNING = "Command and Planning"
    CODING = "Coding"
    RESEARCH = "Research"
    CONTENT = "Content"
    VISUAL = "Visual"
    DATA = "Data"
    PRODUCT = "Product"
    AI_ML = "AI and ML"
    AUTOMATION = "Automation"
    BUSINESS_QUALITY = "Business and Quality"


class TaskMode(str, Enum):
    QUICK = "QUICK"
    STANDARD = "STANDARD"
    DEEP = "DEEP"
    CRITICAL = "CRITICAL"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class AgentMetadata:
    id: str
    name: str
    department: AgentDepartment
    description: str
    capabilities: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)
    specialized_instruction: str = ""
    domain_quality_criteria: list[str] = field(default_factory=list)
    input_schema: dict[str, str] = field(default_factory=dict)
    output_schema: dict[str, str] = field(default_factory=dict)
    required_tools: list[str] = field(default_factory=list)
    optional_tools: list[str] = field(default_factory=list)
    priority: int = 1
    dependencies: list[str] = field(default_factory=list)
    can_run_in_parallel: bool = True
    max_retries: int = 3
    enabled: bool = True
    icon: str = "Bot"


class TaskObject(BaseModel):
    task_id: str
    objective: str
    instructions: str
    mode: TaskMode = TaskMode.STANDARD
    context: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    previous_results: dict[str, Any] = Field(default_factory=dict)
    available_tools: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class AgentResultObject(BaseModel):
    task_id: str
    agent_id: str
    status: str = "completed"  # pending, running, completed, failed, retrying, skipped
    result: str
    reasoning_summary: str = ""
    confidence: float = 1.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.HIGH
    sources: list[dict[str, Any]] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    unresolved_issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    error: Optional[str] = None


class ProductResultObject(BaseModel):
    productName: str
    brand: Optional[str] = None
    model: Optional[str] = None
    category: str = "general"
    price: float
    currency: str = "INR"
    originalPrice: Optional[float] = None
    discount: Optional[str] = None
    budgetSatisfied: bool = True
    seller: Optional[str] = None
    marketplace: Optional[str] = None
    availability: str = "in_stock"  # in_stock, out_of_stock, limited, unknown
    rating: Optional[float] = None
    reviewCount: Optional[int] = None
    specifications: dict[str, Any] = Field(default_factory=dict)
    productUrl: Optional[str] = None
    sourceUrl: Optional[str] = None
    lastVerified: str = ""
    confidence: float = 1.0
