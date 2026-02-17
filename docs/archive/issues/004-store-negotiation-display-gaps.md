# Issue 004: App Store 协商展示层缺陷（4 项）

**发现日期**: 2026-02-12
**影响范围**: App Store 协商展示层（前端 + API 响应）
**严重程度**: High — 协商能跑但用户看不到完整效果
**状态**: 问题 1/3/4 已修复，问题 2 需本地验证
**关联**: Feature 001 (streaming), docs/app-store-evolution-plan.md (Track B2/C)

---

## 问题清单

### 问题 1: 只有 8 个 Agent 响应

**根因**: 硬编码 `k_star = min(len(candidate_ids), 8)`

| 文件 | 行号 | 代码 |
|------|------|------|
| `apps/app_store/backend/routers.py` | 518 | `"k_star": min(len(candidate_ids), 8)` |
| `apps/app_store/backend/app.py` | 522 | `"k_star": min(len(candidate_ids), 8)` |

不管网络中有多少 agent，共振检测最多只返回 8 个。这是开发期的安全值，从未放开。

**修复**: 去掉 8 的上限，改为 `len(candidate_ids)`。

**已修**: `routers.py:518` 已改为 `len(candidate_ids)`（2026-02-12）。`app.py:522` 待改。

### 问题 2: 流式输出"不流式"

前端代码链完整：`DemandInput.tsx:78-84` → `assistDemandStream()` → `onChunk` → `setText(accumulated)`。
后端 SSE `_sse_generator()` 也正确。

**可能原因**:

1. **Next.js rewrite 缓冲 SSE** — Feature 001 文档自己标记了这个风险（`docs/features/001-assist-demand-streaming.md` line 96/172 "待验证"）
2. **SecondMe API 一次性返回所有内容**，没有真正的 chunk-by-chunk 流

**诊断方法**: 本地启动后端，观察 `_sse_generator()` 的 log 是否逐 chunk yield。如果后端是逐个 yield 的，问题在 Next.js 代理层。

### 问题 3: 方案不可见（plan_json 断链）

**根因**: `NegotiationResponse` 缺少 `plan_json` 字段

```python
# routers.py:68-77
class NegotiationResponse(BaseModel):
    negotiation_id: str
    state: str
    demand_raw: str
    demand_formulated: Optional[str] = None
    participants: list[dict[str, Any]] = Field(default_factory=list)
    plan_output: Optional[str] = None     # ← 有 plan_output
    center_rounds: int = 0
    scope: str = "all"
    agent_count: int = 0
    # ← 没有 plan_json！
```

GET 端点 (`routers.py:559-568`) 只返回 `plan_output`，不返回 `plan_json`：

```python
return NegotiationResponse(
    ...
    plan_output=session.plan_output,  # ← 只有这个
    # plan_json 没传
)
```

**数据流断裂分析**:

```
Engine (_finish_with_plan)
  ↓ session.plan_json = plan_json     ← engine 写了
  ↓ session.plan_output = plan_text   ← engine 写了

WebSocket event (plan.ready)
  ↓ event.plan_json = plan_json       ← 可能传了（取决于 event pusher）
  ↓ 前端 useStoreNegotiation.ts:206-208 能收到

GET /store/api/negotiate/{neg_id}
  ↓ NegotiationResponse               ← 没有 plan_json 字段
  ↓ 前端 negotiation?.plan_json       ← 永远是 null
```

**前端期望** (`website/lib/store-api.ts:64-65`):
```typescript
plan_output: string | null;
plan_json: Record<string, unknown> | null;
```

**前端消费** (`useStoreNegotiation.ts:320-321`):
```typescript
planOutput: negotiation?.plan_output || null,
planJson: planJson || negotiation?.plan_json || null,  // WS 优先，GET fallback
```

两条路径：
- **WebSocket `plan.ready` 事件** → 前端能拿到 `plan_json`（如果事件包含的话）
- **轮询 `getNegotiation()`** → 永远拿不到 `plan_json`（后端没返回）

**修复**: `NegotiationResponse` 加 `plan_json` 字段，GET 端点传 `session.plan_json`。

### 问题 4: 图谱缺动画、内容截断

| 位置 | 问题 | 值 |
|------|------|------|
| `NegotiationProgress.tsx:370` | Agent 名字截断 | `name.substring(0, 3) + '..'`（仅显示 4 个字） |
| `useStoreNegotiation.ts:155` | Offer 内容截断 | 200 字 |
| `NegotiationProgress.tsx` RadialGraphView | 动画 | 只有 agent 节点有 `transition: 'all 0.3s'`，边和 Center 节点无动画，无进入动画 |

**修复方向**: 放宽截断、加 CSS animation。

---

## 对照规划的反思

| 规划项 | 状态 | 问题 |
|--------|------|------|
| Track B2: plan_json 双轨输出 | 部分完成 | Response model 没加 plan_json，GET 端点没返回 |
| Track C: 拓扑可视化 | 已实现 | TopologyView 存在但需要 plan_json 数据，数据没过来 |
| Track A: 功能迁移 | 已完成 | NegotiationProgress 的图谱是简化版 RadialGraph，不是规划里的 TopologyView |
| k_star 上限 | 规划未提及 | 写死 8 是开发时安全值，从未放开 |

**核心问题**: Track B2 的"最后一公里"没接上 — engine 在生成 plan_json，但 response model 和 GET 端点没传给前端。

---

## 修复计划

所有修复都是实现层（≤3 文件，无契约变更），走快速通道。

1. **问题 1 (k_star)**: `app.py:522` 去掉 8 上限（`routers.py` 已修）
2. **问题 3 (plan_json)**: `NegotiationResponse` 加 `plan_json` 字段 + GET 端点传值
3. **问题 4 (截断/动画)**: 放宽截断阈值 + 加 CSS animation
4. **问题 2 (streaming)**: 需本地验证，如为 Next.js 层问题则加 API Route 代理

## 修复记录

### 2026-02-12: 问题 1 修复 — k_star 去掉上限

- `routers.py:518`: `min(len(candidate_ids), 8)` → `len(candidate_ids)`
- `app.py:522`: 同上

### 2026-02-12: 问题 3 修复 — plan_json 传到前端

- `routers.py` `NegotiationResponse` 加 `plan_json: Optional[dict[str, Any]] = None`
- GET `/store/api/negotiate/{neg_id}` 端点加 `plan_json=session.plan_json`

### 2026-02-12: 问题 4 修复 — 截断放宽 + 动画 + 展开

**改动文件**: `NegotiationProgress.tsx`, `useStoreNegotiation.ts`

- Agent 名字截断从 4 字放宽到 8 字（hover 可看全名）
- Offer 内容保持 200 字预览，新增"展开全部/收起"按钮查看完整内容
- `TimelineEntry` 新增 `fullDetail?: string` 字段
- CSS animation: Agent 节点 `nodeAppear`（缩放淡入）+ 连线 `lineGrow`（描边动画）+ Center 节点 `centerPulse`（脉冲）
- 连线加 `transition: stroke, stroke-width` 响应状态变化
