# ADR-002: MCP 作为通爻网络的独立入口

**日期**: 2026-02-12
**状态**: 已批准
**前置依赖**: ADR-001 (AgentRegistry) 实现完成后方可开始代码实现
**关联**: ADR-001 (AgentRegistry), Architecture Section 7.1, Section 13.2

---

## 背景

通爻网络目前有两个应用层入口：Website (Next.js) 和 App Store。用户需要通过 Web 注册、登录、填写 Profile 才能参与协商。

MCP (Model Context Protocol) 是连接 AI 模型与外部工具的标准协议。Claude Code、Cursor 等 AI 开发工具支持 MCP。

**核心想法**：封装通爻网络为 MCP Server，让用户在 Claude Code/Cursor 里直接注册 Agent、参与协商、查看结果——完全不碰 Web。

**为什么现在做**：
1. 展示通爻协议的可扩展性（应用层可替换，协议层不变）
2. 降低 Agent 接入门槛到最低（在已有 AI 工具里说一句话就能注册）
3. 吸引开发者群体（他们最先理解响应范式的价值）

---

## 已达成的共识

### 共识 1: MCP 是应用层入口，和 Website 完全平级

```
应用层 ─── Website | App Store | MCP Server（新）
能力层 ─── Skills, LLM 客户端
基础设施层 ─── AgentRegistry, Encoder, EventPusher
协议层 ─── 状态机, 事件语义, 递归规则（不可改）
```

MCP Server 消费的是 Section 13.2 定义的同一套协议层 API（5 个调用 + 9 种事件）。协议层和基础设施层不需要改动。

**架构原则**：0.2 本质与实现分离——协议不变，入口可以是网页、MCP、未来的 CLI。

### 共识 2: MCP 完全独立，不依赖 Web

用户可以只通过 MCP 完成完整流程：注册 Agent → 加入 Scene → 提需求 → 确认 formulation → 看方案。

理由：Web 注册也只是提交一段数据。MCP 做同样的事，不需要 Web 作前置。

SecondMe OAuth 连接是未来的多入口联通功能（一个人从 MCP 和 Web 同时进入，身份关联），不是 MCP 入口的前置条件。

### 共识 3: 开发者模式 + 普通模式，全量 API 先行

**开发者模式**（默认，全量工具暴露）：

| MCP Tool | 对应协议层 API | 说明 |
|----------|---------------|------|
| `towow_create_scene` | `create_scene(config)` | 创建场景 |
| `towow_register_agent` | `register_agent(scene_id, profile_data)` | 注册 Agent |
| `towow_list_scenes` | 读取操作 | 查看可用场景 |
| `towow_list_agents` | 读取操作 | 查看场景内 Agent |
| `towow_submit_demand` | `submit_demand(scene_id, user_id, intent)` | 提交需求 |
| `towow_confirm` | `confirm_formulation(demand_id, text)` | 确认 formulation |
| `towow_get_negotiation` | 读取操作 | 查看协商状态、事件、方案 |
| `towow_action` | `user_action(negotiation_id, action)` | 用户操作（取消等） |

**普通模式**（简化，语法糖）：

| MCP Tool | 内部等价于 | 说明 |
|----------|-----------|------|
| `towow_join` | register_agent + 加入场景 | 一步完成注册 |
| `towow_demand` | submit_demand + 等待 formulation + 提示确认 | 简化流程 |
| `towow_status` | get_negotiation | 查看结果 |

两种模式可切换。普通模式是开发者模式的语法糖，内部调用同一套 API。

### 共识 4: Profile 采集——用户的 AI 做结构化处理

流程：

```
用户丢原始内容（简历、自我介绍、任意材料）
    ↓
MCP Server 提供一段引导提示词（描述通爻需要什么信息）
    ↓
用户的 AI（Claude Code 的 LLM）基于：
  - 用户提供的原始内容
  - 引导提示词
  - 对用户的已有了解（对话上下文）
处理并输出结构化 Profile 数据
    ↓
MCP Server 用结构化数据调用 register_agent
```

**关键设计**：
- LLM 调用用的是**用户自己的模型**，不消耗通爻的 API 额度
- 不需要担心延迟——这是注册时的一次性操作
- 引导提示词定义了通爻需要什么字段（skills, bio, experience 等）
- 用户的 AI 比我们更了解用户，结构化质量更高

