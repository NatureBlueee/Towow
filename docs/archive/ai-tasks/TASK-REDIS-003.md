# TASK-REDIS-003: 实现 RedisSessionStore

> Beads 任务ID: `towow-3gj`

## 任务信息

- **任务 ID**: TASK-REDIS-003
- **所属 Epic**: SESSION-REDIS
- **状态**: completed
- **优先级**: P1

## 任务描述

实现基于 Redis 的 Session 存储，支持连接管理和健康检查。

## 验收标准

- [x] 创建 `web/session_store_redis.py` 文件
- [x] 实现 `RedisSessionStore` 类
- [x] 支持连接池
- [x] 实现健康检查
- [x] 处理连接失败
- [ ] 单元测试覆盖

## 依赖关系

- **硬依赖**: TASK-REDIS-001
- **接口依赖**: 无
- **可并行**: TASK-REDIS-002

## 新增依赖

```
redis[hiredis]>=5.0.0
```

## 实现要点

```python
# web/session_store_redis.py

import redis.asyncio as redis
from typing import Optional

class RedisSessionStore(SessionStore):
    def __init__(self, redis_url: str, key_prefix: str = "towow:"):
        self._redis_url = redis_url
        self._key_prefix = key_prefix
        self._client: Optional[redis.Redis] = None
        self._is_available = False

    async def connect(self) -> bool:
        """建立 Redis 连接"""
        try:
            self._client = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._client.ping()
            self._is_available = True
            return True
        except Exception as e:
            self._is_available = False
            return False

    def _make_key(self, key: str) -> str:
        """添加 key 前缀"""
        return f"{self._key_prefix}{key}"
```

## 预计工作量

2-3 小时
