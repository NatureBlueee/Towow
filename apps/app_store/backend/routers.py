"""
App Store routes — extracted from app.py for the unified server.

All routes are relative (no prefix) — the caller adds /store prefix.

In the unified server, App Store state attributes are prefixed with ``store_``
(e.g. ``app.state.store_engine``).  The ``_store_state_proxy`` helper adapts
them to the unprefixed names used by internal functions.
``agent_registry`` is a shared instance (no store_ prefix).
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from database import (
    save_negotiation,
    update_negotiation,
    save_offers,
    get_user_history,
    get_negotiation_detail,
    save_assist_output,
)

logger = logging.getLogger(__name__)


class _StoreStateProxy:
    """Maps store_xxx attributes on unified app.state to unprefixed names."""

    _ATTR_MAP = {
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
    plan_json: Optional[dict[str, Any]] = None
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
    "polish": """你是这个人的分身。你比他自己更了解他——你读过他所有的文字、知道他的思维习惯和盲区。

现在他写了一个协作需求，但可能没说清楚，或者他说的"要求"不是他真正的"需求"。
你的工作：用你对他的了解，帮他把需求说得更准确。

## 你要做的（按顺序思考）

第一步：理解他真正想要什么
他说的具体要求（"要一个会 React 的人"）背后，真正的需求是什么？（"需要一个能把想法快速变成可交互原型的人"）

第二步：补充他没说出来的背景
他有哪些经历或能力跟这个需求相关，但他自己没提？想想：他的什么经历在这里有意想不到的价值？

第三步：区分硬性和柔性
他说的条件里，哪些是底线（不满足就必定失败），哪些是偏好（可以灵活）？

第四步：用他的方式重新表达
保留他的核心意图，但让响应者真正理解：这个人是谁、他要做什么、为什么值得响应。

## 规则
- 直接输出需求文本，不加"以下是优化后的需求"之类的前缀
- 保留他的语气和表达习惯，不要变成另一个人
- 不编造他没有的能力或经历

当前场景：{scene_name} — {scene_description}
网络中已有的参与者：
{agent_summaries}""",

    "surprise": """你是这个人的分身。你了解他所有的文字、思维方式、经历和盲区。

现在你要替他做一件他自己做不到的事——你比他多看到两样东西：
1. 这个场景里有什么机会（他不知道）
2. 网络里有什么样的能力和资源（他不知道）

用你对他的了解 × 他不知道的场景和能力生态，找到一个碰撞点——让他看到会说"对啊，我确实需要这个，但我自己没想到"。

## 你要做的（按顺序思考，但只输出最后一步的结果）

第一步：分析他
从你掌握的所有信息里，找到他最独特的能力/经历/视角。不是泛泛的"他喜欢XX"，而是具体的：他做过什么、擅长什么、关心什么。

第二步：感受网络氛围
下面列出的是场景中部分参与者的画像。你的目的不是挑选某个人，而是从中感受：这个网络里有什么样的能力生态？什么领域的人比较多？存在什么意想不到的能力类型？把这些当作"空气中的气味"来感知，不是"货架上的商品"来挑选。

第三步：发现碰撞点
把他的某个具体能力/经历 × 场景中的某个机会 × 网络中存在的某类能力，交叉在一起。注意：你找的是一个"方向"，不是一个"合作对象"。

第四步：构造一个具体的需求
围绕这个碰撞点，写一个他自己的需求——
- 他想做什么具体的事？想要什么样的产出？
- 他自己能贡献什么？
- 他需要什么样的能力来补充？（描述能力类型，不要指名道姓）
- 什么条件下会失败？（1-2 条底线）
- 大概的时间和方式

第五步：用他的声音说出来
像他自己写需求一样表达。注意他的说话方式——有的人结构化，有的人口语化，有的人简洁，有的人细致。用他的方式，不是你的方式。

## 绝对不要做的
- 不要指名道姓提到任何具体的参与者——你不知道最终谁会响应，协作对象由后续共振决定
- 不要描述"他是一个什么样的人"——那是 Profile，不是需求
- 不要编造他没有的能力或经历
- 不要贪多——只围绕一个碰撞点，一个需求
- 不要加任何前缀（"以下是..."）或后缀（"祝你顺利..."）——直接输出需求本身

