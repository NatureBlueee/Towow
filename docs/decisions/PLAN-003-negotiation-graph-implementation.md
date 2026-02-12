# PLAN-003: 协商图谱可视化实现方案

**关联**: ADR-003 (协商图谱可视化决策)
**日期**: 2026-02-12

本文档包含阶段 ③（接口设计）和阶段 ④（实现方案），是 ADR-003 的 companion 文档。

---

## 0. 关键前提（自包含）

### 当前后端关键文件和接口

| 文件 | 当前接口 | 说明 |
|------|---------|------|
| `backend/towow/hdc/resonance.py` | `detect(demand_vector, agent_vectors, k_star) → list[tuple[str, float]]` | 余弦相似度排序，返回 top-k*，无最低阈值 |
| `backend/towow/core/events.py` | `resonance_activated(negotiation_id, activated_count, agents)` | agents 只含通过的，无 filtered |
| `backend/towow/core/events.py` | `plan_ready(negotiation_id, plan_text, center_rounds, participating_agents, plan_json=None)` | plan_json 条件携带 |
| `backend/towow/api/schemas.py` | `SubmitDemandRequest(scene_id, user_id, intent)` | 无 k_star / min_score 参数 |
| `backend/towow/api/routes.py:323` | `k_star=scene.expected_responders` | K 值来源于 scene，用户不可调 |
| `backend/towow/core/engine.py:431-434` | `detect(demand_vector, candidate_vectors, k_star)` | 调用 detect，所有结果都加入 participants |

### 当前前端关键文件

| 文件 | 说明 |
|------|------|
| `website/types/negotiation.ts` | `ResonanceActivatedData` 无 filtered_agents；`PlanReadyData` 无 plan_json |
| `website/hooks/useNegotiationStream.ts` | reducer 无 filteredAgents 状态 |
| `website/hooks/useNegotiationApi.ts` | `submitDemand(scene_id, user_id, intent)` 无 k_star / min_score |
| `website/components/negotiation/NegotiationPage.tsx` | 两栏布局（AgentPanel + CenterPanel），无图谱 |

### 后端 center.tool_call 的 4 种 tool_name

来自 `backend/towow/skills/center.py`，Center Agent 在 synthesis 阶段可调用的工具：

1. `ask_agent` — tool_args: `{agent_id: str, question: str}`，向特定 Agent 追问
2. `discover_connections` — tool_args: `{agent_a: str, agent_b: str, reason: str}`，发现两个 Agent 互补
3. `create_sub_demand` — tool_args: `{gap_description: str}`，识别缺口触发子协商
4. `output_plan` — tool_args: `{plan_text: str, plan_json: dict}`，输出最终方案

---

## 1. 接口设计（阶段 ③）

### 1.1 后端接口变更

#### ResonanceDetector.detect() — 新增 min_score，返回值变更

```python
# 变更前
async def detect(
    demand_vector: Vector,
    agent_vectors: dict[str, Vector],
    k_star: int,
) -> list[tuple[str, float]]

# 变更后
async def detect(
    demand_vector: Vector,
    agent_vectors: dict[str, Vector],
    k_star: int,
    min_score: float = 0.0,
) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]
#          ^activated (≥ min_score, 最多 k_star 个)    ^filtered (< min_score)
```

语义：
- 先按分数降序排列所有候选
- 按 min_score 划分为 activated / filtered 两组
- activated 组再受 k_star 上限约束
- 返回 `(activated, filtered)`，两组都按分数降序

默认 min_score=0.0 保证向后兼容——不传阈值时行为与旧版一致。

#### resonance_activated 事件 — 新增 filtered_agents

```python
resonance_activated(
    negotiation_id=...,
    activated_count=len(activated),
    agents=[{agent_id, display_name, resonance_score}],          # ≥ min_score
    filtered_agents=[{agent_id, display_name, resonance_score}],  # < min_score（新增）
)
```

#### SubmitDemandRequest — 新增 k_star + min_score

```python
class SubmitDemandRequest(BaseModel):
    scene_id: str
    user_id: str
    intent: str
    k_star: Optional[int] = None       # 新增：用户指定的最大参与数
    min_score: Optional[float] = None   # 新增：用户指定的最低共振阈值
```

后端逻辑：
- k_star: 用户指定 → 用用户值；None → 用 scene.expected_responders
- min_score: 用户指定 → 用用户值；None → 用默认值 0.5

#### plan_ready 事件 — plan_json 始终携带

