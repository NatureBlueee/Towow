# PRD: Multi-Agent Negotiation MVP v3

> **文档路径**: `.ai/epic-multiagent-negotiation/PRD-multiagent-negotiation-v3.md`
>
> * EPIC_ID: E-001
> * 版本: v3
> * 状态: 可开发
> * 创建日期: 2026-01-22
> * 最后更新: 2026-01-22

---

## 0. 版本变更说明

### v3 相对于之前版本的核心变化

| 变更项 | v1/v2 状态 | v3 状态 | 变更原因 |
|--------|-----------|---------|----------|
| 协商引擎 | 硬编码 Mock（`demand.py` 预编排剧本） | **真实 LLM 驱动** | 核心问题：v1/v2 不是真正 AI 协商 |
| 协商轮次 | 最多 5 轮 | **最多 3 轮** | MVP 简化，减少延迟 |
| 递归层次 | 最多 2 层 | **最多 1 层** | MVP 简化，降低复杂度 |
| Agent 架构 | OpenAgent 设计但未实现 | **本地 Mock Agent 模式** | 继续用现有模式，聚焦 LLM 逻辑 |
| LLM 集成 | 无 | **9 个提示词全面集成** | 实现真正的 AI 协商能力 |

### 核心问题诊断

当前 `towow/api/routers/demand.py` 的 `trigger_mock_negotiation()` 函数存在以下问题：

1. **预编排剧本**：候选人、响应内容、协商过程都是硬编码
2. **无 LLM 调用**：没有使用任何提示词进行真实决策
3. **无真实协商**：Agent 响应是预设的，不基于需求内容
4. **缺乏动态性**：相同需求总是产生相同结果

v3 的目标是将这个 Mock 流程替换为真实的 LLM 驱动协商。

---

## 1. 关联文档

| 文档类型 | 路径 |
|----------|------|
| 主设计文档 | `/docs/ToWow-Design-MVP.md` |
| 技术方案 | `/docs/tech/TECH-TOWOW-MVP-v1.md` |
| 提示词清单 | `/docs/提示词清单.md` |
| Story 文档 | 本目录下 `STORY-*.md` |

---

## 2. 背景与目标

### 2.1 业务背景

ToWow 是一个基于 OpenAgent 框架的 AI 代理协作网络，核心能力是：
- 用户通过 SecondMe（数字分身）发起需求
- 系统智能匹配网络中的其他 Agent
- 多 Agent 协商形成合作方案

### 2.2 MVP 目标（2026-02-01 演示）

**核心验证假设**：上千个 Agent 的网络可以通信并产生涌现协商效果。

**成功标准**：
- 现场至少 100 个真实用户发起或响应需求
- 观众能够实时看到协商过程（流式展示）
- 至少出现一个触发子网递归的案例
- 系统在 2000 人同时在线时不崩溃

### 2.3 v3 版本目标

将现有的"预编排剧本"升级为"真实 LLM 驱动协商"，具体包括：

1. **需求理解**：用 LLM 理解用户需求的深层含义
2. **智能筛选**：用 LLM 从 Agent 池中筛选相关候选人
3. **响应生成**：用 LLM 让每个 Agent 独立决策是否参与
4. **方案聚合**：用 LLM 将多个 Offer 整合成可执行方案
5. **多轮协商**：用 LLM 处理反馈并调整方案
6. **缺口识别**：用 LLM 识别方案缺失的能力
7. **递归判断**：用 LLM 决定是否触发子网

---

## 3. MVP 范围定义

### 3.1 In Scope（本期必须实现）

| 功能模块 | 优先级 | 说明 |
|----------|--------|------|
| F1: 需求理解 | P0 | LLM 理解用户输入，提取深层需求 |
| F2: 智能筛选 | P0 | LLM 从 Agent 简介中筛选 10-20 个候选人 |
| F3: 响应收集 | P0 | 每个 Agent 独立决策：participate/decline/conditional |
| F4: 方案聚合 | P0 | LLM 将 Offer 整合为方案，分配角色和任务 |
| F5: 多轮协商 | P0 | 最多 3 轮反馈-调整循环 |
| F6: 缺口识别与子网 | P1 | 识别缺口，最多 1 层递归 |
| F7: 实时展示 | P0 | SSE 推送协商过程到前端 |
| F8: 妥协方案 | P0 | 无完美匹配时生成妥协方案 |

