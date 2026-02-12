# ADR-003: 协商图谱可视化

**日期**: 2026-02-12
**状态**: 已批准
**关联**: Feature 002 (plan_json 保障), Issue 004 (展示层缺陷)

---

## 1. 系统上下文（自包含）

### 1.1 通爻协商协议概要

通爻网络是一个 AI Agent 协作平台，核心是**响应范式**：用户发出需求信号，能响应的 Agent 自己判断、自己来响应，而不是用户去搜索 Agent。

一次完整协商的流程：

```
用户提交需求 (raw_intent)
  → Formulation: 需求精炼（可能用 LLM 增强原始意图）
  → 用户确认精炼后的需求
  → Resonance: 将需求编码为 HDC 向量，与场景中所有 Agent 向量做余弦相似度
  → 按 k_star（最大参与数）和 min_score（最低共振分数）筛选
  → Offer: 通过筛选的 Agent 并行生成 offer（各自回复"我能做什么"）
  → Barrier: 所有 Agent 回复完毕或超时
  → Center Synthesis: Center Agent 综合所有 offer，可能：
    - ask_agent: 向某个 Agent 追问（可多轮）
    - discover_connections: 发现两个 Agent 之间的互补关系
    - create_sub_demand: 识别缺口，触发子协商（递归）
    - output_plan: 输出最终方案
  → Plan Ready: 方案生成，包含 plan_text（文本）+ plan_json（结构化拓扑）
```

### 1.2 后端事件系统（7 种事件）

后端通过 WebSocket 向前端推送 7 种事件：

| 事件 | 数据 | 含义 |
|------|------|------|
| `formulation.ready` | raw_intent, formulated_text, enrichments, degraded | 需求精炼完成 |
| `resonance.activated` | activated_count, agents[{agent_id, display_name, resonance_score}] | 共振匹配结果 |
| `offer.received` | agent_id, display_name, content, capabilities[] | 单个 Agent 的 offer |
| `barrier.complete` | total_participants, offers_received, exited_count | 所有 offer 收集完毕 |
| `center.tool_call` | tool_name, tool_args, round_number | Center 的每次工具调用 |
| `plan.ready` | plan_text, center_rounds, participating_agents[], plan_json | 方案生成完毕 |
| `sub_negotiation.started` | sub_negotiation_id, gap_description | 子协商启动 |

### 1.3 当前前端状态（问题所在）

前端协商页面位于 `website/app/negotiation/`，使用以下组件：

- `NegotiationPage.tsx` — 页面布局：输入 → PhaseIndicator → 两栏（AgentPanel + CenterPanel）→ EventTimeline
- `AgentPanel.tsx` — Agent 卡片列表（显示 resonance score + offer 内容）
- `CenterPanel.tsx` — Center 活动列表 + plan_text 文字显示
- `EventTimeline.tsx` — 7 种事件的文字日志

**三个核心缺失**：

1. **方案无处可看** — CenterPanel 只有 plan_text 按行分段显示。plan_json（任务拓扑、参与者分工、依赖关系）完全未接入。后端 Feature 002 已保障 plan_json 三层防线永不为 None，但前端从未使用。

2. **图谱动画链条断裂** — 只有 Agent 卡片出现的简单动画。缺少：
   - 共振筛选可视化（谁通过/谁没通过）
   - Center 形成动画
   - Center 与 Agent 的多轮对话（ask_agent）
   - Agent 间关系发现（discover_connections）
   - 子协商生长
   - 方案从 Center 展开

3. **全流程不可视** — EventTimeline 只是文字条目，用户无法直观"看到"协商在发生什么。空间结构和时间演化完全丢失。

**核心矛盾**：后端协议有完整的 7 种事件 + 丰富数据（分数、多轮交互、plan_json 拓扑），但前端只用了一小部分，且以卡片/列表呈现。

### 1.4 当前后端参数

- `k_star`：最大参与 Agent 数，当前来源于 `scene.expected_responders`（创建场景时设置），用户提交需求时不能调整
- 共振阈值：**不存在**。`resonance.py` 的 `detect()` 只做 top-k 排序，无最低分数筛选。0.1 分的 Agent 也会参与 offer 生成（浪费 LLM 调用）
- `plan_json`：后端 engine 有三层防线保障永不为 None，但 `events.py` 的 `plan_ready()` 工厂函数是条件携带（`if plan_json is not None`）

---

## 2. 选项分析

### 选项 A: 图谱为主（Graph-First）

用 SVG + Framer Motion 实现动态图谱，每种协议事件映射为一次图谱变异（加节点、加边、动画）。图谱占页面主区域，点击任何元素查看详情。方案内嵌在图谱终态中。

- 优势：直观展示协商的空间结构和时间演化；与协议的"投影"概念一致；动画丰富度高
- 劣势：实现复杂度高（布局算法、动画编排、交互设计）

### 选项 B: 增强时间线（Timeline-Enhanced）

