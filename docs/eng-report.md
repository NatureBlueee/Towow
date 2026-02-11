# Machine JSON 输出与协作拓扑可视化 -- 工程分析报告

## A. Machine JSON Schema 设计

### A.1 目标 Schema

当前 `output_plan` 工具只接收一个 `plan_text: string`。下面是结构化 JSON schema 的完整设计：

```json
{
  "summary": "一句话总结协商结果",
  "participants": [
    {
      "agent_id": "agent_abc123",
      "display_name": "Alice",
      "avatar_color": "#F9A87C",
      "role_in_plan": "前端开发 - 负责 React Native 移动端实现"
    }
  ],
  "tasks": [
    {
      "id": "task_1",
      "title": "搭建移动端框架",
      "description": "使用 React Native 搭建 App 基本框架，包括导航和状态管理",
      "assignee_id": "agent_abc123",
      "prerequisites": [],
      "status": "pending"
    },
    {
      "id": "task_2",
      "title": "后端 API 开发",
      "description": "实现健康数据采集和分析 API",
      "assignee_id": "agent_def456",
      "prerequisites": [],
      "status": "pending"
    },
    {
      "id": "task_3",
      "title": "端到端联调",
      "description": "移动端与后端 API 联调测试",
      "assignee_id": "agent_abc123",
      "prerequisites": ["task_1", "task_2"],
      "status": "pending"
    }
  ],
  "topology": {
    "edges": [
      { "from": "task_1", "to": "task_3" },
      { "from": "task_2", "to": "task_3" }
    ]
  }
}
```

设计理由：

- **participants** 单独抽出来，因为一个 agent 可能承担多个 task，但身份信息只需声明一次。`avatar_color` 由前端赋值即可，schema 中可设为 optional。
- **tasks** 中的 `prerequisites` 数组构成了一个 DAG（有向无环图），这就是拓扑的本体。`topology.edges` 是它的冗余展平形式，方便前端直接消费而不用遍历所有 task 重建边集。
- **summary** 是纯文本，兼顾纯文本回退场景。
- **status** 枚举值 `pending | in_progress | done`，V1 只用 `pending`，为 Echo 阶段预留。

### A.2 center.py 中 `output_plan` 工具定义的改动

需要改动的文件：`/Users/nature/个人项目/Towow/backend/towow/skills/center.py`

**改动位置：第 34-47 行的 `TOOL_OUTPUT_PLAN` 字典。**

改动方式 -- 将 `input_schema` 从单个 `plan_text` 字段扩展为双模式：

```python
TOOL_OUTPUT_PLAN = {
    "name": "output_plan",
    "description": "Output the negotiation plan. Provide BOTH plan_text (summary) and plan_json (structured). This terminates the negotiation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "plan_text": {
                "type": "string",
                "description": "A human-readable text summary of the plan.",
            },
            "plan_json": {
                "type": "object",
                "description": "Structured plan with participants, tasks, and dependency topology.",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "One-sentence summary.",
                    },
                    "participants": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "agent_id": {"type": "string"},
                                "display_name": {"type": "string"},
                                "role_in_plan": {"type": "string"},
                            },
                            "required": ["agent_id", "display_name", "role_in_plan"],
                        },
                    },
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "assignee_id": {"type": "string"},
                                "prerequisites": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress", "done"],
                                },
                            },
                            "required": ["id", "title", "assignee_id"],
                        },
                    },
                    "topology": {
                        "type": "object",
                        "properties": {
                            "edges": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "from": {"type": "string"},
                                        "to": {"type": "string"},
                                    },
                                    "required": ["from", "to"],
                                },
                            },
                        },
                    },
                },
            },
        },
        "required": ["plan_text"],
    },
}
```

关键决策：**`plan_text` 保持 required，`plan_json` 设为 optional。** 这实现了渐进式兼容 -- LLM 可能不总是输出结构化 JSON，但必定输出文本。前端检测到 `plan_json` 存在时渲染拓扑图，否则回退到纯文本展示。

**风险**：中等。tool schema 的改变不影响其他工具（ask_agent、start_discovery 等）的行为，也不改变状态机转换逻辑。但 LLM 输出的 JSON 质量需要通过 prompt 引导保证。

### A.3 Center Prompt 的改动

需要改动的文件：`/Users/nature/个人项目/Towow/backend/towow/skills/center.py`

**改动位置：第 132-187 行的 `SYSTEM_PROMPT_ZH` 和 `SYSTEM_PROMPT_EN`。**

改动方式 -- 在 "行动" 部分增加结构化输出指导。以中文 prompt 为例，在 `## 行动` 之后增加：

