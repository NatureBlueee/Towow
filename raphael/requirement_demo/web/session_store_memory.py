"""
基于内存的 Session 存储实现

提供简单高效的内存存储，支持 TTL 过期和后台自动清理。
适用于单实例部署或开发测试环境。

特性:
- 异步安全（使用 asyncio.Lock）
- TTL 过期支持
- 后台定时清理过期数据
- 零外部依赖
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

from .session_store import SessionStore

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """内存存储条目"""
    value: str
    expires_at: Optional[datetime] = None

    @property
    def is_expired(self) -> bool:
        """检查条目是否已过期"""
        if self.expires_at is None:
            return False
        return datetime.now() >= self.expires_at


class MemorySessionStore(SessionStore):
    """
    基于内存的 Session 存储实现

    使用 Python 字典存储数据，通过后台任务定期清理过期条目。
    适用于单实例部署场景，不支持多实例共享。

    Args:
        cleanup_interval: 后台清理任务执行间隔（秒），默认 60 秒

    Example:
        store = MemorySessionStore(cleanup_interval=30)
        await store.start()

        await store.set("session:123", "user_data", ttl_seconds=3600)
        value = await store.get("session:123")

        await store.close()
    """

    def __init__(self, cleanup_interval: int = 60):
        self._data: Dict[str, MemoryEntry] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = cleanup_interval
        self._is_available = False

    async def start(self) -> None:
        """
        启动后台清理任务

        必须在使用存储前调用此方法。
        """
        self._is_available = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(
            f"MemorySessionStore started (cleanup_interval={self._cleanup_interval}s)"
        )

    async def _cleanup_loop(self) -> None:
        """后台清理循环"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                logger.debug("Cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def _cleanup_expired(self) -> None:
        """清理所有过期条目"""
        async with self._lock:
            expired_keys = [k for k, v in self._data.items() if v.is_expired]
            for key in expired_keys:
                del self._data[key]
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired sessions")

    async def get(self, key: str) -> Optional[str]:
        """
        获取 Session 值

        如果条目已过期，会自动删除并返回 None。

        Args:
            key: Session 键名

        Returns:
            Session 值，不存在或已过期时返回 None
        """
        async with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            if entry.is_expired:
                del self._data[key]
                return None
            return entry.value

    async def set(
        self,
        key: str,
        value: str,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        设置 Session 值

        Args:
            key: Session 键名
            value: Session 值
            ttl_seconds: 过期时间（秒），None 表示永不过期

        Returns:
            始终返回 True（内存操作不会失败）
        """
        async with self._lock:
            expires_at = None
            if ttl_seconds is not None:
                expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
            self._data[key] = MemoryEntry(value=value, expires_at=expires_at)
            return True

    async def delete(self, key: str) -> bool:
        """
        删除 Session

        Args:
            key: Session 键名

        Returns:
            键存在并被删除返回 True，键不存在返回 False
        """
        async with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        """
        检查 Session 是否存在

        如果条目已过期，会自动删除并返回 False。

        Args:
            key: Session 键名

        Returns:
            Session 是否存在且未过期
        """
        async with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                del self._data[key]
                return False
            return True

    async def close(self) -> None:
        """
        关闭存储并停止后台清理任务

        应在应用关闭时调用以释放资源。
        """
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        self._is_available = False
        self._data.clear()
        logger.info("MemorySessionStore closed")

    @property
    def is_available(self) -> bool:
        """存储是否可用"""
        return self._is_available

    @property
    def store_type(self) -> str:
        """存储类型标识"""
        return "memory"

    # 调试辅助方法

    async def size(self) -> int:
        """
        获取当前存储的条目数量（包含可能已过期的条目）

        仅用于调试和监控。

        Returns:
            条目数量
        """
        async with self._lock:
            return len(self._data)

    async def clear(self) -> None:
        """
        清空所有数据

        仅用于测试。
        """
        async with self._lock:
            self._data.clear()
            logger.debug("MemorySessionStore cleared")
