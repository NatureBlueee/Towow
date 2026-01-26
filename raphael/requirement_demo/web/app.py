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
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent_manager import get_agent_manager, AgentManager

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

    # 关闭时：停止所有 Agent
    logger.info("Web 服务关闭中...")
    await manager.stop_all_agents()
    logger.info("所有 Agent 已停止")


# ============ FastAPI 应用 ============

app = FastAPI(
    title="Requirement Demo - 用户注册服务",
    description="""
## 功能说明

这个服务允许用户通过 SecondMe 认证后注册为 Worker Agent。

### 主要功能

1. **用户注册** - 创建新的 Worker Agent
2. **Agent 管理** - 查看、启动、停止 Agent
3. **状态查询** - 查询 Agent 运行状态

### 流程

1. 用户通过 SecondMe 登录
2. 填写技能和专长信息
3. 系统自动创建 Worker Agent
4. Agent 连接到 OpenAgents 网络
5. Agent 注册能力到 registry
6. 完成！用户的 Agent 可以参与需求协作了
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制
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
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


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


# ============ SecondMe 认证相关（预留） ============

@app.post(
    "/api/auth/secondme/callback",
    tags=["认证"],
    summary="SecondMe 认证回调",
    description="处理 SecondMe OAuth 回调（预留接口）"
)
async def secondme_callback(code: str, state: Optional[str] = None):
    """
    SecondMe OAuth 回调处理

    这是一个预留接口，用于处理 SecondMe 的 OAuth 认证流程。
    实际实现需要根据 SecondMe 的 API 文档来完成。
    """
    # TODO: 实现 SecondMe OAuth 验证
    # 1. 用 code 换取 access_token
    # 2. 用 access_token 获取用户信息
    # 3. 返回 secondme_id 和用户基本信息

    return {
        "status": "not_implemented",
        "message": "SecondMe 认证功能待实现",
        "code": code,
        "state": state,
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
