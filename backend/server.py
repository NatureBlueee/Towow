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
load_dotenv(_backend_dir / ".env", override=False)  # Railway env vars take precedence

logger = logging.getLogger(__name__)


# ============================================================
# Lifespan — initialize all three subsystems
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Towow unified backend starting...")

    # ── 0. Persistent data directory ─────────────────────
    # In production (Railway), /app/data/ is a mounted persistent volume.
    # Ensure required sub-directories exist and sync immutable assets.
    _data_dir = _project_dir / "data"
    _data_dir.mkdir(parents=True, exist_ok=True)
    (_data_dir / "secondme_users").mkdir(exist_ok=True)

    # Sync pre-computed vectors from Docker image assets to persistent data dir.
    # This runs on every deploy so new agents get their vectors updated.
    _assets_vectors = Path("/app/assets/agent_vectors.npz")
    _data_vectors = _data_dir / "agent_vectors.npz"
    if _assets_vectors.exists():
        import shutil
        shutil.copy2(_assets_vectors, _data_vectors)
        logger.info("Synced agent vectors from assets to data dir")

    # ── 0b. Database ─────────────────────────────────────
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

    # Encoder — try local first, fallback to HF API
    encoder = None
    try:
        from towow.hdc.encoder import EmbeddingEncoder
        encoder = EmbeddingEncoder()
        logger.info("Encoder: local EmbeddingEncoder (backend=%s)", encoder._backend)
    except Exception as e:
        logger.info("Encoder: local not available (%s), trying HF API...", e)
        try:
            from towow.hdc.api_encoder import HuggingFaceAPIEncoder
            hf_token = os.environ.get("HF_API_TOKEN", "")
            encoder = HuggingFaceAPIEncoder(api_token=hf_token or None)
            logger.info("Encoder: HuggingFace API (token=%s)", "yes" if hf_token else "no")
        except Exception as e2:
            logger.warning("Encoder: no encoder available (%s)", e2)

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

    # V1 Demo scene — disabled, App Store uses real agents from JSON files
    # _seed_demo_scene(app, registry, default_adapter)

    # ── 2b. V2 Intent Field subsystem ────────────────────────
    from towow.field import MemoryField, BgeM3Encoder, SimHashProjector, EncodingPipeline
    field_encoder = BgeM3Encoder()
    field_projector = SimHashProjector(input_dim=field_encoder.dim)
    field_pipeline = EncodingPipeline(field_encoder, field_projector)
    field = MemoryField(field_pipeline)
    app.state.field = field
    logger.info("V2 Intent Field initialized (encoder=%s, dim=%d)", type(field_encoder).__name__, field_encoder.dim)

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


def _restore_playground_users(registry, scene_ids: list[str]) -> None:
    """启动时从 DB 恢复 Playground 用户到 AgentRegistry。

    与 _restore_secondme_users() 的关键区别：
    - SecondMe 恢复: adapter=None（token 过期，chat 不可用）
    - Playground 恢复: adapter=default_adapter（用平台 Claude，Offer 可用）
    """
    from database import get_playground_users

    users = get_playground_users()
    default_adapter = registry.default_adapter
    restored = 0

    for user in users:
        if user.agent_id in registry.all_agent_ids:
            continue
        profile_data = {
            "raw_text": user.raw_profile_text or "",
            "display_name": user.display_name,
            "source": "playground",
        }
        registry.register_agent(
            agent_id=user.agent_id,
            adapter=default_adapter,
            source="playground",
            scene_ids=list(scene_ids),
            display_name=user.display_name,
            profile_data=profile_data,
        )
        restored += 1

    if restored:
        logger.info("恢复 %d 个 Playground 用户 (adapter=%s)",
                     restored, type(default_adapter).__name__ if default_adapter else "None")


