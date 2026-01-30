# TASK-REDIS-001: 创建 SessionStore 抽象接口

> Beads 任务ID: `towow-lw6`

## 任务信息

- **任务 ID**: TASK-REDIS-001
- **所属 Epic**: SESSION-REDIS
- **状态**: pending
- **优先级**: P0 (关键路径)

## 任务描述

创建 Session 存储的抽象接口，定义统一的 API 供内存和 Redis 实现使用。

## 验收标准

- [ ] 创建 `web/session_store.py` 文件
- [ ] 定义 `SessionStore` 抽象基类
- [ ] 定义 `SessionStoreType` 枚举
- [ ] 实现 `create_session_store()` 工厂函数
- [ ] 实现 `get_session_store()` 单例获取函数
- [ ] 类型注解完整

## 依赖关系

- **硬依赖**: 无
- **被依赖**: TASK-REDIS-002, 003, 004, 005

## 实现要点

```python
# web/session_store.py

from abc import ABC, abstractmethod
from typing import Optional
from enum import Enum

class SessionStoreType(Enum):
    AUTO = "auto"
    REDIS = "redis"
    MEMORY = "memory"

class SessionStore(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[str]: ...

    @abstractmethod
    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool: ...

    @abstractmethod
    async def delete(self, key: str) -> bool: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...

    @abstractmethod
    async def close(self) -> None: ...

    @property
    @abstractmethod
    def is_available(self) -> bool: ...

# 全局单例
_session_store: Optional[SessionStore] = None

async def get_session_store() -> SessionStore:
    """获取 Session 存储单例"""
    ...

async def create_session_store(
    store_type: SessionStoreType = SessionStoreType.AUTO,
    redis_url: Optional[str] = None,
) -> SessionStore:
    """创建 Session 存储实例"""
    ...
```

## 预计工作量

1-2 小时
