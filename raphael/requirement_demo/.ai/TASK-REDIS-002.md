# TASK-REDIS-002: 实现 MemorySessionStore

> Beads 任务ID: `towow-8sh`

## 任务信息

- **任务 ID**: TASK-REDIS-002
- **所属 Epic**: SESSION-REDIS
- **状态**: completed
- **优先级**: P1

## 任务描述

实现基于内存的 Session 存储，支持 TTL 过期和后台清理。

## 验收标准

- [x] 创建 `web/session_store_memory.py` 文件
- [x] 实现 `MemorySessionStore` 类
- [x] 支持 TTL 过期
- [x] 实现后台清理任务
- [ ] 单元测试覆盖

## 依赖关系

- **硬依赖**: TASK-REDIS-001
- **接口依赖**: 无
- **可并行**: TASK-REDIS-003

## 实现要点

```python
# web/session_store_memory.py

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
import asyncio

@dataclass
class MemoryEntry:
    value: str
    expires_at: Optional[datetime] = None

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() >= self.expires_at

class MemorySessionStore(SessionStore):
    def __init__(self):
        self._data: Dict[str, MemoryEntry] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup(self, interval: int = 60):
        """启动后台清理任务"""
        ...

    async def _cleanup_loop(self):
        """清理过期数据"""
        ...
```

## 预计工作量

2-3 小时
