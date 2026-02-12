# PLAN-001: AgentRegistry 统一实施计划

**日期**: 2026-02-12
**前置文档**:
- [ADR-001: 统一 Adapter 注册表](./ADR-001-unified-adapter-registry.md)（已批准的三个决策）
- [Issue 001: Formulation 数据管道断裂](../issues/001-formulation-pipeline-broken.md)（五个根因）
**产出要求**: 生产级，做完直接能用。不是中间态。

---

## 目标

修复 formulation 数据管道断裂，统一 adapter 基础设施，使：
1. SecondMe 用户的分身在 V1 negotiation 中生效（"通向惊喜"恢复）
2. Formulation 不再卡死（超时 + 错误处理）
3. 用户遇到错误时得到诚实的反馈
4. 未来任何新应用接入时，adapter 基础设施已经在那里

## 执行原则

- **增量可运行**: 每个 Phase 结束时系统完整可用
- **一次做对**: 不留"后面再改"的技术债
- **变更传播**: 改一个文件时，沿依赖图追问所有受影响方
- **190 测试基线**: 每个 Phase 结束时所有测试通过

---

## 工程决策补充（2026-02-12 第二轮分析）

以下 6 项决策解决了 PLAN 初版中的模糊点。每项都附有分析和理由。

### ED-1: ClaudeAdapter.profiles 参数 → 删除

**现状**: `ClaudeAdapter.__init__` 接受 `profiles: dict` 参数（`claude_adapter.py:36`），`get_profile()` 从中查找（`line 48-50`）。`server.py:133` 传入 `app.state.profiles`。

**决策**: 删除 `profiles` 参数。`get_profile()` 简化为 `return {"agent_id": agent_id}`。

**理由**: AgentRegistry 接管了 profile 路由职责。ClaudeAdapter 的身份是"默认 LLM 通道"，不是 profile 存储。demo agent 的 profile（skills, bio）存储在 `AgentEntry.profile_data` 中，由 AgentRegistry.get_profile() 返回。

**影响**: `claude_adapter.py`（删除参数+简化方法）、`server.py`（不再传 profiles）、`test_routes.py`（MockAdapter 已经不用 profiles）。

### ED-2: 两个 _register_secondme_user → 统一到 auth.py 版本

**现状**:
- `backend/routers/auth.py:115-164` — `_register_agent_from_secondme()`
- `apps/app_store/backend/app.py:191-250` — `_register_secondme_user()`

两个函数做同样的事但实现不同。app.py 版本通过 _StoreStateProxy 被 `store/routers.py:249` 的 `connect_user_to_scene` 调用。

**决策**: 删除 app.py 版本。`connect_user_to_scene` 改为直接调用 auth.py 的 `_register_agent_from_secondme()`。auth.py 版本增加可选 `scene_ids` 参数（注册后调用 `registry.add_scene_to_agent`）。

**理由**: 一个注册入口，一个真相。auth.py 版本更成熟（用 `profile_to_text` 而非拼字符串）。

**影响**: `auth.py`（加 scene_ids）、`store/routers.py`（connect_user_to_scene 改 import）、`app.py`（删除函数）。

### ED-3: register_source 的 profile_data 参数 → 不需要

**现状**: `CompositeAdapter.register_source()` 批量注册 JSON agent，这些 agent 共享一个 JSONFileAdapter 作为 adapter。JSONFileAdapter 自身实现了 `get_profile(agent_id)` — 从 JSON 文件读取并返回 profile。

**决策**: AgentRegistry 的 `register_source()` 不需要 profile_data 参数。JSONFileAdapter agent 的 profile 由 adapter 自己提供。

**理由**: 与 SecondMe agent 一致——adapter 负责提供自己 agent 的 profile。AgentEntry.profile_data 只在 adapter.get_profile() 返回最小数据时作为 fallback（即 ClaudeAdapter 场景）。

### ED-4: _StoreStateProxy → 保留，移除 composite 映射

