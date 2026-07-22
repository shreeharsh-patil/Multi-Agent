from src.agents.registry import AgentRegistry
from src.utils.logger import logger


def initialize_agents() -> None:
    if AgentRegistry._initialized:
        return

    from src.agents.knowledge.agent import KnowledgeAgent
    from src.agents.drive.agent import DriveAgent
    from src.agents.notes.agent import NotesAgent
    from src.agents.quiz.agent import QuizAgent
    from src.agents.planner.agent import PlannerAgent
    from src.agents.research.agent import ResearchAgent
    from src.agents.coding.agent import CodingAgent
    from src.agents.memory.agent import MemoryAgent
    from src.agents.tool.agent import ToolAgent
    from src.agents.calendar.agent import CalendarAgent
    from src.agents.data_analysis.agent import DataAnalysisAgent
    from src.agents.weather_news.agent import WeatherNewsAgent
    from src.agents.gmail.agent import GmailAgent
    from src.agents.tasks.agent import TasksAgent
    from src.agents.youtube.agent import YouTubeAgent
    from src.agents.contacts.agent import ContactsAgent

    AgentRegistry.register(KnowledgeAgent())
    AgentRegistry.register(DriveAgent())
    AgentRegistry.register(NotesAgent())
    AgentRegistry.register(QuizAgent())
    AgentRegistry.register(PlannerAgent())
    AgentRegistry.register(ResearchAgent())
    AgentRegistry.register(CodingAgent())
    AgentRegistry.register(MemoryAgent())
    AgentRegistry.register(ToolAgent())
    AgentRegistry.register(CalendarAgent())
    AgentRegistry.register(DataAnalysisAgent())
    AgentRegistry.register(WeatherNewsAgent())
    AgentRegistry.register(GmailAgent())
    AgentRegistry.register(TasksAgent())
    AgentRegistry.register(YouTubeAgent())
    AgentRegistry.register(ContactsAgent())

    AgentRegistry.initialize()
    logger.info(f"Initialized {len(AgentRegistry.get_all_agents())} agents")
