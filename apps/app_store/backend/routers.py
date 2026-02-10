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


# ── OAuth2 登录 API ──

@router.get("/auth/login")
async def oauth_login(request: Request, scene_id: str = ""):
    state = request.app.state
    if not state.store_oauth2_client:
        raise HTTPException(503, "SecondMe OAuth2 未配置")

    auth_url, oauth_state = await state.store_oauth2_client.build_authorization_url()

    if not hasattr(state, "store_oauth_states"):
        state.store_oauth_states = {}
    state.store_oauth_states[oauth_state] = scene_id

    return {"auth_url": auth_url}


@router.get("/auth/callback")
async def oauth_callback(
    request: Request,
    code: str = "",
    state: str = "",
):
    app_state = request.app.state
    if not code:
        raise HTTPException(400, "缺少授权码")

    if not app_state.store_oauth2_client:
        raise HTTPException(503, "SecondMe OAuth2 未配置")

    scene_id = ""
    if hasattr(app_state, "store_oauth_states"):
        scene_id = app_state.store_oauth_states.pop(state, "")

    try:
        token_set = await app_state.store_oauth2_client.exchange_token(code)
    except Exception as e:
        raise HTTPException(400, f"授权码无效: {e}")

    from .app import _register_secondme_user

    scene_ids = [scene_id] if scene_id else []
    result = await _register_secondme_user(
        _StoreStateProxy(app_state),
        access_token=token_set.access_token,
        scene_ids=scene_ids,
    )

    return {"status": "ok", "message": "登录成功，你的 AI 分身已加入网络", **result}


@router.get("/auth/me")
async def get_my_info(request: Request, agent_id: str = ""):
    if not agent_id:
        raise HTTPException(400, "请提供 agent_id")
    info = request.app.state.store_composite.get_agent_info(agent_id)
    if not info:
        raise HTTPException(404, "Agent 不存在")
    return info


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
