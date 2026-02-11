# App Store 产品架构分析

## 1. App Store 的本质是什么

### 本质判断

当前 App Store 的代码形态是一个**协商演示页**。它做了三件事：展示 Agent 列表、发起协商、展示纯文本方案。但它应该是什么？

回到 Section 13 的核心洞察：**协商单元是通用引擎，场景定义是唯一的差异化。** App Store 的本质不是"应用商店"——它是**通爻网络的第一个客户端**，是响应范式的体验入口。用户进来不是来"逛店"的，是来**发出信号、观察共振、获取协作方案**的。

当前缺失的产品能力：

| 能力 | 当前状态 | 应有状态 |
|------|---------|---------|
| 网络感知 | 静态 Agent 卡片列表 | 实时网络拓扑，能看到谁在线、谁在协商、共振场的活跃度 |
| 方案可执行 | `plan_output` 是纯文本字符串 | 结构化方案：参与者、任务、依赖关系、时间线、可操作的下一步 |
| 协作拓扑 | 径向图只展示"谁参与了" | 流程图：节点=参与者，边=依赖/协作关系，点击看任务详情 |
| 用户闭环 | 方案输出即结束 | 方案 -> 确认 -> 执行跟踪（即使 V1 只是"标记已完成"） |
| 场景身份 | 4 个场景共享同一个页面，tab 切换 | 4 个场景应有各自的视觉身份和交互模式 |

### 工程建议

App Store 需要从"单页协商 Demo"升级为"场景化网络客户端"。但升级路径的关键约束是：**协议层不改，能力层可扩展，应用层自由变化。** 当前的改造应该集中在应用层和能力层的接缝处——即 `output_plan` 的结构化。

---

## 2. 场景即产品的工程含义

### 本质判断

4 个场景（黑客松组队、技能交换、智能招聘、AI相亲）共享的是**协商单元引擎**（状态机、共振、Offer 收集、Center 综合），独立的是**场景上下文**（谁参与、需求怎么表达、结果怎么展示）。

当前代码已经做了一层分离——`SCENE_DISPLAY` 配置对象定义了每个场景的颜色、字段高亮、标签来源。但这只是展示层的配置，不是产品层的分离。

### 共享什么 vs 独立什么

**共享（协议层+基础设施层，已有）**：
- 状态机（8 个状态）
- 事件协议（7 种事件）
- 共振机制（HDC 编码 + cosine 检测）
- Center 工具集（5 个工具）
- WebSocket 实时推送

**独立（产品层，需要做）**：

| 维度 | 黑客松组队 | 技能交换 | 智能招聘 | AI 相亲 |
|------|-----------|---------|---------|---------|
| 入口叙事 | "48小时，你需要什么队友？" | "你能教什么？想学什么？" | "你在找什么样的人？" | "描述你理想中的..." |
| Agent 卡片重点 | 技术栈、黑客松经历、时间可用性 | 能教的技能、想学的技能、价格 | 工作经验、薪资期望、位置 | 年龄、性格、价值观 |
| 方案展示 | 团队阵容图 + 分工 | 配对关系 + 交换计划 | 候选人排名 + 匹配理由 | 推荐列表 + 契合度分析 |
| Center 上下文 | "技术互补性优先" | "双向匹配度优先" | "经验与岗位匹配优先" | "价值观契合度优先" |
| 结果形态 | 一个团队（多对多） | 配对（一对一或小组） | 排序列表 | 推荐列表 |

### 工程建议

当前的 `SceneContext` (`/Users/nature/个人项目/Towow/apps/app_store/backend/app.py` 中的 `SAMPLE_APPS`) 已经有 `priority_strategy` 和 `domain_context` 字段，但这些字段目前在协商中**没有被注入到 Center**。代码中有明确的 TODO 注释：

```python
# TODO: 场景上下文注入 — 当 Center skill 支持 context 参数时启用
# 目前 scene_context 暂不注入，等 Center skill 支持后再接入
```

**现在就能做**：
- 前端：每个场景独立的入口 URL（`/store/hackathon`、`/store/skill-exchange`），用同一个 SPA 但根据 URL 切换场景主题和布局
- 前端：`SCENE_DISPLAY` 配置扩展，加入方案展示逻辑的差异化

**需要后端改动**：
- Center skill 的 `_build_prompt` 方法接受 `scene_context` 参数，将场景的 `priority_strategy` 和 `domain_context` 注入到 system prompt 中
- 这是能力层改动，不触及协议层

**不需要协议层改动**：
- 场景上下文通过 Center 的 system prompt 注入，是 Skill 实现细节，不改变事件语义或状态机