### 3.2 Out of Scope（本期不做）

| 功能 | 优先级 | 后续版本 |
|------|--------|----------|
| 真实 SecondMe 对接 | P2 | V2 |
| A2A 跨网络协议 | P2 | V2 |
| Offer 缓存与知识沉淀 | P2 | V2 |
| Agent 验证/信誉系统 | P3 | V3 |
| 断线重连 token | P2 | V2 |
| 复杂递归（>1 层） | P2 | V2 |
| 协商超过 3 轮 | P1 | V2 |

### 3.3 简化决策记录

| 决策项 | 原设计 | MVP 简化 | 原因 |
|--------|--------|----------|------|
| 协商轮次 | 最多 5 轮 | 最多 3 轮 | 减少延迟，演示效果足够 |
| 递归层次 | 最多 2 层 | 最多 1 层 | 降低复杂度，1 层已能展示递归能力 |
| Agent 架构 | OpenAgent gRPC 连接 | 本地 Mock Agent | 聚焦 LLM 逻辑，架构后续迭代 |
| SecondMe 对接 | 真实 MCP 调用 | Mock 服务 | 依赖外部服务，先用 Mock 验证流程 |
| 智能筛选 | 两层（规则+LLM） | 纯 LLM | 简化实现，LLM 上下文足够大 |

---

## 4. 核心用户故事

### 4.1 需求发起者视角

**作为**一个有协作需求的用户
**我希望**向网络发起需求，让 AI Agent 自动找到合适的协作者
**以便**不需要手动一个个联系，就能组织起一次活动

### 4.2 需求响应者视角

**作为**网络中的一个 Agent
**我希望**收到协作邀请时，基于我的能力和意愿做出决策
**以便**只参与真正适合我的协作

### 4.3 观众视角

**作为**演示现场的观众
**我希望**实时看到 AI Agent 的协商过程
**以便**理解 ToWow 网络的涌现协作能力

---

## 5. 功能需求清单

### 5.1 F1: 需求理解

| 项目 | 内容 |
|------|------|
| 描述 | 用户输入自然语言需求，LLM 理解并提取深层含义 |
| 提示词 | 提示词 1：需求理解 |
| 输入 | `raw_input`: 用户原始输入文本 |
| 输出 | `surface_demand`, `deep_understanding`, `capability_tags`, `context` |
| 验收标准 | AC-1.1: 能提取表面需求；AC-1.2: 能推断深层需求；AC-1.3: 能识别能力标签 |
| 关联 Story | STORY-01-demand-understanding.md |

### 5.2 F2: 智能筛选

| 项目 | 内容 |
|------|------|
| 描述 | 从所有 Agent 简介中筛选出 10-20 个与需求相关的候选人 |
| 提示词 | 提示词 2：智能筛选 |
| 输入 | `demand`, `all_agent_profiles` |
| 输出 | `definitely_related[]`, `possibly_related[]`, `reasons{}` |
| 验收标准 | AC-2.1: 不遗漏明显相关的 Agent；AC-2.2: 推断有理有据；AC-2.3: 返回 10-20 个候选 |
| 关联 Story | STORY-02-smart-filtering.md |

### 5.3 F3: 响应收集

| 项目 | 内容 |
|------|------|
| 描述 | 每个候选 Agent 独立决策是否参与，生成 Offer 或拒绝理由 |
| 提示词 | 提示词 3：回应生成 |
| 输入 | `agent_profile`, `demand`, `collaboration_invite` |
| 输出 | `decision`, `contribution`, `conditions`, `reasoning`, `decline_reason` |
| 决策类型 | `participate`: 参与；`decline`: 拒绝；`conditional`: 有条件参与 |
| 验收标准 | AC-3.1: 决策基于 Agent 能力；AC-3.2: 贡献内容具体真实；AC-3.3: 拒绝有合理理由 |
| 关联 Story | STORY-03-response-collection.md |

