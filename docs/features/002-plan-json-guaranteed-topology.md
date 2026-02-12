# Feature 002: plan_json 强制保障 + TopologyView 永不退化

**日期**: 2026-02-12
**状态**: 已实现
**关联**: Issue 004 (展示层缺陷), docs/app-store-evolution-plan.md Track B2/C3
**原则**: 代码保障 > Prompt 保障 (Section 0.5)

---

## 功能概述

协商完成后的方案**永远以拓扑图谱（TopologyView）形式展示**，不退化为纯文本。

通过三层防线保证 `plan_json` 永不为 None：
1. **Prompt 层**：强制 LLM 生成 plan_json（软保障）
2. **Code 提取层**：从 plan_text 中提取 JSON 结构（中等保障）
3. **Code 构造层**：从 session 数据构造最小 plan_json（硬保障）

## 设计哲学

> 投影是基本操作（Section 0.8）— plan_json 是协商结果的投影，总是能被投影出来，只是精度不同。

当前的 `isTopologyPlan()` 守卫意味着：LLM 不生成 plan_json → 退化成纯文本 → TopologyView 永远不触发。这违反了"代码保障 > Prompt 保障"原则——我们把展示质量完全交给了 LLM 的遵从度。

正确做法：**不管 LLM 输出什么，代码都能提取/构造出合法的 plan_json**。

---

## 改动清单

### 后端

| 文件 | 改动 | 类型 |
|------|------|------|
| `backend/towow/skills/center.py:102` | `required` 加 `plan_json` | Prompt 强化 |
| `backend/towow/skills/center.py:216-225` | 中文 prompt 强调"必须" | Prompt 强化 |
| `backend/towow/skills/center.py:259-269` | 英文 prompt 强调"MUST" | Prompt 强化 |
| `backend/towow/core/engine.py:_finish_with_plan()` | 三层防线 | 代码保障 |
| `backend/towow/core/engine.py` | 新增 `_extract_plan_json()` | 代码保障 |
| `backend/towow/core/engine.py` | 新增 `_build_minimal_plan_json()` | 代码保障 |

### 前端

| 文件 | 改动 | 类型 |
|------|------|------|
| `website/components/store/PlanOutput.tsx` | 去掉纯文本退化，永远渲染 TopologyView | UI |
| `website/components/store/PlanOutput.tsx` | 新增 `ensureTopologyPlan()` 前端兜底 | 防御性编程 |

---

## 三层防线详解

### 第一层：Prompt + Tool Schema（软保障）

Center Skill 的 `output_plan` tool：
- `required` 从 `["plan_text"]` → `["plan_text", "plan_json"]`
- Prompt 从"同时提供"→"**必须同时提供，plan_json 是必需的**"

这让 LLM 在绝大多数情况下会生成 plan_json。但 LLM 不保证 100% 遵从。

### 第二层：从 plan_text 提取 JSON（中等保障）

如果 plan_json 为空或不合法，扫描 plan_text 寻找嵌入的 JSON：

```python
def _extract_plan_json(self, plan_text: str) -> Optional[dict]:
    """从 plan_text 中提取看起来像 plan_json 的 JSON 块。"""
    # 找所有 { ... } 块，从最长的开始尝试
    # json.loads 解析
    # 验证有 tasks[] 和 participants[]
    # 返回第一个合法的，或 None
```

### 第三层：从 session 数据构造（硬保障）

如果提取也失败，从 session 已有数据构造最小 plan_json：

```python
def _build_minimal_plan_json(self, session) -> dict:
    """从 session.participants 构造最小但合法的 plan_json。"""
    participants = []
    tasks = []
    for i, p in enumerate(session.participants):
        if p.state == AgentState.REPLIED:
            participants.append({
                "agent_id": p.agent_id,
                "display_name": p.display_name,
                "role_in_plan": "参与者",
            })
            tasks.append({
                "id": f"task_{i+1}",
                "title": p.display_name + " 的贡献",
                "description": (p.offer.content[:100] + "...") if p.offer else "",
                "assignee_id": p.agent_id,
                "prerequisites": [],
                "status": "pending",
            })
    return {
        "summary": session.demand.formulated_text or session.demand.raw_intent,
        "participants": participants,
        "tasks": tasks,
        "topology": {"edges": []},
    }
```

结果：每人一个 task、无依赖关系、平行排列。不漂亮，但 TopologyView 能渲染。

---

## 全链路数据流

```
Center LLM 调用
│
├─ tool_call: output_plan({plan_text, plan_json})
│  plan_json 可能存在（LLM 遵从），可能为 None（LLM 不遵从）
│
├─ engine.py:665-669 提取 tool_args
│  plan_text = tool_args.get("plan_text", "")
│  plan_json = tool_args.get("plan_json")   ← 可能为 None
│
├─ engine.py:_finish_with_plan()  ← 【三层防线】
│  ├─ plan_json 合法（有 tasks[]）？→ 直接用
│  ├─ 否 → _extract_plan_json(plan_text) → 提取到？用它
│  └─ 否 → _build_minimal_plan_json(session) → 构造兜底
│  ↓
│  session.plan_json = plan_json  ← 永不为 None
│
├─ plan_ready 事件 (plan_json=plan_json) → WebSocket 推送
├─ GET /store/api/negotiate/{neg_id} → plan_json=session.plan_json
│
├─ 前端 useStoreNegotiation
│  planJson: planJson || negotiation?.plan_json || null
│
├─ PlanOutput.tsx
│  planJson = ensureTopologyPlan(planJson, participants)  ← 前端最后防线
│  ↓
└─ TopologyView 渲染（永远）
```

---

## 前端改动详解

### PlanOutput.tsx

```
之前:
  isTopologyPlan(planJson)
    ? <TopologyView planJson={planJson} />
    : <div style={...}>{planText}</div>     ← 纯文本退化

之后:
  <TopologyView planJson={ensureTopologyPlan(planJson, participants)} />
  ← 永远 TopologyView
```

`ensureTopologyPlan(planJson, participants)`:
- planJson 有 tasks[] 且长度 > 0？直接返回
- 否则从 participants 构造最小版本（镜像后端第三层逻辑）
- 保证返回值符合 TopologyViewProps['planJson'] 类型

---

## 不改的文件

| 文件 | 原因 |
|------|------|
| `events.py` | plan_ready 事件格式不变 |
| `models.py` | plan_json 类型不变（Optional[dict]，运行时永不 None） |
| `routers.py` | GET 端点已传 plan_json（Issue 004 已修） |
| `useStoreNegotiation.ts` | 接收逻辑不变 |
| `TopologyView.tsx` | 渲染逻辑不变 |
| `topology-layout.ts` | 算法不变 |

---

## 关键文件索引

| 文件 | 说明 |
|------|------|
| `backend/towow/skills/center.py:32-103` | output_plan tool schema |
| `backend/towow/skills/center.py:189-231` | 中文 system prompt |
| `backend/towow/skills/center.py:233-272` | 英文 system prompt |
| `backend/towow/core/engine.py:665-669` | tool_call 提取 plan_json |
| `backend/towow/core/engine.py:749-761` | forced plan 提取（轮次限制） |
| `backend/towow/core/engine.py:959-994` | _finish_with_plan() |
| `website/components/store/PlanOutput.tsx:14-70` | isTopologyPlan 守卫 + 渲染 |
| `website/components/store/TopologyView.tsx:46` | TopologyView 组件 |
| `website/lib/topology-layout.ts` | Kahn 拓扑排序算法 |