保持当前时间线为主的布局，但每个阶段内嵌可视化卡片。

- 优势：改动量小
- 劣势：丢失空间结构，无法直观展示 Agent 之间的关系和 Center 交互

### 选项 C: 分阶段全屏

每个协商阶段占满屏幕，滚动推进。

- 优势：每个阶段空间充分
- 劣势：用户失去全局视野

## 3. 决策

**选择选项 A：图谱为主。**

原因：
- 协商本质是多方在空间中的互动，图谱是最自然的表达
- 后端已有完整事件+数据，图谱能充分利用
- 与通爻"投影"哲学一致：图谱是协议事件流的空间投影（Section 0.8）
- 用户明确要求看到全链条 + Center 交互 + 方案

## 4. 核心原则

- **Section 0.8 投影是基本操作**：图谱是事件流的空间投影
- **Section 0.5 代码保障 > Prompt 保障**：图谱状态由事件 reducer 驱动，不依赖 LLM 输出
- **Section 0.2 本质与实现分离**：图谱组件只消费事件数据，不关心事件如何产生
- **Section 0.6 需求 ≠ 要求**：共振阈值不做硬筛选，而是用户可调的偏好参数

---

## 5. 八条共识

### 共识 1: Event → Graph Mutation 映射

协商图谱的本质：**协议事件流的空间投影**。每种事件对应确定的图谱变异操作。

| 事件 | 图谱变异 |
|------|---------|
| `formulation.ready` | 需求节点出现/变形（模糊→清晰） |
| `resonance.activated` | 共振波纹扩散 → 候选节点闪现 → 通过的亮起连线 / 未通过的渐隐 |
| `offer.received` | Agent 节点脉冲 + 数据粒子流向中心 |
| `barrier.complete` | Center 节点形成 + 连线固化 |
| `center.tool_call(ask_agent)` | Center ↔ Agent 对话动画（脉冲往返 + 对话气泡） |
| `center.tool_call(discover_connections)` | Agent ↔ Agent 新边弹出 |
| `center.tool_call(create_sub_demand)` | 子图谱从缺口节点生长 |
| `center.tool_call(output_plan)` | Center 展开为方案视图 |
| `plan.ready` | 任务分配线射出 + 方案面板出现 |

图谱状态完全由事件 reducer 驱动，没有事件就没有变异。这保证了可重放性（replay 事件就能重现图谱）。

### 共识 2: 共振阈值用户可调（默认 0.5）

**阈值（min_score）不是硬编码的协议常数，是用户可调的偏好参数。**

- 前端提供阈值滑块，默认 0.5，范围 0.0 ~ 1.0
- 阈值通过 submit API 传到后端
- 后端 `resonance.py` 按阈值分为 activated（≥ min_score）和 filtered（< min_score）
- 只有 activated 组参与后续 offer 生成
- 事件数据同时携带 activated + filtered 两组（前端用 filtered 做"渐隐"动画）

与 Section 0.6 "需求 ≠ 要求"一致：阈值是偏好，不是硬约束。用户降低阈值可以纳入更多 Agent（发现未知价值），提高阈值聚焦高匹配度 Agent。

### 共识 3: K 值（k_star）用户可调

- 前端提供 K 值输入/滑块，默认从 scene 配置取
- K 值和阈值一起通过 submit API 传递
- `SubmitDemandRequest` 新增 `k_star: Optional[int]` 和 `min_score: Optional[float]`
- 后端：用户指定则覆盖 scene 默认值

### 共识 4: Center 交互全部可视化（4 种工具）

后端 `center.tool_call` 事件的 4 种 tool_name 全部有独立动画：

1. **`ask_agent`**（与单个 Agent 对话）：
   - Center → Agent 方向的脉冲线 + 问题气泡
   - 等待后 Agent → Center 方向的脉冲线 + 回复气泡
   - 多轮对话时：动画序列排队执行，每轮都可见
   - 点击边可看完整问答内容

2. **`discover_connections`**（发现 Agent 间关系）：
   - Agent A ↔ Agent B 之间新边弹出
   - 边上标注发现原因
   - 点击边可看关系详情

3. **`create_sub_demand`**（触发子协商）：
   - 缺口标记出现在图谱边缘
   - 子图谱从缺口节点生长出来（缩略版的完整协商图谱）
   - 点击可展开子协商详情

4. **`output_plan`**（输出方案）：
   - Center 节点展开动画
   - 任务分配线从 Center 射向对应 Agent
   - 方案面板从图谱下方或侧面滑入

### 共识 5: 方案内嵌，plan_json 驱动拓扑

- 方案在图谱终态中内嵌展示，**不跳转独立页**
- 使用 plan_json 渲染结构化拓扑：
  - 任务节点（带标题、描述、状态）
  - 任务间依赖边（prerequisites）
  - 每个任务标注 assignee（指向哪个 Agent）
- plan_text 作为方案文本摘要展示
- Accept/Reject 按钮保留
- 可点击任务节点查看详情

