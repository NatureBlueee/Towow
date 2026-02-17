# Issue 001 调查指南：ADR-001 改动引发问题时的排查原则

> 本文档不预测具体问题，而是建立针对本次改动特征的排查思维框架。
> 任何上下文中的开发者（包括上下文切换后的 Claude）都可以依此快速定位问题。

## 本次改动的本质特征

ADR-001 做了一件事：**把分散的 agent 管理统一到 AgentRegistry**。

这意味着：
- 原来有 3 个地方管 agent（`state.agents`, `state.profiles`, `CompositeAdapter`），现在只有 1 个（`AgentRegistry`）
- 原来数据在不同地方各存一份，现在所有调用方通过同一个实例访问
- 原来 V1 和 Store 各自管各自的，现在共享同一个 Registry

**这类改动最危险的不是"新代码有 bug"，而是"旧路径以为数据还在旧的地方"。**

---

## 排查原则

### 原则 1：先定位断裂层，再定位断裂点

系统有四层。问题出现时，第一步不是猜哪行代码错了，而是判断**断裂发生在哪一层的边界**。

```
应用层（前端 / API handler）
    ↕ 契约：HTTP endpoint + event schema
基础设施层（AgentRegistry / EventPusher）
    ↕ 契约：ProfileDataSource 协议（get_profile / chat / chat_stream）
协议层（Engine 状态机）
    ↕ 契约：Skill 接口（execute(context) → dict）
能力层（Skills / LLM Client）
```

**判断方法**：
- 如果前端收到的事件结构错误 → 应用层 ↔ 基础设施层边界
- 如果 Engine 拿到的 profile 数据不对 → 基础设施层 ↔ 协议层边界
- 如果 LLM 返回异常但 Engine 没处理 → 协议层 ↔ 能力层边界

### 原则 2：追踪 agent_id 的生命旅程

本次改动的核心数据是 **agent_id**——它是贯穿整个系统的身份锚点。

当某个功能不工作时，沿 agent_id 的旅程追踪：

```
agent_id 诞生
  → 在哪里注册的？（auth.py? seed_demo? register_source?）
  → 注册时带了什么数据？（adapter, profile_data, scene_ids, display_name）

agent_id 被查询
  → 谁在查？（Engine? Routes? Store?）
  → 查的是什么？（get_profile? chat? get_identity? get_display_names?）
  → 查到的结果对不对？

agent_id 被路由
  → AgentRegistry 找到了对应的 AgentEntry 吗？
  → 路由到了正确的 sub-adapter 吗？（ClaudeAdapter? SecondMeAdapter?）
  → sub-adapter 返回了什么？Registry 做了 fallback 吗？
```

**快速验证命令**：在后端加临时 log 或用 debugger 在 `AgentRegistry.get_profile()` 打断点，看 agent_id 经过时的完整数据。

### 原则 3：区分"注册态"和"运行态"

本次改动引入了一个时序依赖：**agent 必须先注册到 Registry，才能被 Engine 使用**。

如果发现 agent 数据为空或行为异常，先问：

1. **注册发生了吗？** — agent 是否真的调用了 `registry.register_agent()`
2. **注册的时序对吗？** — 注册是否发生在 Engine 使用之前
3. **注册的 adapter 对吗？** — SecondMe 用户注册的是 SecondMeAdapter 还是 ClaudeAdapter

常见陷阱：
- Demo 场景的 agent 在 `lifespan()` 里注册 → 启动时就有
- SecondMe 用户在 auth callback 里注册 → 登录后才有
- 如果用户没登录就触发协商，Registry 里找不到该 agent → fallback 到默认 adapter

### 原则 4：Profile fallback 是双刃剑

AgentRegistry 的 `get_profile()` 有 fallback 逻辑：

```python
profile = await entry.adapter.get_profile(agent_id)
if len(profile) <= 1 and entry.profile_data:
    profile = {**entry.profile_data, **profile}
```

这意味着：
- ClaudeAdapter 返回 `{"agent_id": id}`（1 个字段）→ 触发 fallback → 用注册时的 profile_data
- SecondMeAdapter 返回完整 profile → 不触发 fallback → 用 adapter 的数据