**现状**: `_StoreStateProxy`（`store/routers.py:26-57`）有 11 条映射，其中 `"composite" → "store_composite"` 支持旧的 `_register_secondme_user` 调用。

**决策**: 保留 Proxy（其他 10 条映射仍需要），删除 `"composite"` 映射。统一后 `app.state.agent_registry` 不带 store_ 前缀，不需要代理。

**理由**: 最小变更。代理解决的是"统一 server 的 store_ 前缀"问题，这个问题还在（除了 agent_registry）。

**影响**: `store/routers.py` 第 30 行删除 `"composite": "store_composite"`。所有原先通过 proxy 访问 `state.composite` 的代码改为直接访问 `state.agent_registry` 或通过新映射 `"agent_registry": "agent_registry"`。

### ED-5: 两个 Engine 实例 → 保留，共享 AgentRegistry

**现状**: `server.py` 创建两个 `NegotiationEngine`（V1: line 103, Store: line 244），有不同的 event_pusher。

**决策**: 保留两个实例。两者共享同一个 AgentRegistry 作为 adapter。Store Engine 的 event_pusher 发到 App Store WebSocket，V1 Engine 的发到 V1 WebSocket。

**理由**: Engine 是无状态的协议执行器（状态在 session 中）。不同 event_pusher → 不同 WebSocket 频道 → 不同前端。共享 AgentRegistry 保证 agent 数据一致。

**影响**: `server.py` V1 Engine 和 Store Engine 都传 `registry` 作为共享数据源，各自在 `_run_negotiation` 时使用 `adapter=registry`。

### ED-6: 向量存储 → 不移入 Registry

**现状**: `app.state.store_agent_vectors = {}` 存储在 server.py。agent 注册时在 auth.py 编码向量并存入。

**决策**: 向量存储不移入 AgentRegistry。保持独立。

**理由**: 向量是 HDC 编码的产物，属于能力层。AgentRegistry 属于基础设施层。混在一起违反分层。且向量未来可能用专门的向量存储（Faiss 等），保持独立更易替换。

---

## Phase 1: AgentRegistry 搬家 + server.py 统一

### 目标
AgentRegistry 作为唯一的 agent 信息源和 adapter 路由，替代 `state.profiles`、`state.agents`、`state.store_composite`。

### 1.1 创建 `backend/towow/infra/agent_registry.py`

**来源**: 从 `apps/app_store/backend/composite_adapter.py`（250 行）搬过来

**改动**:
- 类名 `CompositeAdapter` → `AgentRegistry`
- import 从 `from towow import BaseAdapter` 改为 `from towow.adapters.base import BaseAdapter`（避免循环依赖）
- `AgentEntry.__slots__` 扩展：增加 `profile_data`
- `AgentEntry.__init__` 增加 `profile_data: dict | None = None`
- `register_agent()` 增加 `profile_data: dict | None = None` 参数
- `get_profile()` 逻辑改为（对应 ED-3）：
  ```python
  async def get_profile(self, agent_id):
      entry = self._agents.get(agent_id)
      if not entry:
          return {"agent_id": agent_id}
      # 先问 adapter
      profile = await entry.adapter.get_profile(agent_id)
      # 如果 adapter 只返回最小数据（如 ClaudeAdapter），用 profile_data 补充
      if len(profile) <= 1 and entry.profile_data:
          profile = {**entry.profile_data, **profile}
      profile.setdefault("source", entry.source)
      profile.setdefault("scene_ids", entry.scene_ids)
      return profile
  ```
- 新增 `get_identity(agent_id) -> dict | None`：返回 `{agent_id, display_name, source, scene_ids}`（替代 `state.agents` 中 AgentIdentity 的查询功能）
- 新增 `set_default_adapter(adapter)` + `default_adapter` 属性
- 保留：`register_source()`、`get_agents_by_scope()`、`get_display_names()`、`get_agent_info()`、`get_all_agents_info()`、`unregister_agent()`、`add_scene_to_agent()`、`chat()`、`chat_stream()`