```python
# 变更前：条件携带
def plan_ready(..., plan_json: dict | None = None):
    if plan_json is not None:
        data["plan_json"] = plan_json

# 变更后：始终携带（三层防线保障不为 None）
def plan_ready(..., plan_json: dict):
    data["plan_json"] = plan_json
```

### 1.2 前端接口变更

#### Types 新增/变更

```typescript
// ===== 变更 =====

interface ResonanceActivatedData {
  activated_count: number;
  agents: ResonanceAgent[];
  filtered_agents: ResonanceAgent[];  // 新增：未通过阈值的 Agent
}

interface PlanReadyData {
  plan_text: string;
  center_rounds: number;
  participating_agents: string[];
  plan_json: PlanJson;  // 新增：结构化方案拓扑
}

interface SubmitDemandRequest {
  scene_id: string;
  user_id: string;
  intent: string;
  k_star?: number;      // 新增
  min_score?: number;    // 新增
}

interface NegotiationState {
  // ...existing...
  filteredAgents: ResonanceAgent[];  // 新增
}

// ===== 新增 =====

interface PlanJson {
  summary?: string;
  participants: Array<{
    agent_id: string;
    display_name: string;
    role_in_plan: string;
  }>;
  tasks: Array<{
    id: string;
    title: string;
    description: string;
    assignee_id: string;
    prerequisites: string[];
    status: string;
  }>;
  topology?: {
    edges: Array<{ from: string; to: string }>;
  };
}
```

#### 图谱组件接口

```typescript
// 核心图谱 — 消费 NegotiationState，产出图谱可视化
interface NegotiationGraphProps {
  state: NegotiationState;
  onNodeClick: (nodeType: 'demand' | 'agent' | 'center', id: string) => void;
  onEdgeClick: (edgeId: string) => void;
  onTaskClick: (taskId: string) => void;
}

// 详情面板 — 侧滑展示点击元素的详情
interface DetailPanelProps {
  type: 'agent' | 'center' | 'demand' | 'task' | 'edge' | null;
  data: Record<string, unknown> | null;
  onClose: () => void;
}

// 方案视图 — plan_json 驱动的拓扑 + plan_text
interface PlanViewProps {
  plan: PlanReadyData;
  onAccept: () => void;
  onReject: () => void;
  onTaskClick: (taskId: string) => void;
}

// 共振参数控件 — K 值 + 阈值
interface ResonanceControlsProps {
  kStar: number;
  minScore: number;
  onKStarChange: (k: number) => void;
  onMinScoreChange: (score: number) => void;
  disabled: boolean;
}
```

---

## 2. 实现方案（阶段 ④）

### 2.1 变更链路分析

#### 链路 1: K 值 + 阈值从前端到后端

```
ResonanceControls (UI: 两个滑块)
  → NegotiationPage state: kStar, minScore
  → handleSubmit(intent, kStar, minScore)
  → useNegotiationApi.submitDemand(scene_id, user_id, intent, kStar, minScore)
  → POST /v1/api/negotiations/submit {scene_id, user_id, intent, k_star, min_score}
  → routes.py submit_demand(): req.k_star, req.min_score
  → _run_negotiation(): k_star = req.k_star ?? scene.expected_responders; min_score = req.min_score ?? 0.5
  → engine.start_negotiation(k_star=k_star, min_score=min_score)
  → engine._run_encoding(): resonance.detect(demand_vec, agent_vecs, k_star, min_score)
```

**契约变更点**：SubmitDemandRequest（后端+前端）、submitDemand() hook、engine.start_negotiation() 签名

**注意**：engine.start_negotiation() 签名变更需要同步所有调用方。当前调用方：
- `routes.py:315` — `_run_negotiation()`
- `apps/app_store/backend/app.py` — Store 的协商调用（如果有的话）

#### 链路 2: 共振筛选结果到前端图谱

```
resonance.detect(demand_vec, agent_vecs, k_star, min_score)
  → 返回 (activated, filtered)
  → engine._run_encoding():
    - 只把 activated 加入 session.participants
    - push resonance_activated 事件 {agents: activated, filtered_agents: filtered}
  → WS 推送
  → useNegotiationStream reducer: EVENT_RECEIVED
    - state.resonanceAgents = data.agents (activated)
    - state.filteredAgents = data.filtered_agents (filtered)
  → NegotiationGraph:
    - 所有 agent (activated + filtered) 的节点先短暂闪现（opacity 0→0.5）
    - activated: opacity 0.5→1 + 共振连线从中心生长
    - filtered: opacity 0.5→0 渐隐消失
```