```
## 输出格式
当使用 output_plan 时，同时提供：
- plan_text: 可读的方案全文
- plan_json: 结构化方案，包含：
  - summary: 一句话总结
  - participants: 每个参与者的 {agent_id, display_name, role_in_plan}
  - tasks: 每个任务的 {id, title, description, assignee_id, prerequisites, status}
    - id 用 "task_1", "task_2" ... 格式
    - prerequisites 列出前置任务的 id 数组（无前置则为空数组）
    - status 统一为 "pending"
  - topology.edges: 从 prerequisites 展平得到的 {from, to} 边列表

agent_id 和 display_name 必须与上面 Participant Responses 中给出的完全一致。
```

**风险**：低。Prompt 改动是纯增量的，不影响 Center 选择其他工具（ask_agent 等）的行为。Claude 对 JSON schema 的遵从性很高，特别是在 tool-use 模式下，tool 的 input_schema 本身就约束了输出结构。

### A.4 对 9 种事件的影响

**结论：需要改动 `plan.ready` 事件的 data 结构。**

当前 `plan.ready` 的 data 结构（见 `/Users/nature/个人项目/Towow/backend/towow/core/events.py` 第 142-156 行）：

```python
{
    "plan_text": plan_text,           # string
    "center_rounds": center_rounds,   # int
    "participating_agents": [...]     # list[str]
}
```

需要增加一个 `plan_json` 字段：

```python
{
    "plan_text": plan_text,
    "plan_json": plan_json,           # Optional[dict] -- 新增
    "center_rounds": center_rounds,
    "participating_agents": [...]
}
```

**涉及的改动链路**（3 个文件）：

1. **`events.py`** -- `plan_ready()` 工厂函数增加 `plan_json` 参数（Optional，默认 None）
2. **`engine.py`** -- `_finish_with_plan()` 方法（第 905-937 行）需要从 `tool_args` 中提取 `plan_json` 并传递给 `plan_ready()`
3. **`schemas.py`** -- `PlanResponse` 模型增加 `plan_json: Optional[dict] = None`

**对其他 8 种事件没有影响。** `formulation.ready`、`resonance.activated`、`offer.received`、`barrier.complete`、`center.tool_call`、`sub_negotiation.started` 以及 V1 不推送的 `execution.progress`、`echo.received` 均不需要改动。

**风险**：低。`plan_json` 是 additive change -- 旧的前端如果不识别这个字段，直接忽略即可。不破坏现有契约。

### A.5 具体改动链路总结

| 文件 | 改动位置 | 改动类型 | 风险 |
|------|---------|---------|------|
| `center.py` L34-47 | `TOOL_OUTPUT_PLAN` schema | 扩展 input_schema | 中（LLM 输出质量依赖 prompt） |
| `center.py` L132-187 | System prompt ZH/EN | 增加结构化输出指导 | 低 |
| `events.py` L142-156 | `plan_ready()` | 增加 `plan_json` 参数 | 低 |
| `engine.py` L905-937 | `_finish_with_plan()` | 从 tool_args 提取 plan_json | 低 |
| `engine.py` L614-617 | output_plan 处理 | 传递 plan_json 到 _finish_with_plan | 低 |
| `schemas.py` L78-83 | `PlanResponse` | 增加 `plan_json` 字段 | 低 |
| `models.py` L161 | `NegotiationSession.plan_output` | 考虑增加 `plan_json` 字段 | 低 |

---

## B. 前端流程图渲染

### B.1 前端数据消费格式

前端从 `plan.ready` 事件的 `data` 中收到：

```javascript
{
  plan_text: "...",         // 必定存在
  plan_json: {              // 可能不存在
    summary: "...",
    participants: [...],
    tasks: [...],
    topology: { edges: [...] }
  },
  center_rounds: 2,
  participating_agents: ["agent_abc", "agent_def"]
}
```

前端需要的渲染数据结构可以直接使用 `plan_json`，再辅以从协商过程中积累的信息（`graphAgents` 中的 avatar_color）：

```javascript
// 渲染所需的内部格式
{
  nodes: [
    { id: "task_1", title: "搭建移动端", assignee: { agent_id, display_name, avatar_color }, x, y },
    ...
  ],
  edges: [
    { from: "task_1", to: "task_3" },
    ...
  ],
  agents: [
    { agent_id, display_name, avatar_color, role_in_plan, tasks: ["task_1", "task_3"] },
    ...
  ]
}
```

### B.2 布局算法：层级布局（Layered/Sugiyama）

**推荐使用层级布局，不使用径向布局。** 理由：

- 协作拓扑本质上是一个 DAG（有向无环图），层级布局是 DAG 的自然表达方式。
- 径向布局适合表达"中心-辐射"关系（如现有 graph-view 中需求节点在中心、agent 在圆周），但任务依赖关系是"前后"关系，不是"中心-边缘"关系。
- 用户期望的"流程图"心智模型就是从左到右或从上到下的层级图。

