"""
AToA 应用工厂 — 创建标准化的 FastAPI 应用。

每个 AToA 应用的后端结构相同：
1. 加载 Agent 数据（JSON）
2. 初始化 SDK 引擎
3. 提供 REST API + WebSocket
4. 提供静态前端文件

用法：
    from apps.shared import create_app, AppConfig
    config = AppConfig(
        app_name="黑客松组队",
        data_dir="data",
        frontend_dir="frontend",
        port=8100,
    )
    app = create_app(config)
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============ 配置 ============

@dataclass
class AppConfig:
    """AToA 应用配置。"""
    app_name: str = "AToA 应用"
    app_description: str = ""
    data_dir: str = "data"
    frontend_dir: str = "frontend"
    port: int = 8100
    scene_id: str = ""
    scene_name: str = ""
    scene_description: str = ""
    expected_responders: int = 5


# ============ 请求/响应模型 ============

class SubmitDemandRequest(BaseModel):
    intent: str
    user_id: str = "anonymous"

class ConfirmRequest(BaseModel):
    confirmed_text: Optional[str] = None

class NegotiationResponse(BaseModel):
    negotiation_id: str
    state: str
    demand_raw: str
    demand_formulated: Optional[str] = None
    participants: list[dict[str, Any]] = Field(default_factory=list)
    plan_output: Optional[str] = None
    center_rounds: int = 0

class AgentListResponse(BaseModel):
    agents: list[dict[str, Any]]
    count: int


# ============ 简易 WebSocket 管理 ============

class SimpleWSManager:
    """简化的 WebSocket 管理器，适用于单应用场景。"""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, ws: WebSocket, channel: str) -> None:
        await ws.accept()
        if channel not in self._connections:
            self._connections[channel] = []
        self._connections[channel].append(ws)

    async def disconnect(self, ws: WebSocket, channel: str) -> None:
        if channel in self._connections:
            self._connections[channel] = [
                c for c in self._connections[channel] if c != ws
            ]

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
            self._connections[channel] = [
                c for c in self._connections[channel] if c != ws
            ]


class SimpleEventPusher:
    """基于 SimpleWSManager 的事件推送器。"""

    def __init__(self, ws_manager: SimpleWSManager):
        self._ws = ws_manager

    async def push(self, event: Any) -> None:
        channel = f"negotiation:{event.negotiation_id}"
        await self._ws.broadcast(channel, event.to_dict())

    async def push_many(self, events: list) -> None:
        for event in events:
            await self.push(event)


# ============ 应用工厂 ============

def create_app(config: AppConfig) -> FastAPI:
    """创建标准化的 AToA 应用。"""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用启动时初始化所有依赖。"""
        from towow import (
            EngineBuilder,
            CenterCoordinatorSkill,
            DemandFormulationSkill,
            OfferGenerationSkill,
            SubNegotiationSkill,
            GapRecursionSkill,
            NullEventPusher,
        )
        from .json_adapter import JSONFileAdapter

        # 数据目录
        data_dir = Path(config.data_dir)
        agents_json = data_dir / "agents.json"

        # LLM 客户端
        api_key = os.environ.get("TOWOW_ANTHROPIC_API_KEY", "")
        llm_client = None
        if api_key:
            from towow.infra.llm_client import ClaudePlatformClient
            llm_client = ClaudePlatformClient(api_key=api_key)
            logger.info("使用 Claude API（真实 LLM）")
        else:
            from .mock_llm import MockLLMClient
            llm_client = MockLLMClient()
            logger.info("使用 Mock LLM（开发模式）")

        # 适配器
        adapter = JSONFileAdapter(
            json_path=agents_json,
            llm_client=llm_client,
        )

        # WebSocket 管理
        ws_manager = SimpleWSManager()
        event_pusher = SimpleEventPusher(ws_manager)

        # 引擎
        try:
            engine, defaults = (
                EngineBuilder()
                .with_adapter(adapter)
                .with_llm_client(llm_client)
                .with_center_skill(CenterCoordinatorSkill())
                .with_formulation_skill(DemandFormulationSkill())
                .with_offer_skill(OfferGenerationSkill())
                .with_sub_negotiation_skill(SubNegotiationSkill())
                .with_gap_recursion_skill(GapRecursionSkill())
                .with_event_pusher(event_pusher)
                .with_display_names(adapter.get_display_names())
                .with_k_star(config.expected_responders)
                .build()
            )
        except Exception as e:
            logger.warning("引擎初始化降级（无 encoder）: %s", e)
            # 降级：无 embedding encoder
            import numpy as np

            class StubEncoder:
                async def encode(self, text: str):
                    return np.random.randn(128).astype(np.float32)
                async def batch_encode(self, texts: list[str]):
                    return [np.random.randn(128).astype(np.float32) for _ in texts]

            from towow.hdc.resonance import CosineResonanceDetector
            from towow.core.engine import NegotiationEngine

            engine = NegotiationEngine(
                encoder=StubEncoder(),
                resonance_detector=CosineResonanceDetector(),
                event_pusher=event_pusher,
            )
            defaults = {
                "adapter": adapter,
                "llm_client": llm_client,
                "center_skill": CenterCoordinatorSkill(),
                "formulation_skill": DemandFormulationSkill(),
                "offer_skill": OfferGenerationSkill(),
                "sub_negotiation_skill": SubNegotiationSkill(),
                "gap_recursion_skill": GapRecursionSkill(),
                "agent_display_names": adapter.get_display_names(),
                "k_star": config.expected_responders,
            }

        # 编码 Agent 向量
        agent_vectors = {}
        for aid in adapter.agent_ids:
            profile = adapter.profiles.get(aid, {})
            text_parts = []
            if profile.get("skills"):
                text_parts.append(", ".join(profile["skills"]))
            if profile.get("bio"):
                text_parts.append(profile["bio"])
            if profile.get("role"):
                text_parts.append(profile["role"])
            text = " ".join(text_parts) if text_parts else aid
            try:
                vec = await engine._encoder.encode(text)
                agent_vectors[aid] = vec
            except Exception:
                pass

        if agent_vectors:
            defaults["agent_vectors"] = agent_vectors

        # 存储到 app state
        app.state.engine = engine
        app.state.defaults = defaults
        app.state.adapter = adapter
        app.state.llm_client = llm_client
        app.state.ws_manager = ws_manager
        app.state.sessions = {}
        app.state.tasks = {}
        app.state.config = config

        logger.info(
            "%s 启动完成 — %d 个 Agent, 端口 %d",
            config.app_name, len(adapter.agent_ids), config.port,
        )
        yield

        for task in app.state.tasks.values():
            if not task.done():
                task.cancel()
        logger.info("%s 关闭", config.app_name)

    app = FastAPI(
        title=config.app_name,
        description=config.app_description or f"{config.app_name} — 基于通爻 SDK 的 AToA 应用",
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

    # ============ API 路由 ============

    @app.get("/api/agents", response_model=AgentListResponse)
    async def list_agents(request: Request):
        """列出所有可用 Agent。"""
        adapter = request.app.state.adapter
        agents = []
        for aid, profile in adapter.profiles.items():
            agents.append({
                "agent_id": aid,
                "name": profile.get("name", aid),
                "role": profile.get("role", ""),
                "skills": profile.get("skills", []),
                "bio": profile.get("bio", ""),
            })
        return AgentListResponse(agents=agents, count=len(agents))

    @app.post("/api/negotiate", response_model=NegotiationResponse, status_code=201)
    async def submit_demand(req: SubmitDemandRequest, request: Request):
        """提交需求，启动协商。"""
        from towow import NegotiationSession, DemandSnapshot, NegotiationState
        from towow.core.models import TraceChain, generate_id

        state = request.app.state
        neg_id = generate_id("neg")
        session = NegotiationSession(
            negotiation_id=neg_id,
            demand=DemandSnapshot(
                raw_intent=req.intent,
                user_id=req.user_id,
                scene_id=state.config.scene_id,
            ),
            trace=TraceChain(negotiation_id=neg_id),
        )
        state.sessions[neg_id] = session

        # 注册子协商回调
        def _register(s):
            state.sessions[s.negotiation_id] = s

        run_defaults = {**state.defaults, "register_session": _register}

        task = asyncio.create_task(
            _run_negotiation(state.engine, session, run_defaults)
        )
        state.tasks[neg_id] = task

        return _to_response(session)

    @app.post("/api/negotiate/{neg_id}/confirm", response_model=NegotiationResponse)
    async def confirm_formulation(neg_id: str, req: ConfirmRequest, request: Request):
        """确认需求表述。"""
        from towow import NegotiationState
        state = request.app.state
        session = state.sessions.get(neg_id)
        if not session:
            raise HTTPException(404, f"协商 {neg_id} 不存在")
        if session.state != NegotiationState.FORMULATED:
            raise HTTPException(409, f"当前状态不允许确认: {session.state.value}")
        accepted = state.engine.confirm_formulation(neg_id, req.confirmed_text)
        if not accepted:
            raise HTTPException(409, "引擎未在等待确认")
        return _to_response(session)

    @app.get("/api/negotiate/{neg_id}", response_model=NegotiationResponse)
    async def get_negotiation(neg_id: str, request: Request):
        """查询协商状态。"""
        session = request.app.state.sessions.get(neg_id)
        if not session:
            raise HTTPException(404, f"协商 {neg_id} 不存在")
        return _to_response(session)

    @app.get("/api/info")
    async def app_info(request: Request):
        """应用信息（供 App Store 注册使用）。"""
        cfg = request.app.state.config
        adapter = request.app.state.adapter
        return {
            "app_name": cfg.app_name,
            "scene_id": cfg.scene_id,
            "scene_name": cfg.scene_name,
            "description": cfg.app_description,
            "agent_count": len(adapter.agent_ids),
            "agent_ids": adapter.agent_ids,
        }

    # ============ WebSocket ============

    @app.websocket("/ws/{neg_id}")
    async def negotiation_ws(ws: WebSocket, neg_id: str):
        state = ws.app.state
        session = state.sessions.get(neg_id)
        if not session:
            await ws.close(code=4004, reason="协商不存在")
            return

        channel = f"negotiation:{neg_id}"
        await state.ws_manager.connect(ws, channel)

        # 重放已有事件
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

    frontend_path = Path(config.frontend_dir)
    if frontend_path.exists():
        @app.get("/")
        async def index():
            index_file = frontend_path / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            return HTMLResponse("<h1>前端文件未找到</h1>")

        app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    return app


# ============ 辅助函数 ============

async def _run_negotiation(engine, session, defaults):
    """在后台运行完整协商流程。"""
    from towow import NegotiationState
    try:
        # 自动确认 formulation（生产环境由前端用户确认）
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
        logger.error("协商 %s 失败: %s", session.negotiation_id, e, exc_info=True)
        session.metadata["error"] = str(e)
        if session.state != NegotiationState.COMPLETED:
            session.state = NegotiationState.COMPLETED


def _to_response(session) -> NegotiationResponse:
    """将 NegotiationSession 转为 API 响应。"""
    from towow import AgentParticipant
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
            entry["offer_capabilities"] = p.offer.capabilities
        participants.append(entry)

    return NegotiationResponse(
        negotiation_id=session.negotiation_id,
        state=session.state.value,
        demand_raw=session.demand.raw_intent,
        demand_formulated=session.demand.formulated_text,
        participants=participants,
        plan_output=session.plan_output,
        center_rounds=session.center_rounds,
    )
