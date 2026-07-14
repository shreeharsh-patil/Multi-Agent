from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from src.config import settings
from src.utils.logger import logger
from src.api.middleware import (
    api_response_envelope_middleware,
    error_handler_middleware,
    jwt_auth_middleware,
)
from src.api.routes import auth, chat, documents, agents as agents_route, knowledge, drive, notes, quiz, research, planner


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # --- Initialize MongoDB / Beanie ---
    mongo_client = None
    try:
        for uri in [
            settings.mongodb_uri,
            settings.mongodb_uri + ("&" if "?" in settings.mongodb_uri else "?") + "tls=true&tlsInsecure=true&retryWrites=true&w=majority",
            "mongodb://localhost:27017/multi-agent-platform",
        ]:
            try:
                client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=15000)
                await client.admin.command("ping")
                mongo_client = client
                logger.info("MongoDB connected")
                break
            except Exception as e:
                logger.warning(f"MongoDB attempt failed: {e}")

        if mongo_client is None:
            raise RuntimeError("No MongoDB connection available")

        from src.models.user import User
        from src.models.document import Document, DocumentChunk
        from src.models.conversation import Conversation
        from src.models.memory import MemoryItem
        from src.models.agent import AgentConfig, AgentTask, ActivityLog
        from src.models.note import Note
        from src.models.research import ResearchReport
        from src.models.planner import PlannerPlan
        from src.models.quiz import QuizSession

        await init_beanie(
            database=mongo_client[settings.mongodb_db_name],
            document_models=[
                User, Document, DocumentChunk, Conversation, MemoryItem,
                AgentConfig, AgentTask, ActivityLog, Note, ResearchReport,
                PlannerPlan, QuizSession,
            ],
        )
        logger.info("Beanie models initialized")
    except Exception as e:
        logger.warning(f"MongoDB initialization failed: {e}")
        logger.warning("App will start without database — some features will be unavailable")

    # --- Initialize custom agents (fallback) ---
    from src.agents.init_agents import initialize_agents
    initialize_agents()
    logger.info("Custom agents initialized")

    # --- Initialize ADK orchestrator eagerly ---
    from src.adk.runner import get_orchestrator
    get_orchestrator()
    logger.info("ADK multi-agent system initialized")

    yield

    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(jwt_auth_middleware)
app.middleware("http")(error_handler_middleware)
app.middleware("http")(api_response_envelope_middleware)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(agents_route.router)
app.include_router(knowledge.router)
app.include_router(drive.router)
app.include_router(notes.router)
app.include_router(quiz.router)
app.include_router(research.router)
app.include_router(planner.router)


@app.get("/api/health")
async def health_check(request: Request) -> dict:
    db_status = "unknown"
    try:
        from src.models.user import User
        await User.find_one()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "database": db_status,
    }


@app.get("/api")
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "endpoints": {
            "chat": "/api/chat",
            "documents": "/api/documents",
            "agents": "/api/agents",
            "knowledge": "/api/knowledge",
            "health": "/api/health",
            "research": "/api/research",
            "planner": "/api/planner",
        },
    }