**架构原则**：0.4 计算分布在端侧。Profile 结构化发生在用户端，通爻只接收结果。

### 共识 5: 事件流——轮询 + 关键节点通知

MCP 没有 WebSocket，采用轮询模式：

```
submit_demand → 返回 negotiation_id
    ↓
MCP Server 内部轮询 Backend（或用户手动 towow_status）
    ↓
每到关键状态转变，MCP 向用户报告：
  "需求已丰富化，等待你确认..."
  "共振检测完成，激活了 5 个 Agent..."
  "所有 Offer 已收集，Center 正在综合..."
  "方案已生成。"
    ↓
用户可以：
  - 在 MCP 里看完整方案
  - 去 Web 查看协商实时过程（未来连通后）
  - 保存方案为本地文件/文档
```

**Formulation 确认是协议层要求**（Section 10.2）：无论开发者模式还是普通模式，formulation 都需要用户确认后才广播。MCP 在 formulation.ready 时暂停，等待用户 confirm。

**MCP 和 Web 暂不连通**——先保证 MCP 端到端跑通，后续再做跨入口的实时展示。

### 共识 6: MCP Server 远程调用 Backend REST API

```
用户机器:
  Claude Code ←→ MCP Server (localhost, 轻量进程)
                    ↕ HTTPS
远端 (Railway):
  Backend Server (port 8080)
    ├── V1 Engine
    ├── App Store
    └── Auth
```

MCP Server 是纯粹的 API 客户端——把 MCP tool calls 翻译成 Backend REST API 调用，把响应翻译回 MCP 结果。

不在 MCP Server 里嵌入引擎逻辑。保持应用层和协议层的分离。

### 共识 7: 身份持久化——一人一 ID

- 整个网络中一个用户只有一个唯一 ID
- MCP 注册时生成，存入 MCP Server 本地配置（`~/.towow/config.json` 或类似）
- 后续 session 自动携带，不需要重新注册
- 未来上链（DID），但现在先用平台签发的 UUID（Section 7.1.2 已预留）
- 多入口联通（MCP + Web + SecondMe）是未来功能，ID 系统从一开始就支持

---

## 架构原则对齐

| 原则 | 如何体现 |
|------|---------|
| 0.2 本质与实现分离 | MCP 是新的应用层实现，协议层不变 |
| 0.4 计算分布在端侧 | Profile 结构化由用户自己的 AI 完成 |
| 0.7 复杂性从简单规则生长 | 普通模式是开发者模式的语法糖，不是另一套系统 |
| 0.8 投影是基本操作 | 注册 = 丢原始数据 → 投影成 Agent，入口方式不影响投影本身 |
| 7.1 Agent 就是 Profile | MCP 注册就是提交 Profile 数据，门槛最低 |
| 13.2 统一 API 边界 | MCP 消费同一套 5 个调用 API + 9 种事件 |

---

## 影响范围

| 影响对象 | 变更类型 | 说明 |
|----------|---------|------|
| Backend REST API | 可能需要补充 | list_scenes, list_agents 等读取端点（现有 API 主要是写操作） |
| Backend 认证 | 新增 | MCP 客户端的 token 认证（区别于 Web 的 cookie/session） |
| 新增 MCP Server 包 | 新增 | 独立的 MCP Server 实现（Python 或 Node.js） |
| 引导提示词 | 新增 | Profile 结构化的引导 prompt |
| 文档 | 新增 | MCP 使用指南 |
| 现有协议层 | **不变** | engine, skills, hdc, adapters 不需要改动 |

---

## 待后续讨论

1. **MCP Server 的技术选型**：Python (与 backend 同栈) vs Node.js (MCP 生态更成熟)？
2. **引导提示词的设计**：怎么引导用户的 AI 输出最优质的结构化 Profile？
3. **轮询策略细节**：轮询间隔、超时、最大等待时间
4. **多入口联通**：MCP 注册的用户如何后续关联 SecondMe/Web 身份？
5. **MCP 发布和分发**：怎么让用户安装和配置 MCP Server？
6. **安全模型**：API token 的签发、刷新、权限范围
