"""
Towow 统一后端 — Auth + V1 Engine + App Store Network.

单进程服务三个子系统，路由布局：
  /api/auth/*     ← SecondMe OAuth2 (从 app.py 提取)
  /v1/api/*       ← V1 协商引擎 (现有 APIRouter)
  /v1/ws/*        ← V1 WebSocket
  /store/api/*    ← App Store 网络
  /store/ws/*     ← App Store WebSocket
  /health         ← 健康检查

启动：
    cd backend && source venv/bin/activate
    TOWOW_ANTHROPIC_API_KEY=sk-ant-... uvicorn server:app --reload --port 8080
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend/ and project root are on sys.path so imports resolve
# when running as: uvicorn backend.server:app  (from project root)
# or as:          uvicorn server:app            (from backend/)
_backend_dir = Path(__file__).resolve().parent
_project_dir = _backend_dir.parent
for p in (str(_backend_dir), str(_project_dir)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Load .env
from dotenv import load_dotenv
load_dotenv(_backend_dir / ".env")

logger = logging.getLogger(__name__)


# ============================================================
# Lifespan — initialize all three subsystems
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Towow unified backend starting...")

    # ── 0. Database ──────────────────────────────────────
    from database import get_engine
    get_engine()  # 自动建表 (NegotiationHistory, NegotiationOffer, User)

    # ── 1. Auth subsystem ──────────────────────────────────
    from backend.session_store import get_session_store, close_session_store
    from backend.agent_manager import get_agent_manager

    session_store = await get_session_store()
    app.state.session_store = session_store
    logger.info(f"Session store: {session_store.store_type}")

    manager = get_agent_manager()
    app.state.agent_manager = manager
    logger.info(f"Agent manager: {len(manager.agents_config)} users loaded")

    # ── 2. V1 Engine subsystem ─────────────────────────────
    from towow.infra.config import TowowConfig
    from towow.infra.event_pusher import WebSocketEventPusher
    from websocket_manager import WebSocketManager

    config = TowowConfig()
    app.state.v1_config = config

    # V1 in-memory stores
    app.state.scenes = {}
    app.state.sessions = {}
    app.state.tasks = {}
    app.state.skills = {}

    # 基础设施层：AgentRegistry（唯一实例，全网络共享）
    from towow.infra import AgentRegistry
    registry = AgentRegistry()
    app.state.agent_registry = registry

    # V1 WebSocket
    ws_manager = WebSocketManager()
    app.state.ws_manager = ws_manager
    event_pusher = WebSocketEventPusher(ws_manager)
    app.state.event_pusher = event_pusher

    # V1 Encoder — lazy, may fail
    encoder = None
    try:
        from towow.hdc.encoder import EmbeddingEncoder
        encoder = EmbeddingEncoder()
        logger.info("V1: EmbeddingEncoder initialized")
    except Exception as e:
        logger.warning(f"V1: EmbeddingEncoder not available: {e}")

    app.state.encoder = encoder

    # V1 Resonance
    from towow.hdc.resonance import CosineResonanceDetector
    resonance_detector = CosineResonanceDetector()

    # V1 Engine
    from towow.core.engine import NegotiationEngine
    engine = NegotiationEngine(
        encoder=encoder or _stub_encoder(),
        resonance_detector=resonance_detector,
        event_pusher=event_pusher,
        offer_timeout_s=config.offer_timeout_seconds,
    )
    app.state.engine = engine

    # V1 LLM client (multi-key round-robin)
    v1_keys = config.get_api_keys()
    if v1_keys:
        from towow.infra.llm_client import ClaudePlatformClient
        llm_client = ClaudePlatformClient(
            api_key=v1_keys,
            model=config.default_model,
            max_tokens=config.max_tokens,
            base_url=config.get_base_url(),
        )
        app.state.llm_client = llm_client
        logger.info("V1: ClaudePlatformClient initialized (%d key(s))", len(v1_keys))
    else:
        app.state.llm_client = None
        logger.warning("V1: No TOWOW_ANTHROPIC_API_KEY(S) — LLM calls will fail")

    # Default adapter（给 demo/匿名用户的 LLM 通道）
    if v1_keys:
        from towow.adapters.claude_adapter import ClaudeAdapter
        default_adapter = ClaudeAdapter(
            api_key=v1_keys[0],
            model=config.default_model,
            base_url=config.get_base_url(),
        )
        registry.set_default_adapter(default_adapter)
    else:
        default_adapter = None

    # V1 Skills
    try:
        from towow.skills import (
            CenterCoordinatorSkill,
            DemandFormulationSkill,
            GapRecursionSkill,
            OfferGenerationSkill,
            SubNegotiationSkill,
        )
        app.state.skills = {
            "formulation": DemandFormulationSkill(),
            "offer": OfferGenerationSkill(),
            "center": CenterCoordinatorSkill(),
            "sub_negotiation": SubNegotiationSkill(),
            "gap_recursion": GapRecursionSkill(),
        }
        logger.info("V1: Skills initialized")
    except Exception as e:
        logger.warning(f"V1: Skills not available: {e}")

    app.state.config = config

    # V1 Demo scene
    _seed_demo_scene(app, registry, default_adapter)

    # ── 3. App Store subsystem ─────────────────────────────
    _init_app_store(app, config, registry)

    # Pre-encode Store agent vectors (async, needs to run in lifespan)
    await _encode_store_agent_vectors(app, registry)

    logger.info("Towow unified backend ready")
    yield

    # ── Cleanup ────────────────────────────────────────────
    # V1 tasks
    for task in app.state.tasks.values():
        if not task.done():
            task.cancel()

    # Store tasks
    for task in getattr(app.state, "store_tasks", {}).values():
        if not task.done():
            task.cancel()

    # Store OAuth2 client
    if getattr(app.state, "store_oauth2_client", None):
        await app.state.store_oauth2_client.close()

    # Session store
    await close_session_store()
    logger.info("Towow unified backend shutdown")


def _restore_secondme_users(registry) -> None:
    """启动时从 data/secondme_users/ 恢复已注册的 SecondMe 用户。

    每个用户一个 JSON 文件（{agent_id}.json），包含 profile + scene_ids。
    token 不持久化——用户需要重新登录才能使用 chat 等功能，但画像信息会保留在网络中。
    """
    import json as _json
    users_dir = _project_dir / "data" / "secondme_users"
    if not users_dir.exists():
        return

    restored = 0
    for fp in sorted(users_dir.glob("*.json")):
        try:
            data = _json.loads(fp.read_text(encoding="utf-8"))
            agent_id = data["agent_id"]
            profile = data["profile"]
            scene_ids = data.get("scene_ids", [])

            registry.register_agent(
                agent_id=agent_id,
                adapter=None,  # 无 token，chat 不可用，但画像可见
                source="SecondMe",
                scene_ids=scene_ids,
                display_name=profile.get("name", agent_id),
                profile_data=profile,
            )
            restored += 1
        except Exception as e:
            logger.warning("恢复 SecondMe 用户失败 %s: %s", fp.name, e)

    if restored:
        logger.info("恢复 %d 个 SecondMe 用户 (from %s)", restored, users_dir)


def _init_app_store(app: FastAPI, config, registry) -> None:
    """Synchronous App Store initialization (called from lifespan)."""
    from apps.app_store.backend.scene_registry import SceneContext, SceneRegistry

    scene_registry = SceneRegistry()
    app.state.store_scene_registry = scene_registry

    # LLM client (multi-key round-robin, reuse V1 config)
    store_keys = config.get_api_keys()
    llm_client = None
    if store_keys:
        from towow.infra.llm_client import ClaudePlatformClient
        llm_client = ClaudePlatformClient(api_key=store_keys, base_url=config.get_base_url())
        logger.info("Store: ClaudePlatformClient initialized (%d key(s), base_url=%s)",
                     len(store_keys), config.get_base_url() or "default")
    else:
        try:
            from apps.shared.mock_llm import MockLLMClient
            llm_client = MockLLMClient()
            logger.warning("Store: ⚠️  Using MockLLMClient — TOWOW_ANTHROPIC_API_KEY(S) not set! "
                           "All Center outputs will be hardcoded templates.")
        except ImportError:
            logger.warning("Store: No LLM client available")
    app.state.store_llm_client = llm_client

    # Load sample agents (into shared registry)
    from apps.app_store.backend.app import SAMPLE_APPS, _load_sample_agents
    apps_dir = Path(__file__).resolve().parent.parent / "apps"
    _load_sample_agents(registry, apps_dir, llm_client)

    # Register sample scenes
    for app_id, sample_config in SAMPLE_APPS.items():
        scene_registry.register(sample_config["scene"])

    # Store WebSocket
    from apps.app_store.backend.app import SimpleWSManager, NetworkEventPusher
    store_ws = SimpleWSManager()
    store_event_pusher = NetworkEventPusher(store_ws)
    app.state.store_ws_manager = store_ws

    # Store Engine (separate instance from V1)
    import numpy as np
    from towow.hdc.resonance import CosineResonanceDetector
    from towow.core.engine import NegotiationEngine

    encoder = app.state.encoder  # share encoder with V1
    if encoder is None:
        class StubEncoder:
            async def encode(self, text: str):
                return np.random.randn(128).astype(np.float32)
            async def batch_encode(self, texts: list[str]):
                return [np.random.randn(128).astype(np.float32) for _ in texts]
        encoder = StubEncoder()

    store_engine = NegotiationEngine(
        encoder=encoder,
        resonance_detector=CosineResonanceDetector(),
        event_pusher=store_event_pusher,
    )
    app.state.store_engine = store_engine

    # Agent vectors — populated by _encode_store_agent_vectors() in lifespan
    app.state.store_agent_vectors = {}

    app.state.store_sessions = {}
    app.state.store_tasks = {}
    app.state.store_user_tokens = {}

    # Store Skills
    try:
        from towow.skills import (
            CenterCoordinatorSkill,
            DemandFormulationSkill,
            OfferGenerationSkill,
            SubNegotiationSkill,
            GapRecursionSkill,
        )
        app.state.store_skills = {
            "center": CenterCoordinatorSkill(),
            "formulation": DemandFormulationSkill(),
            "offer": OfferGenerationSkill(),
            "sub_negotiation": SubNegotiationSkill(),
            "gap_recursion": GapRecursionSkill(),
        }
    except Exception as e:
        logger.warning(f"Store: Skills not available: {e}")
        app.state.store_skills = {}

    # Store OAuth2 client (optional)
    app.state.store_oauth2_client = None
    try:
        client_id = os.environ.get("SECONDME_CLIENT_ID", "")
        if client_id:
            from backend.oauth2_client import SecondMeOAuth2Client, OAuth2Config
            oauth_config = OAuth2Config.from_env()
            app.state.store_oauth2_client = SecondMeOAuth2Client(oauth_config)
            logger.info("Store: SecondMe OAuth2 enabled")
    except Exception as e:
        logger.warning(f"Store: SecondMe OAuth2 not configured: {e}")

    # 恢复已持久化的 SecondMe 用户
    _restore_secondme_users(registry)

    logger.info(
        "Store: %d agents, %d scenes",
        registry.agent_count,
        len(scene_registry.all_scenes),
    )


async def _encode_store_agent_vectors(app: FastAPI, registry) -> None:
    """Pre-encode vectors for all Store agents so resonance works.

    Encodes in batches to control memory usage on constrained environments.
    """
    encoder = app.state.encoder
    if encoder is None:
        logger.warning("Store vectors: no encoder available, skipping")
        return

    vectors = app.state.store_agent_vectors
    encoded = 0
    skipped = 0

    # Collect texts first, then encode in batches
    to_encode: list[tuple[str, str]] = []  # (agent_id, text)

    for aid in registry.all_agent_ids:
        if aid in vectors:
            continue
        try:
            profile = await registry.get_profile(aid)
        except Exception:
            skipped += 1
            continue

        text_parts = []
        for field in ("self_introduction", "bio", "role"):
            if profile.get(field):
                text_parts.append(str(profile[field]))
        if profile.get("skills"):
            skills = profile["skills"]
            if isinstance(skills, list):
                text_parts.append(", ".join(str(s) for s in skills))
        for shade in profile.get("shades", []):
            desc = shade.get("description", "") or shade.get("name", "")
            if desc:
                text_parts.append(desc)

        text = " ".join(text_parts) if text_parts else aid
        to_encode.append((aid, text))

    # Batch encode to reduce memory spikes (batch_size=32)
    BATCH_SIZE = 32
    logger.info("Store vectors: encoding %d agents in batches of %d...", len(to_encode), BATCH_SIZE)

    for i in range(0, len(to_encode), BATCH_SIZE):
        batch = to_encode[i:i + BATCH_SIZE]
        batch_texts = [text for _, text in batch]
        try:
            batch_vecs = await encoder.batch_encode(batch_texts)
            for (aid, _), vec in zip(batch, batch_vecs):
                vectors[aid] = vec
                encoded += 1
        except Exception as e:
            logger.warning("Store vectors: batch %d failed, falling back to single: %s", i // BATCH_SIZE, e)
            # Fallback: encode one by one
            for aid, text in batch:
                try:
                    vec = await encoder.encode(text)
                    vectors[aid] = vec
                    encoded += 1
                except Exception as e2:
                    logger.warning("Store vectors: failed to encode %s: %s", aid, e2)
                    skipped += 1

        if (i + BATCH_SIZE) % 128 == 0:
            logger.info("Store vectors: progress %d/%d", min(i + BATCH_SIZE, len(to_encode)), len(to_encode))

    logger.info("Store vectors: encoded %d agents, skipped %d (total in dict: %d)",
                encoded, skipped, len(vectors))


def _seed_demo_scene(app: FastAPI, registry, default_adapter) -> None:
    """Pre-seed V1 demo scene with 5 agents."""
    from towow.core.models import SceneDefinition, SourceType

    scene_id = "scene_default"
    if scene_id in app.state.scenes:
        return

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
        # 注册到 AgentRegistry（唯一数据源）
        adapter = default_adapter if default_adapter else None
        if adapter:
            registry.register_agent(
                agent_id=agent_id,
                adapter=adapter,
                source=source_type.value,
                scene_ids=[scene_id],
                display_name=display_name,
                profile_data=profile_data,
            )
        scene.agent_ids.append(agent_id)

    app.state.scenes[scene_id] = scene
    logger.info("V1: Demo scene seeded with %d agents", len(demo_agents))


def _stub_encoder():
    """Stub encoder for V1 when real encoder unavailable."""
    import numpy as np

    class StubEncoder:
        async def encode(self, text: str):
            return np.zeros(128, dtype=np.float32)

        async def batch_encode(self, texts: list[str]):
            return [np.zeros(128, dtype=np.float32) for _ in texts]

    return StubEncoder()


# ============================================================
# Create the unified FastAPI app
# ============================================================

def create_app() -> FastAPI:
    application = FastAPI(
        title="Towow Backend",
        description="Auth + V1 Negotiation Engine + App Store Network",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    allowed_origins = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:8080",
    ).split(",")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Health check ──
    @application.get("/health")
    async def health():
        return {"status": "ok"}

    # ── Auth routes (/api/auth/*) ──
    from backend.routers.auth import router as auth_router
    application.include_router(auth_router)

    # ── V1 Engine routes (/v1/api/*, /v1/ws/*) ──
    from towow.api.routes import router as v1_api_router, ws_router as v1_ws_router
    application.include_router(v1_api_router, prefix="/v1")
    application.include_router(v1_ws_router, prefix="/v1")

    # ── App Store routes (/store/api/*, /store/ws/*, /store/auth/*) ──
    from apps.app_store.backend.routers import (
        router as store_router,
        ws_router as store_ws_router,
    )
    application.include_router(store_router, prefix="/store")
    application.include_router(store_ws_router, prefix="/store")

    return application


app = create_app()
