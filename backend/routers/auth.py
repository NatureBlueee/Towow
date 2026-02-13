"""
Platform-level Auth — 统一身份认证。

路由前缀 /api/auth，由 server.py 直接 include（router 自带 prefix）。

6 个路由：
  GET  /api/auth/secondme/start     发起 SecondMe OAuth2 登录
  GET  /api/auth/secondme/callback  OAuth2 回调（注册 Agent + 设 cookie）
  GET  /api/auth/google/start       发起 Google OAuth2 登录
  GET  /api/auth/google/callback    Google OAuth2 回调（注册 Agent + 设 cookie）
  GET  /api/auth/me                 查询当前用户
  POST /api/auth/logout             登出

依赖（通过 request.app.state 访问）：
  session_store         — SessionStore（session 持久化）
  store_oauth2_client   — SecondMeOAuth2Client
  agent_registry        — AgentRegistry（Agent 注册，基础设施层唯一实例）
  encoder               — EmbeddingEncoder（向量编码）
  store_agent_vectors   — dict（向量存储）

设计文档：memory/auth-engineering-spec.md
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import urllib.parse

import httpx
from fastapi import APIRouter, Cookie, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse

from ..oauth2_client import OAuth2Error, profile_to_text

logger = logging.getLogger(__name__)

# ============ 常量 ============

SESSION_COOKIE_NAME = "towow_session"
SESSION_MAX_AGE = 7 * 24 * 60 * 60  # 7 days
AUTH_STATE_TTL = 10 * 60  # 10 minutes

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", "")  # e.g. "towow.net" for prod
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "")  # dev: "http://localhost:3000"; prod: "" (same origin)

REDIRECT_URI_MAP = {
    "localhost:8080": "http://localhost:8080/api/auth/secondme/callback",
    "localhost:3000": "http://localhost:8080/api/auth/secondme/callback",
    "127.0.0.1:8080": "http://localhost:8080/api/auth/secondme/callback",
    "towow.net": "https://towow.net/api/auth/secondme/callback",
    "www.towow.net": "https://towow.net/api/auth/secondme/callback",
    "towow-api-production-69e3.up.railway.app": "https://towow.net/api/auth/secondme/callback",
}

# ============ Google OAuth2 ============

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_SCOPES = "openid email profile"

GOOGLE_REDIRECT_URI_MAP = {
    "localhost:8080": "http://localhost:8080/api/auth/google/callback",
    "localhost:3000": "http://localhost:8080/api/auth/google/callback",
    "127.0.0.1:8080": "http://localhost:8080/api/auth/google/callback",
    "towow.net": "https://towow.net/api/auth/google/callback",
    "www.towow.net": "https://towow.net/api/auth/google/callback",
    "towow-api-production-69e3.up.railway.app": "https://towow.net/api/auth/google/callback",
}


def _get_google_redirect_uri(host: str) -> str:
    host_key = host.split("/")[0]
    return GOOGLE_REDIRECT_URI_MAP.get(
        host_key,
        os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080/api/auth/google/callback"),
    )


# ============ 统计追踪 ============

STATS_TTL = 90 * 24 * 60 * 60  # 90 天不过期


async def _track_event(session_store, event_type: str, agent_id: str = "", extra: str = ""):
    """记录一个统计事件到 session_store（持久化）。"""
    ts = datetime.now(timezone.utc).isoformat()

    # 递增计数器
    count_key = f"stats:{event_type}_count"
    current = await session_store.get(count_key)
    count = int(current) + 1 if current else 1
    await session_store.set(count_key, str(count), ttl_seconds=STATS_TTL)

    # 记录最近事件（存最近 200 条）
    log_key = f"stats:{event_type}_log"
    entry = {"ts": ts, "agent_id": agent_id, "extra": extra}
    existing = await session_store.get(log_key)
    if existing:
        try:
            log_list = json.loads(existing)
        except (json.JSONDecodeError, TypeError):
            log_list = []
    else:
        log_list = []
    log_list.append(entry)
    log_list = log_list[-200:]  # 只保留最近 200 条
    await session_store.set(log_key, json.dumps(log_list, ensure_ascii=False), ttl_seconds=STATS_TTL)

    # 唯一用户追踪
    if agent_id:
        user_key = f"stats:user:{agent_id}"
        if not await session_store.get(user_key):
            await session_store.set(user_key, ts, ttl_seconds=STATS_TTL)
            # 递增唯一用户数
            ucount_key = "stats:unique_users_count"
            ucurrent = await session_store.get(ucount_key)
            ucount = int(ucurrent) + 1 if ucurrent else 1
            await session_store.set(ucount_key, str(ucount), ttl_seconds=STATS_TTL)

    logger.info("STATS: %s agent=%s count=%d", event_type, agent_id or "-", count)


def _get_redirect_uri(host: str) -> str:
    """根据 request host 选择 redirect_uri。"""
    host_key = host.split("/")[0]
    return REDIRECT_URI_MAP.get(
        host_key,
        os.getenv(
            "SECONDME_REDIRECT_URI",
            "http://localhost:8080/api/auth/secondme/callback",
        ),
    )


# ============ SecondMe 用户持久化 ============

# 每个 SecondMe 用户一个 JSON 文件，重启后自动恢复
_SECONDME_USERS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "secondme_users"


def _persist_secondme_user(agent_id: str, profile: dict, scene_ids: list[str]) -> None:
    """将 SecondMe 用户画像写入 JSON 文件。重复登录覆盖更新。

    写入失败不阻断登录流程——持久化是最佳努力，不是硬性依赖。
    """
    try:
        _SECONDME_USERS_DIR.mkdir(parents=True, exist_ok=True)
        filepath = _SECONDME_USERS_DIR / f"{agent_id}.json"
        data = {
            "agent_id": agent_id,
            "profile": profile,
            "scene_ids": scene_ids,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("SecondMe 用户已持久化: %s → %s", agent_id, filepath.name)
    except Exception as e:
        logger.error("SecondMe 用户持久化失败 %s: %s", agent_id, e)


# ============ Agent 注册管线 ============

async def _register_agent_from_secondme(
    access_token: str,
    oauth2_client,
    registry,
    encoder,
    agent_vectors: dict,
    scene_ids: list[str] | None = None,
) -> dict:
    """
    access_token → SecondMe 画像 → Agent 注册 → 向量编码。

    Returns:
        {"agent_id", "name", "display_name", "shades_count", "memories_count"}
    """
    from towow.adapters.secondme_adapter import SecondMeAdapter

    adapter = SecondMeAdapter(oauth2_client=oauth2_client, access_token=access_token)
    profile = await adapter.fetch_and_build_profile()
    agent_id = profile["agent_id"]

    # 注册或更新 adapter（每次登录都要更新 token）
    registry.register_agent(
        agent_id=agent_id,
        adapter=adapter,
        source="SecondMe",
        scene_ids=list(scene_ids or []),
        display_name=profile.get("name", agent_id),
        profile_data=profile,
    )

    # 持久化到 JSON 文件（重启后可恢复）
    _persist_secondme_user(agent_id, profile, list(scene_ids or []))

    # 向量编码
    text = profile_to_text(profile)
    try:
        vec = await encoder.encode(text or agent_id)
        agent_vectors[agent_id] = vec
    except Exception as e:
        logger.warning("向量编码失败 %s: %s", agent_id, e)

    logger.info(
        "Agent 注册: %s (name=%s, shades=%d)",
        agent_id,
        profile.get("name"),
        len(profile.get("shades", [])),
    )

    return {
        "agent_id": agent_id,
        "name": profile.get("name"),
        "display_name": profile.get("name", agent_id),
        "shades_count": len(profile.get("shades", [])),
        "memories_count": len(profile.get("memories", [])),
    }


# ============ Router ============

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.get("/secondme/start")
async def auth_start(
    request: Request,
    return_to: str = Query("/", description="登录成功后跳回的 URL"),
):
    """发起 SecondMe OAuth2 登录 → 302 重定向到 SecondMe 授权页。"""
    oauth2_client = request.app.state.store_oauth2_client
    if not oauth2_client:
        raise HTTPException(503, "SecondMe OAuth2 未配置")

    host = request.headers.get("host", "localhost:8080")
    redirect_uri = _get_redirect_uri(host)

    auth_url, state = await oauth2_client.build_authorization_url(
        redirect_uri=redirect_uri,
    )

    # 存 state → return_to 映射
    session_store = request.app.state.session_store
    await session_store.set(
        f"auth_state:{state}",
        return_to,
        ttl_seconds=AUTH_STATE_TTL,
    )

    # 统计：登录发起
    await _track_event(session_store, "auth_start", extra=host)

    logger.info("Auth start: host=%s, redirect_uri=%s, return_to=%s", host, redirect_uri, return_to)
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/secondme/callback")
async def auth_callback(
    request: Request,
    code: str = Query("", description="SecondMe 授权码"),
    state: str = Query("", description="OAuth2 state"),
):
    """SecondMe 回调 → 注册 Agent → 设 cookie → 302 回 return_to。"""
    session_store = request.app.state.session_store

    # 取 return_to（开发环境补全前端 origin）
    return_to = await session_store.get(f"auth_state:{state}")
    if return_to:
        await session_store.delete(f"auth_state:{state}")
    else:
        return_to = "/"
    if FRONTEND_ORIGIN and return_to.startswith("/"):
        return_to = FRONTEND_ORIGIN + return_to

    if not code:
        logger.warning("Auth callback: 缺少授权码")
        return RedirectResponse(
            url=f"{return_to}?error=missing_code",
            status_code=302,
        )

    oauth2_client = request.app.state.store_oauth2_client
    if not oauth2_client:
        return RedirectResponse(
            url=f"{return_to}?error=oauth_not_configured",
            status_code=302,
        )

    # 交换令牌
    host = request.headers.get("host", "localhost:8080")
    redirect_uri = _get_redirect_uri(host)

    try:
        token_set = await oauth2_client.exchange_token(code, redirect_uri=redirect_uri)
    except OAuth2Error as e:
        logger.error("Auth callback: 令牌交换失败: %s", e)
        return RedirectResponse(
            url=f"{return_to}?error=token_exchange_failed",
            status_code=302,
        )

    # 注册 Agent
    try:
        result = await _register_agent_from_secondme(
            access_token=token_set.access_token,
            oauth2_client=oauth2_client,
            registry=request.app.state.agent_registry,
            encoder=request.app.state.encoder,
            agent_vectors=request.app.state.store_agent_vectors,
        )
    except Exception as e:
        logger.error("Auth callback: Agent 注册失败: %s", e, exc_info=True)
        return RedirectResponse(
            url=f"{return_to}?error=registration_failed",
            status_code=302,
        )

    # 创建 session
    agent_id = result["agent_id"]
    session_id = secrets.token_urlsafe(32)
    await session_store.set(
        f"session:{session_id}",
        agent_id,
        ttl_seconds=SESSION_MAX_AGE,
    )

    # 设 cookie + 重定向
    response = RedirectResponse(url=return_to, status_code=302)
    cookie_kwargs = dict(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
    )
    if COOKIE_DOMAIN:
        cookie_kwargs["domain"] = COOKIE_DOMAIN
    response.set_cookie(**cookie_kwargs)

    # 统计：登录完成
    await _track_event(session_store, "auth_complete", agent_id=agent_id)

    logger.info("Auth callback: 登录成功 agent_id=%s, return_to=%s", agent_id, return_to)
    return response


@router.get("/google/start")
async def google_auth_start(
    request: Request,
    return_to: str = Query("/", description="登录成功后跳回的 URL"),
):
    """发起 Google OAuth2 登录 → 302 重定向到 Google 授权页。"""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google OAuth2 未配置")

    host = request.headers.get("host", "localhost:8080")
    redirect_uri = _get_google_redirect_uri(host)
    state = secrets.token_urlsafe(24)

    # 存 state → return_to 映射
    session_store = request.app.state.session_store
    await session_store.set(f"google_state:{state}", return_to, ttl_seconds=AUTH_STATE_TTL)

    # 统计
    await _track_event(session_store, "google_auth_start", extra=host)

    params = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    })
    auth_url = f"{GOOGLE_AUTH_URL}?{params}"

    logger.info("Google auth start: host=%s, redirect_uri=%s", host, redirect_uri)
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/google/callback")
async def google_auth_callback(
    request: Request,
    code: str = Query("", description="Google 授权码"),
    state: str = Query("", description="OAuth2 state"),
):
    """Google 回调 → 注册 Agent → 设 cookie → 302 回 return_to。"""
    session_store = request.app.state.session_store

    # 取 return_to
    return_to = await session_store.get(f"google_state:{state}")
    if return_to:
        await session_store.delete(f"google_state:{state}")
    else:
        return_to = "/"
    if FRONTEND_ORIGIN and return_to.startswith("/"):
        return_to = FRONTEND_ORIGIN + return_to

    if not code:
        logger.warning("Google callback: 缺少授权码")
        return RedirectResponse(url=f"{return_to}?error=missing_code", status_code=302)

    host = request.headers.get("host", "localhost:8080")
    redirect_uri = _get_google_redirect_uri(host)

    # 1. 交换 token
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token_resp = await client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            })
            token_resp.raise_for_status()
            tokens = token_resp.json()
    except Exception as e:
        logger.error("Google callback: token 交换失败: %s", e)
        return RedirectResponse(url=f"{return_to}?error=token_exchange_failed", status_code=302)

    access_token = tokens.get("access_token")
    if not access_token:
        logger.error("Google callback: 无 access_token")
        return RedirectResponse(url=f"{return_to}?error=no_access_token", status_code=302)

    # 2. 获取用户信息
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            userinfo_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_resp.raise_for_status()
            userinfo = userinfo_resp.json()
    except Exception as e:
        logger.error("Google callback: 获取用户信息失败: %s", e)
        return RedirectResponse(url=f"{return_to}?error=userinfo_failed", status_code=302)

    google_id = userinfo.get("id", "")
    email = userinfo.get("email", "")
    name = userinfo.get("name", email)
    picture = userinfo.get("picture", "")

    if not google_id:
        return RedirectResponse(url=f"{return_to}?error=no_google_id", status_code=302)

    agent_id = f"google_{google_id}"

    # 3. 注册 Agent（无 SecondMe adapter）
    registry = request.app.state.agent_registry
    profile_data = {
        "agent_id": agent_id,
        "name": name,
        "email": email,
        "picture": picture,
        "raw_text": f"{name} ({email})",
    }
    registry.register_agent(
        agent_id=agent_id,
        adapter=None,
        source="google",
        scene_ids=[],
        display_name=name,
        profile_data=profile_data,
    )

    # 向量编码
    encoder = request.app.state.encoder
    agent_vectors = request.app.state.store_agent_vectors
    try:
        vec = await encoder.encode(f"{name} {email}")
        agent_vectors[agent_id] = vec
    except Exception as e:
        logger.warning("Google 用户向量编码失败 %s: %s", agent_id, e)

    # 持久化
    _persist_secondme_user(agent_id, profile_data, [])

    # 4. 创建 session + cookie
    session_id = secrets.token_urlsafe(32)
    await session_store.set(f"session:{session_id}", agent_id, ttl_seconds=SESSION_MAX_AGE)

    response = RedirectResponse(url=return_to, status_code=302)
    cookie_kwargs = dict(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
    )
    if COOKIE_DOMAIN:
        cookie_kwargs["domain"] = COOKIE_DOMAIN
    response.set_cookie(**cookie_kwargs)

    # 统计
    await _track_event(session_store, "google_auth_complete", agent_id=agent_id)

    logger.info("Google callback: 登录成功 agent_id=%s (%s), return_to=%s", agent_id, email, return_to)
    return response


@router.get("/me")
async def auth_me(
    request: Request,
    towow_session: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
):
    """查询当前登录用户的 Agent 信息。"""
    if not towow_session:
        raise HTTPException(401, "未登录")

    session_store = request.app.state.session_store
    agent_id = await session_store.get(f"session:{towow_session}")
    if not agent_id:
        raise HTTPException(401, "Session 已过期")

    registry = request.app.state.agent_registry
    info = registry.get_agent_info(agent_id)
    if not info:
        # Session 存在但 Agent 不在网络中（可能重启后丢失）
        await session_store.delete(f"session:{towow_session}")
        raise HTTPException(401, "Agent 不存在，请重新登录")

    return {
        "agent_id": info.get("agent_id", agent_id),
        "name": info.get("display_name", agent_id),
        "display_name": info.get("display_name", agent_id),
        "source": info.get("source", ""),
        "scene_ids": info.get("scene_ids", []),
    }


@router.post("/logout")
async def auth_logout(
    request: Request,
    response: Response,
    towow_session: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
):
    """登出 — 删除 session + 清除 cookie。"""
    if towow_session:
        session_store = request.app.state.session_store
        await session_store.delete(f"session:{towow_session}")

    delete_kwargs = dict(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
    )
    if COOKIE_DOMAIN:
        delete_kwargs["domain"] = COOKIE_DOMAIN
    response.delete_cookie(**delete_kwargs)

    return {"success": True, "message": "已登出"}


@router.get("/stats")
async def auth_stats(
    request: Request,
    detail: bool = Query(False, description="是否返回详细事件列表"),
):
    """
    查询登录统计。

    访问：GET /api/auth/stats
    详细：GET /api/auth/stats?detail=true
    """
    session_store = request.app.state.session_store

    # 读取计数器
    starts = await session_store.get("stats:auth_start_count")
    completions = await session_store.get("stats:auth_complete_count")
    unique = await session_store.get("stats:unique_users_count")

    result = {
        "auth_starts": int(starts) if starts else 0,
        "auth_completions": int(completions) if completions else 0,
        "unique_users": int(unique) if unique else 0,
        "conversion_rate": (
            f"{int(completions) / int(starts) * 100:.1f}%"
            if starts and int(starts) > 0
            else "N/A"
        ),
    }

    if detail:
        # 返回最近事件列表
        start_log = await session_store.get("stats:auth_start_log")
        complete_log = await session_store.get("stats:auth_complete_log")
        result["recent_starts"] = json.loads(start_log) if start_log else []
        result["recent_completions"] = json.loads(complete_log) if complete_log else []

    return result
