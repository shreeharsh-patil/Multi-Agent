from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.config import settings
from src.utils.logger import logger
from src.api.middleware import error_handler_middleware
from src.agents.init_agents import initialize_agents
from src.api.routes import chat, documents, agents as agents_route, knowledge


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    initialize_agents()
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
app.middleware("http")(error_handler_middleware)

app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(agents_route.router)
app.include_router(knowledge.router)


@app.get("/api/health")
async def health_check() -> dict:
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
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
        },
    }
