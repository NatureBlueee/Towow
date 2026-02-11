"""
Platform-level Auth — 统一身份认证。

路由前缀 /api/auth，由 server.py 直接 include（router 自带 prefix）。

4 个路由：
  GET  /api/auth/secondme/start     发起 SecondMe OAuth2 登录
  GET  /api/auth/secondme/callback  OAuth2 回调（注册 Agent + 设 cookie）
  GET  /api/auth/me                 查询当前用户
  POST /api/auth/logout             登出

依赖（通过 request.app.state 访问）：
  session_store         — SessionStore（session 持久化）
  store_oauth2_client   — SecondMeOAuth2Client
  store_composite       — CompositeAdapter（Agent 注册）
  encoder               — EmbeddingEncoder（向量编码）
  store_agent_vectors   — dict（向量存储）

设计文档：memory/auth-engineering-spec.md
"""

from __future__ import annotations

import logging
import os
import secrets
from typing import Optional

from fastapi import APIRouter, Cookie, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse

from ..oauth2_client import OAuth2Error, profile_to_text

logger = logging.getLogger(__name__)

# ============ 常量 ============

SESSION_COOKIE_NAME = "towow_session"
SESSION_MAX_AGE = 7 * 24 * 60 * 60  # 7 days
AUTH_STATE_TTL = 10 * 60  # 10 minutes

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

REDIRECT_URI_MAP = {
    "localhost:8080": "http://localhost:8080/api/auth/secondme/callback",
    "localhost:3000": "http://localhost:8080/api/auth/secondme/callback",
    "127.0.0.1:8080": "http://localhost:8080/api/auth/secondme/callback",
    "towow.net": "https://towow.net/api/auth/secondme/callback",
    "towow-api-production.up.railway.app": "https://towow.net/api/auth/secondme/callback",
}


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


# ============ Agent 注册管线 ============

async def _register_agent_from_secondme(
    access_token: str,
    oauth2_client,
    composite,
    encoder,
    agent_vectors: dict,
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

    # 检查是否已注册（幂等）
    existing = composite.get_agent_info(agent_id)
    if not existing:
        composite.register_agent(
            agent_id=agent_id,
            adapter=adapter,
            source="SecondMe",
            scene_ids=[],
            display_name=profile.get("name", agent_id),
        )

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

    # 取 return_to
    return_to = await session_store.get(f"auth_state:{state}")
    if return_to:
        await session_store.delete(f"auth_state:{state}")
    else:
        return_to = "/"

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
            composite=request.app.state.store_composite,
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
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
    )

    logger.info("Auth callback: 登录成功 agent_id=%s, return_to=%s", agent_id, return_to)
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

    composite = request.app.state.store_composite
    info = composite.get_agent_info(agent_id)
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

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
    )

    return {"success": True, "message": "已登出"}
