# TASK-REDIS-005: 修改 oauth2_client.py 使用 SessionStore

## 任务信息

- **任务 ID**: TASK-REDIS-005
- **所属 Epic**: SESSION-REDIS
- **状态**: pending
- **优先级**: P1

## 任务描述

修改 `oauth2_client.py`，将 OAuth2 State 存储替换为 SessionStore。

## 验收标准

- [ ] 移除 `_pending_states` 变量
- [ ] 注入 SessionStore 依赖
- [ ] 修改 `generate_state()` 使用 SessionStore
- [ ] 修改 `verify_state()` 使用 SessionStore
- [ ] 移除 `_cleanup_expired_states()` 方法
- [ ] 功能测试通过

## 依赖关系

- **硬依赖**: TASK-REDIS-001
- **接口依赖**: TASK-REDIS-002, TASK-REDIS-003
- **可并行**: TASK-REDIS-004

## 修改点

| 行号 | 当前代码 | 修改说明 |
|------|---------|---------|
| 154 | `self._pending_states = {}` | 删除 |
| 178-185 | `generate_state()` | 改用 SessionStore |
| 187-193 | `verify_state()` | 改用 SessionStore |
| 195-200 | `_cleanup_expired_states()` | 删除 |

## 实现要点

```python
class SecondMeOAuth2Client:
    def __init__(
        self,
        config: OAuth2Config,
        session_store: Optional[SessionStore] = None
    ):
        self.config = config
        self._session_store = session_store

    async def generate_state(self) -> str:
        state = secrets.token_hex(16)
        if self._session_store:
            await self._session_store.set(
                f"oauth_state:{state}",
                "1",
                ttl_seconds=STATE_EXPIRY_MINUTES * 60
            )
        return state

    async def verify_state(self, state: str) -> bool:
        if self._session_store:
            key = f"oauth_state:{state}"
            exists = await self._session_store.exists(key)
            if exists:
                await self._session_store.delete(key)
                return True
        return False
```

## 预计工作量

2-3 小时
