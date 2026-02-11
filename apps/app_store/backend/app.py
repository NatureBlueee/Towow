"""
AToA App Store — 通爻网络入口。

核心逻辑：一个引擎，所有 Agent 在同一个网络里。
- SecondMe 用户通过 OAuth2 登录后，其 AI 分身注册为网络中的 Agent
- 样板间 Agent 从 JSON 文件加载（演示用）
- 其他应用注册"场景上下文"，其用户通过 SecondMe 授权接入
- 用户发需求时选择 scope（全网 / 某个场景）

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

from .composite_adapter import CompositeAdapter
from .scene_registry import SceneContext, SceneRegistry

logger = logging.getLogger(__name__)


# ============ 请求/响应模型 ============

class NegotiateRequest(BaseModel):
    intent: str
    user_id: str = "anonymous"
    scope: str = "all"  # "all" | "scene:{scene_id}"

class NegotiationResponse(BaseModel):
    negotiation_id: str
    state: str
    demand_raw: str
    demand_formulated: Optional[str] = None
    participants: list[dict[str, Any]] = Field(default_factory=list)
    plan_output: Optional[str] = None
    center_rounds: int = 0
    scope: str = "all"
    agent_count: int = 0

class RegisterSceneRequest(BaseModel):
    scene_id: str
    name: str
    description: str = ""
    priority_strategy: str = ""
    domain_context: str = ""
    created_by: str = ""

class ConnectUserRequest(BaseModel):
    """其他应用把用户的 SecondMe 授权码发过来。"""
    authorization_code: str
    scene_id: str = ""  # 可选：标记该用户关联的场景

class AppListResponse(BaseModel):
    scenes: list[dict[str, Any]]
    agents: list[dict[str, Any]]
    total_agents: int


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


class NetworkEventPusher:
    def __init__(self, ws_manager: SimpleWSManager):
        self._ws = ws_manager

    async def push(self, event: Any) -> None:
        channel = f"negotiation:{event.negotiation_id}"
        await self._ws.broadcast(channel, event.to_dict())

    async def push_many(self, events: list) -> None:
        for event in events:
            await self.push(event)


# ============ 样板间加载 ============

SAMPLE_APPS = {
    "hackathon": {
        "name": "黑客松组队",
        "json_path": "S1_hackathon/data/agents.json",
        "scene": SceneContext(
            scene_id="hackathon",
            name="黑客松组队",
            description="帮助参赛者找到最佳队友，组建互补的黑客松团队",
            priority_strategy="优先匹配技术互补性和协作意愿",
            domain_context="黑客松比赛场景，参与者需要快速组队，技能互补比经验更重要",
        ),
    },
    "skill_exchange": {
        "name": "技能交换",
        "json_path": "S2_skill_exchange/data/agents.json",
        "scene": SceneContext(
            scene_id="skill_exchange",
            name="技能交换",
            description="连接有互补技能的人，促进知识和技能的双向交流",
            priority_strategy="优先匹配技能互补度和学习意愿",
            domain_context="技能交换场景，重点是找到可以互相教学的配对",
        ),
    },
    "recruitment": {
        "name": "智能招聘",
        "json_path": "R1_recruitment/data/agents.json",
        "scene": SceneContext(
            scene_id="recruitment",
            name="智能招聘",
            description="匹配求职者与职位需求，找到最佳人岗配对",
            priority_strategy="优先匹配专业能力和岗位要求",
            domain_context="招聘场景，需要评估候选人的技能匹配度、文化契合度和成长潜力",
        ),
    },
    "matchmaking": {
        "name": "AI 相亲",
        "json_path": "M1_matchmaking/data/agents.json",
        "scene": SceneContext(
            scene_id="matchmaking",
            name="AI 相亲",
            description="基于价值观和兴趣匹配有缘人",
            priority_strategy="优先匹配价值观契合度和兴趣重叠度",
            domain_context="相亲场景，关注性格互补、生活方式兼容和共同兴趣",
        ),
    },
}


def _load_sample_agents(composite: CompositeAdapter, apps_dir: Path, llm_client):
    """加载所有样板间的 Agent 到 CompositeAdapter。"""
    import sys
    sys.path.insert(0, str(apps_dir.parent))
    from apps.shared.json_adapter import JSONFileAdapter

    total = 0
    for app_id, config in SAMPLE_APPS.items():
        json_path = apps_dir / config["json_path"]
        if not json_path.exists():
            logger.warning("样板间数据不存在: %s", json_path)
            continue

        adapter = JSONFileAdapter(json_path=json_path, llm_client=llm_client)
        registered = composite.register_source(
            source_name=config["name"],
            adapter=adapter,
            scene_ids=[app_id],
        )
        total += len(registered)
        logger.info("加载样板间 %s: %d 个 Agent", config["name"], len(registered))

    return total


# ============ SecondMe 用户注册 ============

async def _register_secondme_user(
    app_state,
    access_token: str,
    scene_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    用 SecondMe token 注册一个用户的 AI 分身到网络。

    Returns:
        注册结果 dict，含 agent_id 和 profile 摘要
    """
    from towow.adapters.secondme_adapter import SecondMeAdapter

    oauth2_client = app_state.oauth2_client
    adapter = SecondMeAdapter(oauth2_client=oauth2_client, access_token=access_token)

    # 拉取完整画像
    profile = await adapter.fetch_and_build_profile()
    agent_id = profile["agent_id"]

    # 注册到 CompositeAdapter
    composite: CompositeAdapter = app_state.composite
    composite.register_agent(
        agent_id=agent_id,
        adapter=adapter,
        source="SecondMe",
        scene_ids=list(scene_ids or []),
        display_name=profile.get("name", agent_id),
    )

    # 编码向量
    try:
        from oauth2_client import profile_to_text
        text = profile_to_text(profile)
    except ImportError:
        text = f"{profile.get('name', '')} {profile.get('self_introduction', '')} {profile.get('bio', '')}"
    try:
        vec = await app_state.engine._encoder.encode(text)
        app_state.agent_vectors[agent_id] = vec
    except Exception as e:
        logger.warning("向量编码失败 %s: %s", agent_id, e)

    # 更新场景计数
    for sid in (scene_ids or []):
        app_state.scene_registry.increment_agent_count(sid)

    # 存储 token 供后续对话使用
    app_state.user_tokens[agent_id] = access_token

    logger.info(
        "SecondMe 用户注册: %s (name=%s, shades=%d, scenes=%s)",
        agent_id, profile.get("name"), len(profile.get("shades", [])), scene_ids or [],
    )

    return {
        "agent_id": agent_id,
        "name": profile.get("name"),
        "shades_count": len(profile.get("shades", [])),
        "memories_count": len(profile.get("memories", [])),
        "scene_ids": list(scene_ids or []),
    }


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

    # CompositeAdapter + SceneRegistry
    composite = CompositeAdapter()
    scene_registry = SceneRegistry()
    app.state.composite = composite
    app.state.scene_registry = scene_registry

    # LLM 客户端
    api_key = os.environ.get("TOWOW_ANTHROPIC_API_KEY", "")
    llm_client = None
    if api_key:
        from towow.infra.llm_client import ClaudePlatformClient
        llm_client = ClaudePlatformClient(api_key=api_key)
        logger.info("App Store: 使用 Claude API")
    else:
        import sys
        apps_dir = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(apps_dir))
        from apps.shared.mock_llm import MockLLMClient
        llm_client = MockLLMClient()
        logger.info("App Store: 使用 Mock LLM")

    app.state.llm_client = llm_client

    # 加载样板间 Agent
    apps_dir = Path(__file__).resolve().parent.parent.parent
    sample_count = _load_sample_agents(composite, apps_dir, llm_client)

    # 注册样板间场景
    for app_id, config in SAMPLE_APPS.items():
        scene_registry.register(config["scene"])

    # WebSocket
    ws_manager = SimpleWSManager()
    event_pusher = NetworkEventPusher(ws_manager)
    app.state.ws_manager = ws_manager

    # 引擎
    import numpy as np
    from towow.hdc.resonance import CosineResonanceDetector

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

    from towow.core.engine import NegotiationEngine
    engine = NegotiationEngine(
        encoder=encoder,
        resonance_detector=CosineResonanceDetector(),
        event_pusher=event_pusher,
    )
    app.state.engine = engine

    # 预编码样板间 Agent 向量
    agent_vectors = {}
    for aid in composite.all_agent_ids:
        profile = await composite.get_profile(aid)
        text_parts = []
        for field in ("self_introduction", "bio", "role"):
            if profile.get(field):
                text_parts.append(str(profile[field]))
        if profile.get("skills"):
            skills = profile["skills"]
            if isinstance(skills, list):
                text_parts.append(", ".join(str(s) for s in skills))
        # shades
        for shade in profile.get("shades", []):
            desc = shade.get("description", "") or shade.get("name", "")
            if desc:
                text_parts.append(desc)
        text = " ".join(text_parts) if text_parts else aid
        try:
            vec = await encoder.encode(text)
            agent_vectors[aid] = vec
        except Exception:
            pass
    app.state.agent_vectors = agent_vectors

    app.state.sessions = {}
    app.state.tasks = {}
    app.state.user_tokens = {}  # agent_id → SecondMe access_token

    # Skills
    app.state.skills = {
        "center": CenterCoordinatorSkill(),
        "formulation": DemandFormulationSkill(),
        "offer": OfferGenerationSkill(),
        "sub_negotiation": SubNegotiationSkill(),
        "gap_recursion": GapRecursionSkill(),
    }

    # SecondMe OAuth2 客户端（可选 — 有配置才启用）
    app.state.oauth2_client = None
    try:
        client_id = os.environ.get("SECONDME_CLIENT_ID", "")
        if client_id:
            from oauth2_client import SecondMeOAuth2Client, OAuth2Config
            config = OAuth2Config.from_env()
            app.state.oauth2_client = SecondMeOAuth2Client(config)
            logger.info("App Store: SecondMe OAuth2 已启用")
    except Exception as e:
        logger.warning("SecondMe OAuth2 未配置: %s", e)

    logger.info(
        "App Store 启动完成: %d 个 Agent, %d 个场景, %d 个向量",
        composite.agent_count,
        len(scene_registry.all_scenes),
        len(agent_vectors),
    )
    yield

    for task in app.state.tasks.values():
        if not task.done():
            task.cancel()
    if app.state.oauth2_client:
        await app.state.oauth2_client.close()
    logger.info("App Store 关闭")