### 5.4 F4: 方案聚合

| 项目 | 内容 |
|------|------|
| 描述 | 将收到的 Offer 整合为结构化方案，分配角色和任务 |
| 提示词 | 提示词 4：方案聚合 |
| 输入 | `demand`, `all_offers[]` |
| 输出 | `proposal{summary, objective, assignments[], timeline, confidence}` |
| 验收标准 | AC-4.1: 方案满足需求核心；AC-4.2: 每个角色任务合理；AC-4.3: 有清晰分工 |
| 关联 Story | STORY-04-proposal-aggregation.md |

### 5.5 F5: 多轮协商

| 项目 | 内容 |
|------|------|
| 描述 | Agent 对方案反馈，管理员调整方案，最多 3 轮 |
| 提示词 | 提示词 5：方案反馈、提示词 6：方案调整 |
| 反馈类型 | `accept`: 接受；`negotiate`: 协商调整；`withdraw`: 退出 |
| 终止条件 | 全员 accept / 达到 3 轮 / 核心参与者退出 |
| 验收标准 | AC-5.1: 反馈能被合理处理；AC-5.2: 方案能迭代改进；AC-5.3: 3 轮内收敛 |
| 关联 Story | STORY-05-multi-round-negotiation.md |

### 5.6 F6: 缺口识别与子网

| 项目 | 内容 |
|------|------|
| 描述 | 识别方案缺口，判断是否触发子网递归（最多 1 层） |
| 提示词 | 提示词 7：缺口识别、提示词 8：递归判断 |
| 输入 | `demand`, `final_proposal`, `agent_feedbacks` |
| 输出 | `gaps[]`, `should_recurse`, `sub_demands[]` |
| 验收标准 | AC-6.1: 能识别明显缺口；AC-6.2: 递归判断有依据；AC-6.3: 子网能独立协商 |
| 关联 Story | STORY-06-gap-subnet.md |

### 5.7 F7: 实时展示

| 项目 | 内容 |
|------|------|
| 描述 | 通过 SSE 推送协商过程到前端，支持流式展示 |
| 事件类型 | 见下方 SSE 事件清单 |
| 验收标准 | AC-7.1: 事件实时推送；AC-7.2: 前端流式渲染；AC-7.3: 断线可重连 |
| 关联 Story | STORY-07-realtime-display.md |

### 5.8 F8: 妥协方案生成

| 项目 | 内容 |
|------|------|
| 描述 | 当没有完美匹配时，生成妥协方案 |
| 提示词 | 提示词 9：妥协方案生成 |
| 触发条件 | 无足够参与者 / 核心角色缺失 / 协商失败 |
| 验收标准 | AC-8.1: 有方案总比没方案好；AC-8.2: 说明能做到什么；AC-8.3: 给出替代建议 |
| 关联 Story | 包含在 STORY-04 中 |

---

## 6. 数据结构定义

### 6.1 Demand（需求）

```json
{
  "demand_id": "d-abc12345",
  "requester_id": "agent_alice",
  "raw_input": "我想在北京办一场AI主题聚会，需要场地和嘉宾",
  "surface_demand": "想在北京办一场AI主题聚会",
  "deep_understanding": {
    "motivation": "上个月参加聚会后很兴奋，想当组织者",
    "likely_preferences": ["轻松氛围", "质量优先"],
    "emotional_context": "期待、有信心"
  },
  "capability_tags": ["场地提供", "演讲嘉宾", "活动策划"],
  "context": {
    "location": "北京",
    "expected_attendees": 50,
    "date": "2026-02-15",
    "budget": "5000元以内"
  },
  "status": "processing",
  "created_at": "2026-01-22T10:00:00Z"
}
```

### 6.2 Offer（响应）

```json
{
  "offer_id": "offer_001",
  "agent_id": "agent_bob",
  "demand_id": "d-abc12345",
  "decision": "participate",
  "contribution": "我有一家咖啡厅可以提供活动场地，位于北京朝阳区，可容纳50人",
  "conditions": ["需要提前一周预约", "场地费可商量"],
  "reasoning": "这个活动正好是我擅长的领域，很乐意参与",
  "decline_reason": "",
  "confidence": 90,
  "submitted_at": "2026-01-22T10:05:00Z"
}
```

