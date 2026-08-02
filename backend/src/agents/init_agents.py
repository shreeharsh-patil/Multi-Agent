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
    from src.agents.engineer.agent import EngineerAgent
    from src.agents.pharmacologist.agent import PharmacologistAgent
    from src.agents.doctor.agent import DoctorAgent
    from src.agents.finance.agent import FinanceAgent
    from src.agents.accountant.agent import AccountantAgent
    from src.agents.economics.agent import EconomicsAgent
    from src.agents.architect.agent import ArchitectAgent
    from src.agents.hacker.agent import HackerAgent
    from src.agents.cooking.agent import ChefAgent
    from src.agents.music.agent import MusicAgent
    from src.agents.fitness.agent import FitnessAgent
    from src.agents.art.agent import ArtAgent

    AgentRegistry.register(KnowledgeAgent())
    AgentRegistry.register(DriveAgent())
    AgentRegistry.register(NotesAgent())
    AgentRegistry.register(QuizAgent())
    AgentRegistry.register(PlannerAgent())
    AgentRegistry.register(ResearchAgent())
    AgentRegistry.register(DeepResearchAgent())
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
    AgentRegistry.register(EngineerAgent())
    AgentRegistry.register(PharmacologistAgent())
    AgentRegistry.register(DoctorAgent())
    AgentRegistry.register(FinanceAgent())
    AgentRegistry.register(AccountantAgent())
    AgentRegistry.register(EconomicsAgent())
    AgentRegistry.register(ArchitectAgent())
    AgentRegistry.register(HackerAgent())
    AgentRegistry.register(ChefAgent())
    AgentRegistry.register(MusicAgent())
    AgentRegistry.register(FitnessAgent())
    AgentRegistry.register(ArtAgent())

    AgentRegistry.initialize()
    logger.info(f"Initialized {len(AgentRegistry.get_all_agents())} agents")
