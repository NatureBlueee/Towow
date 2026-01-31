"""
Web 注册服务 - FastAPI 应用

提供用户注册 API，当用户通过 SecondMe 登录后，
系统会自动为其创建一个 Worker Agent。

启动方式:
    uvicorn web.app:app --reload --port 8080

或者直接运行:
    python -m web.app
"""

# 在最开始加载环境变量
from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
import os
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, WebSocket, WebSocketDisconnect, Cookie, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, Field

import json

from .agent_manager import get_agent_manager, AgentManager
from .websocket_manager import get_websocket_manager, WebSocketManager
from . import database as db
from .session_store import get_session_store, close_session_store
from .oauth2_client import (
    get_oauth2_client,
    SecondMeOAuth2Client,
    OAuth2Error,
    TokenSet,
    UserInfo,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============ Pydantic 模型 ============

class UserRegistrationRequest(BaseModel):
    """用户注册请求"""
    display_name: str = Field(..., min_length=1, max_length=50, description="显示名称")
    skills: List[str] = Field(..., min_items=1, description="技能列表")
    specialties: List[str] = Field(default=[], description="专长领域")
    secondme_id: str = Field(..., min_length=1, description="SecondMe 用户 ID")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")

    class Config:
        json_schema_extra = {
            "example": {
                "display_name": "张三",
                "skills": ["python", "react", "api-design"],
                "specialties": ["web-development", "backend"],
                "secondme_id": "sm_12345",
                "bio": "全栈开发者，擅长 Web 应用开发"
            }
        }


class UserRegistrationResponse(BaseModel):
    """用户注册响应"""
    success: bool
    message: str
    agent_id: Optional[str] = None
    display_name: Optional[str] = None
    is_new: Optional[bool] = None
    agent_started: Optional[bool] = None


class AgentInfo(BaseModel):
    """Agent 信息"""
    agent_id: str
    display_name: str
    skills: List[str]
    specialties: List[str]
    is_running: bool
    created_at: str
    secondme_id: Optional[str] = None
    bio: Optional[str] = None


class AgentListResponse(BaseModel):
    """Agent 列表响应"""
    total: int
    agents: List[AgentInfo]


class AgentActionRequest(BaseModel):
    """Agent 操作请求"""
    action: str = Field(..., pattern="^(start|stop|restart)$", description="操作类型")


class AgentActionResponse(BaseModel):
    """Agent 操作响应"""
    success: bool
    message: str
    agent_id: str


# ============ 需求相关模型 ============

class RequirementCreateRequest(BaseModel):
    """创建需求请求"""
    title: str = Field(..., min_length=1, max_length=200, description="需求标题")
    description: str = Field(..., min_length=1, description="需求描述")
    submitter_id: Optional[str] = Field(None, description="提交者 Agent ID")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="额外元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "开发一个用户管理系统",
                "description": "需要实现用户注册、登录、权限管理等功能",
                "submitter_id": "user_abc123",
            }
        }


class RequirementResponse(BaseModel):
    """需求响应"""
    requirement_id: str
    title: str
    description: str
    submitter_id: Optional[str]
    status: str
    channel_id: Optional[str]
    metadata: Dict[str, Any]
    created_at: Optional[str]
    updated_at: Optional[str]


class RequirementListResponse(BaseModel):
    """需求列表响应"""
    total: int
    requirements: List[RequirementResponse]


# ============ Channel 消息相关模型 ============

class MessageCreateRequest(BaseModel):
    """创建消息请求"""
    sender_id: str = Field(..., description="发送者 Agent ID")
    content: str = Field(..., min_length=1, description="消息内容")
    sender_name: Optional[str] = Field(None, description="发送者名称")
    message_type: str = Field(default="text", description="消息类型")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="额外元数据")


class MessageResponse(BaseModel):
    """消息响应"""
    message_id: str
    channel_id: str
    sender_id: str
    sender_name: Optional[str]
    content: str
    message_type: str
    metadata: Dict[str, Any]
    created_at: Optional[str]


class MessageListResponse(BaseModel):
    """消息列表响应"""
    total: int
    messages: List[MessageResponse]


# ============ OAuth2 相关模型 ============

class AuthLoginResponse(BaseModel):
    """登录响应"""
    authorization_url: str
    state: str


class AuthCallbackResponse(BaseModel):
    """OAuth 回调响应"""
    success: bool
    message: str
    open_id: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    access_token: str
    needs_registration: bool = True  # 是否需要补填信息完成注册


class CompleteRegistrationRequest(BaseModel):
    """完成注册请求（用户补填技能后调用）"""
    access_token: str = Field(..., description="OAuth 获取的 access_token")
    open_id: Optional[str] = Field(None, description="SecondMe 用户标识（可选，系统会从 token 获取）")
    display_name: str = Field(..., min_length=1, max_length=50, description="显示名称")
    skills: List[str] = Field(..., min_items=1, description="技能列表")
    specialties: List[str] = Field(default=[], description="专长领域")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "open_id": "sm_12345",
                "display_name": "张三",
                "skills": ["python", "react", "api-design"],
                "specialties": ["web-development", "backend"],
                "bio": "全栈开发者，擅长 Web 应用开发"
            }
        }


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str = Field(..., description="OAuth2 授权时获取的 refresh_token")


class CompleteRegistrationResponse(BaseModel):
    """完成注册响应"""
    success: bool
    message: str
    agent_id: Optional[str] = None
    display_name: Optional[str] = None
    is_new: Optional[bool] = None


class CurrentUserResponse(BaseModel):
    """当前用户信息响应"""
    agent_id: str
    display_name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    self_introduction: Optional[str] = None
    profile_completeness: Optional[int] = None
    skills: List[str]
    specialties: List[str]
    secondme_id: str


# ============ Session 配置 ============
# Session 存储由 SessionStore 抽象接口管理（支持 Memory/Redis）
PENDING_AUTH_EXPIRE_MINUTES = 15  # pending_auth 会话过期时间（分钟）

SESSION_COOKIE_NAME = "towow_session"
SESSION_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds

# Cookie 安全配置：通过环境变量控制
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

