"""OmniSight Backend - AI Visual Conversation Assistant."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.ws import router as ws_router
from app.services.transcriber import AudioTranscriber
from app.services.ollama_client import OllamaClient
from app.services.conversation import ConversationOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize AI services at startup, clean up at shutdown."""
    logger.info("OmniSight backend starting up")

    settings = get_settings()

    # Initialize faster-whisper (downloads model on first run if needed)
    logger.info(
        "Loading Whisper model '%s' (language=%s)...",
        settings.whisper_model,
        settings.whisper_language or "auto",
    )
    transcriber = AudioTranscriber(settings.whisper_model, settings.whisper_language)

    # Initialize Ollama client
    logger.info(
        "Connecting to Ollama at %s (model=%s)...",
        settings.ollama_base_url,
        settings.ollama_model,
    )
    ollama = OllamaClient(settings.ollama_base_url, settings.ollama_model)

    # Health check
    ollama_ok = await ollama.check_health()
    if ollama_ok:
        logger.info("Ollama model '%s' is available", settings.ollama_model)
    else:
        logger.warning(
            "Ollama model '%s' is NOT available. AI features will be degraded. "
            "Run: ollama pull %s",
            settings.ollama_model,
            settings.ollama_model,
        )

    orchestrator = ConversationOrchestrator(transcriber, ollama)

    # Store in app.state for route handlers
    app.state.settings = settings
    app.state.transcriber = transcriber
    app.state.ollama = ollama
    app.state.orchestrator = orchestrator

    yield

    logger.info("Shutting down AI services")
    await ollama.close()
    logger.info("OmniSight backend shut down")


app = FastAPI(
    title="OmniSight",
    version="0.2.0",
    description="AI Visual Conversation Assistant Backend",
    lifespan=lifespan,
)

# CORS middleware - allows all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(ws_router)


@app.get("/health")
async def health(request: Request):
    """Health check — includes Ollama connectivity status."""
    ollama = getattr(request.app.state, "ollama", None)
    ollama_ok = await ollama.check_health() if ollama else False
    return {
        "status": "ok",
        "version": "0.2.0",
        "ollama_available": ollama_ok,
    }