**契约变更点**：detect() 返回值、resonance_activated 事件 schema、前端 types

#### 链路 3: Center 多轮交互到图谱动画

```
engine._run_synthesis() 循环：
  → LLM 返回 tool_calls
  → 逐个处理，每个 push center.tool_call 事件 {tool_name, tool_args, round_number}
  → WS 推送
  → reducer: centerActivities 数组追加
  → NegotiationGraph 动画调度器（按事件到达顺序排队执行）：

    ask_agent {agent_id: "agent_A", question: "能否详细说明..."}
      → Center→AgentA 脉冲线（0.3s）+ 问题气泡浮现
      → 等待 0.3s
      → AgentA→Center 脉冲线（0.3s）+ 回复气泡浮现
      → 气泡 1.5s 后淡出（或保留至下一个事件）

    discover_connections {agent_a: "A", agent_b: "B", reason: "互补技能"}
      → AgentA ↔ AgentB 之间弹出新的虚线边（0.4s）
      → 边中间标注发现原因的小标签

    create_sub_demand {gap_description: "缺少前端开发能力"}
      → 图谱边缘出现缺口标记（0.3s）
      → 从缺口生长出缩略子图谱（0.6s）

    output_plan {plan_text: "...", plan_json: {...}}
      → Center 节点展开动画（0.5s）
      → 任务分配线从 Center 射向各 Agent（0.4s/条）
      → 方案面板从底部滑入（0.5s）
```

**无契约变更**。center.tool_call 事件已有完整的 tool_name + tool_args 数据。

#### 链路 4: 方案 plan_json 到前端展示

```
plan.ready 事件 {plan_text, center_rounds, participating_agents, plan_json}
  → WS 推送
  → reducer: state.plan = data（含 plan_json）
  → NegotiationGraph 终态：
    - 任务分配线从 Center 指向各 Agent（每条线标注任务名）
    - Agent 节点上显示其在方案中的角色
  → PlanView 组件（图谱下方/侧面）：
    - plan_json.tasks 渲染为任务节点网络
    - plan_json.topology.edges 渲染为依赖线
    - plan_text 作为文本摘要
    - Accept / Reject 按钮
  → DetailPanel（点击任务节点）：
    - 任务标题、描述、状态
    - assignee Agent 信息
    - 前置依赖列表
```

**契约变更点**：PlanReadyData 新增 plan_json（前端 types），events.py plan_ready() 始终携带

---

### 2.2 文件变更清单

#### Track A: 后端（5 文件）

| # | 文件 | 变更 | 契约？ |
|---|------|------|--------|
| A1 | `backend/towow/hdc/resonance.py` | `detect()` 新增 min_score 参数，返回 (activated, filtered) 二元组 | 是 |
| A2 | `backend/towow/core/events.py` | `resonance_activated()` 加 filtered_agents 参数；`plan_ready()` plan_json 改为必填 | 是 |
| A3 | `backend/towow/core/engine.py` | `start_negotiation()` 加 min_score 参数；`_run_encoding()` 适配新 detect() 返回值 + 分两组处理 | 实现 |
| A4 | `backend/towow/api/schemas.py` | `SubmitDemandRequest` 加 `k_star: Optional[int]` + `min_score: Optional[float]` | 是 |
| A5 | `backend/towow/api/routes.py` | `submit_demand()` 读取 req.k_star / req.min_score；`_run_negotiation()` 传递给 engine | 实现 |

#### Track B: 前端类型 + 状态（3 文件）

| # | 文件 | 变更 |
|---|------|------|
| B1 | `website/types/negotiation.ts` | ResonanceActivatedData 加 filtered_agents；PlanReadyData 加 plan_json；新增 PlanJson 类型；SubmitDemandRequest 加 k_star + min_score |
| B2 | `website/hooks/useNegotiationStream.ts` | initialState 加 filteredAgents: []；reducer 处理 resonance.activated 时存 filtered_agents |
| B3 | `website/hooks/useNegotiationApi.ts` | submitDemand() 接受 k_star + min_score 可选参数 |

#### Track C: 前端图谱组件（新增 ~11 文件）