### 6.3 Proposal（方案）

```json
{
  "proposal_id": "prop_001",
  "demand_id": "d-abc12345",
  "version": 1,
  "summary": "关于'北京AI主题聚会'的协作方案",
  "objective": "组织一次高质量的技术交流活动",
  "assignments": [
    {
      "agent_id": "agent_bob",
      "display_name": "Bob",
      "role": "场地提供者",
      "responsibility": "提供30人会议室，负责茶歇和设备",
      "dependencies": []
    },
    {
      "agent_id": "agent_alice",
      "display_name": "Alice",
      "role": "技术讲师",
      "responsibility": "30分钟AI技术分享",
      "dependencies": ["需要Bob确认场地时间"]
    }
  ],
  "timeline": {
    "start_date": "2026-02-15",
    "milestones": [
      {"name": "方案确认", "date": "本周内"},
      {"name": "活动执行", "date": "2026-02-15"}
    ]
  },
  "confidence": "high",
  "created_at": "2026-01-22T10:10:00Z"
}
```

### 6.4 Gap（缺口）

```json
{
  "gap_type": "摄影师",
  "importance": 70,
  "reason": "需要记录活动内容，用于后续传播",
  "suggested_capability_tags": ["摄影", "活动拍摄"]
}
```

---

## 7. SSE 事件清单

| 事件类型 | 触发时机 | Payload 关键字段 |
|----------|----------|------------------|
| `towow.demand.understood` | 需求理解完成 | `demand_id`, `surface_demand`, `capability_tags` |
| `towow.filter.completed` | 智能筛选完成 | `demand_id`, `candidates[]`, `total_candidates` |
| `towow.channel.created` | 协商 Channel 创建 | `channel_id`, `demand_id`, `invited_agents[]` |
| `towow.offer.submitted` | Agent 提交响应 | `agent_id`, `decision`, `contribution`, `reasoning` |
| `towow.proposal.distributed` | 方案分发 | `proposal`, `participants[]`, `round` |
| `towow.negotiation.bargain` | 讨价还价 | `agent_id`, `bargain_type`, `content` |
| `towow.proposal.feedback` | 方案反馈 | `agent_id`, `feedback_type`, `reasoning` |
| `towow.agent.withdrawn` | Agent 退出 | `agent_id`, `reason` |
| `towow.gap.identified` | 缺口识别 | `gaps[]`, `is_complete` |
| `towow.subnet.triggered` | 子网触发 | `parent_demand_id`, `sub_demand`, `depth` |
| `towow.proposal.finalized` | 协商完成 | `final_proposal`, `status`, `summary` |

---

## 8. 提示词与 LLM 调用映射

| 功能 | 提示词编号 | 调用位置 | 输入 | 输出 |
|------|-----------|----------|------|------|
| 需求理解 | 提示词 1 | UserAgent | raw_input | surface_demand, deep_understanding |
| 智能筛选 | 提示词 2 | Coordinator | demand, all_profiles | candidates[] |
| 回应生成 | 提示词 3 | UserAgent | demand, agent_profile | decision, contribution |
| 方案聚合 | 提示词 4 | ChannelAdmin | demand, offers[] | proposal |
| 方案反馈 | 提示词 5 | UserAgent | proposal, assignment | feedback_type, reasoning |
| 方案调整 | 提示词 6 | ChannelAdmin | proposal, feedbacks[] | adjusted_proposal |
| 缺口识别 | 提示词 7 | ChannelAdmin | demand, proposal | gaps[] |
| 递归判断 | 提示词 8 | ChannelAdmin | demand, gaps | should_recurse, sub_demands |
| 妥协方案 | 提示词 9 | ChannelAdmin | demand, available_resources | compromise_proposal |

---

## 9. 验收标准总览

### 9.1 P0 验收标准（必须通过）

