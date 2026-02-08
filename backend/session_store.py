"""
Session 存储抽象接口

提供统一的 Session 存储 API，支持内存和 Redis 两种实现。
通过工厂函数自动选择最佳存储方式（优先 Redis，降级 Memory）。
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SessionStoreType(Enum):
    """Session 存储类型枚举"""
    AUTO = "auto"      # 自动选择（优先 Redis，降级 Memory）
    REDIS = "redis"    # 强制使用 Redis
    MEMORY = "memory"  # 强制使用内存


class SessionStore(ABC):
    """
    Session 存储抽象基类

    定义统一的 Session 存储接口，所有具体实现必须继承此类。
    支持异步操作，适用于 FastAPI 等异步框架。
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """
        获取 Session 值

        Args:
            key: Session 键名

        Returns:
            Session 值，不存在时返回 None
        """
        pass

    @abstractmethod
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
            设置是否成功
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        删除 Session

        Args:
            key: Session 键名

        Returns:
            True 如果键存在并被删除，False 如果键不存在
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        检查 Session 是否存在

        Args:
            key: Session 键名

        Returns:
            Session 是否存在
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        关闭存储连接

        释放资源，关闭连接池等。应在应用关闭时调用。
        """
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """
        存储是否可用

        Returns:
            存储连接是否正常可用
        """
        pass

    @property
    @abstractmethod
    def store_type(self) -> str:
        """
        获取存储类型名称

        Returns:
            存储类型标识字符串（如 "memory", "redis"）
        """
        pass


# 全局单例
_session_store: Optional[SessionStore] = None


async def get_session_store() -> SessionStore:
    """
    获取 Session 存储单例

    首次调用时根据环境变量自动创建存储实例。

    环境变量:
        SESSION_STORE_TYPE: 存储类型（auto/redis/memory），默认 auto
        REDIS_URL: Redis 连接 URL

    Returns:
        SessionStore 实例

    Raises:
        RuntimeError: 无法创建存储实例
    """
    global _session_store
    if _session_store is None:
        store_type_str = os.getenv("SESSION_STORE_TYPE", "auto")
        try:
            store_type = SessionStoreType(store_type_str.lower())
        except ValueError:
            logger.warning(
                f"Invalid SESSION_STORE_TYPE: {store_type_str}, using auto"
            )
            store_type = SessionStoreType.AUTO

        redis_url = os.getenv("REDIS_URL")
        _session_store = await create_session_store(store_type, redis_url)
    return _session_store


async def create_session_store(
    store_type: SessionStoreType = SessionStoreType.AUTO,
    redis_url: Optional[str] = None,
) -> SessionStore:
    """
    创建 Session 存储实例

    根据指定类型创建对应的存储实现。AUTO 模式下优先尝试 Redis，
    失败时自动降级到内存存储。

    Args:
        store_type: 存储类型
        redis_url: Redis 连接 URL（Redis 模式必需）

    Returns:
        SessionStore 实例

    Raises:
        ValueError: Redis 模式下未提供 redis_url
        ConnectionError: Redis 模式下连接失败
    """
    # 强制使用内存存储
    if store_type == SessionStoreType.MEMORY:
        from .session_store_memory import MemorySessionStore
        store = MemorySessionStore()
        await store.start()
        logger.info("Using memory session store (forced)")
        return store

    # 强制使用 Redis 存储
    if store_type == SessionStoreType.REDIS:
        if not redis_url:
            raise ValueError("REDIS_URL is required for redis store type")
        from .session_store_redis import RedisSessionStore
        store = RedisSessionStore(redis_url)
        if not await store.connect():
            raise ConnectionError("Failed to connect to Redis")
        logger.info("Using Redis session store (forced)")
        return store

    # AUTO 模式：优先 Redis，降级 Memory
    if redis_url:
        try:
            from .session_store_redis import RedisSessionStore
            store = RedisSessionStore(redis_url)
            if await store.connect():
                logger.info("Using Redis session store (auto)")
                return store
            else:
                logger.warning(
                    "Redis connection failed, falling back to memory"
                )
        except ImportError as e:
            logger.warning(
                f"Redis store not available: {e}, falling back to memory"
            )
        except Exception as e:
            logger.warning(
                f"Failed to initialize Redis store: {e}, falling back to memory"
            )
    else:
        logger.info("No REDIS_URL configured, using memory store")

    # 降级到内存存储
    from .session_store_memory import MemorySessionStore
    store = MemorySessionStore()
    await store.start()
    logger.info("Using memory session store (fallback)")
    return store


async def close_session_store() -> None:
    """
    关闭 Session 存储

    释放全局单例资源。应在应用关闭时调用。
    """
    global _session_store
    if _session_store:
        await _session_store.close()
        _session_store = None
        logger.info("Session store closed")


def reset_session_store() -> None:
    """
    重置 Session 存储单例（仅用于测试）

    清除全局单例引用，下次调用 get_session_store() 时会重新创建。
    注意：此函数不会关闭现有连接，测试中应先调用 close_session_store()。
    """
    global _session_store
    _session_store = None