当前场景：{scene_name} — {scene_description}
以下是网络中的能力生态画像（仅供感知氛围，不要在需求中提及具体人名）：
{agent_summaries}""",
}


def _build_agent_summaries(composite, scope: str, max_agents: int = 5) -> str:
    """构建 Agent 列表摘要供 SecondMe 参考。

    每次随机抽取 max_agents 个，确保 SecondMe 每次看到不同的人。

    两类数据源：
    - JSON 样板间 Agent：有 skills, bio, role, experience
    - SecondMe 用户：有 shades (兴趣标签), bio, self_introduction
    """
    all_ids = composite.get_agents_by_scope(scope)
    agent_ids = random.sample(all_ids, min(max_agents, len(all_ids)))
    lines = []
    for aid in agent_ids:
        info = composite.get_agent_info(aid)
        if not info:
            continue
        name = info.get("display_name", aid)
        parts = [f"- {name}"]

        # 角色/职业
        role = info.get("role", "")
        if role:
            parts.append(f"（{role}）")

        # 技能（JSON 样板间格式）
        skills = info.get("skills", [])
        if skills:
            parts.append(f"，擅长 {', '.join(skills[:4])}")

        # 兴趣标签（SecondMe shades 格式）
        if not skills:
            shades = info.get("shades", [])
            if shades:
                shade_names = [s.get("name", "") or s.get("description", "") for s in shades[:4]]
                shade_names = [s for s in shade_names if s]
                if shade_names:
                    parts.append(f"，关注 {', '.join(shade_names)}")

        # 简介
        bio = info.get("bio", "") or info.get("self_introduction", "")
        if bio:
            parts.append(f"。{bio[:100]}")

        lines.append("".join(parts))
    return "\n".join(lines) if lines else "（暂无参与者信息）"


async def _get_agent_id_from_session(request: Request) -> Optional[str]:
    """从 cookie 中解析 agent_id。"""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        logger.warning("assist-demand: cookie '%s' 不存在，所有 cookies: %s",
                        SESSION_COOKIE_NAME, list(request.cookies.keys()))
        return None
    session_store = request.app.state.session_store
    agent_id = await session_store.get(f"session:{session_id}")
    if not agent_id:
        logger.warning("assist-demand: session '%s...' 在 store 中不存在", session_id[:8])
    return agent_id


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
        "total_agents": state.agent_registry.agent_count,
        "total_scenes": len(state.store_scene_registry.all_scenes),
        "scenes": state.store_scene_registry.list_scenes(),
        "secondme_enabled": state.store_oauth2_client is not None,
    }


@router.get("/api/agents")
async def list_agents(request: Request, scope: str = "all"):
    state = request.app.state
    agent_ids = state.agent_registry.get_agents_by_scope(scope)
    agents = []
    for aid in agent_ids:
        info = state.agent_registry.get_agent_info(aid)
        if not info:
            continue
        profile = await state.agent_registry.get_profile(aid)
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

    from backend.routers.auth import _register_agent_from_secondme

    result = await _register_agent_from_secondme(
        access_token=token_set.access_token,
        oauth2_client=state.store_oauth2_client,
        registry=state.agent_registry,
        encoder=state.encoder,
        agent_vectors=state.store_agent_vectors,
        scene_ids=[scene_id],
    )

    # 存储 token 供后续对话使用（assist-demand 等）
    state.store_user_tokens[result["agent_id"]] = token_set.access_token

    # 更新场景计数
    state.store_scene_registry.increment_agent_count(scene_id)

    return {"status": "ok", **result}


# ── SecondMe 辅助需求 API ──

@router.post("/api/assist-demand")
async def assist_demand(req: AssistDemandRequest, request: Request):
    """让用户的 SecondMe 分身帮助填写或创造需求。"""
    agent_id = await _get_agent_id_from_session(request)
    if not agent_id:
        raise HTTPException(401, "需要登录 SecondMe 才能使用分身辅助")

    state = request.app.state
    composite = state.agent_registry

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

    logger.info("assist-demand: agent=%s, mode=%s, scene=%s", agent_id, req.mode, scene_name)

    async def _sse_generator():
        chunk_count = 0
        has_content = False
        accumulated_text = []
        try:
            async with asyncio.timeout(60):
                async for chunk in composite.chat_stream(agent_id, messages, system_prompt):
                    chunk_count += 1
                    if chunk:
                        has_content = True
                        accumulated_text.append(chunk)
                        yield f"data: {json.dumps(chunk)}\n\n"
            if not has_content:
                logger.warning("assist-demand: SecondMe 返回空内容 agent=%s (chunks=%d)", agent_id, chunk_count)
                yield "event: error\ndata: 分身思考后没有产出内容，请重试\n\n"
            else:
                logger.info("assist-demand: 成功, %d chunks", chunk_count)
                # 持久化：assist 输出写入 DB (ADR-007)
                try:
                    full_text = "".join(accumulated_text)
                    save_assist_output(
                        user_id=agent_id,
                        scene_id=req.scene_id or "network",
                        demand_mode=req.mode,
                        assist_output=full_text,
                        raw_text=req.raw_text,
                    )
                except Exception as db_err:
                    logger.warning("History: assist_demand DB write failed: %s", db_err)
            yield "data: [DONE]\n\n"
        except TimeoutError:
            logger.error("assist-demand: 超时 60s agent=%s (已收到 %d chunks)", agent_id, chunk_count)
            yield "event: error\ndata: 分身响应超时，请重试\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("assist-demand stream 错误 (已收到 %d chunks): %s",
                         chunk_count, e, exc_info=True)
            yield "event: error\ndata: 分身暂时无法响应\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/debug/chat-test")
async def debug_chat_test(request: Request):
    """诊断端点：测试当前用户的 SecondMe chat 连通性。"""
    agent_id = await _get_agent_id_from_session(request)
    if not agent_id:
        return {"error": "未登录", "step": "session"}

    registry = request.app.state.agent_registry
    info = registry.get_agent_info(agent_id)
    if not info:
        return {"error": "Agent 不在网络中", "step": "registry", "agent_id": agent_id}

    if info.get("source") != "SecondMe":
        return {"error": "非 SecondMe 用户", "step": "source", "source": info.get("source")}

    # 获取 adapter 内部信息
    entry = registry._agents.get(agent_id)
    adapter = entry.adapter if entry else None
    if not adapter:
        return {"error": "无 adapter", "step": "adapter"}

    token_preview = getattr(adapter, "_access_token", "")[:20] + "..." if getattr(adapter, "_access_token", None) else "NONE"
    client = getattr(adapter, "_client", None)

    result = {
        "agent_id": agent_id,
        "adapter_type": type(adapter).__name__,
        "has_client": client is not None,
        "token_preview": token_preview,
        "steps": [],
    }

    # 尝试简单的 chat 调用
    try:
        import httpx
        base_url = client.config.api_base_url if client else "unknown"
        url = f"{base_url}/gate/lab/api/secondme/chat/stream"
        result["chat_url"] = url

        access_token = getattr(adapter, "_access_token", "")
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0), follow_redirects=True) as c:
            resp = await c.post(
                url,
                json={"messages": [{"role": "user", "content": "hello"}]},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
            )
            result["status_code"] = resp.status_code
            result["response_headers"] = dict(resp.headers)
            result["response_body"] = resp.text[:2000]
            result["steps"].append(f"HTTP POST → {resp.status_code}")

    except Exception as e:
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
        result["steps"].append(f"Exception: {type(e).__name__}: {e}")

    return result


# ── 协商 API ──

@router.post("/api/negotiate", response_model=NegotiationResponse, status_code=201)
async def negotiate(req: NegotiateRequest, request: Request):
    from towow import NegotiationSession, DemandSnapshot
    from towow.core.models import TraceChain, generate_id

    state = request.app.state
    composite = state.agent_registry

    candidate_ids = composite.get_agents_by_scope(req.scope)
    if not candidate_ids:
        raise HTTPException(400, f"scope '{req.scope}' 下没有可用的 Agent")

    scene_context = None
    scene_id = ""
    if req.scope.startswith("scene:"):
        scene_id = req.scope[len("scene:"):]
        scene_obj = state.store_scene_registry.get(scene_id)
        if scene_obj:
            scene_context = {
                "priority_strategy": scene_obj.priority_strategy,
                "domain_context": scene_obj.domain_context,
            }

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

    # 持久化：协商创建时写入 DB (ADR-007)
    # 优先从 cookie session 获取真实 agent_id，fallback 到 request body 的 user_id
    real_agent_id = await _get_agent_id_from_session(request)
    persist_user_id = real_agent_id or req.user_id
    try:
        save_negotiation(
            negotiation_id=neg_id,
            user_id=persist_user_id,
            demand_text=req.intent,
            scene_id=scene_id or "network",
            demand_mode="manual",
            scope=req.scope,
            agent_count=len(candidate_ids),
        )
    except Exception as e:
        logger.warning("History: negotiate DB write failed %s: %s", neg_id, e)

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
        "k_star": min(20, len(candidate_ids)),
        "min_score": 0.15,
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
        # Memory miss — try DB persistence (ADR-007)
        history, offers = get_negotiation_detail(neg_id)
        if history:
            participants = [
                {
                    "agent_id": o.agent_id,
                    "display_name": o.agent_name,
                    "resonance_score": o.resonance_score,
                    "state": o.agent_state,
                    "offer_content": o.offer_text,
                    "source": o.source or "",
                }
                for o in offers
            ]
            return NegotiationResponse(
                negotiation_id=history.negotiation_id,
                state=history.status,
                demand_raw=history.demand_text,
                demand_formulated=history.formulated_text,
                participants=participants,
                plan_output=history.plan_output,
                plan_json=history.plan_json,
                center_rounds=history.center_rounds,
                scope=history.scope or "all",
                agent_count=history.agent_count,
            )
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
        agent_info = request.app.state.agent_registry.get_agent_info(p.agent_id)
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
        plan_json=session.plan_json,
        center_rounds=session.center_rounds,
        scope=session.demand.scene_id or "all",
    )


# ── 历史 API (ADR-007) ──

@router.get("/api/history")
async def get_history(request: Request, scene_id: str = ""):
    """返回当前用户的协商历史列表。"""
    agent_id = await _get_agent_id_from_session(request)
    if not agent_id:
        raise HTTPException(401, "需要登录才能查看历史")

    history = get_user_history(agent_id, scene_id or None)
    return [h.to_dict() for h in history]


@router.get("/api/history/{negotiation_id}")
async def get_history_detail_endpoint(negotiation_id: str, request: Request):
    """返回单次协商详情（含所有 Offer）。"""
    agent_id = await _get_agent_id_from_session(request)
    if not agent_id:
        raise HTTPException(401, "需要登录才能查看历史")

    history, offers = get_negotiation_detail(negotiation_id)
    if not history or history.user_id != agent_id:
        raise HTTPException(404, "协商记录不存在")

    result = history.to_dict()
    result["offers"] = [o.to_dict() for o in offers]
    return result


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


def _persist_to_db(session, agent_registry=None) -> None:
    """协商完成后写入 DB (ADR-007)。更新主记录 + 保存所有 Offer。"""
    neg_id = session.negotiation_id
    try:
        from towow import NegotiationState
        status = "completed" if session.state == NegotiationState.COMPLETED else "failed"
        if session.metadata.get("error"):
            status = "failed"

        update_negotiation(
            neg_id,
            status=status,
            formulated_text=session.demand.formulated_text,
            plan_output=session.plan_output,
            plan_json=session.plan_json,
            center_rounds=session.center_rounds,
            agent_count=len(session.participants),
        )

        offer_list = []
        for p in session.participants:
            source = ""
            if agent_registry:
                agent_info = agent_registry.get_agent_info(p.agent_id)
                if agent_info:
                    source = agent_info.get("source", "")
            offer_list.append({
                "agent_id": p.agent_id,
                "agent_name": p.display_name,
                "resonance_score": p.resonance_score,
                "offer_text": p.offer.content if p.offer else "",
                "confidence": getattr(p.offer, "confidence", None) if p.offer else None,
                "agent_state": p.state.value,
                "source": source,
            })

        if offer_list:
            save_offers(neg_id, offer_list)

        logger.info("History: 协商 %s 已持久化到 DB (status=%s, offers=%d)",
                     neg_id, status, len(offer_list))
    except Exception as exc:
        logger.warning("History: 协商 %s DB 持久化失败: %s", neg_id, exc)


async def _run_negotiation(engine, session, defaults, scene_context: dict | None = None):
    from towow import NegotiationState

    try:
        async def auto_confirm():
            for _ in range(120):
                await asyncio.sleep(0.5)
                if engine.is_awaiting_confirmation(session.negotiation_id):
                    engine.confirm_formulation(session.negotiation_id)
                    return

        confirm_task = asyncio.create_task(auto_confirm())
        await engine.start_negotiation(
            session=session, scene_context=scene_context, **defaults
        )
        confirm_task.cancel()
    except Exception as e:
        logger.error("协商 %s 失败: %s", session.negotiation_id, e, exc_info=True)
        session.metadata["error"] = str(e)
        if session.state != NegotiationState.COMPLETED:
            session.state = NegotiationState.COMPLETED
    finally:
        # 持久化到 DB (ADR-007) — 替代旧的 JSON 文件持久化
        agent_registry = defaults.get("adapter")
        _persist_to_db(session, agent_registry)