| AC ID | 功能 | 验收标准 | 验证方式 |
|-------|------|----------|----------|
| AC-1.1 | 需求理解 | 能从用户输入提取表面需求 | 单元测试 |
| AC-1.2 | 需求理解 | 能推断用户深层需求和偏好 | 人工验收 |
| AC-2.1 | 智能筛选 | 不遗漏明显相关的 Agent | 测试用例 |
| AC-2.2 | 智能筛选 | 每个候选都有选择理由 | 输出检查 |
| AC-3.1 | 响应收集 | 决策基于 Agent 实际能力 | 人工验收 |
| AC-3.2 | 响应收集 | 三种决策类型都能正确生成 | 单元测试 |
| AC-4.1 | 方案聚合 | 方案能满足需求核心目标 | 人工验收 |
| AC-4.2 | 方案聚合 | 每个角色有明确职责 | 输出检查 |
| AC-5.1 | 多轮协商 | 反馈能被处理并调整方案 | 集成测试 |
| AC-5.2 | 多轮协商 | 3 轮内能达成共识或终止 | 集成测试 |
| AC-7.1 | 实时展示 | 事件能在 2 秒内推送到前端 | 性能测试 |
| AC-7.2 | 实时展示 | 前端能正确渲染所有事件类型 | E2E 测试 |

### 9.2 P1 验收标准（重要但可延后）

| AC ID | 功能 | 验收标准 | 验证方式 |
|-------|------|----------|----------|
| AC-6.1 | 缺口识别 | 能识别方案中缺失的关键能力 | 人工验收 |
| AC-6.2 | 子网递归 | 能正确触发 1 层子网并返回结果 | 集成测试 |
| AC-8.1 | 妥协方案 | 无完美匹配时仍能给出方案 | 人工验收 |

---

## 10. UI 证据要求

### 10.1 需要的截图/录屏

| 场景 | 证据类型 | 说明 |
|------|----------|------|
| 需求提交 | 截图 | 用户输入需求的界面 |
| 筛选过程 | 截图 | 显示候选 Agent 列表 |
| 响应收集 | 录屏 | 展示 Agent 逐个响应的动态效果 |
| 方案展示 | 截图 | 聚合后的方案卡片 |
| 协商过程 | 录屏 | 展示讨价还价和反馈调整 |
| 最终结果 | 截图 | 协商成功/失败的结果页 |

### 10.2 前端关键状态

| 状态 | UI 表现 |
|------|---------|
| 空态 | 显示需求输入框，提示"输入你的需求" |
| 加载态 | 显示"AI 正在理解你的需求..." |
| 筛选中 | 显示"正在寻找合适的协作者..." |
| 协商中 | 实时展示事件时间线 |
| 成功态 | 显示最终方案卡片和参与者列表 |
| 失败态 | 显示失败原因和妥协方案建议 |

---

## 11. 风险与 OPEN

### 11.1 技术风险

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| LLM 响应慢（>5s） | 中 | 中 | 设置超时，流式输出 |
| LLM 输出格式不稳定 | 中 | 中 | JSON Schema 约束，重试机制 |
| 并发协商性能问题 | 低 | 高 | 限流，异步处理 |

### 11.2 业务风险

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| 匹配质量差 | 中 | 高 | 提示词优化，人工兜底 |
| 协商时间过长 | 中 | 中 | 3 轮限制，超时自动生成妥协方案 |
| Agent 简介不足 | 高 | 中 | 准备丰富的 Mock 数据 |

### 11.3 OPEN 事项

| 编号 | 问题 | 责任人 | 解决时点 |
|------|------|--------|----------|
| OPEN-1 | SecondMe 真实对接时机 | 产品 | V2 规划 |
| OPEN-2 | Agent 简介格式是否需要标准化 | 技术 | 开发前 |
| OPEN-3 | 妥协方案的兜底策略细节 | 产品 | 开发中 |

---

## 12. 变更记录

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|----------|
| v1 | 2026-01-20 | - | 初版 PRD，Mock 流程 |
| v2 | 2026-01-21 | - | 补充技术方案对齐 |
| v3 | 2026-01-22 | Claude | 核心升级：Mock -> LLM 驱动；简化：5轮->3轮，2层->1层 |