---

## 3. Machine JSON vs 纯文本

### 本质判断

当前 Center 的 `output_plan` 工具定义（`/Users/nature/个人项目/Towow/backend/towow/skills/center.py`）：

```python
TOOL_OUTPUT_PLAN = {
    "name": "output_plan",
    "input_schema": {
        "type": "object",
        "properties": {
            "plan_text": {
                "type": "string",
                "description": "The complete plan text...",
            }
        },
        "required": ["plan_text"],
    },
}
```

只有一个 `plan_text` 字符串字段。前端 `showPlan()` 函数直接 `textContent = text`。整个链路是纯文本管道。

要支持协作拓扑可视化和结构化方案，`output_plan` 需要输出结构化 JSON。但这里有一个重要的架构判断：

**改 `output_plan` 的 schema 是改契约还是改实现？**

分析 `output_plan` 的依赖图：
1. `center.py` 中的 `TOOL_OUTPUT_PLAN` 定义 schema —— Skill 层
2. `engine.py` 中的 `_finish_with_plan` 只取 `plan_text` 字符串 —— 引擎层
3. `NegotiationSession.plan_output` 是 `Optional[str]` —— 模型层
4. `events.py` 中的 `plan_ready` 事件推送 `plan_text` —— 事件层
5. App Store 后端 `NegotiationResponse.plan_output` 是 `Optional[str]` —— API 层
6. 前端 `showPlan(text)` —— 展示层

这是一条 6 层的数据管道，从 LLM 输出到用户眼睛。改 `plan_text` 从字符串变为结构化 JSON，需要同步修改**所有 6 层**。

### 结构化方案的数据结构

```python
# 方案一：兼容方案（推荐 V1）
# plan_text 保持字符串，但 output_plan 新增可选的 plan_structured 字段
TOOL_OUTPUT_PLAN = {
    "name": "output_plan",
    "input_schema": {
        "type": "object",
        "properties": {
            "plan_text": {
                "type": "string",
                "description": "The complete plan text (human-readable summary).",
            },
            "plan_structured": {
                "type": "object",
                "description": "Structured plan data (optional, for visualization).",
                "properties": {
                    "participants": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "agent_id": {"type": "string"},
                                "role": {"type": "string"},
                                "tasks": {"type": "array", "items": {"type": "string"}},
                            }
                        }
                    },
                    "dependencies": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from_agent": {"type": "string"},
                                "to_agent": {"type": "string"},
                                "relationship": {"type": "string"},
                            }
                        }
                    },
                    "phases": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "agent_ids": {"type": "array", "items": {"type": "string"}},
                                "description": {"type": "string"},
                            }
                        }
                    }
                }
            }
        },
        "required": ["plan_text"],
    },
}
```

### 影响范围分析

| 层 | 文件 | 改动量 | 是否破坏性 |
|----|------|--------|-----------|
| Skill 层 | `backend/towow/skills/center.py` | 修改 `TOOL_OUTPUT_PLAN` schema + system prompt 要求输出结构化 | 非破坏性（`plan_structured` 是可选字段） |
| 引擎层 | `backend/towow/core/engine.py` | `_finish_with_plan` 需要传递完整 tool_args（不只是 plan_text） | 小改动 |
| 模型层 | `backend/towow/core/models.py` | `NegotiationSession.plan_output` 从 `Optional[str]` 变为 `Optional[dict]` 或新增 `plan_structured` 字段 | 需要审慎，因为 190 个测试依赖此模型 |
| 事件层 | `backend/towow/core/events.py` | `plan_ready` 事件增加 `plan_structured` 字段 | 向后兼容（新增字段） |
| API 层 | `apps/app_store/backend/app.py` | `NegotiationResponse` 增加 `plan_structured` 字段 | 向后兼容 |
| 前端 | `apps/app_store/frontend/app.js` | `showPlan` 函数解析结构化数据并渲染拓扑图 | 主要工作量 |

### 工程建议

**推荐方案：向后兼容的双轨输出**。`plan_text` 保持字符串（人类可读摘要），新增 `plan_structured` 可选字段（机器可读结构）。这样：
- 现有测试不受影响（它们只检查 `plan_text`）
- 旧的前端（如果还有其他客户端）只看 `plan_text`，不会崩溃
- 新的前端可以利用 `plan_structured` 渲染拓扑图

**不需要协议层改动**：`plan.ready` 事件语义不变（"方案已就绪"），只是数据字段更丰富。这是能力层（Skill prompt 引导 LLM 输出结构化 JSON）和应用层（前端渲染）的改动。