def create_store_app() -> FastAPI:
    application = FastAPI(
        title="通爻网络 App Store",
        description="所有 Agent 在同一个网络里。场景是上下文，不是边界。",
        version="2.0.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ============ 网络状态 API ============

    @application.get("/api/info")
    async def network_info(request: Request):
        """网络状态总览。"""
        state = request.app.state
        return {
            "name": "通爻网络 App Store",
            "version": "2.0.0",
            "total_agents": state.composite.agent_count,
            "total_scenes": len(state.scene_registry.all_scenes),
            "scenes": state.scene_registry.list_scenes(),
            "secondme_enabled": state.oauth2_client is not None,
        }

    @application.get("/api/agents")
    async def list_agents(request: Request, scope: str = "all"):
        """列出网络中的 Agent（支持 scope 过滤），含画像摘要。"""
        state = request.app.state
        agent_ids = state.composite.get_agents_by_scope(scope)
        agents = []
        for aid in agent_ids:
            info = state.composite.get_agent_info(aid)
            if not info:
                continue
            # 全量合并 profile 字段（前端按场景自选展示）
            # NOTE: JSON adapter 是内存字典 O(1)；SecondMe adapter 未来需要缓存层
            profile = await state.composite.get_profile(aid)
            for key, value in profile.items():
                if key not in ("agent_id", "source", "scene_ids"):
                    info.setdefault(key, value)
            agents.append(info)
        return {"agents": agents, "count": len(agents), "scope": scope}

    @application.get("/api/scenes")
    async def list_scenes(request: Request):
        """列出所有已注册场景。"""
        return {"scenes": request.app.state.scene_registry.list_scenes()}

    # ============ 场景注册 API ============

    @application.post("/api/scenes/register")
    async def register_scene(req: RegisterSceneRequest, request: Request):
        """其他应用注册场景上下文。"""
        scene = SceneContext(
            scene_id=req.scene_id,
            name=req.name,
            description=req.description,
            priority_strategy=req.priority_strategy,
            domain_context=req.domain_context,
            created_by=req.created_by,
        )
        request.app.state.scene_registry.register(scene)
        return {"status": "ok", "scene_id": req.scene_id}

    @application.post("/api/scenes/{scene_id}/connect")
    async def connect_user_to_scene(
        scene_id: str,
        req: ConnectUserRequest,
        request: Request,
    ):
        """
        其他应用把用户的 SecondMe 授权码发过来。
        App Store 换 token → 构建画像 → 注册 Agent（带场景标签）。

        方案 A：用户显式授权。授权码由用户在其他应用里点击"连接到通爻网络"后产生。
        """
        state = request.app.state
        if not state.oauth2_client:
            raise HTTPException(503, "SecondMe OAuth2 未配置")

        # 验证场景存在
        scene = state.scene_registry.get(scene_id)
        if not scene:
            raise HTTPException(404, f"场景 {scene_id} 不存在")

        # 用授权码换 token
        try:
            token_set = await state.oauth2_client.exchange_token(req.authorization_code)
        except Exception as e:
            raise HTTPException(400, f"授权码无效: {e}")

        # 注册用户
        result = await _register_secondme_user(
            state,
            access_token=token_set.access_token,
            scene_ids=[scene_id],
        )

        return {"status": "ok", **result}

    # ============ 协商 API ============

    @application.post("/api/negotiate", response_model=NegotiationResponse, status_code=201)
    async def negotiate(req: NegotiateRequest, request: Request):
        """
        发起协商 — 需求信号在网络中传播。

        scope 参数控制广播范围：
        - "all": 全网所有 Agent 参与共振
        - "scene:{scene_id}": 只有该场景的 Agent 参与
        """
        from towow import NegotiationSession, DemandSnapshot
        from towow.core.models import TraceChain, generate_id

        state = request.app.state
        composite: CompositeAdapter = state.composite

        # 根据 scope 过滤候选 Agent
        candidate_ids = composite.get_agents_by_scope(req.scope)
        if not candidate_ids:
            raise HTTPException(400, f"scope '{req.scope}' 下没有可用的 Agent")

        # 获取场景上下文（如果是场景模式）
        scene_context = ""
        scene_id = ""
        if req.scope.startswith("scene:"):
            scene_id = req.scope[len("scene:"):]
            scene_context = state.scene_registry.get_center_context(scene_id)

        neg_id = generate_id("neg")
        session = NegotiationSession(
            negotiation_id=neg_id,
            demand=DemandSnapshot(
                raw_intent=req.intent,
                user_id=req.user_id,
                scene_id=scene_id or "network",
            ),
            trace=TraceChain(negotiation_id=neg_id),
        )
        state.sessions[neg_id] = session

        # 筛选候选 Agent 的向量
        candidate_vectors = {
            aid: state.agent_vectors[aid]
            for aid in candidate_ids
            if aid in state.agent_vectors
        }

        def _register(s):
            state.sessions[s.negotiation_id] = s

        # 支持用户自带 API Key
        user_api_key = request.headers.get("x-api-key", "")
        if user_api_key:
            from towow.infra.llm_client import ClaudePlatformClient
            req_llm_client = ClaudePlatformClient(api_key=user_api_key)
        else:
            req_llm_client = state.llm_client

        run_defaults = {
            "adapter": composite,
            "llm_client": req_llm_client,
            "center_skill": state.skills["center"],
            "formulation_skill": state.skills["formulation"],
            "offer_skill": state.skills["offer"],
            "sub_negotiation_skill": state.skills["sub_negotiation"],
            "gap_recursion_skill": state.skills["gap_recursion"],
            "agent_vectors": candidate_vectors or None,
            "k_star": min(len(candidate_ids), 8),
            "agent_display_names": composite.get_display_names(),
            "register_session": _register,
        }

        task = asyncio.create_task(
            _run_negotiation(state.engine, session, run_defaults, scene_context)
        )
        state.tasks[neg_id] = task

        return NegotiationResponse(
            negotiation_id=neg_id,
            state=session.state.value,
            demand_raw=req.intent,
            scope=req.scope,
            agent_count=len(candidate_ids),
        )

    @application.get("/api/negotiate/{neg_id}", response_model=NegotiationResponse)
    async def get_negotiation(neg_id: str, request: Request):
        """查询协商状态。"""
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
            # 注入来源信息
            agent_info = request.app.state.composite.get_agent_info(p.agent_id)
            if agent_info:
                entry["source"] = agent_info.get("source", "")
                entry["scene_ids"] = agent_info.get("scene_ids", [])
            participants.append(entry)

        return NegotiationResponse(
            negotiation_id=session.negotiation_id,
            state=session.state.value,
            demand_raw=session.demand.raw_intent,
            demand_formulated=session.demand.formulated_text,
            participants=participants,
            plan_output=session.plan_output,
            center_rounds=session.center_rounds,
            scope=session.demand.scene_id or "all",
        )

    @application.post("/api/negotiate/{neg_id}/confirm")
    async def confirm(neg_id: str, request: Request):
        """确认需求表述。"""
        accepted = request.app.state.engine.confirm_formulation(neg_id)
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
            return HTMLResponse("<h1>App Store 加载中...</h1>")

        application.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    return application


async def _run_negotiation(engine, session, defaults, scene_context: str = ""):
    """运行协商（带自动确认和场景上下文注入）。"""
    from towow import NegotiationState

    try:
        async def auto_confirm():
            for _ in range(120):
                await asyncio.sleep(0.5)
                if engine.is_awaiting_confirmation(session.negotiation_id):
                    engine.confirm_formulation(session.negotiation_id)
                    return
        confirm_task = asyncio.create_task(auto_confirm())

        # TODO: 场景上下文注入 — 当 Center skill 支持 context 参数时启用
        # 目前 scene_context 暂不注入，等 Center skill 支持后再接入
        await engine.start_negotiation(session=session, **defaults)
        confirm_task.cancel()
    except Exception as e:
        logger.error("协商 %s 失败: %s", session.negotiation_id, e, exc_info=True)
        session.metadata["error"] = str(e)
        if session.state != NegotiationState.COMPLETED:
            session.state = NegotiationState.COMPLETED


app = create_store_app()