**如果看到 profile 数据不符合预期**，检查：
- adapter.get_profile() 返回了几个字段？（`len(profile) <= 1` 是触发条件）
- 注册时传了 profile_data 吗？（如果没传，fallback 也没数据可用）
- 两种来源的字段名是否冲突？（fallback 用 `{**profile_data, **profile}`，adapter 的字段会覆盖 profile_data）

### 原则 5：降级标记是诊断信号

Engine 的 formulation 管道有四种降级标记：

| degraded_reason | 含义 | 排查方向 |
|-----------------|------|----------|
| `token_expired` | SecondMe token 过期（401/403） | 检查 token 刷新逻辑；检查 SecondMeAdapter 是否用了过期 access_token |
| `adapter_error` | Adapter 调用失败（非 token 问题） | 检查 adapter 连通性；检查 SecondMe API 可用性 |
| `formulation_timeout` | 30s 超时 | 检查 LLM 响应速度；检查网络；检查 adapter.chat() 是否卡在某处 |
| `formulation_error` | 通用异常 | 看 Engine 日志的 exception 堆栈 |

**如果用户看到降级提示**：
1. 先看 `degraded_reason` 判断大方向
2. 再看后端日志的对应 warning/error
3. 根据方向定位到具体的 adapter 或 skill

### 原则 6：双入口一致性

改动后有两个入口可以触发相同逻辑：

| 功能 | 新入口（生产） | 旧入口（独立模式） |
|------|---------------|-------------------|
| SecondMe 注册 | `routers.py` → `auth._register_agent_from_secondme()` | `app.py` → 也调 `auth._register_agent_from_secondme()` |
| 场景连接 | `routers.py:connect_user_to_scene` | `app.py:connect_user_to_scene` |

两个入口现在调用同一个底层函数，但周边逻辑（token 存储、场景计数）各自处理。

**如果注册行为不一致**：检查请求走的是哪个入口（看 URL 前缀：`/store/api/` = routers.py，`/api/` = app.py）。

### 原则 7：共享实例 = 全局状态

AgentRegistry 是单实例全局共享的。这意味着：
- V1 注册的 agent，Store 能看到
- Store 注册的 agent，V1 也能看到
- Auth 回调注册的 SecondMe 用户，V1 和 Store 都能用

**如果某个子系统看不到 agent**：
- 不是隔离问题（共享同一个实例）
- 检查 scene_ids 过滤（`agents_in_scene()` 只返回属于该 scene 的 agent）
- 检查时序（agent 是否在查询之前已注册）

---

## 排查流程模板

遇到问题时按此顺序：

```
1. 复现
   → 什么操作触发了问题？
   → 前端看到什么？后端日志说什么？

2. 定位层级
   → 是前端展示问题？API 响应问题？Engine 流程问题？LLM 调用问题？

3. 追踪 agent_id
   → 这个 agent 在 Registry 里吗？
   → 注册时的数据完整吗？
   → get_profile() 返回了什么？

4. 检查时序
   → 注册先于使用？
   → Token 仍然有效？
   → 降级标记是什么？

5. 验证数据流通
   → 不只看类型对齐，看运行时实际的数据值
   → 在关键节点打 log 或断点：Registry.get_profile(), Engine._run_formulation(), Skill.execute()
```

---

## 关键文件速查

| 场景 | 文件 | 关键函数/行 |
|------|------|------------|
| Agent 注册（平台 auth） | `backend/routers/auth.py:115` | `_register_agent_from_secondme()` |
| Agent 注册（demo seed） | `backend/server.py` | `_seed_demo_scene()` |
| Agent 查询/路由 | `backend/towow/infra/agent_registry.py` | `get_profile()`, `chat()` |
| Formulation 管道 | `backend/towow/core/engine.py` | `_run_formulation()` |
| LLM 错误检测 | `backend/towow/skills/formulation.py` | `_validate_output()` |
| 前端降级展示 | `website/components/negotiation/FormulationConfirm.tsx` | `degradedMessage` 计算 |
| 事件结构 | `backend/towow/core/events.py` | `formulation_ready()` |