| # | 文件 | 说明 |
|---|------|------|
| C1 | `website/components/negotiation/graph/layout.ts` | 径向布局算法：节点定位 + 边路径计算 |
| C2 | `website/components/negotiation/NegotiationGraph.tsx` | 核心图谱容器：SVG viewBox、事件→动画调度队列、子组件编排 |
| C3 | `website/components/negotiation/graph/DemandNode.tsx` | 需求节点（中心位置，formulation 阶段变形动画） |
| C4 | `website/components/negotiation/graph/AgentNode.tsx` | Agent 节点（分数色彩渐变、offer 状态标记、角色标签） |
| C5 | `website/components/negotiation/graph/CenterNode.tsx` | Center 节点（barrier 后合成动画，synthesis 时脉冲效果） |
| C6 | `website/components/negotiation/graph/ResonanceEdge.tsx` | 共振连线（线宽=分数、数据粒子沿线流动动画） |
| C7 | `website/components/negotiation/graph/InteractionEdge.tsx` | 交互连线（ask_agent 脉冲往返 + 气泡、discover 新边弹出） |
| C8 | `website/components/negotiation/graph/SubGraph.tsx` | 子协商缩略图谱（create_sub_demand 时生长动画） |
| C9 | `website/components/negotiation/DetailPanel.tsx` | 详情侧滑面板（7 种内容类型） |
| C10 | `website/components/negotiation/PlanView.tsx` | 方案展示（plan_json 任务拓扑 + plan_text 文本 + Accept/Reject） |
| C11 | `website/components/negotiation/ResonanceControls.tsx` | K 值滑块 + 阈值滑块 |

#### Track D: 页面重构（2 文件）

| # | 文件 | 变更 |
|---|------|------|
| D1 | `website/components/negotiation/NegotiationPage.tsx` | 布局重构：顶部输入+控件（确认后收起）→ 图谱主区域 → 底部事件日志+详情面板 |
| D2 | `website/components/negotiation/NegotiationPage.module.css` | 布局 CSS 重写（图谱区域 60-70% 高度） |

#### Track E: Mock 数据 + Demo 模式

| # | 文件 | 变更 |
|---|------|------|
| E1 | `website/components/negotiation/__mocks__/events.ts` | 更新 mock 数据：加 filtered_agents、plan_json、多轮 ask_agent + discover tool_calls |

#### Track F: 后端测试

| # | 文件 | 变更 |
|---|------|------|
| F1 | `backend/tests/towow/test_resonance.py` | detect() 新返回格式 + min_score 各档位测试（0.0/0.5/0.8/1.0） |
| F2 | `backend/tests/towow/test_engine.py` | min_score 筛选逻辑；k_star + min_score 组合；plan_json 始终存在 |
| F3 | `backend/tests/towow/test_events.py` | resonance_activated filtered_agents 序列化；plan_ready plan_json 必填 |
| F4 | `backend/tests/towow/test_routes.py` | submit 传 k_star + min_score；默认值回退逻辑 |

---

### 2.3 接缝验证清单

| # | 接缝 | 跨越 | 验证方法 |
|---|------|------|---------|
| S1 | detect() 新返回值 → engine 消费 | A1→A3 | engine 测试 mock detect 返回二元组，验证只有 activated 进入 participants |
| S2 | resonance_activated 事件 → WS → reducer | A2→B2 | mock WS 推送含 filtered_agents 的事件，验证 state.filteredAgents 正确 |
| S3 | plan_ready 事件 plan_json → WS → PlanView | A2→C10 | mock WS 推送含 plan_json 的事件，验证 PlanView 渲染拓扑 |
| S4 | SubmitDemandRequest k_star+min_score → routes → engine | A4→A5→A3 | API 测试传 k_star=5 + min_score=0.3，验证 engine 实际使用这些值 |
| S5 | center.tool_call tool_args → 图谱动画 | 后端→C2 | mock 4 种 tool_name 的事件，验证图谱生成对应的节点/边/动画 |
| S6 | engine.start_negotiation() 签名变更 → 所有调用方 | A3→A5 | 搜索所有调用 start_negotiation 的地方，确保都传了 min_score |

---

### 2.4 实施顺序

