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

    _seed_demo_scene(app)

    logger.info("Towow V1 API started")
    yield

    # Cleanup: cancel any running tasks
    for task in app.state.tasks.values():
        if not task.done():
            task.cancel()
    logger.info("Towow V1 API shutdown")


def _seed_demo_scene(app: FastAPI) -> None:
    """Pre-seed a demo scene with 5 agents for frontend integration."""
    from towow.core.models import AgentIdentity, SceneDefinition, SourceType

    scene_id = "scene_default"
    if scene_id in app.state.scenes:
        return  # Idempotent

    scene = SceneDefinition(
        scene_id=scene_id,
        name="AI Startup Co-founder Matching",
        description="Find collaborators for AI product development",
        organizer_id="system",
        expected_responders=3,
    )

    demo_agents = [
        ("agent_alice", "Alice", SourceType.CLAUDE,
         {"skills": ["python", "machine-learning", "data-science"],
          "bio": "ML engineer with 5 years experience in NLP and recommendation systems"}),
        ("agent_bob", "Bob", SourceType.SECONDME,
         {"skills": ["frontend", "react", "design"],
          "bio": "Full-stack developer specializing in React and user experience design"}),
        ("agent_carol", "Carol", SourceType.TEMPLATE,
         {"skills": ["blockchain", "smart-contracts", "solidity"],
          "bio": "Blockchain developer experienced in DeFi and smart contract auditing"}),
        ("agent_dave", "Dave", SourceType.CLAUDE,
         {"skills": ["devops", "kubernetes", "aws"],
          "bio": "DevOps engineer managing large-scale cloud infrastructure"}),
        ("agent_eve", "Eve", SourceType.CUSTOM,
         {"skills": ["product-management", "growth", "analytics"],
          "bio": "Product manager with experience in AI-powered SaaS products"}),
    ]

    for agent_id, display_name, source_type, profile_data in demo_agents:
        identity = AgentIdentity(
            agent_id=agent_id,
            display_name=display_name,
            source_type=source_type,
            scene_id=scene_id,
            metadata=profile_data,
        )
        app.state.agents[agent_id] = identity
        app.state.profiles[agent_id] = profile_data
        scene.agent_ids.append(agent_id)

    app.state.scenes[scene_id] = scene
    logger.info("Demo scene seeded: %s with %d agents", scene_id, len(demo_agents))


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
