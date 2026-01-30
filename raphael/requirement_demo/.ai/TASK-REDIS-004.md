# TASK-REDIS-004: 修改 app.py 使用 SessionStore

> Beads 任务ID: `towow-l2y`

## 任务信息

- **任务 ID**: TASK-REDIS-004
- **所属 Epic**: SESSION-REDIS
- **状态**: pending
- **优先级**: P1

## 任务描述

修改 `app.py`，将内存 Session 存储替换为 SessionStore 抽象接口。

## 验收标准

- [ ] 移除 `_sessions` 和 `_pending_auth_sessions` 变量
- [ ] 在 lifespan 中初始化 SessionStore
- [ ] 修改所有 Session 操作使用 SessionStore
- [ ] 移除 `cleanup_expired_pending_auth` 任务（由 SessionStore 处理 TTL）
- [ ] 功能测试通过

## 依赖关系

- **硬依赖**: TASK-REDIS-001
- **接口依赖**: TASK-REDIS-002, TASK-REDIS-003
- **可并行**: TASK-REDIS-005

## 修改点

| 行号 | 当前代码 | 修改说明 |
|------|---------|---------|
| 250-259 | 内存存储定义 | 删除 |
| 274-293 | `cleanup_expired_pending_auth()` | 删除 |
| 299-361 | `lifespan()` | 添加 SessionStore 初始化 |
| 722 | `_sessions[session_id] = agent_id` | 改用 `session_store.set()` |
| 741-750 | `_pending_auth_sessions[...]` | 改用 `session_store.set()` |
| 914 | `_sessions.get(towow_session)` | 改用 `session_store.get()` |
| 952-953 | `_sessions.pop(towow_session)` | 改用 `session_store.delete()` |
| 1168 | WebSocket session 验证 | 改用 `session_store.get()` |

## 实现要点

```python
# lifespan 修改
@asynccontextmanager
async def lifespan(app: FastAPI):
    from .session_store import get_session_store

    session_store = await get_session_store()
    app.state.session_store = session_store
    logger.info(f"Session store: {type(session_store).__name__}")

    yield

    await session_store.close()

# Session 操作修改
session_store = request.app.state.session_store
await session_store.set(f"session:{session_id}", agent_id, ttl_seconds=SESSION_MAX_AGE)
```

## 预计工作量

3-4 小时
