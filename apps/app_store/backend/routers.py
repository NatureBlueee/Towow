"""
App Store routes — extracted from app.py for the unified server.

All routes are relative (no prefix) — the caller adds /store prefix.

In the unified server, App Store state attributes are prefixed with ``store_``
(e.g. ``app.state.store_composite``).  The ``_store_state_proxy`` helper adapts
them to the unprefixed names that ``_register_secondme_user`` expects.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class _StoreStateProxy:
    """Maps store_xxx attributes on unified app.state to unprefixed names."""

    _ATTR_MAP = {
        "composite": "store_composite",
        "scene_registry": "store_scene_registry",
        "engine": "store_engine",
        "llm_client": "store_llm_client",
        "ws_manager": "store_ws_manager",
        "agent_vectors": "store_agent_vectors",
        "sessions": "store_sessions",
        "tasks": "store_tasks",
        "user_tokens": "store_user_tokens",
        "skills": "store_skills",
        "oauth2_client": "store_oauth2_client",
    }

    def __init__(self, real_state):
        object.__setattr__(self, "_real", real_state)

    def __getattr__(self, name):
        mapped = self._ATTR_MAP.get(name)
        if mapped:
            return getattr(object.__getattribute__(self, "_real"), mapped)
        return getattr(object.__getattribute__(self, "_real"), name)

    def __setattr__(self, name, value):
        mapped = self._ATTR_MAP.get(name)
        if mapped:
            setattr(object.__getattribute__(self, "_real"), mapped, value)
        else:
            setattr(object.__getattribute__(self, "_real"), name, value)


# ============ 请求/响应模型 ============

class NegotiateRequest(BaseModel):
    intent: str
    user_id: str = "anonymous"
    scope: str = "all"


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
    authorization_code: str
    scene_id: str = ""


class AssistDemandRequest(BaseModel):
    mode: str = Field(..., pattern="^(polish|surprise)$")
    scene_id: str = ""
    raw_text: str = ""


# ============ SecondMe 辅助需求 ============

SESSION_COOKIE_NAME = "towow_session"

ASSIST_PROMPTS = {
    "polish": """你是用户的 AI 分身，正在帮用户完善一个协作需求。

用户在「{scene_name}」场景中写了一个初步的想法。请基于你对用户的理解，帮助优化和丰富这个需求表达。

规则：
- 保留用户的核心意图，不要偏离
- 补充具体细节：时间、规模、期望的协作方式
- 表达用户可能没说出来的真实偏好
- 直接输出优化后的需求文本，不加任何解释或前缀

当前场景：{scene_description}
网络中已有的参与者：
{agent_summaries}""",

    "surprise": """你是用户的 AI 分身。用户选了「{scene_name}」场景，想看看你能帮他发现什么有价值的协作需求。

基于你对用户的深层理解——他的兴趣、经历、能力、未被满足的好奇心——结合这个场景和已有的参与者，创造一个他可能真正需要但还没想到的需求。

规则：
- 需求要具体，不要泛泛而谈
- 要有意外感——用户看到会觉得"对啊，我确实需要这个"
- 让需求自然地连接用户的特质和场景中的可能性
- 直接输出需求文本，不加任何解释或前缀

