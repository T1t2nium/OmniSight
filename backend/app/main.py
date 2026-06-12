"""OmniSight Backend - AI Visual Conversation Assistant."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.ws import router as ws_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logging.info("OmniSight backend starting up")
    yield
    logging.info("OmniSight backend shutting down")


app = FastAPI(
    title="OmniSight",
    version="0.1.0",
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
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}