**注意**: 继承 BaseAdapter（ProfileDataSource 协议），engine 直接当 adapter 用。

**导出**: 在 `backend/towow/infra/__init__.py` 中增加 `from .agent_registry import AgentRegistry`。

### 1.2 修改 `backend/server.py`

**删除**（对应 ED-1, ED-5）:
- `app.state.profiles = {}` (line 76)
- `app.state.agents = {}` (line 75)
- ClaudeAdapter 创建 + profiles 引用 (lines 127-138)
- `app.state.adapter = adapter`

**新增**（在 line 75 区域）:
```python
# 基础设施层：AgentRegistry（唯一实例）
from towow.infra import AgentRegistry
registry = AgentRegistry()
app.state.agent_registry = registry

# 默认 adapter（给 demo/匿名用户）
if v1_keys:
    from towow.adapters.claude_adapter import ClaudeAdapter
    default_adapter = ClaudeAdapter(
        api_key=v1_keys[0],
        model=config.default_model,
        base_url=config.get_base_url(),
        # 注意: 不再传 profiles 参数 (ED-1)
    )
    registry.set_default_adapter(default_adapter)
```

**_seed_demo_scene 改动**（lines 298-345）:
- 函数签名加 `registry: AgentRegistry` 参数
- 删除 `app.state.agents[agent_id] = identity` (line 340)
- 删除 `app.state.profiles[agent_id] = profile_data` (line 341)
- 改为 `registry.register_agent(agent_id, adapter=registry.default_adapter, profile_data=profile_data, source=source_type.value, display_name=display_name, scene_ids=[scene_id])`
- 调用处改为 `_seed_demo_scene(app, registry)` (line 163)

**_init_app_store 改动**（lines 191-296）:
- 删除 `from apps.app_store.backend.composite_adapter import CompositeAdapter` (line 193)
- 删除 `composite = CompositeAdapter()` (line 196)
- 删除 `app.state.store_composite = composite` (line 198)
- 改为 `registry = app.state.agent_registry`（复用唯一实例）
- `_load_sample_agents(composite, ...)` → `_load_sample_agents(registry, ...)`
- Store Engine (line 244): 不改，但 `_run_negotiation` 时 adapter 传 registry

**注意**: `app.state.store_composite` 不再存在。所有通过它访问的代码需要改用 `app.state.agent_registry`。

### 1.3 修改 `backend/routers/auth.py`（对应 ED-2）

**参数重命名**:
- `_register_agent_from_secondme()` 参数 `composite` → `registry` (line 118)
- 函数内 `composite.register_agent(...)` → `registry.register_agent(...)` (line 135)

**新增 scene_ids 支持**（ED-2）:
```python
async def _register_agent_from_secondme(
    access_token, oauth2_client, registry, encoder, agent_vectors,
    scene_ids: list[str] | None = None,  # 新增
) -> dict:
    ...
    registry.register_agent(
        agent_id=agent_id, adapter=adapter, source="SecondMe",
        scene_ids=list(scene_ids or []),  # 传入
        display_name=profile.get("name", agent_id),
    )
```

**调用方改动**:
- auth callback (line 252): `composite=request.app.state.store_composite` → `registry=request.app.state.agent_registry`
- `/me` (line 307): `request.app.state.store_composite` → `request.app.state.agent_registry`
- 文件头注释 (line 15): `store_composite` → `agent_registry`

### 1.4 修改 `apps/app_store/backend/routers.py`（对应 ED-2, ED-4）

**_StoreStateProxy 改动** (line 29-41):
- 删除 `"composite": "store_composite"` 映射 (line 30)
- 添加 `"agent_registry": "agent_registry"` 映射（identity，让 proxy 透传）

