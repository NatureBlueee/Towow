# ADR-001: 统一 Adapter 注册表——从应用层下沉到基础设施层

**日期**: 2026-02-12
**状态**: 已批准
**关联问题**: [Issue 001: Formulation 数据管道断裂](../issues/001-formulation-pipeline-broken.md)
**实施计划**: [PLAN-001](./PLAN-001-adapter-registry-implementation.md)

---

## 背景

通爻网络的四层架构：

```
应用层 ─── App Store、Website、未来应用
能力层 ─── Skills（formulation、offer、center）、LLM 客户端
基础设施层 ─── Adapter、Encoder、EventPusher、存储
协议层 ─── 状态机、事件语义、递归规则
```

Adapter（ProfileDataSource）是连接"自"与系统的桥梁：
- SecondMe adapter 连接用户的 AI 分身
- Claude adapter 提供默认的 LLM 能力
- 未来可能有更多来源（GPT、本地模型、模板等）

**问题**: Adapter 管理目前被分裂在两个地方：

| 位置 | 实例 | 用途 |
|------|------|------|
| `server.py` 启动时 | `ClaudeAdapter`（单例） | V1 Engine 所有操作 |
| App Store `_init_app_store()` | `CompositeAdapter` | App Store 网络查询、assist-demand |

V1 Engine（协议层的实现）只看到一个共享的 ClaudeAdapter。
SecondMe 用户注册在 App Store 的 CompositeAdapter 里，V1 Engine 不知道。

结果：无论谁提交需求，formulation 和 offer 都走同一个 ClaudeAdapter，
用户的 SecondMe 分身永远不参与 V1 negotiation。

**本质**：App Store 是 V1 协议的第一个应用，不是协议内部组件。
CompositeAdapter 做的是基础设施工作（agent 注册、adapter 路由），
但被放在了应用层（`apps/app_store/backend/`）。层次错位。

## 已批准的决策

### 决策 1: CompositeAdapter → AgentRegistry，下沉到基础设施层

```
Before:
  server.py
  ├── V1 Engine → ClaudeAdapter（孤立单例）
  ├── state.profiles（静态 dict）
  ├── state.agents（AgentIdentity dict）
  └── App Store → CompositeAdapter（应用层，独立管理）

After:
  server.py
  ├── AgentRegistry（基础设施层，唯一实例）
  │   ├── 实现 ProfileDataSource 接口
  │   ├── register_agent(id, adapter, source, scenes, profile_data)
  │   ├── get_profile(agent_id) → 路由到正确 adapter
  │   ├── chat(agent_id, ...) → 路由到正确 adapter
  │   └── 包含原 state.agents + state.profiles 的功能
  │
  ├── V1 Engine → 使用 AgentRegistry 作为 adapter 参数
  └── App Store → 使用同一个 AgentRegistry
```

**淘汰 `state.profiles` 和 `state.agents`**：AgentRegistry 是 agent 信息的唯一数据源。
不再维护三份并行数据。注册一次，全网络可用。

### 决策 2: Formulation 失败时区分降级等级，诚实告知用户

现阶段是原型，对用户诚实比隐藏错误更好。绝不卡死。

| 失败原因 | 处理方式 | 用户看到什么 |
|----------|----------|-------------|
| **Token 过期**（SecondMe 401/403） | 阻断 + 提示重新登录 | "你的分身连接已断开，请重新登录 SecondMe" |
| **LLM 超时**（30s 无响应） | 降级为 raw_intent + 警告 | "分身暂时无法响应，使用你的原始需求继续" |
| **LLM 返回错误文本** | 降级为 raw_intent + 警告 | 同上 |
| **无 profile**（匿名/demo 用户） | 正常流程，无警告 | 正常体验（formulation 基于静态 profile） |
| **Adapter 不存在**（agent_id 未注册） | 降级为 raw_intent + 警告 | "找不到你的 Agent 信息，使用原始需求继续" |

实现方式：`formulation.ready` 事件新增 `degraded: bool` + `degraded_reason: string` 字段。
前端根据字段展示相应提示。不新增事件类型。

### 决策 3: 淘汰 `backend/towow/api/app.py`

`app.py` 是早期 V1 独立开发的入口，现在不再使用。
`server.py` 是唯一的生产入口。测试走 pytest conftest。
淘汰 `app.py` 消除同步维护成本。

## 核心原则

1. **每个 Agent 在注册时关联自己的 adapter**
   - SecondMe 用户注册时 → SecondMeAdapter
   - Demo agent 注册时 → 共享的 ClaudeAdapter
   - 模板 agent → 共享的 ClaudeAdapter

2. **协议层只看到一个 ProfileDataSource**
   - Engine 不关心底层是 SecondMe 还是 Claude
   - 按 agent_id 路由是基础设施层的事

3. **"通向惊喜"自然恢复**
   - Formulation 时：`registry.get_profile(user_id)` 路由到用户自己的 adapter
   - SecondMe 用户 → shades + memories → prompt 有丰富 profile
   - Claude/demo 用户 → 静态 profile → prompt 有基础信息
   - `registry.chat(user_id, ...)` 走用户自己的 LLM

4. **生产级——做完直接能用**
   - 不是"为了测试"的中间态
   - 每个 Phase 结束后系统都是完整可运行的生产状态

## 为什么不是"最小修复"

做过多次小修复，每次解决一个点但留下新的接缝：

- "在 engine 里加一行 `adapter.get_profile()`" → 解决 profile_data 传递，
  但 adapter 还是 ClaudeAdapter，SecondMe 用户还是用不了分身
- "在 _run_negotiation 里判断 session cookie 选 adapter" → 让协议层去感知应用层的认证，
  耦合方向反了
- "给 App Store 的 CompositeAdapter 打个引用到 V1" → 应用层反向注入基础设施

正确的方式：基础设施层有一个 registry，所有人往里注册，所有操作从里取。
修地基，不是贴瓷砖。

## 1000 Agent 考量

| 关注点 | 分析 | 结论 |
|--------|------|------|
| 注册表查找 | dict O(1) | 1000 entries 无压力 |
| 内存 | 每个 entry ~1KB | ~1MB 总计 |
| Formulation | 每次 negotiation 1 个 | 不是瓶颈 |
| Offer 生成 | k* 个 agent 并行 adapter.chat() | 现有超时+EXITED 机制够用 |
| Profile 缓存 | adapter 内部缓存 | 不重复 fetch |
| Token 刷新 | adapter 内部处理 | 注册表不管 |