def _init_app_store(app: FastAPI, config, registry) -> None:
    """Synchronous App Store initialization (called from lifespan)."""
    from apps.app_store.backend.scene_registry import SceneContext, SceneRegistry

    scene_registry = SceneRegistry()
    app.state.store_scene_registry = scene_registry

    # LLM client (multi-key round-robin, reuse V1 config)
    store_keys = config.get_api_keys()
    base_url = config.get_base_url()
    # WARNING-level so it always appears in Railway logs
    key_previews = [f"...{k[-4:]}" for k in store_keys] if store_keys else ["NONE"]
    logger.warning(
        "Store LLM config: keys=%s, base_url=%s, source=%s",
        key_previews, base_url or "api.anthropic.com (default)",
        "TOWOW_ANTHROPIC_API_KEYS" if config.anthropic_api_keys else
        "TOWOW_ANTHROPIC_API_KEY" if config.anthropic_api_key else "NONE",
    )
    llm_client = None
    if store_keys:
        from towow.infra.llm_client import ClaudePlatformClient
        llm_client = ClaudePlatformClient(api_key=store_keys, base_url=base_url)
        logger.info("Store: ClaudePlatformClient initialized (%d key(s), base_url=%s)",
                     len(store_keys), base_url or "default")
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

    # 恢复 Playground 用户 (ADR-009)
    all_scene_ids = [s["scene_id"] for s in scene_registry.list_scenes()]
    _restore_playground_users(registry, all_scene_ids)

    logger.info(
        "Store: %d agents, %d scenes",
        registry.agent_count,
        len(scene_registry.all_scenes),
    )


async def _encode_store_agent_vectors(app: FastAPI, registry) -> None:
    """Load pre-computed agent vectors, or encode live if local model available.

    Priority:
    1. Pre-computed .npz file (fast, no model needed — production path)
    2. Live encoding with local EmbeddingEncoder (dev path)
    3. Skip resonance (degraded — API encoder can't batch-encode 400+ agents)
    """
    vectors = app.state.store_agent_vectors

    # 1. Try loading pre-computed vectors
    npz_path = _project_dir / "data" / "agent_vectors.npz"
    if npz_path.exists():
        try:
            data = __import__("numpy").load(str(npz_path), allow_pickle=True)
            agent_ids = data["agent_ids"]
            vecs = data["vectors"]
            loaded = 0
            for aid, vec in zip(agent_ids, vecs):
                aid_str = str(aid)
                if aid_str in registry.all_agent_ids:
                    vectors[aid_str] = vec
                    loaded += 1
            logger.info("Store vectors: loaded %d/%d from %s", loaded, len(agent_ids), npz_path.name)
            if loaded > 0:
                return
        except Exception as e:
            logger.warning("Store vectors: failed to load .npz: %s", e)

    # 2. Try live encoding with local model (dev only — needs sentence-transformers)
    encoder = app.state.encoder
    if encoder is None:
        logger.warning("Store vectors: no encoder and no pre-computed file, resonance disabled")
        return

    # Check if this is a local encoder (not API — API is too slow for 400+ agents)
    encoder_type = type(encoder).__name__
    if "API" in encoder_type:
        logger.info("Store vectors: API encoder detected, skipping batch pre-encoding (use precompute_vectors.py)")
        return

    encoded = 0
    skipped = 0
    to_encode: list[tuple[str, str]] = []

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
        # Playground 用户 fallback 到 raw_text (ADR-009)
        if not text_parts:
            raw_text = profile.get("raw_text", "")
            if raw_text:
                text_parts.append(raw_text[:500])
        text = " ".join(text_parts) if text_parts else aid
        to_encode.append((aid, text))

    BATCH_SIZE = 32
    logger.info("Store vectors: live encoding %d agents (batch=%d)...", len(to_encode), BATCH_SIZE)
    for i in range(0, len(to_encode), BATCH_SIZE):
        batch = to_encode[i:i + BATCH_SIZE]
        for aid, text in batch:
            try:
                vec = await encoder.encode(text)
                vectors[aid] = vec
                encoded += 1
            except Exception as e:
                logger.warning("Store vectors: failed %s: %s", aid, e)
                skipped += 1

    logger.info("Store vectors: encoded %d, skipped %d (total: %d)", encoded, skipped, len(vectors))


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

    # ── Intent Field routes (/field/api/*) ──
    from towow.field.routes import field_router
    application.include_router(field_router)

    # ── App Store routes (/store/api/*, /store/ws/*, /store/auth/*) ──
    from apps.app_store.backend.routers import (
        router as store_router,
        ws_router as store_ws_router,
    )
    application.include_router(store_router, prefix="/store")
    application.include_router(store_ws_router, prefix="/store")

    return application


app = create_app()