**connect_user_to_scene 改动** (lines 230-256):
- 删除 `from .app import _register_secondme_user` (line 249)
- 改为 `from backend.routers.auth import _register_agent_from_secondme`
- 调用改为:
  ```python
  result = await _register_agent_from_secondme(
      access_token=token_set.access_token,
      oauth2_client=state.store_oauth2_client,
      registry=state.agent_registry,
      encoder=state.encoder,
      agent_vectors=state.store_agent_vectors,
      scene_ids=[scene_id],
  )
  ```

**全局替换** `state.store_composite` → `state.agent_registry`:
- `assist_demand()` 中获取 adapter (lines 269, 344 等)
- network API 中获取 agent 列表 (lines 181, 193, 199, 427 等)
- 其他查询方法

用 Grep 确认所有 `store_composite` 引用已替换。

### 1.5 修改 `backend/towow/api/routes.py`

**register_agent 端点改动**:
- 删除 `state.agents[req.agent_id] = identity` 和 `state.profiles[req.agent_id] = req.profile_data`
- 改为 `state.agent_registry.register_agent(agent_id, adapter=default_adapter, profile_data=req.profile_data, ...)`
- 需要获取 default_adapter：`state.agent_registry.default_adapter`

**_run_negotiation 改动**:
- `adapter = state.adapter` → `adapter = state.agent_registry`
- 向量编码部分：`state.profiles.get(agent_id, {})` → `await state.agent_registry.get_profile(agent_id)`
  - 注意：这里 `_run_negotiation` 已经是 async，所以 await 没问题
- `state.agents.get(agent_id)` → `state.agent_registry.get_identity(agent_id)`

**_session_to_response 不变**

### 1.6 修改 `backend/towow/adapters/claude_adapter.py`（对应 ED-1）

**删除**:
- `profiles` 参数 (line 36)
- `self._profiles = profiles if profiles is not None else {}` (line 46)

**简化 get_profile**:
```python
async def get_profile(self, agent_id: str) -> dict[str, Any]:
    """ClaudeAdapter 不持有 profile 数据，返回最小标识。"""
    return {"agent_id": agent_id}
```

### 1.7 删除 `backend/towow/api/app.py`

淘汰早期 V1 独立入口。确认无其他 import 依赖后删除。

### 1.8 处理旧的 `apps/app_store/backend/composite_adapter.py`

直接删除。所有 import 改为 `from towow.infra import AgentRegistry`。

检查清单:
- `apps/app_store/backend/routers.py` — 如有直接 import CompositeAdapter，改为 AgentRegistry
- `apps/app_store/backend/app.py` — 如有 import，删除（app.py 的 _register_secondme_user 已在 ED-2 中废弃）
- `backend/server.py` — import 已在 1.2 中改过

### 1.9 测试更新

**`backend/tests/towow/conftest.py`**:
- 当前测试用 `MockProfileDataSource` 作为 adapter，这个不用改（engine 接受 ProfileDataSource 协议）
- 但需要确保 `test_routes.py` 的 `app.state` 初始化从 `state.profiles/agents/adapter` 改为 `state.agent_registry`

**`backend/tests/towow/api/test_routes.py`**:
- `_create_test_app()` 中删除:
  - `app.state.agents = {}`
  - `app.state.profiles = {}`
  - `app.state.adapter = AsyncMock()`
- 替换为:
  ```python
  from towow.infra import AgentRegistry
  registry = AgentRegistry()
  mock_adapter = AsyncMock()  # 或使用 MockProfileDataSource
  registry.set_default_adapter(mock_adapter)
  app.state.agent_registry = registry
  ```
- 修改所有读取 `state.agents/profiles/adapter` 的地方

**新增测试**: `backend/tests/towow/infra/test_agent_registry.py`
- `test_register_and_get_profile`: register_agent → get_profile 路由到正确 adapter
- `test_register_with_profile_data_fallback`: ClaudeAdapter agent → get_profile 返回 profile_data
- `test_chat_routes_to_adapter`: register_agent → chat 路由到正确 adapter
- `test_unregistered_agent_returns_minimal`: 未注册的 agent_id → `{"agent_id": id}`
- `test_get_agents_by_scope`: scene 过滤正确
- `test_set_default_adapter`: default_adapter 功能正确
- `test_get_identity`: 返回 display_name, source, scene_ids
- `test_register_source`: 批量注册 + scope 查询