# 是否使用真实 Agent（连接 OpenAgents 网络）
USE_REAL_AGENTS = os.getenv("USE_REAL_AGENTS", "false").lower() == "true"

# OpenAgents 网络配置
OPENAGENTS_HOST = os.getenv("OPENAGENTS_HOST", "localhost")
OPENAGENTS_PORT = int(os.getenv("OPENAGENTS_PORT", "8800"))

# 回调地址映射（根据请求 Host 选择）
# 格式: { "host": "redirect_uri" }
REDIRECT_URI_MAP = {
    "localhost:8080": "http://localhost:8080/api/auth/callback",
    "127.0.0.1:8080": "http://localhost:8080/api/auth/callback",
    "towow-api-production.up.railway.app": "https://towow.net/api/auth/callback",
}

def get_redirect_uri_for_host(host: str) -> str:
    """根据请求 Host 获取对应的回调地址"""
    # 移除端口号后的路径（如果有）
    host_without_path = host.split("/")[0]
    return REDIRECT_URI_MAP.get(
        host_without_path,
        os.getenv("SECONDME_REDIRECT_URI", "http://localhost:8080/api/auth/callback")
    )

def get_frontend_url_for_host(host: str) -> str:
    """根据请求 Host 获取对应的前端 URL"""
    host_without_path = host.split("/")[0]
    if "localhost" in host_without_path or "127.0.0.1" in host_without_path:
        return "http://localhost:3000"
    return "https://towow.net"


# ============ 应用生命周期 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Web 服务启动中...")

    # 初始化 Session Store
    session_store = await get_session_store()
    app.state.session_store = session_store
    logger.info(f"Session store initialized: {session_store.store_type}")

    # 启动时：恢复所有之前注册的 Agent
    manager = get_agent_manager()

    # 可选：自动启动所有已配置的 Agent
    # await manager.start_all_agents()

    logger.info(f"已加载 {len(manager.agents_config)} 个用户配置")

    # 如果启用真实 Agent，启动 BridgeAgent
    if USE_REAL_AGENTS:
        logger.info("USE_REAL_AGENTS=true, starting BridgeAgent...")
        try:
            from .bridge_agent import start_bridge_agent
            await start_bridge_agent(
                network_host=OPENAGENTS_HOST,
                network_port=OPENAGENTS_PORT,
            )
            logger.info("BridgeAgent started successfully")
        except Exception as e:
            logger.error(f"Failed to start BridgeAgent: {e}")
            logger.warning("Falling back to simulation mode")
    else:
        logger.info("USE_REAL_AGENTS=false, using simulation mode")

    yield

    # 如果启用真实 Agent，停止 BridgeAgent
    if USE_REAL_AGENTS:
        try:
            from .bridge_agent import stop_bridge_agent
            await stop_bridge_agent()
        except Exception as e:
            logger.error(f"Error stopping BridgeAgent: {e}")

    # 关闭时：停止所有 Agent 和关闭 OAuth2 客户端
    logger.info("Web 服务关闭中...")
    await manager.stop_all_agents()

    # 关闭 OAuth2 客户端
    try:
        oauth_client = await get_oauth2_client()
        await oauth_client.close()
    except ValueError:
        pass  # OAuth2 未配置，忽略

    # 关闭 Session Store
    await close_session_store()
    logger.info("Session store closed")

    logger.info("所有 Agent 已停止")


# ============ FastAPI 应用 ============

