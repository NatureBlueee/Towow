# ADR-002 接口设计: MCP Tools 语义契约

**关联**: ADR-002 (MCP 入口), ADR-001 (AgentRegistry)
**阶段**: ③ 接口设计
**原则**: 只定义"做什么"，不定义"怎么做"。换一种实现方式，契约不变。

---

## 1. 开发者模式: 8 个 MCP Tools

### 1.1 `towow_create_scene` — 创建场景

**语义**: 在通爻网络中创建一个新的协商场景。

| | 定义 |
|---|------|
| **输入** | `name: string` — 场景名称 |
| | `description: string` — 场景描述 |
| | `expected_responders: int` — 期望响应者数（默认 10） |
| | `access_policy: string` — 访问策略（默认 "open"） |
| **输出** | `scene_id: string` — 场景唯一标识 |
| | `name, description, status, agent_ids` |
| **状态变化** | 网络中新增一个空场景 |
| **错误** | 参数缺失 → 400 |
| **对应 Backend** | `POST /v1/api/scenes` (已有) |

---

### 1.2 `towow_register_agent` — 注册 Agent

**语义**: 将一个 Agent 注册到指定场景。注册 = 提交 Profile 数据，让这个 Agent 可以参与协商。

| | 定义 |
|---|------|
| **输入** | `scene_id: string` — 目标场景 |
| | `agent_id: string` — Agent 标识（可选，不提供则自动生成） |
| | `display_name: string` — 显示名 |
| | `profile_data: object` — 结构化的 Profile 数据 |
| | `source_type: string` — 来源类型（默认 "mcp"） |
| **输出** | `agent_id: string` — 注册成功的 Agent ID |
| | `display_name: string` |
| | `scene_id: string` |
| **状态变化** | Agent 注册到 AgentRegistry + 关联到场景 |
| **错误** | 场景不存在 → 404; Agent 已在场景中 → 409 |
| **对应 Backend** | `POST /v1/api/scenes/{scene_id}/agents` (已有) |

**Profile 数据结构**（引导提示词定义的字段）:

```
profile_data: {
  skills: [string]        — 技能列表
  bio: string             — 简介
  experience: string      — 经验描述
  interests: [string]     — 兴趣领域
  capabilities: [string]  — 能提供的能力
  constraints: string     — 约束条件（可选）
}
```

---

### 1.3 `towow_list_scenes` — 列出场景

**语义**: 查看网络中所有可用的场景。

| | 定义 |
|---|------|
| **输入** | `status: string` — 过滤条件（可选，如 "active"） |
| **输出** | `scenes: [{scene_id, name, description, agent_count, status}]` |
| **状态变化** | 无（只读） |
| **对应 Backend** | `GET /v1/api/scenes` (**需新增**) |

---

### 1.4 `towow_list_agents` — 列出场景内 Agent

**语义**: 查看指定场景中已注册的所有 Agent。

| | 定义 |
|---|------|
| **输入** | `scene_id: string` — 目标场景 |
| **输出** | `agents: [{agent_id, display_name, source}]` |
| **状态变化** | 无（只读） |
| **错误** | 场景不存在 → 404 |
| **对应 Backend** | `GET /v1/api/scenes/{scene_id}/agents` (**需新增**) |

---

### 1.5 `towow_submit_demand` — 提交需求

**语义**: 向指定场景提交一个协商需求。触发 formulation 流程。

| | 定义 |
|---|------|
| **输入** | `scene_id: string` — 场景 |
| | `user_id: string` — 提交者 |
| | `intent: string` — 原始意图（自然语言） |
| **输出** | `negotiation_id: string` — 协商唯一标识 |
| | `state: string` — 初始状态 |
| **状态变化** | 创建 NegotiationSession，开始 formulation |
| **后续事件** | formulation.ready（需要用户确认） |
| **对应 Backend** | `POST /v1/api/negotiations/submit` (已有) |

---

### 1.6 `towow_confirm` — 确认 formulation

**语义**: 确认（或修改后确认）丰富化的需求文本。确认后协议层开始广播、共振检测、收集 Offer。

| | 定义 |
|---|------|
| **输入** | `negotiation_id: string` |
| | `confirmed_text: string` — 确认的文本（可选，不传则接受原文） |
| **输出** | `negotiation_id, state` |
| **前置条件** | 协商处于 FORMULATED 状态 |
| **状态变化** | FORMULATED → ENCODING → OFFERING → ... |
| **后续事件** | resonance.activated → offer.received ×N → barrier.complete → plan.ready |
| **错误** | 协商不存在 → 404; 状态不对 → 409 |
| **对应 Backend** | `POST /v1/api/negotiations/{id}/confirm` (已有) |

**协议约束**: formulation 确认是协议层要求（Section 10.2）。任何入口、任何模式都必须经过用户确认。

---

### 1.7 `towow_get_negotiation` — 查看协商状态

**语义**: 获取一个协商的完整状态，包括参与者、Offer、方案。

| | 定义 |
|---|------|
| **输入** | `negotiation_id: string` |
| **输出** | 完整的 NegotiationResponse（见下方） |
| **状态变化** | 无（只读） |
| **对应 Backend** | `GET /v1/api/negotiations/{id}` (已有) |