### Phase 1 验收
- [ ] `python -m pytest tests/towow/ -v` 全部通过
- [ ] `server.py` 启动无报错
- [ ] demo scene 的 5 个 agent 通过 registry 注册
- [ ] SecondMe 登录后 agent 注册在 registry
- [ ] App Store network API 返回所有 agent
- [ ] V1 `/negotiations/submit` 使用 registry 作为 adapter

---

## Phase 2: Engine 数据管道修复 + 错误处理

### 目标
Formulation 拿到 profile、有超时保护、错误诚实反馈。

### 2.1 修改 `backend/towow/core/engine.py` — `_run_formulation()`

**当前代码** (行 299-313):
```python
if formulation_skill:
    try:
        result = await formulation_skill.execute({
            "raw_intent": session.demand.raw_intent,
            "agent_id": session.demand.user_id or "user",
            "adapter": adapter,
        })
        formulated_text = result.get("formulated_text", session.demand.raw_intent)
    except Exception as e:
        logger.warning(...)
        formulated_text = session.demand.raw_intent
```

**改为**:
```python
if formulation_skill:
    degraded = False
    degraded_reason = ""
    user_id = session.demand.user_id or "user"

    # Step 1: Fetch profile (向 offer 阶段对齐)
    try:
        profile_data = await adapter.get_profile(user_id)
    except Exception as e:
        logger.warning("Profile fetch failed for %s: %s", user_id, e)
        profile_data = {}

    # Step 2: Execute formulation with timeout
    try:
        result = await asyncio.wait_for(
            formulation_skill.execute({
                "raw_intent": session.demand.raw_intent,
                "agent_id": user_id,
                "adapter": adapter,
                "profile_data": profile_data,
            }),
            timeout=self._formulation_timeout_s,
        )
        formulated_text = result.get("formulated_text", session.demand.raw_intent)
    except asyncio.TimeoutError:
        logger.warning("Formulation timed out for %s", session.negotiation_id)
        formulated_text = session.demand.raw_intent
        degraded = True
        degraded_reason = "formulation_timeout"
    except AdapterError as e:
        # 区分 token 过期 vs 其他错误
        err_str = str(e).lower()
        if "401" in err_str or "403" in err_str or "token" in err_str:
            degraded = True
            degraded_reason = "token_expired"
            # Token 过期：仍然降级继续，但前端会提示重新登录
        else:
            degraded = True
            degraded_reason = "adapter_error"
        formulated_text = session.demand.raw_intent
        logger.warning("Formulation adapter error for %s: %s", session.negotiation_id, e)
    except Exception as e:
        logger.warning("Formulation failed for %s: %s", session.negotiation_id, e)
        formulated_text = session.demand.raw_intent
        degraded = True
        degraded_reason = "formulation_error"
else:
    formulated_text = session.demand.raw_intent
    degraded = False
    degraded_reason = ""
```

**formulation.ready 事件改动** (行 321-328):
```python
await self._push_event(
    session,
    formulation_ready(
        negotiation_id=session.negotiation_id,
        raw_intent=session.demand.raw_intent,
        formulated_text=formulated_text,
        degraded=degraded,           # 新增
        degraded_reason=degraded_reason,  # 新增
    ),
)
```

**新增配置**:
```python
DEFAULT_FORMULATION_TIMEOUT_S = 30.0
```
在 `__init__` 中接受 `formulation_timeout_s` 参数。

### 2.2 修改 `backend/towow/core/events.py`

`formulation_ready()` 工厂函数新增 `degraded` 和 `degraded_reason` 参数：
```python
def formulation_ready(
    negotiation_id: str,
    raw_intent: str,
    formulated_text: str,
    degraded: bool = False,
    degraded_reason: str = "",
) -> NegotiationEvent:
    return NegotiationEvent(
        event_type=EventType.FORMULATION_READY,
        negotiation_id=negotiation_id,
        data={
            "raw_intent": raw_intent,
            "formulated_text": formulated_text,
            "degraded": degraded,
            "degraded_reason": degraded_reason,
        },
    )
```