plan_json 结构（由后端 Feature 002 三层防线保障）：
```json
{
  "summary": "方案摘要",
  "participants": [{"agent_id", "display_name", "role_in_plan"}],
  "tasks": [{"id", "title", "description", "assignee_id", "prerequisites[]", "status"}],
  "topology": {"edges": [{"from": "task_1", "to": "task_2"}]}
}
```

### 共识 6: 点击详情面板

图上每个元素可点击，弹出详情面板（侧滑）：

| 点击目标 | 详情内容 |
|----------|---------|
| Agent 节点 | 共振分数、offer 全文、capabilities 列表、在方案中的角色 |
| Center 节点 | 综合轮次数、每轮工具调用列表、推理过程 |
| 需求节点 | 原始意图 vs 精炼文本、enrichments |
| 共振边 | 共振分数、连接时间 |
| 交互边（ask_agent）| 完整问答对话内容 |
| 发现边（discover）| 发现的关系描述 |
| 任务节点（plan）| 任务详情、分配的 Agent、依赖的前置任务 |

### 共识 7: SVG + Framer Motion 技术选型

- **SVG** 渲染图谱：每个节点/边是独立 React 组件，天然支持 onClick
- **Framer Motion** 驱动动画：variants、animate、layout、AnimatePresence
- **径向布局**：需求节点在中心，Agent 节点均匀分布在圆环上
- 节点量级 10-50 个，SVG 性能完全够用（无需 Canvas/WebGL）
- 与 Next.js 生态无缝集成

选型理由：React Flow 偏向编辑器 UI，D3 与 React 集成别扭，Canvas 不支持 DOM 事件。SVG + Framer Motion 在动画控制精度和 React 原生集成两方面最优。

### 共识 8: 页面布局

```
┌─────────────────────────────────────────────────┐
│  需求输入 + K值/阈值控件（确认后收起为 bar）       │
├─────────────────────────────────────────────────┤
│                                                 │
│              协商图谱（主视觉区域）                │
│              占页面 60-70% 高度                   │
│              SVG + 径向布局 + 动画                │
│                                                 │
├──────────────────────┬──────────────────────────┤
│   事件日志（精简）     │   详情/方案面板           │
│   可收起              │   点击节点时滑入          │
│                      │   方案阶段自动展示        │
└──────────────────────┴──────────────────────────┘
```

---

## 6. 影响范围

### 后端契约变更（4 处）

| 文件 | 变更 | 说明 |
|------|------|------|
| `backend/towow/hdc/resonance.py` | `detect()` 新增 `min_score` 参数，返回 `(activated, filtered)` 二元组 | Protocol 接口变更 |
| `backend/towow/core/events.py` | `resonance_activated()` 新增 `filtered_agents` 字段；`plan_ready()` 始终携带 plan_json | 事件 schema 变更 |
| `backend/towow/api/schemas.py` | `SubmitDemandRequest` 新增 `k_star: Optional[int]` 和 `min_score: Optional[float]` | API schema 变更 |
| `backend/towow/api/routes.py` | `submit_demand()` + `_run_negotiation()` 传递 k_star / min_score | 实现变更 |
| `backend/towow/core/engine.py` | `_run_encoding()` 适配 detect() 新返回值 + min_score 参数 | 实现变更 |

### 前端契约变更

| 文件 | 变更 |
|------|------|
| `website/types/negotiation.ts` | `ResonanceActivatedData` 加 `filtered_agents`；`PlanReadyData` 加 `plan_json`；`SubmitDemandRequest` 加 `k_star` + `min_score`；新增 `PlanJson` 类型 |
| `website/hooks/useNegotiationStream.ts` | reducer 状态增加 `filteredAgents` |
| `website/hooks/useNegotiationApi.ts` | `submitDemand()` 接受 k_star + min_score |

### 前端新增组件（~12 文件）

| 文件 | 说明 |
|------|------|
| `NegotiationGraph.tsx` | 核心图谱容器：SVG viewBox、径向布局、事件→动画调度 |
| `graph/DemandNode.tsx` | 需求节点 |
| `graph/AgentNode.tsx` | Agent 节点（分数色彩、offer 状态、角色标签） |
| `graph/CenterNode.tsx` | Center 节点（barrier 后形成，synthesis 时脉冲） |
| `graph/ResonanceEdge.tsx` | 共振连线（粗细=分数，数据粒子动画） |
| `graph/InteractionEdge.tsx` | 交互连线（ask_agent 对话、discover 新边） |
| `graph/SubGraph.tsx` | 子协商子图 |
| `graph/layout.ts` | 径向布局算法 |
| `DetailPanel.tsx` | 详情侧滑面板 |
| `PlanView.tsx` | 方案展示（plan_json 拓扑 + plan_text） |
| `ResonanceControls.tsx` | K 值 + 阈值控件 |
| `NegotiationPage.tsx` | 页面布局重构 |