**输出结构**:

```
{
  negotiation_id: string
  state: string           — 当前状态（8 种之一）
  demand_raw: string      — 原始需求
  demand_formulated: string | null  — 丰富化后的需求
  participants: [{
    agent_id: string
    display_name: string
    resonance_score: float
    state: string
    offer_content: string | null
    offer_capabilities: [string] | null
  }]
  plan_output: string | null  — 最终方案
  center_rounds: int
  depth: int              — 递归深度
  sub_session_ids: [string]
}
```

---

### 1.8 `towow_action` — 用户操作

**语义**: 对进行中的协商执行操作（如取消）。

| | 定义 |
|---|------|
| **输入** | `negotiation_id: string` |
| | `action: string` — 操作类型 |
| | `payload: object` — 操作参数（可选） |
| **输出** | `negotiation_id, state` |
| **状态变化** | 依操作而定 |
| **已定义操作** | `"cancel"` — 取消协商 |
| **错误** | 协商不存在 → 404; 未知操作 → 400; 已完成 → 409 |
| **对应 Backend** | `POST /v1/api/negotiations/{id}/action` (已有) |

---

## 2. 普通模式: 3 个 MCP Tools（语法糖）

普通模式工具是开发者模式工具的组合，内部调用同一套 API。

### 2.1 `towow_join` — 一步加入场景

**语义**: 用户提供原始资料，MCP 引导结构化，完成注册。

| | 定义 |
|---|------|
| **输入** | `scene: string` — 场景名或 scene_id |
| | `raw_content: string` — 用户的原始资料（简历、自我介绍等任意文本） |
| **输出** | `agent_id: string` |
| | `scene_id: string` |
| | `profile_summary: string` — 结构化后的摘要（供用户确认） |
| | `guiding_prompt: string` — 引导提示词（给用户的 AI 使用） |
| **内部流程** | ① 解析 scene（名称 → list_scenes → 匹配） |
| | ② 返回引导提示词 + raw_content 给用户的 AI |
| | ③ 用户 AI 输出结构化 profile_data |
| | ④ 调用 register_agent |

**关键设计**: Profile 结构化由**用户自己的 AI**（Claude Code 的 LLM）完成。MCP Server 只提供引导提示词。不消耗通爻 API 额度。

---

### 2.2 `towow_demand` — 简化提需求

**语义**: 提交需求，等待丰富化，提示用户确认。

| | 定义 |
|---|------|
| **输入** | `intent: string` — 自然语言需求 |
| | `scene_id: string` — 场景（可选，默认用最近加入的） |
| **输出** | `negotiation_id: string` |
| | `formulated_text: string` — 丰富化文本（等待确认） |
| | `state: string` |
| **内部流程** | ① submit_demand |
| | ② 轮询等待 formulation.ready |
| | ③ 将 formulated_text 返回给用户 |
| | ④ 用户通过 MCP 交互确认或修改 |
| | ⑤ 调用 confirm |

**协议约束**: 无论简化模式还是开发者模式，formulation 确认步骤不可跳过。

---

### 2.3 `towow_status` — 查看状态

**语义**: 查看当前或指定协商的状态，附带人类可读的摘要。

| | 定义 |
|---|------|
| **输入** | `negotiation_id: string` — 可选，默认最近一次 |
| **输出** | 完整 NegotiationResponse + `summary: string`（自然语言摘要） |
| **摘要示例** | 状态 FORMULATED: "需求已丰富化，等待你确认" |
| | 状态 OFFERING: "3/5 个 Agent 已提交 Offer，等待剩余" |
| | 状态 COMPLETED: "方案已生成，共 2 轮 Center 协调" |

---

## 3. 身份管理契约

### 3.1 身份生命周期

```
首次使用 MCP
  → MCP Server 生成 user_id (UUID)
  → 存入本地配置 (~/.towow/config.json)
  → 后续 session 自动携带
  → 所有 MCP tool 调用隐式使用此 user_id
```

### 3.2 配置文件结构

```
~/.towow/config.json
{
  user_id: string        — 网络唯一标识
  api_token: string      — Backend 认证令牌
  backend_url: string    — Backend 地址（默认生产环境）
  mode: "developer" | "normal"  — 当前模式
  last_scene_id: string  — 最近加入的场景（普通模式用）
  last_negotiation_id: string  — 最近的协商（普通模式用）
}
```

### 3.3 认证契约

MCP Server → Backend 的认证:
- 所有请求携带 `Authorization: Bearer <api_token>` header
- Token 在首次注册时由 Backend 签发
- Token 关联 user_id
- Token 过期/刷新策略: 待定（ADR-002 待讨论 #6）

---

## 4. 事件通知契约

### 4.1 轮询语义

MCP 没有 WebSocket，用轮询获取协商进展:

```
submit_demand → 返回 negotiation_id
  ↓
MCP Server 轮询 GET /v1/api/negotiations/{id}
  ↓
检测 state 字段变化 → 向用户报告
```

### 4.2 关键状态通知