### 2.3 修改 `backend/towow/skills/formulation.py` — LLM 错误检测

**在 `_validate_output()` 的 lenient 分支中加错误检测**:

```python
except (json.JSONDecodeError, TypeError):
    # 检测常见 LLM 错误模式（在把文本当作 formulated_text 之前）
    cleaned_lower = cleaned.strip().lower()
    error_patterns = [
        "rate limit", "too many requests", "overloaded",
        "internal server error", "service unavailable",
        "i cannot", "i'm unable", "as an ai",
    ]
    if any(pat in cleaned_lower for pat in error_patterns):
        raise SkillError(
            f"DemandFormulationSkill: LLM returned error instead of formulation: "
            f"{cleaned[:100]}"
        )
    formulated = cleaned.strip()
    enrichments = {}
```

### 2.4 修改前端类型和 UI

**`website/types/negotiation.ts`**:
```typescript
export interface FormulationReadyData {
  raw_intent: string;
  formulated_text: string;
  enrichments: Record<string, unknown>;
  degraded?: boolean;          // 新增
  degraded_reason?: string;    // 新增
}
```

**`website/components/negotiation/FormulationConfirm.tsx`**:
- 当 `degraded === true` 时显示警告横幅
- 根据 `degraded_reason` 显示不同提示文案：
  - `token_expired` → "你的 SecondMe 分身连接已断开，建议重新登录后重试"
  - `formulation_timeout` → "分身暂时无法响应，当前使用你的原始需求"
  - 其他 → "需求丰富化未完成，当前使用原始需求"

**`website/hooks/useNegotiationStream.ts`**:
- 新增 formulation 阶段超时：连接 WebSocket 后 45s 未收到 `formulation.ready` → 显示超时提示

### 2.5 测试更新

**`test_engine.py`**:
- 新增 `test_formulation_timeout_degrades_gracefully`: formulation skill 超时 → 降级为 raw_intent + degraded=True
- 新增 `test_formulation_with_profile_data`: profile_data 正确传入 skill context
- 修改现有 `test_full_flow_events_pushed`: 验证 formulation.ready 包含 degraded 字段

**`test_formulation.py`**:
- 新增 `test_error_response_detected`: LLM 返回 "rate limit exceeded" → SkillError
- 新增 `test_profile_data_in_prompt`: 验证 profile_data 出现在 system prompt 中

**`test_events.py`**:
- 更新 `formulation_ready` 测试：包含 degraded 和 degraded_reason

### Phase 2 验收
- [ ] `python -m pytest tests/towow/ -v` 全部通过
- [ ] Formulation 正确获取 profile 并注入 prompt
- [ ] 30s 超时保护生效
- [ ] LLM 错误文本不会变成 formulated_text
- [ ] formulation.ready 事件包含 degraded 信息
- [ ] 前端显示降级提示

---

## Phase 3: 清理 + 端到端验证

### 3.1 删除废弃代码

- 删除 `backend/towow/api/app.py`
- 删除 `apps/app_store/backend/composite_adapter.py`（已搬到 infra）
- 删除 `backend/server.py` 中所有 `state.profiles`、`state.agents` 的痕迹
- 清理 `apps/app_store/backend/` 中对 `composite_adapter` 的 import

### 3.2 更新 `apps/app_store/backend/__init__.py`

如果有 re-export CompositeAdapter 的地方，改为 import AgentRegistry。

### 3.3 更新 `backend/towow/__init__.py`

确保 `AgentRegistry` 可以从 `towow` 包直接 import（如果其他模块需要）。

### 3.4 端到端验证（生产环境标准）

