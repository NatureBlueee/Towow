"""
AToA 应用商城 — 联邦路由层。

核心价值：用户使用任何一个应用的入口，都能享受到所有应用的价值。
不是"推荐你去用另一个应用"，而是"直接在当前界面给到其他应用的 Agent 产出的价值"。

技术实现：
- 应用注册：每个 AToA 应用启动时注册到 App Store
- 信号路由：当任何应用发起需求，路由到所有注册的应用
- 联邦适配器：聚合所有应用的 Agent 到统一的 ProfileDataSource
- 跨应用协商：一个需求可以得到来自多个应用的 Agent 响应

启动：
    cd apps/app_store
    TOWOW_ANTHROPIC_API_KEY=sk-ant-... uvicorn backend.app:app --reload --port 8200
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .registry import AppRegistry, RegisteredApp
from .federation import FederatedAdapter

logger = logging.getLogger(__name__)


# ============ 请求/响应模型 ============

class RegisterAppRequest(BaseModel):
    app_id: str
    app_name: str
    base_url: str
    scene_id: str = ""
    scene_name: str = ""
    description: str = ""

class DiscoverAppRequest(BaseModel):
    base_url: str

class FederatedDemandRequest(BaseModel):
    intent: str
    user_id: str = "anonymous"
    source_app: str = ""  # 发起需求的来源应用

class AppListResponse(BaseModel):
    apps: list[dict[str, Any]]
    total_agents: int

class FederatedNegotiationResponse(BaseModel):
    negotiation_id: str
    state: str
    demand_raw: str
    demand_formulated: Optional[str] = None
    participants: list[dict[str, Any]] = Field(default_factory=list)
    plan_output: Optional[str] = None
    center_rounds: int = 0
    cross_app_agents: list[dict[str, Any]] = Field(default_factory=list)


# ============ WebSocket 管理 ============

class SimpleWSManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, ws: WebSocket, channel: str) -> None:
        await ws.accept()
        self._connections.setdefault(channel, []).append(ws)

    async def disconnect(self, ws: WebSocket, channel: str) -> None:
        if channel in self._connections:
            self._connections[channel] = [c for c in self._connections[channel] if c != ws]

    async def broadcast(self, channel: str, message: dict) -> None:
        if channel not in self._connections:
            return
        dead = []
        for ws in self._connections[channel]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[channel] = [c for c in self._connections[channel] if c != ws]


class FederatedEventPusher:
    def __init__(self, ws_manager: SimpleWSManager):
        self._ws = ws_manager

    async def push(self, event: Any) -> None:
        channel = f"negotiation:{event.negotiation_id}"
        await self._ws.broadcast(channel, event.to_dict())

    async def push_many(self, events: list) -> None:
        for event in events:
            await self.push(event)


# ============ 应用工厂 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App Store 启动初始化。"""
    from towow import (
        EngineBuilder,
        CenterCoordinatorSkill,
        DemandFormulationSkill,
        OfferGenerationSkill,
        SubNegotiationSkill,
        GapRecursionSkill,
    )

    # 注册表
    registry = AppRegistry()
    app.state.registry = registry

    # LLM 客户端
    api_key = os.environ.get("TOWOW_ANTHROPIC_API_KEY", "")
    llm_client = None
    if api_key:
        from towow.infra.llm_client import ClaudePlatformClient
        llm_client = ClaudePlatformClient(api_key=api_key)
        logger.info("App Store: 使用 Claude API")
    else:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from apps.shared.mock_llm import MockLLMClient
        llm_client = MockLLMClient()
        logger.info("App Store: 使用 Mock LLM")

    # 联邦适配器
    fed_adapter = FederatedAdapter(registry)
    fed_adapter.set_llm_client(llm_client)
    app.state.fed_adapter = fed_adapter

    # WebSocket
    ws_manager = SimpleWSManager()
    event_pusher = FederatedEventPusher(ws_manager)

    # 引擎
    import numpy as np
    from towow.hdc.resonance import CosineResonanceDetector
    from towow.core.engine import NegotiationEngine

    try:
        from towow.hdc.encoder import EmbeddingEncoder
        encoder = EmbeddingEncoder()
    except Exception:
        class StubEncoder:
            async def encode(self, text: str):
                return np.random.randn(128).astype(np.float32)
            async def batch_encode(self, texts: list[str]):
                return [np.random.randn(128).astype(np.float32) for _ in texts]
        encoder = StubEncoder()

    engine = NegotiationEngine(
        encoder=encoder,
        resonance_detector=CosineResonanceDetector(),
        event_pusher=event_pusher,
    )
    app.state.engine = engine
    app.state.llm_client = llm_client
    app.state.ws_manager = ws_manager
    app.state.sessions = {}
    app.state.tasks = {}

    # Skills
    app.state.skills = {
        "center": CenterCoordinatorSkill(),
        "formulation": DemandFormulationSkill(),
        "offer": OfferGenerationSkill(),
        "sub_negotiation": SubNegotiationSkill(),
        "gap_recursion": GapRecursionSkill(),
    }

    # 自动发现预设应用
    default_apps = os.environ.get("ATOA_APPS", "").split(",")
    for url in default_apps:
        url = url.strip()
        if url:
            discovered = await registry.discover_app(url)
            if discovered:
                registry.register(discovered)

    logger.info("App Store 启动完成")
    yield

    for task in app.state.tasks.values():
        if not task.done():
            task.cancel()
    logger.info("App Store 关闭")