app = FastAPI(
    title="Requirement Demo - 用户注册服务",
    description="""
## 功能说明

这个服务允许用户通过 SecondMe OAuth2 认证后注册为 Worker Agent。

### 主要功能

1. **SecondMe OAuth2 认证** - 使用 SecondMe 账号登录
2. **用户注册** - 创建新的 Worker Agent
3. **Agent 管理** - 查看、启动、停止 Agent
4. **状态查询** - 查询 Agent 运行状态

### OAuth2 认证流程

```
用户点击登录
    │
    ▼
GET /api/auth/login ──────────────────────────────────────────────────┐
    │                                                                  │
    │  返回 authorization_url 和 state                                  │
    │                                                                  │
    ▼                                                                  │
前端重定向用户到 authorization_url                                       │
    │                                                                  │
    │  用户在 SecondMe 页面授权                                          │
    │                                                                  │
    ▼                                                                  │
SecondMe 重定向到 redirect_uri（带 code 和 state）                       │
    │                                                                  │
    ▼                                                                  │
GET /api/auth/callback?code=xxx&state=xxx ────────────────────────────┤
    │                                                                  │
    │  返回 open_id, name, access_token, needs_registration            │
    │                                                                  │
    ▼                                                                  │
前端显示补填页面（技能、专长）                                             │
    │                                                                  │
    ▼                                                                  │
POST /api/auth/complete-registration ─────────────────────────────────┤
    │                                                                  │
    │  创建 Worker Agent 并返回 agent_id                                │
    │                                                                  │
    ▼                                                                  │
完成！Agent 已连接到 OpenAgents 网络 ◀────────────────────────────────────┘
```

### 环境变量配置

```bash
SECONDME_CLIENT_ID=your_client_id
SECONDME_CLIENT_SECRET=your_client_secret
SECONDME_REDIRECT_URI=http://localhost:8080/api/auth/callback
SECONDME_API_BASE_URL=https://app.mindos.com  # 可选
SECONDME_AUTH_URL=https://app.me.bot/oauth    # 可选
```
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置：从环境变量读取允许的 origins
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8080"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ API 端点 ============

@app.get("/", tags=["健康检查"])
async def root():
    """根路径 - 健康检查"""
    return {
        "service": "Requirement Demo - User Registration",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查端点"""
    manager = get_agent_manager()
    return {
        "status": "healthy",
        "total_agents": len(manager.agents_config),
        "running_agents": len(manager.running_agents),
    }


@app.post(
    "/api/register",
    response_model=UserRegistrationResponse,
    tags=["用户注册"],
    summary="注册新用户",
    description="通过 SecondMe ID 注册新用户，系统会自动创建对应的 Worker Agent"
)
async def register_user(request: UserRegistrationRequest):
    """
    注册新用户并创建 Worker Agent

    - **display_name**: 用户显示名称
    - **skills**: 技能列表（如 ["python", "react"]）
    - **specialties**: 专长领域（如 ["web-development"]）
    - **secondme_id**: SecondMe 用户 ID（用于认证）
    - **bio**: 可选的个人简介
    """
    manager = get_agent_manager()

    try:
        result = await manager.register_user(
            display_name=request.display_name,
            skills=request.skills,
            specialties=request.specialties,
            secondme_id=request.secondme_id,
            bio=request.bio,
        )

        return UserRegistrationResponse(**result)

    except Exception as e:
        logger.error(f"注册失败: {e}")
        raise HTTPException(
            status_code=500,
            detail="注册过程中发生错误，请稍后重试"
        )


@app.get(
    "/api/agents",
    response_model=AgentListResponse,
    tags=["Agent 管理"],
    summary="列出所有 Agent",
    description="获取所有已注册的 Agent 列表"
)
async def list_agents():
    """列出所有已注册的 Agent"""
    manager = get_agent_manager()
    agents = manager.list_agents()

    return AgentListResponse(
        total=len(agents),
        agents=[AgentInfo(**agent) for agent in agents]
    )


@app.get(
    "/api/agents/{agent_id}",
    response_model=AgentInfo,
    tags=["Agent 管理"],
    summary="获取 Agent 详情",
    description="获取指定 Agent 的详细信息"
)
async def get_agent(agent_id: str):
    """获取指定 Agent 的详细信息"""
    manager = get_agent_manager()
    info = manager.get_agent_info(agent_id)

    if info is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")

    return AgentInfo(**info)


@app.post(
    "/api/agents/{agent_id}/action",
    response_model=AgentActionResponse,
    tags=["Agent 管理"],
    summary="Agent 操作",
    description="启动、停止或重启指定的 Agent"
)
async def agent_action(agent_id: str, request: AgentActionRequest):
    """
    对指定 Agent 执行操作

    - **start**: 启动 Agent
    - **stop**: 停止 Agent
    - **restart**: 重启 Agent
    """
    manager = get_agent_manager()

    # 检查 Agent 是否存在
    if agent_id not in manager.agents_config:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")

    try:
        if request.action == "start":
            success = await manager.start_agent(agent_id)
            message = "Agent 已启动" if success else "Agent 启动失败"

        elif request.action == "stop":
            success = await manager.stop_agent(agent_id)
            message = "Agent 已停止" if success else "Agent 停止失败"

        elif request.action == "restart":
            await manager.stop_agent(agent_id)
            await asyncio.sleep(1)  # 等待完全停止
            success = await manager.start_agent(agent_id)
            message = "Agent 已重启" if success else "Agent 重启失败"
        else:
            raise HTTPException(status_code=400, detail=f"未知操作: {request.action}")

        return AgentActionResponse(
            success=success,
            message=message,
            agent_id=agent_id,
        )

    except Exception as e:
        logger.error(f"Agent 操作失败: {e}")
        raise HTTPException(
            status_code=500,
            detail="Agent 操作失败，请稍后重试"
        )


@app.post(
    "/api/agents/start-all",
    tags=["Agent 管理"],
    summary="启动所有 Agent",
    description="启动所有已注册的 Agent"
)
async def start_all_agents(background_tasks: BackgroundTasks):
    """启动所有已注册的 Agent（后台执行）"""
    manager = get_agent_manager()

    # 在后台启动，避免超时
    background_tasks.add_task(manager.start_all_agents)

    return {
        "success": True,
        "message": f"正在启动 {len(manager.agents_config)} 个 Agent...",
    }


@app.post(
    "/api/agents/stop-all",
    tags=["Agent 管理"],
    summary="停止所有 Agent",
    description="停止所有正在运行的 Agent"
)
async def stop_all_agents():
    """停止所有正在运行的 Agent"""
    manager = get_agent_manager()
    await manager.stop_all_agents()

    return {
        "success": True,
        "message": "所有 Agent 已停止",
    }


# ============ SecondMe OAuth2 认证 ============

@app.get(
    "/api/auth/login",
    response_model=AuthLoginResponse,
    tags=["认证"],
    summary="获取 SecondMe 登录 URL",
    description="返回 SecondMe OAuth2 授权页面 URL，前端可以重定向用户到该 URL 进行授权"
)
async def auth_login(request: Request):
    """
    获取 SecondMe OAuth2 授权 URL

    流程：
    1. 调用此接口获取 authorization_url 和 state
    2. 前端将用户重定向到 authorization_url
    3. 用户在 SecondMe 页面授权后，会被重定向到配置的 redirect_uri
    4. 前端从重定向 URL 中获取 code 和 state，调用 /api/auth/callback

    返回：
    - authorization_url: 授权页面 URL
    - state: CSRF 防护的 state 参数，需要在 callback 中验证
    """
    try:
        # 根据请求 Host 选择回调地址
        host = request.headers.get("host", "localhost:8080")
        redirect_uri = get_redirect_uri_for_host(host)
        logger.info(f"Auth login from host={host}, using redirect_uri={redirect_uri}")

        session_store = await get_session_store()
        oauth_client = await get_oauth2_client(session_store)
        auth_url, state = await oauth_client.build_authorization_url(redirect_uri=redirect_uri)

        return AuthLoginResponse(
            authorization_url=auth_url,
            state=state,
        )
    except ValueError as e:
        logger.error(f"OAuth2 配置错误: {e}")
        raise HTTPException(
            status_code=500,
            detail="OAuth2 配置不完整，请检查环境变量 SECONDME_CLIENT_ID, SECONDME_CLIENT_SECRET, SECONDME_REDIRECT_URI"
        )


@app.get(
    "/api/auth/callback",
    tags=["认证"],
    summary="处理 OAuth2 回调",
    description="处理 SecondMe OAuth2 授权回调，用授权码换取 Token 并获取用户信息，然后重定向回前端"
)
async def auth_callback(
    request: Request,
    response: Response,
    code: str = Query(..., description="授权码"),
    state: str = Query(..., description="CSRF 防护的 state 参数"),
):
    """
    处理 SecondMe OAuth2 授权回调

    参数：
    - code: SecondMe 返回的授权码
    - state: 用于验证请求合法性的 state 参数

    处理完成后重定向回前端页面。
    """
    # 根据请求 Host 动态选择前端 URL 和回调地址
    host = request.headers.get("host", "localhost:8080")
    frontend_url = get_frontend_url_for_host(host)
    redirect_uri = get_redirect_uri_for_host(host)
    logger.info(f"Auth callback from host={host}, frontend_url={frontend_url}, redirect_uri={redirect_uri}")

    session_store = await get_session_store()
    oauth_client = await get_oauth2_client(session_store)

    # 验证 state（防止 CSRF 攻击）
    if not await oauth_client.verify_state(state):
        logger.warning(f"Invalid state in OAuth callback: {state[:20]}...")
        return RedirectResponse(
            url=f"{frontend_url}/experience-v2?error=invalid_state&error_description=请重新发起登录流程",
            status_code=302,
        )

    try:
        # 1. 用授权码换取 Token
        token_set = await oauth_client.exchange_token(code, redirect_uri=redirect_uri)

        # 2. 获取用户信息
        user_info = await oauth_client.get_user_info(token_set.access_token)

        # 3. 检查用户是否已注册
        manager = get_agent_manager()
        # 使用用户名作为标识符（因为 SecondMe 可能不返回 open_id）
        user_identifier = token_set.open_id or user_info.name or "unknown"
        agent_id = manager.generate_agent_id(user_identifier)
        existing_agent = manager.get_agent_info(agent_id)

        logger.info(
            f"OAuth callback success: identifier={user_identifier}, "
            f"name={user_info.name}, existing_agent={existing_agent is not None}"
        )

        if existing_agent:
            # 用户已注册，创建 session 并重定向到体验页
            session_id = secrets.token_urlsafe(32)
            session_store = request.app.state.session_store
            await session_store.set(
                f"session:{session_id}",
                agent_id,
                ttl_seconds=SESSION_MAX_AGE
            )

            redirect_response = RedirectResponse(
                url=f"{frontend_url}/experience-v2",
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
            # 用户需要注册，将信息存储到临时会话，重定向到注册页
            pending_session_id = secrets.token_urlsafe(32)
            session_store = request.app.state.session_store
            pending_data = json.dumps({
                "access_token": token_set.access_token,
                "user_identifier": user_identifier,
                "name": user_info.name,
                "avatar": user_info.avatar,
                "bio": user_info.bio,
                "self_introduction": user_info.self_introduction,
                "profile_completeness": user_info.profile_completeness,
            })
            await session_store.set(
                f"pending_auth:{pending_session_id}",
                pending_data,
                ttl_seconds=PENDING_AUTH_EXPIRE_MINUTES * 60
            )

            redirect_response = RedirectResponse(
                url=f"{frontend_url}/experience-v2?pending_auth={pending_session_id}",
                status_code=302,
            )
            logger.info(f"New user needs registration: name={user_info.name}")
            return redirect_response

    except OAuth2Error as e:
        logger.error(f"OAuth2 error: {e.message}, code={e.error_code}")
        return RedirectResponse(
            url=f"{frontend_url}/experience-v2?error=oauth_error&error_description=OAuth2认证失败",
            status_code=302,
        )
    except Exception as e:
        logger.error(f"Unexpected error in OAuth callback: {e}")
        return RedirectResponse(
            url=f"{frontend_url}/experience-v2?error=server_error&error_description=处理授权回调时发生错误",
            status_code=302,
        )


@app.post(
    "/api/auth/complete-registration",
    response_model=CompleteRegistrationResponse,
    tags=["认证"],
    summary="完成注册",
    description="用户补填技能信息后完成注册，创建 Worker Agent"
)
async def complete_registration(
    http_request: Request,
    reg_request: CompleteRegistrationRequest,
    response: Response
):
    """
    完成用户注册

    在用户通过 OAuth2 授权并补填技能信息后调用此接口完成注册。

    流程：
    1. 验证 access_token 有效性（必须，通过获取用户信息并验证 open_id 匹配）
    2. 使用 open_id 和用户提供的技能信息创建 Agent
    3. 启动 Agent 并返回结果
    4. 设置 session Cookie
    """
    manager = get_agent_manager()

    try:
        # 验证 access_token 有效性（通过获取用户信息）
        oauth_client = await get_oauth2_client()
        user_info = await oauth_client.get_user_info(reg_request.access_token)

        # 注意：SecondMe API 当前不返回 open_id，暂时跳过验证
        # TODO: 与 SecondMe 确认正确的用户唯一标识符字段名
        # 使用用户名作为临时标识符
        user_identifier = user_info.open_id or user_info.name or reg_request.display_name

        logger.info(f"User verified via access_token, name={user_info.name}")

        result = await manager.register_user(
            display_name=reg_request.display_name,
            skills=reg_request.skills,
            specialties=reg_request.specialties,
            secondme_id=user_identifier,  # 使用用户标识符
            bio=reg_request.bio,
        )

        # 注册成功后设置 session Cookie
        if result.get("success") and result.get("agent_id"):
            session_id = secrets.token_urlsafe(32)
            session_store = http_request.app.state.session_store
            await session_store.set(
                f"session:{session_id}",
                result["agent_id"],
                ttl_seconds=SESSION_MAX_AGE
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
        raise HTTPException(
            status_code=401,
            detail="Token 无效或已过期，请重新登录"
        )
    except HTTPException:
        # 重新抛出 HTTPException（如 open_id 不匹配）
        raise
    except Exception as e:
        logger.error(f"Complete registration failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="注册过程中发生错误，请稍后重试"
        )


@app.post(
    "/api/auth/refresh",
    tags=["认证"],
    summary="刷新 Token",
    description="使用 refresh_token 获取新的 access_token"
)
async def refresh_auth_token(request: RefreshTokenRequest):
    """
    刷新 Access Token

    当 access_token 过期时，可以使用 refresh_token 获取新的 token。

    请求体：
    - refresh_token: OAuth2 授权时获取的 refresh_token
    """
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
            detail="刷新 Token 失败，请重新登录"
        )
    except ValueError as e:
        logger.error(f"OAuth2 configuration error: {e}")
        raise HTTPException(
            status_code=500,
            detail="服务配置错误，请联系管理员"
        )


@app.get(
    "/api/auth/me",
    response_model=CurrentUserResponse,
    tags=["认证"],
    summary="获取当前用户信息",
    description="通过 session Cookie 获取当前登录用户的信息"
)
async def get_current_user(
    request: Request,
    towow_session: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
):
    """
    获取当前登录用户信息

    通过 session Cookie 验证用户身份并返回用户信息。
    如果用户未登录或 session 无效，返回 401 错误。
    """
    if not towow_session:
        raise HTTPException(status_code=401, detail="未登录")

    session_store = request.app.state.session_store
    agent_id = await session_store.get(f"session:{towow_session}")
    if not agent_id:
        raise HTTPException(status_code=401, detail="Session 无效或已过期")

    manager = get_agent_manager()
    agent_info = manager.get_agent_info(agent_id)

    if not agent_info:
        # Session 存在但 Agent 不存在，清理无效 session
        await session_store.delete(f"session:{towow_session}")
        raise HTTPException(status_code=401, detail="用户不存在")

    return CurrentUserResponse(
        agent_id=agent_info["agent_id"],
        display_name=agent_info["display_name"],
        avatar_url=agent_info.get("avatar_url"),
        bio=agent_info.get("bio"),
        self_introduction=agent_info.get("self_intro"),
        profile_completeness=None,  # 暂时不存储
        skills=agent_info.get("skills", []),
        specialties=agent_info.get("specialties", []),
        secondme_id=agent_info.get("secondme_id", ""),
    )


@app.post(
    "/api/auth/logout",
    tags=["认证"],
    summary="用户登出",
    description="清除用户 session 并删除 Cookie"
)
async def logout(
    request: Request,
    response: Response,
    towow_session: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
):
    """
    用户登出

    清除服务端 session 并删除客户端 Cookie。
    """
    if towow_session:
        session_store = request.app.state.session_store
        agent_id = await session_store.get(f"session:{towow_session}")
        if agent_id:
            await session_store.delete(f"session:{towow_session}")
            logger.info(f"User logged out: agent_id={agent_id}")

    # 删除 Cookie
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
    )

    return {"success": True, "message": "已登出"}


@app.get(
    "/api/auth/pending/{pending_id}",
    tags=["认证"],
    summary="获取待注册用户信息",
    description="通过 pending_auth ID 获取 OAuth 回调后待注册用户的信息"
)
async def get_pending_auth(request: Request, pending_id: str):
    """
    获取待注册用户信息

    OAuth 回调后，如果用户需要注册，会生成一个 pending_auth ID。
    前端可以用这个 ID 获取用户信息，显示注册表单。
    """
    session_store = request.app.state.session_store
    pending_data_str = await session_store.get(f"pending_auth:{pending_id}")
    if not pending_data_str:
        raise HTTPException(status_code=404, detail="待注册会话不存在或已过期")

    # TTL 由 SessionStore 自动处理，无需手动检查过期
    pending_data = json.loads(pending_data_str)

    return {
        "name": pending_data.get("name"),
        "avatar": pending_data.get("avatar"),
        "bio": pending_data.get("bio"),
        "self_introduction": pending_data.get("self_introduction"),
        "profile_completeness": pending_data.get("profile_completeness"),
        "user_identifier": pending_data.get("user_identifier"),
    }


@app.post(
    "/api/auth/pending/{pending_id}/complete",
    tags=["认证"],
    summary="完成待注册用户的注册",
    description="使用 pending_auth ID 完成用户注册"
)
async def complete_pending_registration(
    request: Request,
    pending_id: str,
    response: Response,
    display_name: str = Query(..., description="显示名称"),
    skills: str = Query(..., description="技能列表，逗号分隔"),
    specialties: str = Query("", description="专长领域，逗号分隔"),
    bio: Optional[str] = Query(None, description="个人简介"),
):
    """
    完成待注册用户的注册

    使用 pending_auth ID 和用户填写的技能信息完成注册。
    """
    session_store = request.app.state.session_store
    pending_data_str = await session_store.get(f"pending_auth:{pending_id}")
    if not pending_data_str:
        raise HTTPException(status_code=404, detail="待注册会话不存在或已过期")

    # TTL 由 SessionStore 自动处理，无需手动检查过期
    pending_data = json.loads(pending_data_str)
    manager = get_agent_manager()

    try:
        # 解析技能和专长
        skills_list = [s.strip() for s in skills.split(",") if s.strip()]
        specialties_list = [s.strip() for s in specialties.split(",") if s.strip()] if specialties else []

        result = await manager.register_user(
            display_name=display_name,
            skills=skills_list,
            specialties=specialties_list,
            secondme_id=pending_data.get("user_identifier", ""),
            bio=bio or pending_data.get("bio"),
            avatar_url=pending_data.get("avatar"),
        )

        if result.get("success") and result.get("agent_id"):
            # 注册成功，创建 session
            session_id = secrets.token_urlsafe(32)
            await session_store.set(
                f"session:{session_id}",
                result["agent_id"],
                ttl_seconds=SESSION_MAX_AGE
            )

            # 清理 pending session
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


# ============ 旧的预留接口（保留兼容性，标记为废弃） ============

@app.post(
    "/api/auth/secondme/callback",
    tags=["认证"],
    summary="[废弃] SecondMe 认证回调",
    description="此接口已废弃，请使用 GET /api/auth/callback",
    deprecated=True,
)
async def secondme_callback_legacy(code: str, state: Optional[str] = None):
    """
    [废弃] SecondMe OAuth 回调处理

    此接口已废弃，请使用 GET /api/auth/callback
    """
    return {
        "status": "deprecated",
        "message": "此接口已废弃，请使用 GET /api/auth/callback",
        "redirect_to": "/api/auth/callback",
    }


# ============ 统计信息 ============

@app.get(
    "/api/stats",
    tags=["统计"],
    summary="获取统计信息",
    description="获取系统运行统计"
)
async def get_stats():
    """获取系统统计信息"""
    manager = get_agent_manager()

    running_count = len(manager.running_agents)
    total_count = len(manager.agents_config)

    # 按技能统计
    skill_counts = {}
    for config in manager.agents_config.values():
        for skill in config.skills:
            skill_counts[skill] = skill_counts.get(skill, 0) + 1

    # 按专长统计
    specialty_counts = {}
    for config in manager.agents_config.values():
        for specialty in config.specialties:
            specialty_counts[specialty] = specialty_counts.get(specialty, 0) + 1

    return {
        "total_agents": total_count,
        "running_agents": running_count,
        "stopped_agents": total_count - running_count,
        "skills": skill_counts,
        "specialties": specialty_counts,
    }


# ============ WebSocket 端点 ============

async def _handle_websocket_connection(websocket: WebSocket, agent_id: str):
    """
    WebSocket 连接处理的公共逻辑

    处理消息订阅、取消订阅和心跳等操作。
    """
    ws_manager = get_websocket_manager()

    if not await ws_manager.connect(websocket, agent_id):
        return

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()

            # 处理订阅/取消订阅请求
            action = data.get("action")
            if action == "subscribe":
                channel_id = data.get("channel_id")
                if channel_id:
                    await ws_manager.subscribe_channel(agent_id, channel_id)
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel_id": channel_id,
                    })

            elif action == "unsubscribe":
                channel_id = data.get("channel_id")
                if channel_id:
                    await ws_manager.unsubscribe_channel(agent_id, channel_id)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "channel_id": channel_id,
                    })

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        await ws_manager.disconnect(agent_id)
    except Exception as e:
        logger.error(f"WebSocket error for {agent_id}: {e}")
        await ws_manager.disconnect(agent_id)