**启动验证**:
```bash
cd backend && source venv/bin/activate
TOWOW_ANTHROPIC_API_KEY=sk-ant-... uvicorn server:app --reload --port 8080
# 无报错，所有子系统初始化成功
```

**Demo 用户验证（Claude adapter）**:
1. POST `/v1/api/negotiations/submit` with scene_id=scene_default, intent="找一个AI合伙人"
2. WebSocket 收到 `formulation.ready` → formulated_text 不为空，degraded=false
3. POST `/v1/api/negotiations/{id}/confirm`
4. 后续事件正常到达 → plan.ready

**SecondMe 用户验证（如有 SecondMe 账号）**:
1. GET `/api/auth/secondme/start` → 登录
2. 登录成功后，agent 出现在 registry
3. POST `/v1/api/negotiations/submit` → formulation 使用 SecondMe profile
4. formulated_text 包含用户的兴趣/经历

**App Store 验证**:
1. POST `/store/api/assist-demand` mode=surprise → SecondMe 分身正常响应
2. GET `/store/api/network?scope=all` → 返回所有 agent（含 SecondMe 用户和 demo agent）

**降级验证**:
1. 不启动 SecondMe → formulation 降级为 raw_intent，degraded=true
2. 设置极短超时 → 超时降级生效

### Phase 3 验收
- [ ] 190+ 测试全部通过
- [ ] server.py 启动正常
- [ ] Demo 用户完整 negotiation 流程通过
- [ ] App Store assist-demand 正常
- [ ] 废弃文件已删除
- [ ] 无残留的 state.profiles / state.agents / store_composite 引用

---

## 文件变更总览

### 新增（2 文件）
| 文件 | Phase | 说明 |
|------|-------|------|
| `backend/towow/infra/agent_registry.py` | 1.1 | AgentRegistry（从 CompositeAdapter 搬来 + 扩展） |
| `backend/tests/towow/infra/test_agent_registry.py` | 1.9 | Registry 单元测试（8 个用例） |

### 修改（16 文件）
| 文件 | Phase | 说明 |
|------|-------|------|
| `backend/towow/adapters/claude_adapter.py` | 1.6 | 删除 profiles 参数，简化 get_profile (ED-1) |
| `backend/towow/infra/__init__.py` | 1.1 | export AgentRegistry |
| `backend/server.py` | 1.2 | 统一用 AgentRegistry，淘汰 state.profiles/agents/adapter |
| `backend/routers/auth.py` | 1.3 | store_composite → agent_registry, 加 scene_ids (ED-2) |
| `apps/app_store/backend/routers.py` | 1.4 | store_composite → agent_registry, proxy 改动 (ED-4) |
| `backend/towow/api/routes.py` | 1.5 | state.profiles/agents/adapter → agent_registry |
| `backend/towow/core/engine.py` | 2.1 | formulation fetch profile + timeout + degraded |
| `backend/towow/core/events.py` | 2.2 | formulation_ready 增加 degraded/degraded_reason |
| `backend/towow/skills/formulation.py` | 2.3 | LLM 错误检测 |
| `backend/tests/towow/conftest.py` | 1.9 | 适配新的 state 结构 |
| `backend/tests/towow/api/test_routes.py` | 1.9 | 适配新的 state 结构 |
| `backend/tests/towow/core/test_engine.py` | 2.5 | 新增 formulation timeout/profile 测试 |
| `backend/tests/towow/core/test_events.py` | 2.5 | formulation_ready degraded 字段 |
| `backend/tests/towow/skills/test_formulation.py` | 2.5 | 错误检测测试 |
| `website/types/negotiation.ts` | 2.4 | FormulationReadyData 增加 degraded |
| `website/components/negotiation/FormulationConfirm.tsx` | 2.4 | 降级警告 UI |

### 删除（2 文件）
| 文件 | Phase | 说明 |
|------|-------|------|
| `backend/towow/api/app.py` | 1.7 | 早期 V1 独立入口，已废弃 |
| `apps/app_store/backend/composite_adapter.py` | 1.8 | 已搬到 infra/agent_registry.py |