def create_store_app() -> FastAPI:
    application = FastAPI(
        title="AToA 应用商城",
        description="通爻 AToA 应用生态的联邦路由层 — 跨应用共振",
        version="1.0.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ============ 应用管理 API ============

    @application.post("/api/apps/register")
    async def register_app(req: RegisterAppRequest, request: Request):
        """注册一个 AToA 应用到 App Store。"""
        registry = request.app.state.registry
        reg_app = RegisteredApp(
            app_id=req.app_id,
            app_name=req.app_name,
            base_url=req.base_url,
            scene_id=req.scene_id,
            scene_name=req.scene_name,
            description=req.description,
        )
        registry.register(reg_app)
        return {"status": "ok", "app_id": req.app_id, "message": f"{req.app_name} 注册成功"}

    @application.post("/api/apps/discover")
    async def discover_app(req: DiscoverAppRequest, request: Request):
        """自动发现并注册应用（调用应用的 /api/info 接口）。"""
        registry = request.app.state.registry
        discovered = await registry.discover_app(req.base_url)
        if not discovered:
            raise HTTPException(400, f"无法发现应用: {req.base_url}")
        registry.register(discovered)
        return {
            "status": "ok",
            "app": {
                "app_id": discovered.app_id,
                "app_name": discovered.app_name,
                "agent_count": discovered.agent_count,
            },
        }

    @application.get("/api/apps", response_model=AppListResponse)
    async def list_apps(request: Request):
        """列出所有已注册的应用。"""
        registry = request.app.state.registry
        apps_list = []
        total_agents = 0
        for app_info in registry.apps.values():
            apps_list.append({
                "app_id": app_info.app_id,
                "app_name": app_info.app_name,
                "base_url": app_info.base_url,
                "scene_name": app_info.scene_name,
                "description": app_info.description,
                "agent_count": app_info.agent_count,
            })
            total_agents += app_info.agent_count
        return AppListResponse(apps=apps_list, total_agents=total_agents)

    @application.get("/api/agents/all")
    async def list_all_agents(request: Request):
        """列出所有应用的所有 Agent（联邦视图）。"""
        registry = request.app.state.registry
        agents = registry.get_all_agents()
        return {"agents": agents, "count": len(agents)}

    # ============ 联邦协商 API ============

    @application.post("/api/federated/negotiate", response_model=FederatedNegotiationResponse, status_code=201)
    async def federated_negotiate(req: FederatedDemandRequest, request: Request):
        """
        发起联邦协商 — 需求信号跨所有注册应用传播。

        这是 App Store 的核心能力：
        一个需求发出后，所有应用的 Agent 都有机会响应。
        """
        from towow import NegotiationSession, DemandSnapshot
        from towow.core.models import TraceChain, generate_id

        state = request.app.state
        registry = state.registry
        fed_adapter = state.fed_adapter

        neg_id = generate_id("fed_neg")
        session = NegotiationSession(
            negotiation_id=neg_id,
            demand=DemandSnapshot(
                raw_intent=req.intent,
                user_id=req.user_id,
                scene_id="federated",
            ),
            trace=TraceChain(negotiation_id=neg_id),
        )
        state.sessions[neg_id] = session

        # 编码所有联邦 Agent 的向量
        agent_vectors = {}
        all_agents = registry.get_all_agents()
        for agent_info in all_agents:
            fed_id = agent_info["agent_id"]
            profile = await fed_adapter.get_profile(fed_id)
            text_parts = []
            if profile.get("skills"):
                skills = profile["skills"]
                if isinstance(skills, list):
                    text_parts.append(", ".join(skills))
            if profile.get("bio"):
                text_parts.append(profile["bio"])
            if profile.get("role"):
                text_parts.append(profile["role"])
            text = " ".join(text_parts) if text_parts else fed_id
            try:
                vec = await state.engine._encoder.encode(text)
                agent_vectors[fed_id] = vec
            except Exception:
                pass

        def _register(s):
            state.sessions[s.negotiation_id] = s

        run_defaults = {
            "adapter": fed_adapter,
            "llm_client": state.llm_client,
            "center_skill": state.skills["center"],
            "formulation_skill": state.skills["formulation"],
            "offer_skill": state.skills["offer"],
            "sub_negotiation_skill": state.skills["sub_negotiation"],
            "gap_recursion_skill": state.skills["gap_recursion"],
            "agent_vectors": agent_vectors or None,
            "k_star": min(len(all_agents), 8),
            "agent_display_names": fed_adapter.get_display_names(),
            "register_session": _register,
        }

        task = asyncio.create_task(
            _run_federated_negotiation(state.engine, session, run_defaults)
        )
        state.tasks[neg_id] = task

        # 标注跨应用 Agent 来源
        cross_app = [
            {"agent_id": a["agent_id"], "app_name": a["app_name"], "app_id": a["app_id"]}
            for a in all_agents
        ]

        return FederatedNegotiationResponse(
            negotiation_id=neg_id,
            state=session.state.value,
            demand_raw=req.intent,
            cross_app_agents=cross_app,
        )

    @application.get("/api/federated/negotiate/{neg_id}", response_model=FederatedNegotiationResponse)
    async def get_federated_negotiation(neg_id: str, request: Request):
        session = request.app.state.sessions.get(neg_id)
        if not session:
            raise HTTPException(404, f"协商 {neg_id} 不存在")

        participants = []
        for p in session.participants:
            entry = {
                "agent_id": p.agent_id,
                "display_name": p.display_name,
                "resonance_score": p.resonance_score,
                "state": p.state.value,
            }
            if p.offer:
                entry["offer_content"] = p.offer.content
            participants.append(entry)

        return FederatedNegotiationResponse(
            negotiation_id=session.negotiation_id,
            state=session.state.value,
            demand_raw=session.demand.raw_intent,
            demand_formulated=session.demand.formulated_text,
            participants=participants,
            plan_output=session.plan_output,
            center_rounds=session.center_rounds,
        )

    @application.post("/api/federated/negotiate/{neg_id}/confirm")
    async def confirm_federated(neg_id: str, request: Request):
        state = request.app.state
        engine = state.engine
        accepted = engine.confirm_formulation(neg_id)
        if not accepted:
            raise HTTPException(409, "引擎未在等待确认")
        return {"status": "ok"}

    # ============ WebSocket ============

    @application.websocket("/ws/{neg_id}")
    async def negotiation_ws(ws: WebSocket, neg_id: str):
        state = ws.app.state
        session = state.sessions.get(neg_id)
        if not session:
            await ws.close(code=4004, reason="协商不存在")
            return

        channel = f"negotiation:{neg_id}"
        await state.ws_manager.connect(ws, channel)

        for event_dict in list(session.event_history):
            try:
                await ws.send_json(event_dict)
            except Exception:
                await state.ws_manager.disconnect(ws, channel)
                return

        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            await state.ws_manager.disconnect(ws, channel)

    # ============ 静态文件 ============

    frontend_path = Path(__file__).resolve().parent.parent / "frontend"
    if frontend_path.exists():
        @application.get("/")
        async def index():
            index_file = frontend_path / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            return HTMLResponse("<h1>App Store 前端加载中...</h1>")

        application.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    return application


async def _run_federated_negotiation(engine, session, defaults):
    from towow import NegotiationState
    try:
        async def auto_confirm():
            for _ in range(120):
                await asyncio.sleep(0.5)
                if engine.is_awaiting_confirmation(session.negotiation_id):
                    engine.confirm_formulation(session.negotiation_id)
                    return
        confirm_task = asyncio.create_task(auto_confirm())
        await engine.start_negotiation(session=session, **defaults)
        confirm_task.cancel()
    except Exception as e:
        logger.error("联邦协商 %s 失败: %s", session.negotiation_id, e, exc_info=True)
        session.metadata["error"] = str(e)
        if session.state != NegotiationState.COMPLETED:
            session.state = NegotiationState.COMPLETED


app = create_store_app()
