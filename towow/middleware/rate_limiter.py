"""
请求限流中间件 - TASK-020

提供多层次的请求限流能力：
- 全局限流：限制系统总并发数
- 单用户限流：防止单用户过度使用
- 排队机制：超出限制时排队等待
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """限流配置"""
    # 全局限流
    global_max_concurrent: int = 100      # 最大并发数
    global_queue_size: int = 50           # 排队队列大小
    global_queue_timeout: float = 30.0    # 排队超时（秒）

    # 单用户限流
    user_max_requests: int = 5            # 每分钟最大请求数
    user_window_seconds: float = 60.0     # 时间窗口（秒）
    user_burst_allowance: int = 2         # 突发允许额度

    # 白名单路径（不受限流）
    whitelist_paths: list = field(default_factory=lambda: [
        "/health",
        "/health/ready",
        "/docs",
        "/openapi.json",
        "/admin"  # 管理员 API 不受限
    ])


class RateLimiter:
    """
    请求限流器

    支持：
    - 全局并发限制
    - 单用户请求频率限制
    - 排队机制
    - 统计信息
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        初始化限流器

        Args:
            config: 限流配置
        """
        self.config = config or RateLimitConfig()

        # 全局并发控制
        self._semaphore = asyncio.Semaphore(self.config.global_max_concurrent)
        self._queue_semaphore = asyncio.Semaphore(self.config.global_queue_size)
        self._current_concurrent = 0

        # 单用户限流
        # user_id -> list of request timestamps
        self._user_requests: Dict[str, list] = defaultdict(list)

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "rejected_requests": 0,
            "queued_requests": 0,
            "queue_timeout_requests": 0,
            "user_limited_requests": 0,
            "current_concurrent": 0,
            "current_queue_size": 0
        }

        # 锁
        self._lock = asyncio.Lock()

    def _get_user_id(self, request: Request) -> str:
        """
        获取用户标识

        优先级：
        1. X-User-ID header
        2. Authorization header (取前32位)
        3. 客户端 IP
        """
        # 尝试从 header 获取用户 ID
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id

        # 尝试从 Authorization 获取
        auth = request.headers.get("Authorization")
        if auth:
            return auth[:32]

        # 使用客户端 IP
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def _is_whitelisted(self, path: str) -> bool:
        """检查路径是否在白名单中"""
        for whitelist_path in self.config.whitelist_paths:
            if path.startswith(whitelist_path):
                return True
        return False

    async def _check_user_rate_limit(self, user_id: str) -> bool:
        """
        检查用户请求频率

        Args:
            user_id: 用户标识

        Returns:
            是否允许请求
        """
        current_time = time.time()
        window_start = current_time - self.config.user_window_seconds

        async with self._lock:
            # 清理过期的请求记录
            self._user_requests[user_id] = [
                ts for ts in self._user_requests[user_id]
                if ts > window_start
            ]

            # 检查请求数量
            request_count = len(self._user_requests[user_id])
            max_allowed = (
                self.config.user_max_requests +
                self.config.user_burst_allowance
            )

            if request_count >= max_allowed:
                return False

            # 记录新请求
            self._user_requests[user_id].append(current_time)
            return True

    async def acquire(self, request: Request) -> tuple[bool, str]:
        """
        尝试获取请求许可

        Args:
            request: FastAPI 请求对象

        Returns:
            (是否获得许可, 拒绝原因)
        """
        self.stats["total_requests"] += 1
        path = request.url.path

        # 白名单路径直接放行
        if self._is_whitelisted(path):
            self.stats["allowed_requests"] += 1
            return True, ""

        user_id = self._get_user_id(request)

        # 检查用户限流
        if not await self._check_user_rate_limit(user_id):
            self.stats["user_limited_requests"] += 1
            self.stats["rejected_requests"] += 1
            return False, f"Rate limit exceeded for user: {user_id}"

        # 尝试获取全局并发许可
        if self._semaphore.locked():
            # 并发已满，尝试排队
            if self._queue_semaphore.locked():
                # 队列也满了，直接拒绝
                self.stats["rejected_requests"] += 1
                return False, "Server too busy, please try again later"

            # 进入排队
            self.stats["queued_requests"] += 1
            self.stats["current_queue_size"] += 1

            try:
                await asyncio.wait_for(
                    self._queue_semaphore.acquire(),
                    timeout=0.1  # 快速获取队列位置
                )
            except asyncio.TimeoutError:
                self.stats["current_queue_size"] -= 1
                self.stats["rejected_requests"] += 1
                return False, "Queue full"

            try:
                # 等待获取并发许可
                await asyncio.wait_for(
                    self._semaphore.acquire(),
                    timeout=self.config.global_queue_timeout
                )
                self.stats["current_queue_size"] -= 1
            except asyncio.TimeoutError:
                self._queue_semaphore.release()
                self.stats["current_queue_size"] -= 1
                self.stats["queue_timeout_requests"] += 1
                self.stats["rejected_requests"] += 1
                return False, "Queue timeout"
            finally:
                self._queue_semaphore.release()
        else:
            # 直接获取并发许可
            await self._semaphore.acquire()

        self._current_concurrent += 1
        self.stats["current_concurrent"] = self._current_concurrent
        self.stats["allowed_requests"] += 1
        return True, ""

    def release(self):
        """释放请求许可"""
        self._semaphore.release()
        self._current_concurrent -= 1
        self.stats["current_concurrent"] = self._current_concurrent

    def get_status(self) -> Dict[str, Any]:
        """获取限流器状态"""
        return {
            "config": {
                "global_max_concurrent": self.config.global_max_concurrent,
                "global_queue_size": self.config.global_queue_size,
                "user_max_requests": self.config.user_max_requests,
                "user_window_seconds": self.config.user_window_seconds
            },
            "stats": self.stats.copy(),
            "active_users": len(self._user_requests)
        }

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "rejected_requests": 0,
            "queued_requests": 0,
            "queue_timeout_requests": 0,
            "user_limited_requests": 0,
            "current_concurrent": self._current_concurrent,
            "current_queue_size": 0
        }


# 全局限流器实例
_rate_limiter: Optional[RateLimiter] = None


def rate_limit_status() -> Dict[str, Any]:
    """获取全局限流器状态"""
    if _rate_limiter:
        return _rate_limiter.get_status()
    return {"enabled": False}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI 限流中间件

    将 RateLimiter 集成到 FastAPI 应用中
    """

    def __init__(
        self,
        app,
        config: Optional[RateLimitConfig] = None,
        enabled: bool = True
    ):
        """
        初始化中间件

        Args:
            app: FastAPI 应用
            config: 限流配置
            enabled: 是否启用限流
        """
        super().__init__(app)
        self.enabled = enabled

        global _rate_limiter
        _rate_limiter = RateLimiter(config)
        self.rate_limiter = _rate_limiter

        logger.info(
            f"Rate limit middleware initialized "
            f"(enabled={enabled}, max_concurrent={config.global_max_concurrent if config else 100})"
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """处理请求"""
        if not self.enabled:
            return await call_next(request)

        # 尝试获取许可
        allowed, reason = await self.rate_limiter.acquire(request)

        if not allowed:
            logger.warning(f"Request rejected: {reason} - {request.url.path}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": reason,
                    "retry_after": 60  # 建议 60 秒后重试
                },
                headers={"Retry-After": "60"}
            )

        try:
            response = await call_next(request)
            return response
        finally:
            # 只有非白名单路径才需要释放许可
            if not self.rate_limiter._is_whitelisted(request.url.path):
                self.rate_limiter.release()


def init_rate_limiter(
    global_max_concurrent: int = 100,
    user_max_requests: int = 5,
    **kwargs
) -> RateLimiter:
    """
    初始化全局限流器

    Args:
        global_max_concurrent: 全局最大并发数
        user_max_requests: 单用户每分钟最大请求数
        **kwargs: 其他配置参数

    Returns:
        初始化后的 RateLimiter 实例
    """
    global _rate_limiter

    config = RateLimitConfig(
        global_max_concurrent=global_max_concurrent,
        user_max_requests=user_max_requests,
        **kwargs
    )
    _rate_limiter = RateLimiter(config)

    logger.info(
        f"Rate limiter initialized "
        f"(global_max={global_max_concurrent}, user_max={user_max_requests}/min)"
    )
    return _rate_limiter


def get_rate_limiter() -> Optional[RateLimiter]:
    """获取全局限流器实例"""
    return _rate_limiter
