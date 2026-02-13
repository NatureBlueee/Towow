# ADR-009: 开放注册 + Playground——认证与数据采集解耦

**日期**: 2026-02-13
**状态**: 已批准
**关联**: ADR-001 (AgentRegistry), ADR-002 (MCP 入口), Architecture Section 0.8, 7.1

---

## 背景

通爻网络目前唯一的登录入口是 SecondMe OAuth2。已有约 100 个 SecondMe 用户。

当前目标不是增长 SecondMe 用户，而是**展现项目基础建设的能力**——任何数据来源都能接入通爻网络。证明协议的普适性：向量响应不关心数据从哪来，只关心投影的结果。

**核心洞察**：当前 SecondMe 流程把两件不同层次的事耦合在了一起：
- **认证**（"你是谁"）—— 应用层
- **Profile 数据采集**（"你是什么样的存在"）—— 基础设施层

这两件事应该解耦。认证方式可以有很多（SecondMe OAuth、Google、邮箱、手机号），但 Profile 数据采集应该有一条统一的、数据来源无关的管线。

---

## 选项分析

### 选项 A: 认证与数据输入解耦
- 认证只负责"你是谁"（邮箱/手机/OAuth）
- 数据输入是独立步骤——粘贴文本、上传文件、丢链接
- 两件事分开做，各自可独立扩展
- **优势**：与原则 0.2 一致；每增加一种认证只加应用层代码；AgentRegistry 现有接口无需改动
- **劣势**：存在"已认证但没有 Profile"的中间状态

### 选项 B: 每种平台做专门的 OAuth + Profile 获取
- 像 SecondMe 那样，Google/GitHub/飞书各做一套 OAuth + Profile 获取
- **优势**：用户体验简单（一键完成认证+Profile）
- **劣势**：O(N) 开发成本；平台公开 Profile 信息有限（名字+头像远不如用户自述丰富）；违反原则 0.7

### 选项 C: Profile 输入即注册（认证后置）
- 选项 A 的进一步推演：提交数据就是注册，认证是后置可选的
- **优势**：门槛最低，与 7.1"Agent 就是 Profile"最一致
- **劣势**：匿名 Agent 管理复杂

---

## 决策

**选择选项 A（含 C 的精神）**：认证与数据输入解耦，最小认证前置。

具体设计：

### 1. 认证：最小联络信息

用户提交**邮箱或手机号**即完成注册。不需要 OAuth，不需要密码。

附加：一个 opt-in 勾选框——"是否关注通爻网络的后续动态"。

这不是完整的认证系统，而是**联络信息采集**。目的是：
- 后续可以联系到用户
- 为未来绑定 OAuth 身份（Google、SecondMe 等）留出关联点
- 有邮箱 = 永久存储的前提

### 2. Profile 数据：原始文本直接存，不做结构化

**关键决策：不需要 LLM 对 Profile 做结构化处理。**

理由——沿数据消费链路验证：

| 消费方 | 需要什么 | 原始文本够用吗 |
|--------|---------|-------------|
| `Encoder.encode(text)` | 任意字符串 | 够用——编码器接受任意文本 |
| `ResonanceDetector.detect()` | 向量 | 够用——只看向量，不看来源 |
| Formulation Skill prompt | profile 内容 | 够用——LLM 读原始文本比读 JSON 更自然 |
| Offer Skill prompt | profile 内容 | 够用——同上 |

原始文本同时满足向量化（共振匹配）和 LLM 消费（Skill prompt）两个需求。结构化是对 SecondMe API 返回格式的特定适配，不是协议要求。

存储方式：`profile_data = { "raw_text": "用户粘贴的内容", "source": "playground" }`

### 3. 展示：独立 `/playground` 页面

在 Website 新增 `/playground` 页面，定位是"零门槛体验通爻网络"。

用户操作流程：
```
1. 填写邮箱/手机号 + 勾选关注
2. 粘贴任意文本（简历、自我介绍、项目描述、任何内容）
3. 点击"加入网络"
   → 文本存储为 profile
   → encode() 生成向量
   → 注册到 AgentRegistry
   → 用户看到：你的 Agent 已创建，可以参与协商了
4. （后续）进入场景，体验协商流程
```

### 4. 数据永久存储

有邮箱/手机号的 Agent 永久存储。当前用 SQLite（Railway），后续扩容。

### 5. 后续扩展路径

| 阶段 | 能力 |
|------|------|
| V1（本次） | 纯文本粘贴 + 邮箱注册 |
| V2 | URL 解析（飞书文档、GitHub README 等自动抓取内容） |
| V3 | Google/GitHub OAuth 作为认证方式追加 |
| V4 | MCP 入口（ADR-002）—— 同一条注册链路的另一个入口 |

---

## 核心原则

| 原则 | 如何体现 |
|------|---------|
| 0.2 本质与实现分离 | 认证方式是应用层可替换的实现，Profile 采集是基础设施层 |
| 0.7 复杂性从简单规则生长 | 一条统一的注册管线（文本→向量→Agent），不是 N 套平台集成 |
| 0.8 投影是基本操作 | 粘贴文本 → encode() = 投影。数据来源不影响投影操作本身 |
| 7.1 Agent 就是 Profile | 提交 Profile 文本就等于创建了 Agent，门槛从"会登录"降到"会粘贴" |

---

## 影响范围

| 影响对象 | 变更类型 | 说明 |
|----------|---------|------|
| Backend API | **新增** | `POST /store/api/quick-register`（邮箱+文本→注册 Agent） |
| SQLite 存储 | **新增表** | 用户联络信息表（email/phone + opt-in + agent_id 关联） |
| AgentRegistry | **不变** | 现有 `register_agent(profile_data=dict)` 完全够用 |
| Encoder | **不变** | 现有 `encode(text)` 完全够用 |
| 协议层 | **不变** | 状态机、事件、Skills 全部不动 |
| Website | **新增** | `/playground` 页面 |
| App Store | **不变** | SecondMe 登录流程保持不变 |

---

## 与 ADR-002 (MCP) 的关系

MCP 入口和 Playground 是同一个本质的两种应用层实现：
- Playground：网页 → 粘贴文本 → register_agent()
- MCP：Claude Code → MCP tool → register_agent()

两者共用同一条基础设施链路：`数据 → AgentRegistry → Encoder → 可参与协商`

ADR-002 定义的 MCP 接口（towow_register_agent）和本 ADR 定义的 quick-register 最终都调用 `AgentRegistry.register_agent()`。
