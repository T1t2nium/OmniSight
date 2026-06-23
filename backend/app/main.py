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
from app.services.base_ai_client import BaseAIClient
from app.services.ollama_client import OllamaClient
from app.services.bailian_http_client import BailianHTTPClient
from app.services.conversation import ConversationOrchestrator
from app.services.tts import PiperTTS, PiperTTSError
from app.services.sherpa_tts import SherpaTTS, SherpaTTSError
from app.agents.base import AgentRegistry, ChatAgent
from app.agents.interview import InterviewAgent

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
    transcriber = AudioTranscriber(
        settings.whisper_model,
        settings.whisper_language,
        settings.whisper_device,
    )

    # Initialize AI client based on provider setting
    ai_client: BaseAIClient
    if settings.ai_provider == "bailian":
        if not settings.bailian_api_key:
            logger.error(
                "Bailian provider selected but bailian_api_key is not set. "
                "Set BAILIAN_API_KEY in .env or switch to ai_provider=ollama."
            )
            raise ValueError("Bailian API key is required when ai_provider=bailian")
        logger.info(
            "Connecting to Alibaba Cloud Bailian (model=%s)...",
            settings.bailian_model,
        )
        ai_client = BailianHTTPClient(settings.bailian_api_key, settings.bailian_model)
    else:
        # Default: Ollama (local)
        logger.info(
            "Connecting to Ollama at %s (model=%s)...",
            settings.ollama_base_url,
            settings.ollama_model,
        )
        ai_client = OllamaClient(settings.ollama_base_url, settings.ollama_model)

    # Health check with retry (model may still be loading)
    ai_ok = await ai_client.check_health_with_retry()
    if ai_ok:
        logger.info("%s model '%s' is available", ai_client.provider_name, ai_client.model)
    else:
        logger.warning(
            "%s model '%s' is NOT available. AI features may be degraded.",
            ai_client.provider_name,
            ai_client.model,
        )

    # Initialize TTS engine (sherpa → piper → browser fallback chain)
    tts = None
    if settings.tts_backend == "sherpa":
        try:
            sherpa_tts = SherpaTTS(
                model_dir=settings.sherpa_model_dir,
                speed=settings.sherpa_speed,
                num_threads=settings.sherpa_num_threads,
            )
            await sherpa_tts.initialize()
            tts = sherpa_tts
            logger.info(
                "sherpa-onnx TTS ready (model=%s, %d Hz)",
                sherpa_tts._model_type if hasattr(sherpa_tts, '_model_type') else 'auto',
                sherpa_tts.sample_rate,
            )
        except SherpaTTSError as exc:
            logger.warning(
                "sherpa-onnx TTS unavailable — trying Piper fallback. Error: %s", exc,
            )
            # Fall through to Piper
    if tts is None and settings.tts_backend in ("sherpa", "piper"):
        try:
            piper_tts = PiperTTS(
                executable=settings.piper_executable,
                model_path=settings.piper_model,
                config_path=settings.piper_model_config,
                speaker=settings.piper_speaker,
            )
            await piper_tts.initialize()
            tts = piper_tts
            logger.info(
                "Piper TTS ready (voice=%s, sample_rate=%d Hz)",
                settings.piper_model, piper_tts.sample_rate,
            )
        except PiperTTSError as exc:
            logger.warning(
                "Piper TTS also unavailable — falling back to browser SpeechSynthesis. "
                "Error: %s", exc,
            )
    if tts is None:
        logger.info("TTS: using browser SpeechSynthesis (no local engine available)")

    orchestrator = ConversationOrchestrator(transcriber, ai_client, tts)

    # PR 11: Initialize agent registry and register agents
    AgentRegistry.register(ChatAgent())
    AgentRegistry.register(InterviewAgent())
    logger.info("Agent registry initialized — %d agent(s) registered", len(AgentRegistry.list_agents()))

    # Store in app.state for route handlers
    # PR 5: Configure and start stale session cleanup
    state_manager.set_idle_timeout(settings.session_idle_timeout)
    await state_manager.start_cleanup_task()

    app.state.settings = settings
    app.state.transcriber = transcriber
    app.state.ai_client = ai_client
    app.state.orchestrator = orchestrator
    app.state.tts = tts

    yield

    logger.info("Shutting down AI services")
    await state_manager.stop_cleanup_task()
    await ai_client.close()
    logger.info("OmniSight backend shut down")


app = FastAPI(
    title="OmniSight",
    version="0.9.0",
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
    """Health check — includes AI provider connectivity and session stats."""
    ai_client = getattr(request.app.state, "ai_client", None)
    ai_ok = await ai_client.check_health() if ai_client else False
    provider = ai_client.provider_name if ai_client else "none"
    active_sessions = await state_manager.get_session_count()
    return {
        "status": "ok",
        "version": "0.9.0",
        "ai_provider": provider,
        "ai_available": ai_ok,
        "active_sessions": active_sessions,
        "uptime_seconds": round(time.time() - _start_time, 1),
    }