**风险**：LLM 不一定能可靠输出复杂的结构化 JSON。需要在 Skill 层做校验和 fallback——如果 `plan_structured` 解析失败，退化为纯文本。这符合"代码保障 > Prompt 保障"原则。

---

## 4. 协作拓扑可视化

### 本质判断

当前的图谱视图（`renderGraphView` 函数，`/Users/nature/个人项目/Towow/apps/app_store/frontend/app.js` 第 609-692 行）是一个简单的径向布局：需求在中心，Agent 在圆周上，线表示"参与了"。这只是参与关系图，不是协作拓扑。

真正的协作拓扑应该回答三个问题：
1. **谁做什么** —— 每个参与者的角色和任务
2. **谁依赖谁** —— 任务之间的依赖关系（先后、阻塞、协同）
3. **过程怎么走** —— 阶段划分，哪些并行、哪些串行

### 数据结构需求

拓扑可视化需要 `plan_structured` 提供的数据。最小可用数据结构：

```json
{
  "participants": [
    {
      "agent_id": "agent_xxx",
      "display_name": "Alice",
      "role": "前端开发",
      "avatar_color": "#F9A87C",
      "tasks": ["UI 设计", "React 组件开发", "与后端联调"]
    }
  ],
  "dependencies": [
    {
      "from": "agent_xxx",
      "to": "agent_yyy",
      "type": "depends_on",
      "label": "API 接口定义后开始"
    }
  ],
  "phases": [
    {
      "name": "第一阶段：原型",
      "agent_ids": ["agent_xxx", "agent_yyy"],
      "duration": "Day 1"
    }
  ]
}
```

### 前端实现方案

**方案 A：纯 SVG 手写（推荐 V1）**

当前已经有 SVG 图谱基础（`graph-svg` 元素）。扩展为力导向图或分层图：
- 节点 = 参与者头像（圆形，带名字和角色标签）
- 边 = 依赖关系（有向箭头，带标签）
- 点击节点 = 展开任务面板（overlay 或 side panel）
- 阶段用背景色区域表示

优点：零依赖，与当前架构一致，加载快。
缺点：复杂交互（拖拽、缩放）需要自己实现。

**方案 B：引入轻量图库（如 D3-force 或 elkjs）**

优点：自动布局算法成熟，交互丰富。
缺点：增加依赖，与当前纯原生 JS 架构不一致。

**方案 C：React Flow（如果迁移到 Next.js 的 /store 路由）**

优点：节点自定义、交互丰富、生态成熟。
缺点：需要将 App Store 从独立 HTML 迁移到 Next.js 组件。

### 工程建议

**现在就能做（无后端改动）**：改进现有 SVG 图谱，在 `plan.ready` 事件中解析 participants 数据（现有 `pollStatus` 返回的 `data.participants` 已经有 `agent_id`、`display_name`、`resonance_score`），渲染更丰富的完成态图。

**需要后端改动**：结构化 `output_plan`（如第 3 点分析），前端基于 `plan_structured` 渲染依赖图。

**推荐 V1 路径**：方案 A（纯 SVG），数据来自结构化 plan。手写一个简单的分层布局算法（阶段从左到右，同一阶段的参与者从上到下），不需要力导向。控制复杂度。

---

## 5. 品牌感：4 个场景如何看起来像 4 个产品

### 本质判断

当前的 App Store 是一个单页应用，4 个场景是同一页面的 scope 过滤器。切换场景只改变了 Agent 列表和 placeholder 文字。视觉上没有任何差异化。

让 4 个场景"看起来像 4 个产品"，有两个层次的策略：

**表层策略（视觉差异化）**：
- 不同的主色调（已有 `SCENE_ACCENTS`，但没用在页面整体上）
- 不同的 Hero 文案
- 不同的 Agent 卡片布局（招聘强调经验年限，黑客松强调技术栈）
- 不同的方案展示模板

**深层策略（产品身份差异化）**：
- 每个场景有独立的 URL（`/hackathon`、`/skill-exchange`、`/recruit`、`/matchmaking`）
- 每个场景有独立的着陆页（不是进入 App Store 后再切换）
- 每个场景的叙事完全不同——用户感知不到"这是同一个系统的 4 个 tab"

### 工程建议

**现在就能做（纯前端改动）**：

1. **路由化**：给每个场景一个独立 URL path。由 `index.html` + `app.js` 在 `DOMContentLoaded` 时根据 `window.location.pathname` 决定初始 scope 和主题。例如：
   - `/store/` → 全网总览（当前页面）
   - `/store/hackathon` → 自动 `switchScope('scene:hackathon')` 并应用黑客松主题
   - `/store/skill-exchange` → 自动应用技能交换主题