**简化的层级布局算法**（无需第三方库，纯 JS 实现）：

1. **拓扑排序**：对 tasks 的 DAG 做拓扑排序，得到每个 task 的层级（layer）。没有前置任务的 task 在第 0 层，只依赖第 0 层的在第 1 层，以此类推。
2. **层内排列**：同一层的 task 按 assignee 分组，使同一 agent 的 task 相邻。
3. **坐标计算**：
   - X 轴 = layer * layerWidth（层间距，如 200px）
   - Y 轴 = 在该层内的序号 * nodeHeight（节点间距，如 100px）
   - 整体居中
4. **边绘制**：SVG `<path>` 使用贝塞尔曲线（cubic bezier），从源 task 右侧中点到目标 task 左侧中点。

```
Layer 0          Layer 1          Layer 2
[搭建前端] ------→ [联调测试] ------→ [发布]
[开发API]  ------↗
```

**代码量估算**：拓扑排序 + 坐标计算约 50 行 JS，SVG 渲染约 80 行，总计 150 行以内。

### B.3 节点渲染与交互

**节点设计**：

- 每个 task 节点渲染为一个带 avatar 圆圈的卡片
- Avatar 圆圈使用 assignee 的头像颜色和首字母（复用现有 `getInitial()` 和 `getAvatarColor()` 函数）
- 节点内显示 task.title
- 节点下方可以显示 assignee.display_name

**点击交互**：

```
用户点击节点 → 
  1. 该节点高亮（加 CSS class）
  2. 该节点的前置 task 和后续 task 的边高亮
  3. 其他节点和边降低透明度（opacity: 0.3）
  4. 右侧（或下方）展开信息面板，显示：
     - task.title + task.description
     - assignee 信息
     - 前置任务列表（可点击跳转）
     - 后续任务列表（可点击跳转）
```

实现方式：

- 每个节点和边都带 `data-task-id` 属性
- 点击事件通过事件委托绑定在容器上
- 高亮和降低透明度通过 CSS class 切换：`.topology-dimmed` 降低非相关元素的 opacity，`.topology-highlight` 高亮相关元素和边
- 信息面板是 DOM 元素，点击时填充内容并显示

### B.4 与现有 graph-view 的关系

**结论：不复用，单独实现，但共存。**

理由分析：

| 维度 | 现有 graph-view | 新拓扑图 |
|------|---------------|---------|
| 数据源 | 协商过程中的实时事件（agent 列表、offer 到达） | 协商完成后的 plan_json |
| 展示时机 | 协商进行中 | 协商完成后 |
| 布局 | 径向（需求在中心，agent 在圆周） | 层级（任务 DAG 从左到右） |
| 节点含义 | Agent 身份 | Task 分配 |
| 用途 | 展示"谁在参与" | 展示"谁做什么，什么顺序" |

现有 `renderGraphView()`（第 609-692 行）展示的是**协商过程**的参与者拓扑 -- 需求在中心，agent 在圆周，Center 出现后连线。这是"谁在参与"的视图。

新拓扑图展示的是**协商结果**的协作拓扑 -- 任务之间的依赖和分配。这是"谁做什么"的视图。

两者在时间轴上是串行的（先有过程，后有结果），在功能上是互补的。

**建议的共存方案**：在 `plan-section` 内部新增一个 topology 容器：

```html
<div id="plan-section">
  <div id="plan-topology"></div>   <!-- 新：拓扑图 -->
  <div id="plan-text-fallback"></div>  <!-- 纯文本回退 -->
  <div id="plan-participants"></div>
</div>
```

---

## C. 实施路径

### Phase 1: Mock 数据 + 前端拓扑图（可立即开始，不依赖后端）

**可以先做什么**：

1. 在 `app.js` 中定义一个 mock `plan_json` 常量
2. 实现 `renderTopology(planJson)` 函数：拓扑排序 + 层级布局 + SVG 渲染 + 节点 DOM
3. 实现点击交互：高亮/信息面板
4. 改造 `showPlan()` 函数：检测 `plan_json` 存在时调用 `renderTopology()`，否则显示纯文本

**交付标准**：使用 mock 数据渲染出完整的拓扑流程图，点击节点能高亮并显示详情。

**依赖**：无。完全前端独立工作。

### Phase 2: 后端 output_plan 结构化（改动范围评估）

**center.py 改动**：

改动范围：小。具体是：
- 修改 `TOOL_OUTPUT_PLAN` 字典（约 40 行新增）
- 修改 `SYSTEM_PROMPT_ZH` 和 `SYSTEM_PROMPT_EN`（各增加约 15 行 prompt 文本）
- 不需要改 `_validate_output()` -- 它只验证 tool_name 合法性和 arguments 是 dict，不验证内部结构

