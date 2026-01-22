"""
管理员 API - TASK-020

提供系统管理和监控能力：
- 演示模式开关
- 系统统计
- 健康检查
- 熔断器控制
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import verify_admin_token

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)]
)


# ============================================================================
# 请求/响应模型
# ============================================================================

class DemoModeToggleRequest(BaseModel):
    """演示模式切换请求"""
    enabled: bool
    scenario: Optional[str] = None


class DemoModeResponse(BaseModel):
    """演示模式响应"""
    enabled: bool
    scenario: str
    message: str


class SystemStatsResponse(BaseModel):
    """系统统计响应"""
    uptime_seconds: float
    llm_service: Dict[str, Any]
    rate_limiter: Dict[str, Any]
    demo_mode: Dict[str, Any]


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: float
    components: Dict[str, Dict[str, Any]]


# ============================================================================
# 全局状态
# ============================================================================

_start_time = time.time()


def _get_uptime() -> float:
    """获取系统运行时间"""
    return time.time() - _start_time


# ============================================================================
# API 端点
# ============================================================================

@router.get("/health", response_model=HealthCheckResponse)
async def admin_health_check():
    """
    管理员健康检查端点

    返回所有组件的详细健康状态
    """
    from services.llm import get_llm_service_with_fallback
    from middleware.rate_limiter import rate_limit_status
    from services.demo_mode import get_demo_service

    components = {}

    # LLM 服务状态
    llm_service = get_llm_service_with_fallback()
    if llm_service:
        llm_status = llm_service.get_status()
        components["llm"] = {
            "status": "healthy" if llm_status.get("llm_configured") else "degraded",
            "circuit_breaker_state": llm_status.get("circuit_breaker", {}).get("state", "unknown"),
            "fallback_count": llm_status.get("stats", {}).get("fallback_count", 0)
        }
    else:
        components["llm"] = {"status": "not_initialized"}

    # 限流器状态
    rate_status = rate_limit_status()
    if rate_status.get("enabled", True):
        stats = rate_status.get("stats", {})
        rejection_rate = 0
        if stats.get("total_requests", 0) > 0:
            rejection_rate = stats.get("rejected_requests", 0) / stats["total_requests"]
        components["rate_limiter"] = {
            "status": "healthy" if rejection_rate < 0.5 else "degraded",
            "current_concurrent": stats.get("current_concurrent", 0),
            "rejection_rate": round(rejection_rate, 4)
        }
    else:
        components["rate_limiter"] = {"status": "disabled"}

    # 演示模式状态
    demo_service = get_demo_service()
    if demo_service:
        components["demo_mode"] = {
            "status": "active" if demo_service.enabled else "inactive",
            "scenario": demo_service.config.scenario.value if demo_service.enabled else None
        }
    else:
        components["demo_mode"] = {"status": "not_initialized"}

    # 总体状态
    all_healthy = all(
        c.get("status") in ["healthy", "inactive", "disabled", "not_initialized"]
        for c in components.values()
    )

    return HealthCheckResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=time.time(),
        components=components
    )


@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats():
    """
    获取系统统计信息

    包括 LLM 服务、限流器、演示模式的详细统计
    """
    from services.llm import get_llm_service_with_fallback
    from middleware.rate_limiter import rate_limit_status
    from services.demo_mode import get_demo_service

    # LLM 服务状态
    llm_service = get_llm_service_with_fallback()
    llm_stats = llm_service.get_status() if llm_service else {"status": "not_initialized"}

    # 限流器状态
    rate_stats = rate_limit_status()

    # 演示模式状态
    demo_service = get_demo_service()
    demo_stats = demo_service.get_status() if demo_service else {"status": "not_initialized"}

    return SystemStatsResponse(
        uptime_seconds=_get_uptime(),
        llm_service=llm_stats,
        rate_limiter=rate_stats,
        demo_mode=demo_stats
    )


@router.post("/demo-mode", response_model=DemoModeResponse)
async def toggle_demo_mode(request: DemoModeToggleRequest):
    """
    切换演示模式

    启用或禁用演示模式，可指定演示场景
    """
    from services.demo_mode import (
        get_demo_service,
        init_demo_service,
        DemoScenario
    )

    demo_service = get_demo_service()
    if not demo_service:
        demo_service = init_demo_service()

    if request.enabled:
        scenario = None
        if request.scenario:
            try:
                scenario = DemoScenario(request.scenario)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid scenario: {request.scenario}. "
                           f"Available: {[s.value for s in DemoScenario]}"
                )
        demo_service.enable(scenario)
        message = f"Demo mode enabled with scenario: {demo_service.config.scenario.value}"
    else:
        demo_service.disable()
        message = "Demo mode disabled"

    logger.info(message)

    return DemoModeResponse(
        enabled=demo_service.enabled,
        scenario=demo_service.config.scenario.value,
        message=message
    )


@router.get("/demo-mode")
async def get_demo_mode_status():
    """获取演示模式状态"""
    from services.demo_mode import get_demo_service, init_demo_service

    demo_service = get_demo_service()
    if not demo_service:
        demo_service = init_demo_service()

    return demo_service.get_status()


@router.get("/demo-mode/demands")
async def list_demo_demands():
    """列出可用的演示需求"""
    from services.demo_mode import DEMO_DEMANDS
    return {"demands": DEMO_DEMANDS}


@router.get("/demo-mode/scenarios")
async def list_demo_scenarios():
    """列出可用的演示场景"""
    from services.demo_mode import DemoScenario
    return {
        "scenarios": [
            {"value": s.value, "name": s.name}
            for s in DemoScenario
        ]
    }


@router.post("/demo-mode/session")
async def start_demo_session(
    demand_key: str = Query(default="demo_travel"),
    scenario: Optional[str] = Query(default=None)
):
    """
    启动演示会话

    Args:
        demand_key: 预设需求 key
        scenario: 演示场景
    """
    from services.demo_mode import (
        get_demo_service,
        init_demo_service,
        DemoScenario
    )

    demo_service = get_demo_service()
    if not demo_service:
        demo_service = init_demo_service()

    scene = None
    if scenario:
        try:
            scene = DemoScenario(scenario)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scenario: {scenario}"
            )

    session = await demo_service.start_demo_session(demand_key, scene)
    return session


@router.post("/demo-mode/session/{session_id}/run")
async def run_demo_session(session_id: str):
    """运行演示会话协商"""
    from services.demo_mode import get_demo_service

    demo_service = get_demo_service()
    if not demo_service:
        raise HTTPException(status_code=500, detail="Demo service not initialized")

    result = await demo_service.run_demo_negotiation(session_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/circuit-breaker/reset")
async def reset_circuit_breaker():
    """
    重置熔断器

    将熔断器状态重置为 CLOSED
    """
    from services.llm import get_llm_service_with_fallback

    llm_service = get_llm_service_with_fallback()
    if not llm_service:
        raise HTTPException(
            status_code=500,
            detail="LLM service with fallback not initialized"
        )

    llm_service.reset_circuit_breaker()
    logger.info("Circuit breaker reset by admin")

    return {
        "message": "Circuit breaker reset to CLOSED state",
        "status": llm_service.circuit_breaker.get_status()
    }


@router.get("/circuit-breaker")
async def get_circuit_breaker_status():
    """获取熔断器状态"""
    from services.llm import get_llm_service_with_fallback

    llm_service = get_llm_service_with_fallback()
    if not llm_service:
        return {"status": "not_initialized"}

    return llm_service.circuit_breaker.get_status()


@router.post("/rate-limiter/reset-stats")
async def reset_rate_limiter_stats():
    """重置限流器统计信息"""
    from middleware.rate_limiter import get_rate_limiter

    rate_limiter = get_rate_limiter()
    if not rate_limiter:
        raise HTTPException(
            status_code=500,
            detail="Rate limiter not initialized"
        )

    rate_limiter.reset_stats()
    logger.info("Rate limiter stats reset by admin")

    return {
        "message": "Rate limiter stats reset",
        "status": rate_limiter.get_status()
    }


@router.get("/rate-limiter")
async def get_rate_limiter_status():
    """获取限流器状态"""
    from middleware.rate_limiter import rate_limit_status
    return rate_limit_status()


@router.post("/llm/reset-stats")
async def reset_llm_stats():
    """重置 LLM 服务统计信息"""
    from services.llm import get_llm_service_with_fallback

    llm_service = get_llm_service_with_fallback()
    if not llm_service:
        raise HTTPException(
            status_code=500,
            detail="LLM service with fallback not initialized"
        )

    llm_service.reset_stats()
    logger.info("LLM service stats reset by admin")

    return {
        "message": "LLM service stats reset",
        "status": llm_service.get_status()
    }