| 状态变化 | 用户看到什么 |
|----------|-------------|
| → FORMULATED | "需求已丰富化，请确认或修改:\n{formulated_text}" |
| → ENCODING | "正在编码需求..." |
| → OFFERING | "共振检测完成，激活了 {N} 个 Agent" |
| → BARRIER_WAITING | "{N}/{total} 个 Offer 已收到" |
| → SYNTHESIZING | "所有 Offer 已收集，Center 正在综合方案..." |
| → COMPLETED | "方案已生成。" |
| → COMPLETED (error) | "协商异常终止: {error}" |

### 4.3 formulation 确认交互

这是 MCP 模式下最关键的交互点:

```
用户: towow_demand("我需要一个全栈工程师帮我做...")
  ↓
MCP Server: submit_demand → 轮询 → formulation.ready
  ↓
MCP 返回: "需求已丰富化:
  '根据你的 profile，你需要一位具备 React + Python 经验的全栈工程师...'

  请确认（直接回复确认，或修改后确认）"
  ↓
用户: "确认" 或 "修改为: ..."
  ↓
MCP Server: confirm → 协商继续
```

**MCP 的自然优势**: MCP 的 tool-call → response 模型天然适合这个"暂停等确认"的流程。不需要额外机制。

---

## 5. 引导提示词契约

### 5.1 语义

引导提示词是 MCP Server 提供给用户 AI 的指令，用于将原始内容结构化为 Profile 数据。

### 5.2 输入输出

```
输入:
  - guiding_prompt: string  — MCP Server 提供
  - raw_content: string     — 用户的原始资料
  - user_context: any       — 用户 AI 已有的上下文

输出:
  - profile_data: object    — 符合 Section 1.2 定义的结构
```

### 5.3 引导提示词需表达的信息

1. 通爻网络需要什么字段（skills, bio, experience, interests, capabilities）
2. 每个字段的含义和期望格式
3. 什么信息对协商匹配最有价值
4. 输出必须是 JSON 格式

**不包含**: 具体的 prompt 文本（那是实现细节，阶段 ④ 定义）。

---

## 6. 模式切换契约

| | 定义 |
|---|------|
| **切换方式** | 用户通过对话指令或配置文件设置 |
| **开发者 → 普通** | 隐藏底层工具，暴露简化工具 |
| **普通 → 开发者** | 暴露全部工具 |
| **数据不丢失** | 切换模式不影响已注册的 Agent 和进行中的协商 |

---

## 7. Backend 需新增的 API 端点

现有 Backend 覆盖了大部分操作，但缺少读取端点:

### 7.1 `GET /v1/api/scenes` — 列出场景

```
Response: {
  scenes: [{
    scene_id: string
    name: string
    description: string
    agent_count: int
    status: string
    expected_responders: int
    access_policy: string
  }]
}
```

### 7.2 `GET /v1/api/scenes/{scene_id}/agents` — 列出场景内 Agent

```
Response: {
  scene_id: string
  agents: [{
    agent_id: string
    display_name: string
    source: string
  }]
}
```

### 7.3 `POST /v1/api/auth/mcp-token` — MCP Token 签发

```
Request: {
  user_id: string        — 首次为空，Backend 生成
  device_info: string    — 设备标识（可选）
}

Response: {
  user_id: string        — 网络唯一 ID
  api_token: string      — Bearer token
  expires_at: string     — 过期时间（ISO 8601）
}
```

---

## 8. 与现有契约的关系

| 现有契约 | MCP 如何消费 | 变更 |
|----------|-------------|------|
| `protocols.py: ProfileDataSource` | MCP 注册的 Agent 使用 ClaudeAdapter（MCP 用户的 LLM 是 Claude Code 自带的） | 不变 |
| `protocols.py: Skill` | MCP 不直接调用 Skill，通过 Backend API 间接触发 | 不变 |
| `events.py: 7 事件类型` | MCP 通过轮询 negotiation state 间接获取事件效果 | 不变 |
| `schemas.py: Request/Response` | MCP Server 构造相同的 Request body | 不变 |
| `AgentRegistry` | MCP 注册的 Agent 和 Web 注册的 Agent 进入同一个 Registry | 不变 |

**协议层零改动**。MCP 是纯应用层入口。

---

## 9. 开发者模式 vs 普通模式 工具映射

```
普通模式                    开发者模式
─────────────              ──────────────
towow_join          ═══>   list_scenes + register_agent
towow_demand        ═══>   submit_demand + [轮询] + confirm
towow_status        ═══>   get_negotiation
```

普通模式是开发者模式的严格子集。任何普通模式的操作都可以用开发者模式的工具组合完成。

---

## 10. 关键约束总结

1. **Formulation 必须确认**: 任何模式、任何入口，formulation 都需要用户确认后才广播（Section 10.2）
2. **Profile 结构化在用户端**: MCP Server 不调用 LLM，只提供引导提示词
3. **MCP Server 是 API 客户端**: 不嵌入引擎逻辑，只翻译 MCP tool calls → REST API
4. **一人一 ID**: user_id 网络唯一，本地持久化
5. **协议层不变**: MCP 的所有操作通过已有的 5 个写 API + 2 个新读 API 完成
