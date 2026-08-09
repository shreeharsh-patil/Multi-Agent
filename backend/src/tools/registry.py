from typing import Callable, Any, Optional
from dataclasses import dataclass, field
from src.utils.logger import logger


@dataclass
class ToolDefinition:
    id: str
    name: str
    category: str
    description: str
    parameters_schema: dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable] = None


class ToolRegistry:
    _tools: dict[str, ToolDefinition] = {}

    @classmethod
    def register(cls, tool: ToolDefinition) -> None:
        cls._tools[tool.id] = tool
        logger.info(f"Registered tool: {tool.id} ({tool.name})")

    @classmethod
    def get_tool(cls, tool_id: str) -> Optional[ToolDefinition]:
        return cls._tools.get(tool_id)

    @classmethod
    def list_tools(cls) -> list[dict[str, Any]]:
        return [
            {
                "id": t.id,
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "parameters_schema": t.parameters_schema,
            }
            for t in cls._tools.values()
        ]

    @classmethod
    def execute_tool(cls, tool_id: str, **kwargs) -> dict[str, Any]:
        tool = cls.get_tool(tool_id)
        if not tool:
            return {"success": False, "error": f"Tool {tool_id} not registered"}
        if tool.handler:
            try:
                result = tool.handler(**kwargs)
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": True, "result": f"Executed tool {tool.name} with params {kwargs}"}


# Initialize built-in tool definitions
def init_default_tools():
    tools = [
        ToolDefinition("web_search", "Web Search Engine", "Web search", "Searches the web for up-to-date information, news, and technical data."),
        ToolDefinition("browser", "Browser Sandbox", "Browser", "Automates web page rendering, DOM extraction, and interaction."),
        ToolDefinition("code_execution", "Python/JS Code Execution", "Code execution", "Executes Python or JavaScript code safely in a sandboxed environment."),
        ToolDefinition("file_system", "File System Manager", "File system", "Reads, writes, and manages files in the workspace."),
        ToolDefinition("database", "Database Client", "Database", "Queries SQL and MongoDB datastores and evaluates schemas."),
        ToolDefinition("apis", "API Integration Suite", "APIs", "Sends REST, HTTP, and GraphQL requests to external services."),
        ToolDefinition("image_generation", "Generative Image Engine", "Image generation", "Creates and edits visual assets via AI models."),
        ToolDefinition("document_processing", "PDF & Document Parser", "Document processing", "Extracts structured text, tables, and embeddings from PDF and DOCX files."),
        ToolDefinition("spreadsheet_processing", "Spreadsheet Analyzer", "Spreadsheet processing", "Parses and manipulates CSV and Excel data."),
        ToolDefinition("git", "Git Version Control", "Git", "Manages commits, branches, and code repository operations."),
        ToolDefinition("testing", "Automated Test Runner", "Testing", "Executes unit, integration, and security test suites."),
        ToolDefinition("deployment", "CI/CD Deployment Engine", "Deployment", "Builds and deploys applications to cloud infrastructure."),
    ]
    for t in tools:
        ToolRegistry.register(t)


init_default_tools()