**engine.py 改动**：

改动范围：小。具体是：
- `_finish_with_plan()` 方法需要接收并传递 `plan_json` 参数（约 5 行改动）
- `_run_synthesis()` 中 `output_plan` 分支需要从 `tool_args` 提取 `plan_json`（1 行）
- 轮次限制的 forced output 分支也需要同样处理（2 行）

**events.py 改动**：

改动范围：极小。`plan_ready()` 工厂函数增加 `plan_json: dict | None = None` 参数，在 data 字典中增加一个字段。

**schemas.py 改动**：

改动范围：极小。`PlanResponse` 增加 `plan_json: Optional[dict] = None`。

**总体评估**：后端改动量约 60-80 行代码（含 prompt 文本），不影响任何现有测试的通过（additive change）。

### Phase 3: 渐进式回退策略

这是整个设计中最重要的安全网：

```javascript
// showPlan() 改造后的逻辑
function showPlan(text, participants, planJson) {
    document.getElementById('plan-section').style.display = 'block';
    
    if (planJson && planJson.tasks && planJson.tasks.length > 0) {
        // 结构化渲染
        document.getElementById('plan-topology').style.display = 'block';
        document.getElementById('plan-text-fallback').style.display = 'none';
        renderTopology(planJson, participants);
    } else {
        // 纯文本回退
        document.getElementById('plan-topology').style.display = 'none';
        document.getElementById('plan-text-fallback').style.display = 'block';
        document.getElementById('plan-text').textContent = text;
    }
    
    // 参与者标签始终显示
    if (participants && participants.length > 0) {
        renderParticipants(participants);
    }
    
    document.getElementById('plan-section').scrollIntoView({ behavior: 'smooth' });
}
```

`handleEvent()` 中 `plan.ready` 分支的改动（第 525-531 行）：

```javascript
case 'plan.ready':
    showPlan(
        data.plan_text || '',
        null,                    // participants 从 pollStatus 获取
        data.plan_json || null   // 新增：结构化数据
    );
    // ... rest unchanged
```

这样即使 LLM 没有输出 `plan_json`，或者 `plan_json` 结构不完整（缺少 tasks），系统都会优雅地回退到纯文本显示。

### 实施顺序总结

```
Phase 1（前端，独立）
  ├── 定义 mock plan_json
  ├── 实现拓扑排序 + 层级布局
  ├── 实现 SVG + DOM 渲染
  ├── 实现点击交互
  └── 改造 showPlan() 增加回退逻辑

Phase 2（后端，独立于 Phase 1）
  ├── center.py: 扩展 TOOL_OUTPUT_PLAN schema
  ├── center.py: 更新 prompt
  ├── events.py: plan_ready() 增加 plan_json
  ├── engine.py: _finish_with_plan() 传递 plan_json
  ├── schemas.py: PlanResponse 增加字段
  └── models.py: 考虑 session.plan_json 持久化

Phase 3（集成）
  ├── 前端 handleEvent 消费真实 plan_json
  ├── 端到端测试：发起协商 → 收到结构化 plan → 渲染拓扑图
  └── 回退测试：LLM 不输出 plan_json 时 → 纯文本显示
```

### 风险矩阵

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| LLM 输出的 plan_json 不符合 schema | 中 | 低 -- 回退到纯文本 | Claude tool-use 模式对 schema 遵从性高；前端做防御性检查 |
| plan_json 中 agent_id 与 participants 不匹配 | 中 | 低 -- 渲染时用 fallback 名字 | Prompt 明确要求使用上下文中的 agent_id |
| tasks 构成有环（非 DAG） | 低 | 中 -- 拓扑排序失败 | 前端检测环路，发现环路时回退纯文本 |
| 破坏现有 190 个测试 | 极低 | 高 | 所有改动是 additive -- 新增字段有默认值 None |
| 改变协议层契约 | 无 | N/A | plan.ready 事件增加 optional 字段不改变已有字段的语义 |

### 关键架构对齐点

1. **"代码保障 > Prompt 保障"**：拓扑排序、环路检测、回退逻辑全部用代码实现，不依赖 LLM 输出正确的拓扑。
2. **"协议层不可改，基础设施层可替换"**：plan.ready 事件的已有字段（plan_text, center_rounds, participating_agents）不变，plan_json 是新增 optional 字段。不改变协议。
3. **"事件全量推送，产品层自选展示"**：plan_json 包含在事件中全量推送，前端决定是渲染拓扑图还是纯文本。完全符合这个原则。
4. **"场景即产品"**：不同场景的前端可以对同一个 plan_json 做不同的展示 -- 黑客松场景强调团队组合，招聘场景强调匹配度。Schema 是通用的，展示是场景特定的。