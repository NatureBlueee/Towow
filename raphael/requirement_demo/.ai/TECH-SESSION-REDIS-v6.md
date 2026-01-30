# Redis Session 存储迁移技术方案

## 文档元信息

- **文档类型**: 技术方案 (TECH)
- **版本**: v6
- **状态**: DRAFT
- **创建日期**: 2026-01-30
- **关联项目**: ToWow Requirement Demo

---

## 1. 目标与范围

### 1.1 核心目标

将 Session 存储从内存迁移到 Redis，实现：

1. **持久化**: Session 数据在服务重启后不丢失
2. **可扩展**: 支持多实例部署时 Session 共享
3. **高可用**: Redis 不可用时自动降级到内存存储
4. **可配置**: 通过环境变量灵活切换存储后端

### 1.2 范围边界

| 范围内 | 范围外 |
|--------|--------|
| Session 存储抽象接口 | Redis 集群配置 |
| 内存存储实现 | Session 加密 |
| Redis 存储实现 | 分布式锁 |
| OAuth2 State 存储迁移 | Token 存储 |
| 自动降级机制 | 监控告警 |

### 1.3 成功标准

- [ ] 所有 Session 操作通过抽象接口完成
- [ ] Redis 存储正常工作时，Session 在服务重启后保持
- [ ] Redis 不可用时，自动降级到内存存储且不影响服务
- [ ] 单元测试覆盖率 > 80%

---

## 2. 现状分析

### 2.1 当前实现 [VERIFIED]

基于 `web/app.py` 分析：

#### Session 存储（app.py:250-259）

```python
_pending_auth_sessions: Dict[str, Dict[str, Any]] = {}
PENDING_AUTH_EXPIRE_MINUTES = 15

_sessions: Dict[str, str] = {}  # session_id -> agent_id

SESSION_COOKIE_NAME = "towow_session"
SESSION_MAX_AGE = 7 * 24 * 60 * 60  # 7 days
```

#### OAuth2 State 存储（oauth2_client.py:154）

```python
self._pending_states: Dict[str, datetime] = {}
```

### 2.2 问题分析

| 问题 | 影响 | 严重程度 |
|------|------|----------|
| Session 存储在内存中 | 服务重启后用户需重新登录 | 高 |
| OAuth2 State 存储在内存中 | 多实例部署时 CSRF 验证失败 | 高 |
| Pending Auth 存储在内存中 | 服务重启后待注册用户丢失 | 中 |

---

## 3. 技术架构

### 3.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                       │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   app.py    │  │ oauth2_client.py│  │  其他模块...     │  │
│  └──────┬──────┘  └────────┬────────┘  └────────┬────────┘  │
│         └──────────────────┼────────────────────┘            │
│                            ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                   SessionStore (抽象接口)                 │ │
│  └─────────────────────────────────────────────────────────┘ │
│                            │                                 │
│              ┌─────────────┴─────────────┐                   │
│              ▼                           ▼                   │
│  ┌─────────────────────┐    ┌─────────────────────┐         │
│  │ MemorySessionStore  │    │  RedisSessionStore  │         │
│  │   (开发/降级用)      │    │    (生产环境)        │         │
│  └─────────────────────┘    └──────────┬──────────┘         │
└────────────────────────────────────────┼─────────────────────┘
                                         ▼
                              ┌─────────────────────┐
                              │       Redis         │
                              └─────────────────────┘
```

---

## 4. 接口契约

### 4.1 SessionStore 抽象接口

```python
# web/session_store.py

from abc import ABC, abstractmethod
from typing import Optional
from enum import Enum


class SessionStoreType(Enum):
    AUTO = "auto"      # 自动选择（优先 Redis，降级 Memory）
    REDIS = "redis"    # 强制使用 Redis
    MEMORY = "memory"  # 强制使用内存


class SessionStore(ABC):
    """Session 存储抽象接口"""

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """获取 Session 值"""
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        """设置 Session 值"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除 Session"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查 Session 是否存在"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭存储连接"""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """存储是否可用"""
        pass