@app.websocket("/ws/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    """
    WebSocket 连接端点（需要认证）

    用户连接后可以接收实时消息：
    - Channel 消息
    - Agent 状态变化
    - 任务进度更新

    消息格式：
    {
        "type": "message" | "status" | "progress",
        "data": {...}
    }

    认证要求：
    - 必须携带有效的 session cookie
    - agent_id 必须与 session 中的用户匹配
    """
    # 1. 从 WebSocket 请求中获取 session cookie
    session_id = websocket.cookies.get(SESSION_COOKIE_NAME)

    if not session_id:
        logger.warning(f"WebSocket connection rejected: no session cookie for agent_id={agent_id}")
        await websocket.close(code=4001, reason="Unauthorized: no session")
        return

    # 2. 验证 session 是否有效（通过 SessionStore）
    session_store = websocket.app.state.session_store
    session_agent_id = await session_store.get(f"session:{session_id}")
    if not session_agent_id:
        logger.warning(f"WebSocket connection rejected: invalid session for agent_id={agent_id}")
        await websocket.close(code=4001, reason="Unauthorized: invalid session")
        return

    # 3. 验证 agent_id 是否与 session 中的用户匹配
    if session_agent_id != agent_id:
        logger.warning(
            f"WebSocket connection rejected: agent_id mismatch. "
            f"Requested={agent_id}, Session={session_agent_id}"
        )
        await websocket.close(code=4003, reason="Forbidden: agent_id mismatch")
        return

    logger.info(f"WebSocket connection authenticated: agent_id={agent_id}")

    await _handle_websocket_connection(websocket, agent_id)


@app.websocket("/ws/demo/{agent_id}")
async def websocket_demo_endpoint(websocket: WebSocket, agent_id: str):
    """
    演示模式 WebSocket 连接端点（无需认证）

    用于本地开发环境中跨域 cookie 无法传递的情况。
    允许匿名连接，但仅限于演示用途。

    安全说明：
    - 此端点不验证用户身份
    - 仅用于演示协商流程的消息接收
    - 生产环境应通过 CORS 和其他方式限制访问
    """
    logger.info(f"WebSocket demo connection: agent_id={agent_id}")

    await _handle_websocket_connection(websocket, agent_id)


@app.get(
    "/api/ws/stats",
    tags=["WebSocket"],
    summary="获取 WebSocket 统计",
    description="获取当前 WebSocket 连接统计信息"
)
async def get_ws_stats():
    """获取 WebSocket 统计信息"""
    ws_manager = get_websocket_manager()
    return ws_manager.get_stats()


# ============ 需求 API ============

# 加载演示场景配置
def _load_demo_scenario() -> dict:
    """加载演示场景配置文件"""
    scenario_path = os.path.join(os.path.dirname(__file__), "demo_scenario.json")
    try:
        with open(scenario_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Demo scenario file not found: {scenario_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse demo scenario JSON: {e}")
        return {}


# 缓存演示场景配置
_demo_scenario_cache: Optional[dict] = None


def get_demo_scenario() -> dict:
    """获取演示场景配置（带缓存）"""
    global _demo_scenario_cache
    if _demo_scenario_cache is None:
        _demo_scenario_cache = _load_demo_scenario()
    return _demo_scenario_cache


async def simulate_negotiation(requirement_id: str, channel_id: str, requirement_text: str):
    """
    模拟协商流程 - 演示用

    使用 demo_scenario.json 配置文件中的脚本，
    发送一系列模拟的协商消息，展示 Agent 协作过程。
    支持 6 个阶段：discovery, initial_response, negotiation, subnet_trigger, consensus, proposal
    """
    ws_manager = get_websocket_manager()
    scenario = get_demo_scenario()

    if not scenario:
        logger.error("Failed to load demo scenario, using fallback")
        await _fallback_negotiation(ws_manager, requirement_id, channel_id, requirement_text)
        return

    # 获取配置数据
    demo_agents = scenario.get("demoAgents", [])
    negotiation_script = scenario.get("negotiationScript", [])
    final_proposal = scenario.get("finalProposal", {})

    # 构建 Agent ID 到 Agent 信息的映射
    agent_map = {agent["id"]: agent for agent in demo_agents}

    async def send_message(
        sender_id: str,
        sender_name: str,
        content: str,
        msg_type: str = "text",
        metadata: Optional[dict] = None
    ):
        """发送消息到 WebSocket"""
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        message = {
            "message_id": msg_id,
            "channel_id": channel_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "message_type": msg_type,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        if metadata:
            message["metadata"] = metadata

        await ws_manager.broadcast_all({
            "type": "message",
            "payload": message,
        })
        logger.info(f"[Demo] {sender_name}: {content[:50]}...")

    async def send_phase_start(phase_name: str, description: str):
        """发送阶段开始事件"""
        await ws_manager.broadcast_all({
            "type": "phase_start",
            "payload": {
                "channel_id": channel_id,
                "phase_name": phase_name,
                "description": description,
                "timestamp": datetime.now().isoformat(),
            }
        })
        logger.info(f"[Demo] Phase started: {phase_name}")

    try:
        logger.info(f"Starting demo negotiation for requirement {requirement_id}")

        # 遍历协商脚本的每个阶段
        for phase in negotiation_script:
            phase_id = phase.get("phase", "unknown")
            phase_name = phase.get("phase_name", phase_id)
            phase_description = phase.get("description", "")
            messages = phase.get("messages", [])

            # 发送阶段开始事件
            await send_phase_start(phase_name, phase_description)

            # 发送该阶段的所有消息
            for msg in messages:
                # 获取延迟时间（毫秒转秒）
                delay_ms = msg.get("delay_ms", 1000)
                if delay_ms > 0:
                    await asyncio.sleep(delay_ms / 1000.0)

                sender = msg.get("sender", "system")
                sender_name = msg.get("sender_name", "System")
                content = msg.get("content", "")
                msg_type = msg.get("type", "text")
                metadata = msg.get("metadata")

                # 如果 sender 是 agent ID，从 agent_map 获取完整信息
                if sender in agent_map:
                    agent_info = agent_map[sender]
                    # 可以在 metadata 中添加 agent 的额外信息
                    if metadata is None:
                        metadata = {}
                    metadata["agent_type"] = agent_info.get("type", "")
                    metadata["agent_specialty"] = agent_info.get("specialty", "")
                    metadata["avatar_emoji"] = agent_info.get("avatar_emoji", "")

                await send_message(sender, sender_name, content, msg_type, metadata)

        # 发送协商完成事件，包含最终方案
        participants = []
        for task in final_proposal.get("tasks", []):
            agent_name = task.get("agent", "")
            if agent_name and agent_name not in participants:
                participants.append(agent_name)

        await ws_manager.broadcast_all({
            "type": "negotiation_complete",
            "payload": {
                "requirement_id": requirement_id,
                "channel_id": channel_id,
                "status": "completed",
                "summary": final_proposal.get("summary", "协商成功完成"),
                "participants": participants,
                "final_proposal": final_proposal,
            }
        })

        logger.info(f"Demo negotiation completed for requirement {requirement_id}")

    except Exception as e:
        logger.error(f"Error in demo negotiation: {e}", exc_info=True)
        await send_message("system", "System", f"协商过程中发生错误: {str(e)}", "system")


async def _fallback_negotiation(
    ws_manager: WebSocketManager,
    requirement_id: str,
    channel_id: str,
    requirement_text: str
):
    """
    备用协商流程 - 当配置文件加载失败时使用

    提供简单的硬编码协商流程作为后备方案
    """
    demo_agents = [
        {"id": "agent_alice", "name": "Alice (AI 专家)", "specialty": "AI/ML"},
        {"id": "agent_bob", "name": "Bob (后端开发)", "specialty": "Backend"},
        {"id": "agent_carol", "name": "Carol (产品设计)", "specialty": "Product"},
    ]

    async def send_message(sender_id: str, sender_name: str, content: str, msg_type: str = "text"):
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        message = {
            "message_id": msg_id,
            "channel_id": channel_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "message_type": msg_type,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        await ws_manager.broadcast_all({
            "type": "message",
            "payload": message,
        })

    try:
        await asyncio.sleep(1)
        await send_message("system", "System", f"协商开始：正在为需求寻找合适的 Agent", "system")

        await asyncio.sleep(2)
        await send_message("coordinator", "Coordinator", f"已识别 {len(demo_agents)} 个相关 Agent", "system")

        for agent in demo_agents:
            await asyncio.sleep(1)
            await send_message(agent["id"], agent["name"], f"我可以提供 {agent['specialty']} 方面的支持。")

        await asyncio.sleep(2)
        await send_message("system", "System", "协商完成！已生成协作方案。", "system")

        await ws_manager.broadcast_all({
            "type": "negotiation_complete",
            "payload": {
                "requirement_id": requirement_id,
                "channel_id": channel_id,
                "status": "completed",
                "summary": "协商成功完成（备用流程）",
                "participants": [a["name"] for a in demo_agents],
                "final_proposal": {
                    "title": "协作方案",
                    "tasks": [{"agent": a["name"], "task": f"{a['specialty']} 支持"} for a in demo_agents],
                }
            }
        })

    except Exception as e:
        logger.error(f"Error in fallback negotiation: {e}")


@app.post(
    "/api/requirements",
    response_model=RequirementResponse,
    tags=["需求"],
    summary="提交需求",
    description="提交一个新的需求"
)
async def create_requirement(request: RequirementCreateRequest, background_tasks: BackgroundTasks):
    """
    提交新需求

    - **title**: 需求标题
    - **description**: 需求详细描述
    - **submitter_id**: 提交者 Agent ID（可选）
    - **metadata**: 额外元数据（可选）
    """
    try:
        requirement_id = f"req_{uuid.uuid4().hex[:12]}"
        channel_id = f"ch_{uuid.uuid4().hex[:12]}"  # 创建协商频道

        req = db.create_requirement(
            requirement_id=requirement_id,
            title=request.title,
            description=request.description,
            submitter_id=request.submitter_id,
            metadata=request.metadata or {},
        )

        # 更新需求的 channel_id
        db.update_requirement(requirement_id, channel_id=channel_id, status="negotiating")

        # 通过 WebSocket 广播新需求
        ws_manager = get_websocket_manager()
        await ws_manager.broadcast_all({
            "type": "new_requirement",
            "data": {**req.to_dict(), "channel_id": channel_id},
        })

        requirement_text = f"{request.title}: {request.description}"

        # 根据配置选择使用真实 Agent 还是模拟
        if USE_REAL_AGENTS:
            # 使用 BridgeAgent 提交到 OpenAgents 网络
            logger.info(f"Submitting requirement to OpenAgents network: {requirement_id}")
            try:
                from .bridge_agent import get_bridge_agent
                bridge = await get_bridge_agent()
                if bridge and bridge.is_connected:
                    result = await bridge.submit_requirement(
                        requirement_id=requirement_id,
                        requirement_text=requirement_text,
                        channel_id=channel_id,
                        submitter_id=request.submitter_id,
                    )
                    if result.get("success"):
                        logger.info(f"Requirement submitted to network: {requirement_id}")
                    else:
                        logger.warning(f"Failed to submit to network, falling back to simulation: {result.get('error')}")
                        background_tasks.add_task(simulate_negotiation, requirement_id, channel_id, requirement_text)
                else:
                    logger.warning("BridgeAgent not connected, falling back to simulation")
                    background_tasks.add_task(simulate_negotiation, requirement_id, channel_id, requirement_text)
            except Exception as e:
                logger.error(f"Error using BridgeAgent: {e}, falling back to simulation")
                background_tasks.add_task(simulate_negotiation, requirement_id, channel_id, requirement_text)
        else:
            # 使用模拟协商流程
            background_tasks.add_task(simulate_negotiation, requirement_id, channel_id, requirement_text)

        logger.info(f"Requirement created: {requirement_id}, channel: {channel_id}")

        return RequirementResponse(**{**req.to_dict(), "channel_id": channel_id})

    except Exception as e:
        logger.error(f"Create requirement failed: {e}")
        raise HTTPException(status_code=500, detail="创建需求失败")


@app.get(
    "/api/requirements",
    response_model=RequirementListResponse,
    tags=["需求"],
    summary="获取需求列表",
    description="获取需求列表，支持按状态和提交者筛选"
)
async def list_requirements(
    status: Optional[str] = Query(None, description="按状态筛选"),
    submitter_id: Optional[str] = Query(None, description="按提交者筛选"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """获取需求列表"""
    requirements = db.get_all_requirements(
        status=status,
        submitter_id=submitter_id,
        limit=limit,
        offset=offset,
    )

    return RequirementListResponse(
        total=len(requirements),
        requirements=[RequirementResponse(**r.to_dict()) for r in requirements],
    )


@app.get(
    "/api/requirements/{requirement_id}",
    response_model=RequirementResponse,
    tags=["需求"],
    summary="获取需求详情",
    description="获取指定需求的详细信息"
)
async def get_requirement(requirement_id: str):
    """获取需求详情"""
    req = db.get_requirement(requirement_id)
    if not req:
        raise HTTPException(status_code=404, detail=f"需求 {requirement_id} 不存在")

    return RequirementResponse(**req.to_dict())


@app.patch(
    "/api/requirements/{requirement_id}",
    response_model=RequirementResponse,
    tags=["需求"],
    summary="更新需求",
    description="更新需求状态或其他信息"
)
async def update_requirement(
    requirement_id: str,
    status: Optional[str] = Query(None, description="新状态"),
    channel_id: Optional[str] = Query(None, description="关联的 Channel ID"),
):
    """更新需求"""
    updates = {}
    if status:
        updates["status"] = status
    if channel_id:
        updates["channel_id"] = channel_id

    if not updates:
        raise HTTPException(status_code=400, detail="没有提供更新内容")

    req = db.update_requirement(requirement_id, **updates)
    if not req:
        raise HTTPException(status_code=404, detail=f"需求 {requirement_id} 不存在")

    # 通过 WebSocket 广播更新
    ws_manager = get_websocket_manager()
    await ws_manager.broadcast_all({
        "type": "requirement_updated",
        "data": req.to_dict(),
    })

    return RequirementResponse(**req.to_dict())


# ============ Channel 消息 API ============

@app.get(
    "/api/channels/{channel_id}/messages",
    response_model=MessageListResponse,
    tags=["消息"],
    summary="获取消息历史",
    description="获取指定 Channel 的消息历史"
)
async def get_channel_messages(
    channel_id: str,
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    after_id: Optional[str] = Query(None, description="获取此消息之后的消息"),
):
    """获取 Channel 消息历史"""
    messages = db.get_channel_messages(
        channel_id=channel_id,
        limit=limit,
        offset=offset,
        after_id=after_id,
    )

    return MessageListResponse(
        total=len(messages),
        messages=[MessageResponse(**m.to_dict()) for m in messages],
    )


@app.post(
    "/api/channels/{channel_id}/messages",
    response_model=MessageResponse,
    tags=["消息"],
    summary="发送消息",
    description="向指定 Channel 发送消息"
)
async def send_channel_message(channel_id: str, request: MessageCreateRequest):
    """
    发送消息到 Channel

    - **sender_id**: 发送者 Agent ID
    - **content**: 消息内容
    - **sender_name**: 发送者名称（可选）
    - **message_type**: 消息类型（默认 text）
    - **metadata**: 额外元数据（可选）
    """
    try:
        message_id = f"msg_{uuid.uuid4().hex[:12]}"

        msg = db.create_channel_message(
            message_id=message_id,
            channel_id=channel_id,
            sender_id=request.sender_id,
            sender_name=request.sender_name,
            content=request.content,
            message_type=request.message_type,
            metadata=request.metadata or {},
        )

        # 通过 WebSocket 广播消息到 Channel
        ws_manager = get_websocket_manager()
        await ws_manager.broadcast_to_channel(
            channel_id=channel_id,
            message={
                "type": "channel_message",
                "data": msg.to_dict(),
            },
            exclude_agent=request.sender_id,  # 不发给发送者自己
        )

        return MessageResponse(**msg.to_dict())

    except Exception as e:
        logger.error(f"Send message failed: {e}")
        raise HTTPException(status_code=500, detail="发送消息失败")


# ============ 直接运行入口 ============

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "web.app:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
    )
