from typing import Optional, Any
from src.agents.base import BaseAgent, AgentManifest
from src.agents.metadata import AgentDepartment, AgentMetadata
from src.utils.logger import logger


class AgentRegistry:
    _agents: dict[str, BaseAgent] = {}
    _metadata: dict[str, AgentMetadata] = {}
    _initialized = False

    @classmethod
    def register(cls, agent: BaseAgent, metadata: Optional[AgentMetadata] = None) -> None:
        agent_id = agent.manifest.id
        cls._agents[agent_id] = agent
        if metadata:
            cls._metadata[agent_id] = metadata
        else:
            # Fallback metadata generation if registering legacy or custom agent
            cls._metadata[agent_id] = AgentMetadata(
                id=agent_id,
                name=agent.manifest.name,
                department=AgentDepartment.COMMAND_PLANNING,
                description=agent.manifest.description,
                capabilities=getattr(agent.manifest, "capabilities", []),
                icon=getattr(agent.manifest, "icon", "Bot"),
            )
        logger.info(f"Registered agent: {agent_id} ({agent.manifest.name})")

    @classmethod
    def get_agent(cls, agent_id: str) -> Optional[BaseAgent]:
        return cls._agents.get(agent_id)

    @classmethod
    def get_metadata(cls, agent_id: str) -> Optional[AgentMetadata]:
        return cls._metadata.get(agent_id)

    @classmethod
    def get_all_manifests(cls) -> list[AgentManifest]:
        return [a.manifest for a in cls._agents.values()]

    @classmethod
    def get_all_agents(cls) -> list[BaseAgent]:
        return list(cls._agents.values())

    @classmethod
    def get_all_metadata(cls) -> list[AgentMetadata]:
        return list(cls._metadata.values())

    @classmethod
    def get_by_department(cls, department: AgentDepartment | str) -> list[BaseAgent]:
        dept_val = department.value if isinstance(department, AgentDepartment) else str(department)
        return [
            a for aid, a in cls._agents.items()
            if aid in cls._metadata and cls._metadata[aid].department.value == dept_val
        ]

    @classmethod
    def get_by_capability(cls, capability: str) -> list[BaseAgent]:
        cap_clean = capability.casefold().strip()
        matching = []
        for aid, a in cls._agents.items():
            meta = cls._metadata.get(aid)
            if meta:
                meta_caps = getattr(meta, "capabilities", [])
                if any(cap_clean in str(c).casefold() or str(c).casefold() in cap_clean for c in meta_caps):
                    matching.append(a)
        return matching

    @classmethod
    def search(cls, query: str) -> list[dict[str, Any]]:
        q = query.casefold().strip()
        results = []
        for aid, meta in cls._metadata.items():
            if (
                q in meta.id.casefold()
                or q in meta.name.casefold()
                or q in meta.description.casefold()
                or q in meta.department.value.casefold()
                or any(q in c.casefold() for c in meta.capabilities)
            ):
                results.append({
                    "id": meta.id,
                    "name": meta.name,
                    "department": meta.department.value,
                    "description": meta.description,
                    "capabilities": meta.capabilities,
                    "responsibilities": meta.responsibilities,
                    "required_tools": meta.required_tools,
                    "optional_tools": meta.optional_tools,
                    "priority": meta.priority,
                    "icon": meta.icon,
                })
        return results

    @classmethod
    def initialize(cls, force: bool = False) -> None:
        if cls._initialized and not force:
            return
        if force:
            cls._agents.clear()
            cls._metadata.clear()
            import importlib
            import src.agents.catalog
            importlib.reload(src.agents.catalog)
        cls._initialized = True

        from src.agents.catalog import AGENT_CATALOG_DATA, GenericSpecialistAgent

        # Register existing domain-specific agents
        try:
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

            domain_agents = [
                KnowledgeAgent(), DriveAgent(), NotesAgent(), QuizAgent(), PlannerAgent(),
                ResearchAgent(), CodingAgent(), MemoryAgent(), ToolAgent(), CalendarAgent(),
                DataAnalysisAgent(), WeatherNewsAgent(), GmailAgent(), TasksAgent(), YouTubeAgent(),
                ContactsAgent(), EngineerAgent(), PharmacologistAgent(), DoctorAgent(), FinanceAgent(),
                AccountantAgent(), EconomicsAgent(), ArchitectAgent(), HackerAgent(), ChefAgent(),
                MusicAgent(), FitnessAgent(), ArtAgent()
            ]
            for da in domain_agents:
                cls.register(da)
        except Exception as err:
            logger.warning(f"Domain agents initialization notice: {err}")

        # Register all 100 specialized agents
        for meta in AGENT_CATALOG_DATA:
            agent_instance = GenericSpecialistAgent(meta)
            cls.register(agent_instance, meta)

        logger.info(f"Agent registry initialized with {len(cls._agents)} agents")


# Auto-initialize on import for safety
AgentRegistry.initialize()
