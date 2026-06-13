"""OmniSight Backend - AI Visual Conversation Assistant."""

import sys
import time
import asyncio
import logging
from contextlib import asynccontextmanager

# Windows requires ProactorEventLoop for asyncio subprocess support
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.ws import router as ws_router, state_manager
from app.services.transcriber import AudioTranscriber
from app.services.ollama_client import OllamaClient
from app.services.conversation import ConversationOrchestrator
from app.services.tts import PiperTTS, PiperTTSError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)
_start_time = time.time()


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

    # Health check with retry (Ollama may still be starting up)
    ollama_ok = await ollama.check_health_with_retry()
    if ollama_ok:
        logger.info("Ollama model '%s' is available", settings.ollama_model)
    else:
        logger.warning(
            "Ollama model '%s' is NOT available. AI features will be degraded. "
            "Run: ollama pull %s",
            settings.ollama_model,
            settings.ollama_model,
        )

    # Initialize Piper TTS (optional — graceful fallback to browser TTS)
    piper_tts: PiperTTS | None = None
    if settings.tts_backend == "piper":
        try:
            piper_tts = PiperTTS(
                executable=settings.piper_executable,
                model_path=settings.piper_model,
                config_path=settings.piper_model_config,
                speaker=settings.piper_speaker,
            )
            await piper_tts.initialize()
            logger.info(
                "Piper TTS ready (voice=%s, sample_rate=%d Hz)",
                settings.piper_model, piper_tts.sample_rate,
            )
        except PiperTTSError as exc:
            logger.warning(
                "Piper TTS unavailable — falling back to browser SpeechSynthesis. "
                "Error: %s", exc,
            )
            piper_tts = None

    orchestrator = ConversationOrchestrator(transcriber, ollama, piper_tts)

    # Store in app.state for route handlers
    # PR 5: Configure and start stale session cleanup
    state_manager.set_idle_timeout(settings.session_idle_timeout)
    await state_manager.start_cleanup_task()

    app.state.settings = settings
    app.state.transcriber = transcriber
    app.state.ollama = ollama
    app.state.orchestrator = orchestrator
    app.state.tts = piper_tts

    yield

    logger.info("Shutting down AI services")
    await state_manager.stop_cleanup_task()
    await ollama.close()
    logger.info("OmniSight backend shut down")


app = FastAPI(
    title="OmniSight",
    version="0.4.0",
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
    """Health check — includes Ollama connectivity and session stats."""
    ollama = getattr(request.app.state, "ollama", None)
    ollama_ok = await ollama.check_health() if ollama else False
    active_sessions = await state_manager.get_session_count()
    return {
        "status": "ok",
        "version": "0.4.0",
        "ollama_available": ollama_ok,
        "active_sessions": active_sessions,
        "uptime_seconds": round(time.time() - _start_time, 1),
    }