```
Phase 1: 后端契约 + 测试 (Track A + F)
  ├─ A1: resonance.py — min_score + 二元组返回
  ├─ A2: events.py — filtered_agents + plan_json 必填
  ├─ A3: engine.py — 适配新返回值 + min_score 参数传递
  ├─ A4: schemas.py — SubmitDemandRequest 加字段
  ├─ A5: routes.py — 传递参数
  └─ F1-F4: 测试全部通过

Phase 2: 前端契约 (Track B)
  ├─ B1: types — 类型更新
  ├─ B2: useNegotiationStream — filteredAgents 状态
  └─ B3: useNegotiationApi — 参数传递

Phase 3: 图谱核心骨架 (Track C 部分)
  ├─ C1: layout.ts — 径向布局算法
  ├─ C2: NegotiationGraph.tsx — SVG 容器 + 事件→动画调度
  ├─ C3: DemandNode
  ├─ C4: AgentNode
  ├─ C5: CenterNode
  └─ C6: ResonanceEdge

Phase 4: 交互 + 方案 + 控件 (Track C 剩余 + Track D)
  ├─ C7: InteractionEdge (ask_agent 对话 + discover 新边)
  ├─ C8: SubGraph
  ├─ C9: DetailPanel
  ├─ C10: PlanView
  ├─ C11: ResonanceControls
  ├─ D1: NegotiationPage 布局重构
  └─ D2: CSS 重写

Phase 5: Mock + 端到端验证 (Track E)
  ├─ E1: Mock 数据更新（含完整多轮 center 交互）
  └─ Demo 模式端到端验证
```

---

### 2.5 动画编排

#### 径向布局 (layout.ts)

```
SVG viewBox: 0 0 800 600 (响应式缩放)

需求节点: (cx=400, cy=300) — SVG 中心
Agent 节点: 半径 R=220 的圆上均匀分布
  - 位置: (400 + 220*cos(θ_i), 300 + 220*sin(θ_i))
  - θ_i = 2π * i / N, N = activated + filtered 总数
  - 起始角度 = -π/2（从正上方开始）
Center 节点: (400, 300) — 需求节点缩小后让位给 Center
任务节点（plan 阶段）: 半径 R=120 的内圈，或需求节点下方
```

#### 动画时序

| 阶段 | 触发 | 时长 | 动画描述 |
|------|------|------|---------|
| 需求出现 | formulation.ready | 0.5s | 中心节点 scale(0)→scale(1) + 内容文字淡入 |
| 共振波纹 | resonance.activated | 1.0s | 圆形半透明波纹从中心向外扩散 |
| 候选闪现 | resonance.activated | 0.8s | 所有候选节点 opacity 0→0.5（同时出现） |
| 阈值筛选 | resonance.activated | 0.6s | activated: 0.5→1 + 连线从中心生长；filtered: 0.5→0 渐隐 |
| Offer 到达 | offer.received (逐个) | 0.4s/个 | 节点脉冲 + 粒子沿连线流向中心 + 状态标记变化 |
| Barrier 合成 | barrier.complete | 0.8s | 所有连线颜色加深固化 + Center 节点在中心合成出现 |
| ask_agent | center.tool_call | 0.8s/次 | 往: Center→Agent 脉冲 + 问题气泡(0.3s)；返: Agent→Center 脉冲 + 回复气泡(0.3s) |
| discover | center.tool_call | 0.4s | Agent↔Agent 新虚线边弹出 + 原因标签 |
| sub_demand | center.tool_call | 0.9s | 缺口标记(0.3s) + 子图谱生长(0.6s) |
| output_plan | center.tool_call | 0.5s | Center 展开 + 任务分配线射出 |
| 方案呈现 | plan.ready | 0.8s | 图谱终态（角色标签） + 方案面板滑入 |

动画队列：center.tool_call 的多个事件按到达顺序排队执行，不并行，保持可读性。每个动画完成后才播放下一个。

#### ask_agent 多轮对话可视化细节

Center 与同一个 Agent 可能有多轮对话（Round 1 问 A，Round 2 再问 A）。可视化处理：

- 第一次 ask_agent(A)：连线上出现问/答气泡
- 后续 ask_agent(A)：连线脉冲加强（线变粗或颜色变深），新的气泡替换旧的
- 点击这条边时，DetailPanel 展示完整对话历史（所有轮次的问答）
- 同一 Round 内对不同 Agent 的 ask_agent 可以并行动画（不同连线不冲突）

---

### 2.6 不在本次范围

- WebSocket 之外的实时通信方式（SSE 降级等）
- 子协商的完整递归可视化（本次只做一层缩略图生长动画，点击可展开详情面板看文字）
- 图谱的拖拽/缩放交互（本次固定视角，响应式缩放）
- Agent 头像/图片显示（用色彩哈希区分）
- 移动端适配（本次优先桌面端）