当前场景：{scene_description}
网络中已有的参与者：
{agent_summaries}""",
}


def _build_agent_summaries(composite, scope: str, max_agents: int = 10) -> str:
    """构建 Agent 列表摘要供 SecondMe 参考。"""
    agent_ids = composite.get_agents_by_scope(scope)[:max_agents]
    lines = []
    for aid in agent_ids:
        info = composite.get_agent_info(aid)
        if not info:
            continue
        name = info.get("display_name", aid)
        skills = info.get("skills", [])
        bio = info.get("bio", "")
        line = f"- {name}"
        if skills:
            line += f"（擅长：{', '.join(skills[:3])}）"
        if bio:
            line += f"：{bio[:80]}"
        lines.append(line)
    return "\n".join(lines) if lines else "（暂无参与者信息）"


async def _get_agent_id_from_session(request: Request) -> Optional[str]:
    """从 cookie 中解析 agent_id。"""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return None
    session_store = request.app.state.session_store
    return await session_store.get(f"session:{session_id}")


# ============ Router ============

router = APIRouter()
ws_router = APIRouter()


# ── 网络状态 API ──

@router.get("/api/info")
async def network_info(request: Request):
    state = request.app.state
    return {
        "name": "通爻网络 App Store",
        "version": "2.0.0",
        "total_agents": state.store_composite.agent_count,
        "total_scenes": len(state.store_scene_registry.all_scenes),
        "scenes": state.store_scene_registry.list_scenes(),
        "secondme_enabled": state.store_oauth2_client is not None,
    }


@router.get("/api/agents")
async def list_agents(request: Request, scope: str = "all"):
    state = request.app.state
    agent_ids = state.store_composite.get_agents_by_scope(scope)
    agents = []
    for aid in agent_ids:
        info = state.store_composite.get_agent_info(aid)
        if not info:
            continue
        profile = await state.store_composite.get_profile(aid)
        for key, value in profile.items():
            if key not in ("agent_id", "source", "scene_ids"):
                info.setdefault(key, value)
        agents.append(info)
    return {"agents": agents, "count": len(agents), "scope": scope}


@router.get("/api/scenes")
async def list_scenes(request: Request):
    return {"scenes": request.app.state.store_scene_registry.list_scenes()}


# ── 场景注册 API ──

@router.post("/api/scenes/register")
async def register_scene(req: RegisterSceneRequest, request: Request):
    from .scene_registry import SceneContext

    scene = SceneContext(
        scene_id=req.scene_id,
        name=req.name,
        description=req.description,
        priority_strategy=req.priority_strategy,
        domain_context=req.domain_context,
        created_by=req.created_by,
    )
    request.app.state.store_scene_registry.register(scene)
    return {"status": "ok", "scene_id": req.scene_id}


@router.post("/api/scenes/{scene_id}/connect")
async def connect_user_to_scene(
    scene_id: str,
    req: ConnectUserRequest,
    request: Request,
):
    state = request.app.state
    if not state.store_oauth2_client:
        raise HTTPException(503, "SecondMe OAuth2 未配置")

    scene = state.store_scene_registry.get(scene_id)
    if not scene:
        raise HTTPException(404, f"场景 {scene_id} 不存在")

    try:
        token_set = await state.store_oauth2_client.exchange_token(req.authorization_code)
    except Exception as e:
        raise HTTPException(400, f"授权码无效: {e}")

    from .app import _register_secondme_user

    result = await _register_secondme_user(
        _StoreStateProxy(state),
        access_token=token_set.access_token,
        scene_ids=[scene_id],
    )
    return {"status": "ok", **result}


# ── SecondMe 辅助需求 API ──

@router.post("/api/assist-demand")
async def assist_demand(req: AssistDemandRequest, request: Request):
    """让用户的 SecondMe 分身帮助填写或创造需求。"""
    agent_id = await _get_agent_id_from_session(request)
    if not agent_id:
        raise HTTPException(401, "需要登录 SecondMe 才能使用分身辅助")

    state = request.app.state
    composite = state.store_composite

    # 验证 agent 在网络中
    info = composite.get_agent_info(agent_id)
    if not info:
        raise HTTPException(401, "Agent 不在网络中，请重新登录")

    if info.get("source") != "SecondMe":
        raise HTTPException(400, "仅 SecondMe 用户可使用分身辅助")

    if req.mode == "polish" and not req.raw_text.strip():
        raise HTTPException(400, "润色模式需要提供初始需求文本")

    # 构建上下文
    scope = f"scene:{req.scene_id}" if req.scene_id else "all"
    scene = state.store_scene_registry.get(req.scene_id) if req.scene_id else None
    scene_name = scene.name if scene else "全网络"
    scene_description = scene.description if scene else "跨场景协作"

    agent_summaries = _build_agent_summaries(composite, scope)

    # 组装 system prompt
    system_prompt = ASSIST_PROMPTS[req.mode].format(
        scene_name=scene_name,
        scene_description=scene_description,
        agent_summaries=agent_summaries,
    )

    # 构建用户消息
    if req.mode == "polish":
        user_message = f"请帮我优化这个需求：\n\n{req.raw_text}"
    else:
        user_message = "请帮我在这个场景中发现一个有价值的协作需求。"

    messages = [{"role": "user", "content": user_message}]

    try:
        result = await composite.chat(agent_id, messages, system_prompt)
        return {"demand_text": result, "mode": req.mode}
    except Exception as e:
        logger.error("SecondMe 辅助需求失败 agent=%s: %s", agent_id, e)
        raise HTTPException(502, f"分身暂时无法响应：{e}")


# ── 协商 API ──

@router.post("/api/negotiate", response_model=NegotiationResponse, status_code=201)
async def negotiate(req: NegotiateRequest, request: Request):
    from towow import NegotiationSession, DemandSnapshot
    from towow.core.models import TraceChain, generate_id

    state = request.app.state
    composite = state.store_composite

    candidate_ids = composite.get_agents_by_scope(req.scope)
    if not candidate_ids:
        raise HTTPException(400, f"scope '{req.scope}' 下没有可用的 Agent")

    scene_context = ""
    scene_id = ""
    if req.scope.startswith("scene:"):
        scene_id = req.scope[len("scene:"):]
        scene_context = state.store_scene_registry.get_center_context(scene_id)

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
    state.store_sessions[neg_id] = session

    candidate_vectors = {
        aid: state.store_agent_vectors[aid]
        for aid in candidate_ids
        if aid in state.store_agent_vectors
    }

    def _register(s):
        state.store_sessions[s.negotiation_id] = s

    user_api_key = request.headers.get("x-api-key", "")
    if user_api_key:
        from towow.infra.llm_client import ClaudePlatformClient
        req_llm_client = ClaudePlatformClient(api_key=user_api_key)
    else:
        req_llm_client = state.store_llm_client

    run_defaults = {
        "adapter": composite,
        "llm_client": req_llm_client,
        "center_skill": state.store_skills["center"],
        "formulation_skill": state.store_skills["formulation"],
        "offer_skill": state.store_skills["offer"],
        "sub_negotiation_skill": state.store_skills["sub_negotiation"],
        "gap_recursion_skill": state.store_skills["gap_recursion"],
        "agent_vectors": candidate_vectors or None,
        "k_star": min(len(candidate_ids), 8),
        "agent_display_names": composite.get_display_names(),
        "register_session": _register,
    }

    task = asyncio.create_task(
        _run_negotiation(state.store_engine, session, run_defaults, scene_context)
    )
    state.store_tasks[neg_id] = task

    return NegotiationResponse(
        negotiation_id=neg_id,
        state=session.state.value,
        demand_raw=req.intent,
        scope=req.scope,
        agent_count=len(candidate_ids),
    )


@router.get("/api/negotiate/{neg_id}", response_model=NegotiationResponse)
async def get_negotiation(neg_id: str, request: Request):
    session = request.app.state.store_sessions.get(neg_id)
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
        agent_info = request.app.state.store_composite.get_agent_info(p.agent_id)
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


@router.post("/api/negotiate/{neg_id}/confirm")
async def confirm(neg_id: str, request: Request):
    accepted = request.app.state.store_engine.confirm_formulation(neg_id)
    if not accepted:
        raise HTTPException(409, "引擎未在等待确认")
    return {"status": "ok"}


# ── WebSocket ──

@ws_router.websocket("/ws/{neg_id}")
async def negotiation_ws(ws: WebSocket, neg_id: str):
    state = ws.app.state
    session = state.store_sessions.get(neg_id)
    if not session:
        await ws.close(code=4004, reason="协商不存在")
        return

    channel = f"negotiation:{neg_id}"
    await state.store_ws_manager.connect(ws, channel)

    for event_dict in list(session.event_history):
        try:
            await ws.send_json(event_dict)
        except Exception:
            await state.store_ws_manager.disconnect(ws, channel)
            return

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        await state.store_ws_manager.disconnect(ws, channel)


# ── Static files helper ──

def mount_store_static(app_instance, prefix: str = "/store"):
    """Mount App Store frontend static files under the given prefix."""
    frontend_path = Path(__file__).resolve().parent.parent / "frontend"
    if not frontend_path.exists():
        return

    @app_instance.get(f"{prefix}/")
    async def store_index():
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return HTMLResponse("<h1>App Store 加载中...</h1>")

    app_instance.mount(
        f"{prefix}/static",
        StaticFiles(directory=str(frontend_path)),
        name="store_static",
    )


# ── 协商运行 ──

async def _run_negotiation(engine, session, defaults, scene_context: str = ""):
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
        logger.error("协商 %s 失败: %s", session.negotiation_id, e, exc_info=True)
        session.metadata["error"] = str(e)
        if session.state != NegotiationState.COMPLETED:
            session.state = NegotiationState.COMPLETED