2. **主题系统**：用 CSS 变量实现场景主题。每个场景定义一组 CSS 变量（`--scene-primary`、`--scene-bg`、`--scene-accent`），切换场景时修改 `document.documentElement.style`。

3. **布局差异化**：Agent 卡片的 `renderAgents` 函数根据当前 scene 使用不同模板。`SCENE_DISPLAY` 配置中已经有 `highlight` 和 `tagSource` 函数，但 `renderAgents` 只用了 `skills[0]` 作为标签。应该用 `getSceneConfig().tagSource(agent)` 和 `getSceneConfig().highlight(agent)` 渲染更丰富的卡片。

4. **Hero 区域差异化**：在场景模式下，header 的副标题（"说出你需要什么。能帮你的人，会自己出现。"）替换为场景特定的叙事。

**中期目标（需要架构决策）**：

是否将 App Store 从独立的 `apps/app_store/frontend/` 迁移到 Next.js `website/` 中？考量：
- 迁移后可以复用 Next.js 的路由系统、组件库、国际化、SSR
- 但增加了与 Next.js 版本的耦合
- 当前独立架构的优势是轻量、零依赖、可独立部署

我倾向于**暂不迁移**。App Store 的独立性符合"场景即产品"的哲学——每个产品可以有自己的技术栈。未来如果场景数量增长到 10+ 个，再考虑统一到 Next.js 的路由系统中。

---

## 实施优先级

按照"验证价值优先、改动范围从小到大"排序：

### 第一优先级：前端场景差异化（纯前端，0 后端改动）

1. **路由化 + 主题系统**：每个场景独立 URL + CSS 变量主题
2. **Agent 卡片差异化**：用 `SCENE_DISPLAY` 的 `highlight`/`tagSource` 渲染更丰富的卡片信息
3. **Hero 叙事差异化**：场景模式下的标题和副标题替换

这一步的价值：让用户感知到"这是 4 个不同的产品"，而不是"同一个页面的 4 个 tab"。

### 第二优先级：Center 场景上下文注入（小后端改动）

4. **修改 CenterCoordinatorSkill**：`_build_prompt` 接受 `scene_context` 参数，注入到 system prompt
5. **修改 App Store 后端**：将 `scene_context` 传入 engine 的 `start_negotiation`

这一步的价值：让不同场景的协商结果真正不同——黑客松的方案强调技术互补性，招聘的方案强调经验匹配度。

### 第三优先级：结构化方案输出（需要后端 + 前端改动）

6. **扩展 `output_plan` schema**：增加 `plan_structured` 可选字段
7. **修改 engine**：`_finish_with_plan` 传递完整 tool_args
8. **修改 models**：`NegotiationSession` 增加 `plan_structured` 字段
9. **修改 events**：`plan_ready` 事件携带 `plan_structured`
10. **修改 Center prompt**：引导 LLM 输出结构化 JSON + 纯文本摘要

这一步的价值：方案从"一段话"变成"可操作的结构化数据"，为拓扑可视化提供数据基础。

### 第四优先级：协作拓扑可视化（纯前端，依赖第三优先级）

11. **实现拓扑渲染**：基于 `plan_structured` 数据，用 SVG 渲染参与者节点 + 依赖边 + 阶段分区
12. **交互**：点击节点展示任务详情面板
13. **场景差异化展示**：黑客松显示团队阵容图，招聘显示候选人排名列表

这一步的价值：用户第一次能"看到"协作方案的拓扑结构，而不只是读一段文字。

### 不需要做的事（V1 阶段）

- 不需要改协议层（状态机、事件语义都不动）
- 不需要迁移到 Next.js（保持 App Store 的独立性）
- 不需要实现 `create_machine` 工具的真实 WOWOK 集成（V2+ 方向）
- 不需要实现场景即 Agent（HDC 空间中的场景投影，V2+ 探索方向）

---

### 关键路径总结

```
前端场景差异化 ──→ Center 上下文注入 ──→ 结构化方案输出 ──→ 拓扑可视化
  (纯前端)          (小后端改动)          (跨层改动)          (纯前端)
  ~1-2 天             ~0.5 天              ~2-3 天             ~2-3 天
```

最大的技术风险在第三优先级：LLM 能否可靠输出结构化 JSON。建议在实施前先做一个快速验证——手动修改 Center prompt，跑几次协商，看 Claude 输出的 JSON 结构是否稳定。如果不稳定，需要在 Skill 层加入 JSON 校验和修复逻辑（schema validation + fallback to text），这会增加约 1 天的工作量。