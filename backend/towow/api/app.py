"""
FastAPI application for Towow V1 negotiation system.

Runs on port 8081 (separate from the existing app.py on 8080).
Start with: uvicorn towow.api.app:app --reload --port 8081
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from towow.core.engine import NegotiationEngine
from towow.infra.config import TowowConfig
from towow.infra.event_pusher import WebSocketEventPusher

from .routes import router, ws_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all dependencies on startup, clean up on shutdown."""
    config = TowowConfig()

    # In-memory stores
    app.state.scenes = {}
    app.state.sessions = {}
    app.state.agents = {}
    app.state.profiles = {}
    app.state.tasks = {}
    app.state.skills = {}

    # WebSocket manager
    from websocket_manager import WebSocketManager
    ws_manager = WebSocketManager()
    app.state.ws_manager = ws_manager

    # Event pusher
    event_pusher = WebSocketEventPusher(ws_manager)
    app.state.event_pusher = event_pusher

    # Encoder — lazy, may fail if sentence-transformers not available
    encoder = None
    try:
        from towow.hdc.encoder import EmbeddingEncoder
        encoder = EmbeddingEncoder()
        logger.info("EmbeddingEncoder initialized")
    except Exception as e:
        logger.warning(f"EmbeddingEncoder not available, resonance disabled: {e}")

    app.state.encoder = encoder

    # Resonance detector
    from towow.hdc.resonance import CosineResonanceDetector
    resonance_detector = CosineResonanceDetector()

    # Engine
    engine = NegotiationEngine(
        encoder=encoder or _stub_encoder(),
        resonance_detector=resonance_detector,
        event_pusher=event_pusher,
        offer_timeout_s=config.offer_timeout_seconds,
    )
    app.state.engine = engine

    # Platform LLM client (for Center)
    if config.anthropic_api_key:
        from towow.infra.llm_client import ClaudePlatformClient
        llm_client = ClaudePlatformClient(
            api_key=config.anthropic_api_key,
            model=config.default_model,
            max_tokens=config.max_tokens,
        )
        app.state.llm_client = llm_client
        logger.info("ClaudePlatformClient initialized")
    else:
        app.state.llm_client = None
        logger.warning("No TOWOW_ANTHROPIC_API_KEY set — LLM calls will fail")

    # Default adapter (for users without their own LLM)
    # Pass profiles dict by reference — agent registrations auto-visible to adapter
    if config.anthropic_api_key:
        from towow.adapters.claude_adapter import ClaudeAdapter
        adapter = ClaudeAdapter(
            api_key=config.anthropic_api_key,
            model=config.default_model,
            profiles=app.state.profiles,
        )
        app.state.adapter = adapter
    else:
        app.state.adapter = None

    # Skills — import and create if available
    try:
        from towow.skills import (
            CenterCoordinatorSkill,
            DemandFormulationSkill,
            OfferGenerationSkill,
        )
        app.state.skills = {
            "formulation": DemandFormulationSkill(),
            "offer": OfferGenerationSkill(),
            "center": CenterCoordinatorSkill(),
        }
        logger.info("Skills initialized: formulation, offer, center")
    except Exception as e:
        logger.warning(f"Skills not available: {e}")

    app.state.config = config

    logger.info("Towow V1 API started")
    yield

    # Cleanup: cancel any running tasks
    for task in app.state.tasks.values():
        if not task.done():
            task.cancel()
    logger.info("Towow V1 API shutdown")


def _stub_encoder():
    """Stub encoder when real encoder is unavailable."""
    import numpy as np

    class StubEncoder:
        async def encode(self, text: str):
            return np.zeros(128, dtype=np.float32)

        async def batch_encode(self, texts: list[str]):
            return [np.zeros(128, dtype=np.float32) for _ in texts]

    return StubEncoder()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Towow V1 API",
        description="AI Agent collaboration platform — negotiation engine",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    app.include_router(ws_router)

    return app


app = create_app()