```

### 4.2 Key 命名规范

| 存储类型 | Key 前缀 | 完整格式 | TTL |
|----------|----------|----------|-----|
| Session | `session:` | `session:{session_id}` | 7 天 |
| Pending Auth | `pending_auth:` | `pending_auth:{pending_id}` | 15 分钟 |
| OAuth2 State | `oauth_state:` | `oauth_state:{state}` | 10 分钟 |

---

## 5. 详细设计

### 5.1 文件结构

```
web/
├── session_store.py           # 抽象接口 + 工厂
├── session_store_memory.py    # 内存实现
├── session_store_redis.py     # Redis 实现
├── app.py                     # 修改：使用 SessionStore
└── oauth2_client.py           # 修改：使用 SessionStore
```

---

## 6. 环境变量配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `SESSION_STORE_TYPE` | string | `auto` | 存储类型：`auto`/`redis`/`memory` |
| `REDIS_URL` | string | - | Redis 连接 URL |
| `REDIS_KEY_PREFIX` | string | `towow:` | Redis Key 前缀 |

### 自动降级逻辑

```
SESSION_STORE_TYPE=auto 时：
├── 尝试连接 Redis
│   ├── 成功 → 使用 RedisSessionStore
│   └── 失败 → 降级到 MemorySessionStore

SESSION_STORE_TYPE=redis 时：
├── 尝试连接 Redis
│   ├── 成功 → 使用 RedisSessionStore
│   └── 失败 → 抛出异常，服务启动失败

SESSION_STORE_TYPE=memory 时：
└── 直接使用 MemorySessionStore
```

---

## 7. 任务依赖分析

### 7.1 依赖关系图

```
Phase 1: 基础设施
├── TASK-REDIS-001: 创建 SessionStore 抽象接口

Phase 2: 存储实现（可并行）
├── TASK-REDIS-002: 实现 MemorySessionStore ◄── TASK-REDIS-001
├── TASK-REDIS-003: 实现 RedisSessionStore ◄── TASK-REDIS-001

Phase 3: 集成（可并行）
├── TASK-REDIS-004: 修改 app.py 使用 SessionStore ◄── TASK-REDIS-001
├── TASK-REDIS-005: 修改 oauth2_client.py 使用 SessionStore ◄── TASK-REDIS-001

Phase 4: 测试与文档
└── TASK-REDIS-006: 集成测试与文档 ◄── TASK-REDIS-002, 003, 004, 005
```

### 7.2 任务依赖表

| 任务 ID | 任务名称 | 硬依赖 | 接口依赖 | 可并行 |
|---------|----------|--------|----------|--------|
| TASK-REDIS-001 | SessionStore 抽象接口 | - | - | - |
| TASK-REDIS-002 | MemorySessionStore 实现 | TASK-REDIS-001 | - | 与 003 并行 |
| TASK-REDIS-003 | RedisSessionStore 实现 | TASK-REDIS-001 | - | 与 002 并行 |
| TASK-REDIS-004 | app.py 集成 | TASK-REDIS-001 | 002, 003 | 与 005 并行 |
| TASK-REDIS-005 | oauth2_client.py 集成 | TASK-REDIS-001 | 002, 003 | 与 004 并行 |
| TASK-REDIS-006 | 集成测试与文档 | 002, 003, 004, 005 | - | - |

---

## 8. 风险与预案

| 风险 | 影响 | 概率 | 预案 |
|------|------|------|------|
| Redis 连接不稳定 | Session 丢失 | 中 | 自动降级 + 重连机制 |
| 内存存储数据丢失 | 用户需重新登录 | 高（重启时） | 提示用户，非阻塞 |
| Redis 序列化问题 | 数据读取失败 | 低 | 统一使用 JSON 序列化 |

---

## 9. 未决项

| 编号 | 问题 | 状态 |
|------|------|------|
| [OPEN-1] | 是否需要 Redis 集群支持？ | 待决策 |
| [OPEN-2] | Session 数据是否需要加密？ | 待决策 |
| [TBD-1] | Redis 部署方案（云服务/自建） | 待决策 |
