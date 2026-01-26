"""
Web 注册服务 - FastAPI 应用

提供用户注册 API，当用户通过 SecondMe 登录后，
系统会自动为其创建一个 Worker Agent。

启动方式:
    uvicorn web.app:app --reload --port 8080

或者直接运行:
    python -m web.app
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, Field

from .agent_manager import get_agent_manager, AgentManager
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
    open_id: str = Field(..., description="SecondMe open_id")
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


# ============ 临时 Token 存储 ============
# 生产环境建议使用 Redis 或数据库
_pending_auth_sessions: Dict[str, Dict[str, Any]] = {}


# ============ 应用生命周期 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Web 服务启动中...")

    # 启动时：恢复所有之前注册的 Agent
    manager = get_agent_manager()

    # 可选：自动启动所有已配置的 Agent
    # await manager.start_all_agents()

    logger.info(f"已加载 {len(manager.agents_config)} 个用户配置")

    yield

    # 关闭时：停止所有 Agent 和关闭 OAuth2 客户端
    logger.info("Web 服务关闭中...")
    await manager.stop_all_agents()

    # 关闭 OAuth2 客户端
    try:
        oauth_client = get_oauth2_client()
        await oauth_client.close()
    except ValueError:
        pass  # OAuth2 未配置，忽略

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
async def auth_login():
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
        oauth_client = get_oauth2_client()
        auth_url, state = oauth_client.build_authorization_url()

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
    response_model=AuthCallbackResponse,
    tags=["认证"],
    summary="处理 OAuth2 回调",
    description="处理 SecondMe OAuth2 授权回调，用授权码换取 Token 并获取用户信息"
)
async def auth_callback(
    code: str = Query(..., description="授权码"),
    state: str = Query(..., description="CSRF 防护的 state 参数"),
):
    """
    处理 SecondMe OAuth2 授权回调

    参数：
    - code: SecondMe 返回的授权码
    - state: 用于验证请求合法性的 state 参数

    返回用户基本信息，前端可以显示补填页面让用户完善技能信息。
    """
    oauth_client = get_oauth2_client()

    # 验证 state（防止 CSRF 攻击）
    if not oauth_client.verify_state(state):
        logger.warning(f"Invalid state in OAuth callback: {state[:20]}...")
        raise HTTPException(
            status_code=400,
            detail="Invalid state parameter. 请重新发起登录流程。"
        )

    try:
        # 1. 用授权码换取 Token
        token_set = await oauth_client.exchange_token(code)

        # 2. 获取用户信息
        user_info = await oauth_client.get_user_info(token_set.access_token)

        # 3. 检查用户是否已注册
        manager = get_agent_manager()
        agent_id = manager.generate_agent_id(token_set.open_id)
        existing_agent = manager.get_agent_info(agent_id)

        needs_registration = existing_agent is None

        logger.info(
            f"OAuth callback success: open_id={token_set.open_id}, "
            f"name={user_info.name}, needs_registration={needs_registration}"
        )

        return AuthCallbackResponse(
            success=True,
            message="授权成功" if needs_registration else "用户已注册",
            open_id=token_set.open_id,
            name=user_info.name,
            avatar=user_info.avatar,
            bio=user_info.bio,
            access_token=token_set.access_token,
            needs_registration=needs_registration,
        )

    except OAuth2Error as e:
        logger.error(f"OAuth2 error: {e.message}, code={e.error_code}")
        raise HTTPException(
            status_code=e.status_code or 400,
            detail="OAuth2 认证失败，请重新尝试登录"
        )
    except Exception as e:
        logger.error(f"Unexpected error in OAuth callback: {e}")
        raise HTTPException(
            status_code=500,
            detail="处理授权回调时发生错误，请稍后重试"
        )


@app.post(
    "/api/auth/complete-registration",
    response_model=CompleteRegistrationResponse,
    tags=["认证"],
    summary="完成注册",
    description="用户补填技能信息后完成注册，创建 Worker Agent"
)
async def complete_registration(request: CompleteRegistrationRequest):
    """
    完成用户注册

    在用户通过 OAuth2 授权并补填技能信息后调用此接口完成注册。

    流程：
    1. 验证 access_token 有效性（必须，通过获取用户信息并验证 open_id 匹配）
    2. 使用 open_id 和用户提供的技能信息创建 Agent
    3. 启动 Agent 并返回结果
    """
    manager = get_agent_manager()

    try:
        # P0 修复：必须验证 access_token 有效性，并验证 open_id 匹配
        oauth_client = get_oauth2_client()
        user_info = await oauth_client.get_user_info(request.access_token)

        # 验证 open_id 是否匹配
        if user_info.open_id != request.open_id:
            logger.warning(
                f"open_id mismatch: request={request.open_id[:8]}..., "
                f"token={user_info.open_id[:8]}..."
            )
            raise HTTPException(
                status_code=400,
                detail="open_id 不匹配，请重新授权"
            )

        result = await manager.register_user(
            display_name=request.display_name,
            skills=request.skills,
            specialties=request.specialties,
            secondme_id=request.open_id,
            bio=request.bio,
        )

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
        oauth_client = get_oauth2_client()
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


# ============ 直接运行入口 ============

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "web.app:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
    )
