"""
基于 Redis 的 Session 存储实现

提供分布式 Session 存储，支持连接池、健康检查和自动重连。
适用于多实例部署和生产环境。

特性:
- 连接池管理
- 健康检查
- 连接失败处理
- Key 前缀支持
- 异步操作

依赖:
    pip install redis[hiredis]>=5.0.0
"""

import logging
from typing import Optional

from .session_store import SessionStore

logger = logging.getLogger(__name__)


class RedisSessionStore(SessionStore):
    """
    基于 Redis 的 Session 存储实现

    使用 redis-py 异步客户端，支持连接池和自动重连。
    适用于多实例部署场景，支持分布式 Session 共享。

    Args:
        redis_url: Redis 连接 URL，格式如 redis://localhost:6379/0
        key_prefix: Key 前缀，用于命名空间隔离，默认 "towow:"
        max_connections: 连接池最大连接数，默认 10
        socket_timeout: Socket 超时时间（秒），默认 5.0
        socket_connect_timeout: 连接超时时间（秒），默认 5.0

    Example:
        store = RedisSessionStore(
            redis_url="redis://localhost:6379/0",
            key_prefix="myapp:"
        )
        if await store.connect():
            await store.set("session:123", "user_data", ttl_seconds=3600)
            value = await store.get("session:123")
        await store.close()
    """

    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "towow:",
        max_connections: int = 10,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
    ):
        self._redis_url = redis_url
        self._key_prefix = key_prefix
        self._max_connections = max_connections
        self._socket_timeout = socket_timeout
        self._socket_connect_timeout = socket_connect_timeout
        self._client = None
        self._is_available = False

    async def connect(self) -> bool:
        """
        建立 Redis 连接

        创建连接池并验证连接可用性。

        Returns:
            连接是否成功
        """
        try:
            import redis.asyncio as redis

            self._client = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=self._max_connections,
                socket_timeout=self._socket_timeout,
                socket_connect_timeout=self._socket_connect_timeout,
            )
            # 验证连接
            await self._client.ping()
            self._is_available = True
            logger.info(
                f"Connected to Redis: {self._mask_url(self._redis_url)} "
                f"(max_connections={self._max_connections})"
            )
            return True
        except ImportError as e:
            logger.error(f"Redis package not installed: {e}")
            self._is_available = False
            return False
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self._is_available = False
            return False

    def _mask_url(self, url: str) -> str:
        """
        遮蔽 URL 中的敏感信息（密码）

        Args:
            url: Redis URL

        Returns:
            遮蔽后的 URL
        """
        # 简单遮蔽：redis://:password@host -> redis://:***@host
        if "@" in url and ":" in url.split("@")[0]:
            parts = url.split("@")
            prefix = parts[0]
            if ":" in prefix:
                # 找到密码部分并遮蔽
                scheme_and_auth = prefix.rsplit(":", 1)
                if len(scheme_and_auth) == 2:
                    return f"{scheme_and_auth[0]}:***@{parts[1]}"
        return url

    def _make_key(self, key: str) -> str:
        """
        添加 Key 前缀

        Args:
            key: 原始 Key

        Returns:
            带前缀的完整 Key
        """
        return f"{self._key_prefix}{key}"

    async def get(self, key: str) -> Optional[str]:
        """
        获取 Session 值

        Args:
            key: Session 键名

        Returns:
            Session 值，不存在或出错时返回 None
        """
        if not self._client:
            logger.warning("Redis client not initialized")
            return None
        try:
            return await self._client.get(self._make_key(key))
        except Exception as e:
            logger.error(f"Redis get error for key '{key}': {e}")
            self._is_available = False
            return None

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
        if not self._client:
            logger.warning("Redis client not initialized")
            return False
        try:
            full_key = self._make_key(key)
            if ttl_seconds is not None and ttl_seconds > 0:
                await self._client.setex(full_key, ttl_seconds, value)
            else:
                await self._client.set(full_key, value)
            return True
        except Exception as e:
            logger.error(f"Redis set error for key '{key}': {e}")
            self._is_available = False
            return False

    async def delete(self, key: str) -> bool:
        """
        删除 Session

        Args:
            key: Session 键名

        Returns:
            键存在并被删除返回 True，键不存在或出错返回 False
        """
        if not self._client:
            logger.warning("Redis client not initialized")
            return False
        try:
            result = await self._client.delete(self._make_key(key))
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error for key '{key}': {e}")
            self._is_available = False
            return False

    async def exists(self, key: str) -> bool:
        """
        检查 Session 是否存在

        Args:
            key: Session 键名

        Returns:
            Session 是否存在
        """
        if not self._client:
            logger.warning("Redis client not initialized")
            return False
        try:
            return await self._client.exists(self._make_key(key)) > 0
        except Exception as e:
            logger.error(f"Redis exists error for key '{key}': {e}")
            self._is_available = False
            return False

    async def close(self) -> None:
        """
        关闭 Redis 连接

        释放连接池资源。应在应用关闭时调用。
        """
        if self._client:
            try:
                await self._client.aclose()
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")
            finally:
                self._client = None
        self._is_available = False
        logger.info("RedisSessionStore closed")

    @property
    def is_available(self) -> bool:
        """存储是否可用"""
        return self._is_available

    @property
    def store_type(self) -> str:
        """存储类型标识"""
        return "redis"

    # 健康检查和调试方法

    async def health_check(self) -> bool:
        """
        执行健康检查

        通过 PING 命令验证 Redis 连接是否正常。

        Returns:
            连接是否健康
        """
        if not self._client:
            return False
        try:
            await self._client.ping()
            self._is_available = True
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            self._is_available = False
            return False

    async def get_info(self) -> Optional[dict]:
        """
        获取 Redis 服务器信息

        仅用于调试和监控。

        Returns:
            Redis INFO 命令返回的信息字典，出错时返回 None
        """
        if not self._client:
            return None
        try:
            info = await self._client.info()
            return {
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "uptime_in_seconds": info.get("uptime_in_seconds"),
            }
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            return None

    async def keys_count(self, pattern: str = "*") -> int:
        """
        统计匹配模式的 Key 数量

        仅用于调试和监控。注意：在大型数据库上可能较慢。

        Args:
            pattern: Key 匹配模式，默认 "*" 匹配所有

        Returns:
            匹配的 Key 数量
        """
        if not self._client:
            return 0
        try:
            full_pattern = self._make_key(pattern)
            keys = await self._client.keys(full_pattern)
            return len(keys)
        except Exception as e:
            logger.error(f"Failed to count keys: {e}")
            return 0