---

## 跨文件数据流验证清单

改完后必须逐段验证以下数据流：

### 数据流 1: SecondMe 用户注册
```
SecondMe OAuth callback
  → _register_agent_from_secondme()
  → registry.register_agent(agent_id, adapter=SecondMeAdapter, source="SecondMe")
  → registry._agents[agent_id] = AgentEntry(adapter=SecondMeAdapter, ...)
验证: registry.get_agent_info(agent_id) 返回正确信息
```

### 数据流 2: Demo agent 注册
```
_seed_demo_scene()
  → registry.register_agent(agent_id, adapter=default_adapter, profile_data={skills, bio})
  → registry._agents[agent_id] = AgentEntry(adapter=default_adapter, profile_data=...)
验证: registry.get_profile(agent_id) 返回 profile_data
```

### 数据流 3: Formulation（核心修复）
```
submit_demand()
  → _run_negotiation()
  → adapter = state.agent_registry  (不再是 ClaudeAdapter 单例)
  → engine.start_negotiation(adapter=registry, ...)
  → _run_formulation():
    → profile_data = await adapter.get_profile(user_id)
      → registry 路由到正确的 adapter（SecondMe 或 Claude）
    → formulation_skill.execute({profile_data: ..., adapter: ...})
      → skill 的 _build_prompt 使用 profile_data → 有内容
      → adapter.chat(user_id, ...) → 路由到正确的 LLM
    → formulation.ready 事件推送
验证: formulated_text 包含 profile 相关内容，不是 "(no profile data)"
```

### 数据流 4: Offer 生成
```
_run_offers():
  → adapter.get_profile(participant.agent_id)
    → registry 路由到该 agent 的 adapter
  → offer_skill.execute({profile_data: ...})
    → adapter.chat(agent_id, ...) → 路由到该 agent 的 LLM
验证: 每个 agent 用自己的 adapter 和 profile 生成 offer
```

### 数据流 5: App Store assist-demand
```
assist_demand():
  → agent_id = session cookie
  → registry.get_agent_info(agent_id) → source="SecondMe"
  → registry.chat(agent_id, messages, system_prompt)
    → 路由到 SecondMe adapter → SecondMe chat API
验证: 行为与改动前完全一致
```

### 数据流 6: 向量编码
```
_run_negotiation():
  → for agent_id in scene.agent_ids:
    → profile = await registry.get_profile(agent_id)
    → text = build_text_from_profile(profile)
    → vec = await encoder.encode(text)
验证: SecondMe 用户的 profile 更丰富 → 向量更准确
```

---

## 依赖关系

```
Phase 1.1 (agent_registry.py 新建) + 1.6 (claude_adapter.py 简化)  ← 可并行
  ↓
Phase 1.2 (server.py 统一)  ← 依赖 1.1 + 1.6
  ↓
Phase 1.3 (auth.py) + 1.4 (store routers) + 1.5 (v1 routes)  ← 可并行，都依赖 1.2
  ↓
Phase 1.7 (删除 api/app.py) + 1.8 (删除旧 composite)  ← 依赖 1.3-1.5
  ↓
Phase 1.9 (测试更新)  ← 依赖全部上述
  ↓
Phase 2 (engine 数据管道 + formulation + events + 前端)  ← 依赖 Phase 1 通过测试
  ↓
Phase 3 (清理 + 端到端验证)  ← 依赖 Phase 2 通过测试
```

### Phase 1 构建顺序（推荐执行路径）

```
Group A (基础): 1.1 + 1.6     → 产出: agent_registry.py + 简化的 claude_adapter.py
Group B (统一): 1.2            → 产出: server.py 使用 registry
Group C (路由): 1.3 + 1.4 + 1.5 → 产出: auth/store/v1 路由全部指向 registry
Group D (删除): 1.7 + 1.8     → 产出: 废弃文件清理
Group E (验证): 1.9            → 产出: 190+ 测试全绿
```
