"""
Auth routes — extracted from backend/app.py for unified server.

All routes live under /api/auth/* and depend on:
- request.app.state.session_store  (SessionStore)
- request.app.state.agent_manager  (AgentManager)
- get_oauth2_client() singleton     (SecondMeOAuth2Client)
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from typing import List, Optional

from fastapi import APIRouter, Cookie, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from ..oauth2_client import (
    OAuth2Error,
    get_oauth2_client,
)

logger = logging.getLogger(__name__)

# ============ 常量 ============

PENDING_AUTH_EXPIRE_MINUTES = 15
SESSION_COOKIE_NAME = "towow_session"
SESSION_MAX_AGE = 7 * 24 * 60 * 60  # 7 days

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

REDIRECT_URI_MAP = {
    "localhost:8080": "http://localhost:8080/api/auth/callback",
    "localhost:3000": "http://localhost:8080/api/auth/callback",
    "127.0.0.1:8080": "http://localhost:8080/api/auth/callback",
    "towow-api-production.up.railway.app": "https://towow.net/api/auth/callback",
}


def get_redirect_uri_for_host(host: str) -> str:
    host_without_path = host.split("/")[0]
    return REDIRECT_URI_MAP.get(
        host_without_path,
        os.getenv("SECONDME_REDIRECT_URI", "http://localhost:8080/api/auth/callback"),
    )


def get_frontend_url_for_host(host: str) -> str:
    host_without_path = host.split("/")[0]
    if "localhost" in host_without_path or "127.0.0.1" in host_without_path:
        return "http://localhost:3000"
    return "https://towow.net"


# ============ Pydantic 模型 ============

class AuthLoginResponse(BaseModel):
    authorization_url: str
    state: str


class CompleteRegistrationRequest(BaseModel):
    access_token: str = Field(..., description="OAuth 获取的 access_token")
    open_id: Optional[str] = Field(None, description="SecondMe 用户标识")
    display_name: str = Field(..., min_length=1, max_length=50)
    skills: List[str] = Field(..., min_items=1)
    specialties: List[str] = Field(default=[])
    bio: Optional[str] = Field(None, max_length=500)


class CompleteRegistrationResponse(BaseModel):
    success: bool
    message: str
    agent_id: Optional[str] = None
    display_name: Optional[str] = None
    is_new: Optional[bool] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="OAuth2 refresh_token")


class CurrentUserResponse(BaseModel):
    agent_id: str
    display_name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    self_introduction: Optional[str] = None
    profile_completeness: Optional[int] = None
    skills: List[str]
    specialties: List[str]
    secondme_id: str


# ============ Router ============

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.get("/login", response_model=AuthLoginResponse)
async def auth_login(
    request: Request,
    return_to: Optional[str] = Query(None),
):
    try:
        host = request.headers.get("host", "localhost:8080")
        redirect_uri = get_redirect_uri_for_host(host)
        logger.info(f"Auth login from host={host}, using redirect_uri={redirect_uri}")

        session_store = request.app.state.session_store
        oauth_client = await get_oauth2_client(session_store)
        auth_url, state = await oauth_client.build_authorization_url(redirect_uri=redirect_uri)

        if return_to:
            await session_store.set(
                f"auth_return_to:{state}",
                return_to,
                ttl_seconds=600,
            )

        return AuthLoginResponse(authorization_url=auth_url, state=state)
    except ValueError as e:
        logger.error(f"OAuth2 配置错误: {e}")
        raise HTTPException(
            status_code=500,
            detail="OAuth2 配置不完整，请检查环境变量",
        )


@router.get("/callback")
async def auth_callback(
    request: Request,
    response: Response,
    code: str = Query(...),
    state: str = Query(...),
):
    host = request.headers.get("host", "localhost:8080")
    frontend_url = get_frontend_url_for_host(host)
    redirect_uri = get_redirect_uri_for_host(host)
    logger.info(f"Auth callback from host={host}, frontend_url={frontend_url}")

    session_store = request.app.state.session_store
    oauth_client = await get_oauth2_client(session_store)

    if not await oauth_client.verify_state(state):
        logger.warning(f"Invalid state in OAuth callback: {state[:20]}...")
        return RedirectResponse(
            url=f"{frontend_url}/experience-v2?error=invalid_state&error_description=请重新发起登录流程",
            status_code=302,
        )

    return_to = await session_store.get(f"auth_return_to:{state}")
    default_page = return_to or "/experience-v2"

    try:
        token_set = await oauth_client.exchange_token(code, redirect_uri=redirect_uri)
        user_info = await oauth_client.get_user_info(token_set.access_token)

        manager = request.app.state.agent_manager
        user_identifier = token_set.open_id or user_info.name or "unknown"
        agent_id = manager.generate_agent_id(user_identifier)
        existing_agent = manager.get_agent_info(agent_id)

        logger.info(
            f"OAuth callback success: identifier={user_identifier}, "
            f"name={user_info.name}, existing_agent={existing_agent is not None}"
        )

        if existing_agent:
            session_id = secrets.token_urlsafe(32)
            await session_store.set(
                f"session:{session_id}",
                agent_id,
                ttl_seconds=SESSION_MAX_AGE,
            )
            redirect_response = RedirectResponse(
                url=f"{frontend_url}{default_page}",
                status_code=302,
            )
            redirect_response.set_cookie(
                key=SESSION_COOKIE_NAME,
                value=session_id,
                max_age=SESSION_MAX_AGE,
                httponly=True,
                samesite="lax",
                secure=COOKIE_SECURE,
            )
            logger.info(f"User logged in: agent_id={agent_id}")
            return redirect_response
        else:
            if return_to and "/team-matcher" in return_to:
                logger.info(f"Auto-registering new user for Team Matcher: name={user_info.name}")
                result = await manager.register_user(
                    display_name=user_info.name or user_identifier,
                    skills=[],
                    specialties=[],
                    secondme_id=user_identifier,
                    bio=user_info.bio,
                    avatar_url=user_info.avatar,
                    access_token=token_set.access_token,
                    refresh_token=token_set.refresh_token,
                )
                if result.get("success") and result.get("agent_id"):
                    session_id = secrets.token_urlsafe(32)
                    await session_store.set(
                        f"session:{session_id}",
                        result["agent_id"],
                        ttl_seconds=SESSION_MAX_AGE,
                    )
                    redirect_response = RedirectResponse(
                        url=f"{frontend_url}{default_page}",
                        status_code=302,
                    )
                    redirect_response.set_cookie(
                        key=SESSION_COOKIE_NAME,
                        value=session_id,
                        max_age=SESSION_MAX_AGE,
                        httponly=True,
                        samesite="lax",
                        secure=COOKIE_SECURE,
                    )
                    logger.info(f"Auto-registered and logged in: agent_id={result['agent_id']}")
                    return redirect_response

            pending_session_id = secrets.token_urlsafe(32)
            pending_data = json.dumps({
                "access_token": token_set.access_token,
                "user_identifier": user_identifier,
                "name": user_info.name,
                "avatar": user_info.avatar,
                "bio": user_info.bio,
                "self_introduction": user_info.self_introduction,
                "profile_completeness": user_info.profile_completeness,
                "return_to": return_to,
            })
            await session_store.set(
                f"pending_auth:{pending_session_id}",
                pending_data,
                ttl_seconds=PENDING_AUTH_EXPIRE_MINUTES * 60,
            )

            redirect_response = RedirectResponse(
                url=f"{frontend_url}{default_page}?pending_auth={pending_session_id}",
                status_code=302,
            )
            logger.info(f"New user needs registration: name={user_info.name}")
            return redirect_response

    except OAuth2Error as e:
        logger.error(f"OAuth2 error: {e.message}, code={e.error_code}")
        return RedirectResponse(
            url=f"{frontend_url}{default_page}?error=oauth_error&error_description=OAuth2认证失败",
            status_code=302,
        )
    except Exception as e:
        logger.error(f"Unexpected error in OAuth callback: {e}")
        return RedirectResponse(
            url=f"{frontend_url}{default_page}?error=server_error&error_description=处理授权回调时发生错误",
            status_code=302,
        )


@router.post(
    "/complete-registration",
    response_model=CompleteRegistrationResponse,
)
async def complete_registration(
    http_request: Request,
    reg_request: CompleteRegistrationRequest,
    response: Response,
):
    manager = http_request.app.state.agent_manager

    try:
        oauth_client = await get_oauth2_client()
        user_info = await oauth_client.get_user_info(reg_request.access_token)

        user_identifier = user_info.open_id or user_info.name or reg_request.display_name

        logger.info(f"User verified via access_token, name={user_info.name}")

        result = await manager.register_user(
            display_name=reg_request.display_name,
            skills=reg_request.skills,
            specialties=reg_request.specialties,
            secondme_id=user_identifier,
            bio=reg_request.bio,
            access_token=reg_request.access_token,
        )

        if result.get("success") and result.get("agent_id"):
            session_id = secrets.token_urlsafe(32)
            session_store = http_request.app.state.session_store
            await session_store.set(
                f"session:{session_id}",
                result["agent_id"],
                ttl_seconds=SESSION_MAX_AGE,
            )
            response.set_cookie(
                key=SESSION_COOKIE_NAME,
                value=session_id,
                max_age=SESSION_MAX_AGE,
                httponly=True,
                samesite="lax",
                secure=COOKIE_SECURE,
            )
            logger.info(f"Session created for agent_id={result['agent_id']}")

        return CompleteRegistrationResponse(
            success=result.get("success", False),
            message=result.get("message", "注册完成"),
            agent_id=result.get("agent_id"),
            display_name=result.get("display_name"),
            is_new=result.get("is_new"),
        )

    except OAuth2Error as e:
        logger.error(f"Token validation failed: {e.message}")
        raise HTTPException(status_code=401, detail="Token 无效或已过期，请重新登录")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Complete registration failed: {e}")
        raise HTTPException(status_code=500, detail="注册过程中发生错误")


@router.post("/refresh")
async def refresh_auth_token(request: RefreshTokenRequest):
    try:
        oauth_client = await get_oauth2_client()
        token_set = await oauth_client.refresh_token(request.refresh_token)

        return {
            "success": True,
            "access_token": token_set.access_token,
            "refresh_token": token_set.refresh_token,
            "expires_in": token_set.expires_in,
            "open_id": token_set.open_id,
        }
    except OAuth2Error as e:
        logger.error(f"Token refresh failed: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 400,
            detail="刷新 Token 失败，请重新登录",
        )
    except ValueError as e:
        logger.error(f"OAuth2 configuration error: {e}")
        raise HTTPException(status_code=500, detail="服务配置错误")


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user(
    request: Request,
    towow_session: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
):
    if not towow_session:
        raise HTTPException(status_code=401, detail="未登录")

    session_store = request.app.state.session_store
    agent_id = await session_store.get(f"session:{towow_session}")
    if not agent_id:
        raise HTTPException(status_code=401, detail="Session 无效或已过期")

    manager = request.app.state.agent_manager
    agent_info = manager.get_agent_info(agent_id)

    if not agent_info:
        await session_store.delete(f"session:{towow_session}")
        raise HTTPException(status_code=401, detail="用户不存在")

    return CurrentUserResponse(
        agent_id=agent_info["agent_id"],
        display_name=agent_info["display_name"],
        avatar_url=agent_info.get("avatar_url"),
        bio=agent_info.get("bio"),
        self_introduction=agent_info.get("self_intro"),
        profile_completeness=None,
        skills=agent_info.get("skills", []),
        specialties=agent_info.get("specialties", []),
        secondme_id=agent_info.get("secondme_id", ""),
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    towow_session: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
):
    if towow_session:
        session_store = request.app.state.session_store
        agent_id = await session_store.get(f"session:{towow_session}")
        if agent_id:
            await session_store.delete(f"session:{towow_session}")
            logger.info(f"User logged out: agent_id={agent_id}")

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
    )

    return {"success": True, "message": "已登出"}


@router.get("/pending/{pending_id}")
async def get_pending_auth(request: Request, pending_id: str):
    session_store = request.app.state.session_store
    pending_data_str = await session_store.get(f"pending_auth:{pending_id}")
    if not pending_data_str:
        raise HTTPException(status_code=404, detail="待注册会话不存在或已过期")

    pending_data = json.loads(pending_data_str)

    return {
        "name": pending_data.get("name"),
        "avatar": pending_data.get("avatar"),
        "bio": pending_data.get("bio"),
        "self_introduction": pending_data.get("self_introduction"),
        "profile_completeness": pending_data.get("profile_completeness"),
        "user_identifier": pending_data.get("user_identifier"),
    }


@router.post("/pending/{pending_id}/complete")
async def complete_pending_registration(
    request: Request,
    pending_id: str,
    response: Response,
    display_name: str = Query(...),
    skills: str = Query(...),
    specialties: str = Query(""),
    bio: Optional[str] = Query(None),
):
    session_store = request.app.state.session_store
    pending_data_str = await session_store.get(f"pending_auth:{pending_id}")
    if not pending_data_str:
        raise HTTPException(status_code=404, detail="待注册会话不存在或已过期")

    pending_data = json.loads(pending_data_str)
    manager = request.app.state.agent_manager

    try:
        skills_list = [s.strip() for s in skills.split(",") if s.strip()]
        specialties_list = [s.strip() for s in specialties.split(",") if s.strip()] if specialties else []

        result = await manager.register_user(
            display_name=display_name,
            skills=skills_list,
            specialties=specialties_list,
            secondme_id=pending_data.get("user_identifier", ""),
            bio=bio or pending_data.get("bio"),
            avatar_url=pending_data.get("avatar"),
            access_token=pending_data.get("access_token"),
        )

        if result.get("success") and result.get("agent_id"):
            session_id = secrets.token_urlsafe(32)
            await session_store.set(
                f"session:{session_id}",
                result["agent_id"],
                ttl_seconds=SESSION_MAX_AGE,
            )
            await session_store.delete(f"pending_auth:{pending_id}")

            response.set_cookie(
                key=SESSION_COOKIE_NAME,
                value=session_id,
                max_age=SESSION_MAX_AGE,
                httponly=True,
                samesite="lax",
                secure=COOKIE_SECURE,
            )

            logger.info(f"Registration completed: agent_id={result['agent_id']}")

            return {
                "success": True,
                "message": "注册成功",
                "agent_id": result["agent_id"],
                "display_name": result.get("display_name"),
            }
        else:
            raise HTTPException(status_code=500, detail="注册失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Complete pending registration failed: {e}")
        raise HTTPException(status_code=500, detail="注册过程中发生错误")
